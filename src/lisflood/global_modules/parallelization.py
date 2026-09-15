"""
Centralized thread-pool governance for LISFLOOD.

Several numerical libraries used by LISFLOOD each spin up their own thread
pool sized to the host core count by default:

  * ``numba``   - the ``@njit(parallel=True)`` routing/soil kernels (``prange``).
  * ``numexpr`` - vectorized expressions in the kinematic-wave routing.
  * BLAS/OpenMP - backing ``numpy``/``scipy`` linear algebra (e.g. the SVD in
    the soil-hydraulics ``least_squares`` fit during initialization).

BLAS (Basic Linear Algebra Subprograms) is the low-level library that numpy and
scipy call under the hood for vector/matrix maths (dot products, matrix
multiply, SVD, least-squares, ...). The optimized implementations (OpenBLAS,
Intel MKL, BLIS) are multi-threaded and by default use one thread per CPU core.
Because the actual backend depends on how numpy was built, its thread count is
controlled through several implementation-specific environment variables
(``OMP_NUM_THREADS``, ``OPENBLAS_NUM_THREADS``, ``MKL_NUM_THREADS``,
``BLIS_NUM_THREADS``), which is why they are all set below.

On the domain sizes LISFLOOD typically runs (a single catchment has a
comparatively narrow river network and a modest pixel count), these pools do
not have enough independent work per call to amortize thread fork/join and
synchronization. Worse, they are *nested*: a numba-parallel section may call
into BLAS, and each library independently tries to use every core. The result
is heavy oversubscription - measured as ~1.5M context switches and ~5x more CPU
time than wall time on a benchmark catchment, while actually running *slower*
than a single-threaded execution.

This module reads a small set of settings and applies consistent, explicit
thread limits to numexpr and the BLAS/OpenMP pools. numba itself is configured
separately (``set_num_threads`` in ``Lisflood_initial``) using the same
``numCPUs_parallelNumba`` setting; this module reads that value only to derive
sensible defaults and to report a single coherent summary.

Thread counts affect performance only, never results: LISFLOOD discharge output
is bitwise-identical across thread configurations (verified on the test and Ob
benchmark catchments). Defaults are therefore chosen for speed on typical
single-catchment runs, and every knob can be raised by the user for large
domains.

Settings (all optional; read via ``binding.get`` so older settings files keep
working):

  * ``numCPUs_parallelNumba``   - existing setting; numba thread count.
                                   0 or "" => all cores; N => N threads.
  * ``numCPUs_parallelNumexpr`` - numexpr thread count. Default: 1
                                  (numexpr on the small routing arrays gives no
                                   speedup and causes oversubscription).
  * ``numCPUs_BLAS``            - BLAS/OpenMP thread count for numpy/scipy.
                                  Default: 1.

A value of 0 (or empty/"all") means "use all available cores".
"""

import os

# threadpoolctl can limit already-initialized BLAS/OpenMP pools at runtime,
# which is more robust than relying on environment variables being set before
# numpy is imported. It is an optional dependency: if unavailable we fall back
# to environment variables (best-effort).
try:
    import threadpoolctl
    _HAVE_THREADPOOLCTL = True
except ImportError:  # pragma: no cover - environment dependent
    _HAVE_THREADPOOLCTL = False

try:
    import numexpr
    _HAVE_NUMEXPR = True
except ImportError:  # pragma: no cover - numexpr is a hard dep but be defensive
    _HAVE_NUMEXPR = False

try:
    from numba import set_num_threads as _numba_set_num_threads
    from numba import config as _numba_config
    _HAVE_NUMBA_THREADCTL = True
except ImportError:  # pragma: no cover - older numba without set_num_threads
    _HAVE_NUMBA_THREADCTL = False


# Keep a reference to any threadpoolctl limiter so the applied BLAS limits are
# not garbage-collected (and thus reverted) during the model run.
_blas_limiter = None


def _parse_thread_count(value):
    """Interpret a settings value as a thread count.

    Returns an int >= 1, or None meaning "use all available cores".
    Accepts ints, numeric strings, empty string, and the literal "all".
    """
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip().lower()
        if value in ("", "all", "auto"):
            return None
        try:
            value = int(value)
        except ValueError:
            return None
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None  # 0 / negative => all cores
    return value


def _host_cpu_count():
    return os.cpu_count() or 1


def _resolve(binding, key, default):
    """Read a thread-count setting, falling back to a default when absent."""
    if binding is not None and key in binding and binding.get(key) not in (None, ""):
        return _parse_thread_count(binding.get(key))
    return default


# Below this many valid pixels, numba thread-parallelism (prange over the
# river network's topological orders) does not have enough independent work
# per batch to amortize fork/join, and running serially is faster. Measured on
# the Ob benchmark (~6,900 pixels): serial was faster than any threaded config.
# Only used when the user leaves numba on "auto" (numCPUs_parallelNumba=0).
NUMBA_AUTO_MIN_PIXELS = 50000


def resolve_numba_threads(binding, num_pixels=None):
    """Decide the numba thread count.

    * If the user set ``numCPUs_parallelNumba`` explicitly (>=1), honor it.
    * If it is 0/"auto" (the historical default meaning "all cores") and we
      know the domain size, auto-tune: use 1 thread for small domains where
      threading is pure overhead, otherwise all cores.
    * If the domain size is unknown, keep the historical "all cores" behavior.

    Returns an int >= 1, or None meaning "all available cores".
    """
    explicit = _resolve(binding, "numCPUs_parallelNumba", None)
    if explicit is not None:
        return explicit
    # auto mode
    if num_pixels is not None and num_pixels < NUMBA_AUTO_MIN_PIXELS:
        return 1
    return None


def configure_parallelism(binding, num_pixels=None, verbose=False):
    """Apply thread-pool limits for numba, numexpr and BLAS/OpenMP.

    numba's thread count is decided here (including the small-domain auto-tune)
    and applied via ``numba.set_num_threads``; it governs the soilloop and the
    kinematic-wave/MCT routing kernels.

    Parameters
    ----------
    binding : dict-like
        LISFLOOD settings binding. May be None (defaults are used).
    num_pixels : int or None
        Number of valid land pixels in the domain, used for numba auto-tune.
    verbose : bool
        If True, print a one-line summary of the applied thread counts.

    Returns
    -------
    dict
        The effective thread counts, keyed 'numba', 'numexpr', 'blas'
        (None means "all cores").
    """
    global _blas_limiter

    numba_threads = resolve_numba_threads(binding, num_pixels)

    # --- numba (soilloop + kinematic-wave/MCT routing kernels) ---
    # None means "leave numba at its default" (all cores); a concrete N caps it.
    if numba_threads is not None and _HAVE_NUMBA_THREADCTL:
        if 0 < numba_threads <= _numba_config.NUMBA_NUM_THREADS:
            _numba_set_num_threads(numba_threads)

    # numexpr and BLAS default to serial: on typical LISFLOOD domains their
    # pools cause oversubscription without a throughput benefit. Users can
    # raise these for large domains via the settings file.
    numexpr_threads = _resolve(binding, "numCPUs_parallelNumexpr", 1)
    blas_threads = _resolve(binding, "numCPUs_BLAS", 1)

    host = _host_cpu_count()

    # --- numexpr ---
    if _HAVE_NUMEXPR:
        target = numexpr_threads if numexpr_threads is not None else host
        # numexpr requires at least 1; cap at host cores.
        target = max(1, min(target, host))
        try:
            numexpr.set_num_threads(target)
            # Also set the env so any re-detection stays consistent.
            os.environ["NUMEXPR_NUM_THREADS"] = str(target)
        except Exception:  # pragma: no cover - defensive
            pass

    # --- BLAS / OpenMP (numpy, scipy) ---
    if blas_threads is not None:
        target = max(1, min(blas_threads, host))
        # Set env vars too (helps subprocesses and any pools not yet created).
        for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
                    "BLIS_NUM_THREADS"):
            os.environ[var] = str(target)
        if _HAVE_THREADPOOLCTL:
            try:
                # limit_num_threads returns a controller object; keep a ref so
                # the limits persist for the lifetime of the run.
                _blas_limiter = threadpoolctl.threadpool_limits(
                    limits=target, user_api="blas")
            except Exception:  # pragma: no cover - defensive
                _blas_limiter = None

    effective = {
        "numba": numba_threads,       # applied in Lisflood_initial
        "numexpr": numexpr_threads,
        "blas": blas_threads,
    }

    if verbose:
        def fmt(v):
            return "all" if v is None else str(v)
        print("[X] Parallelization: numba={}, numexpr={}, BLAS={} (host cores={})".format(
            fmt(numba_threads), fmt(numexpr_threads), fmt(blas_threads), host))

    return effective
