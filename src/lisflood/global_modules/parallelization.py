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
thread limits to all three pools: numba (``set_num_threads``), numexpr and the
BLAS/OpenMP backend. It is the single place that governs thread counts;
``Lisflood_initial`` simply calls :func:`configure_parallelism` once at startup.

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

# Last-applied effective thread counts, so the startup banner can report the
# same numbers that were actually applied (see get_effective_parallelism).
_effective = None


def get_effective_parallelism():
    """Return the last-applied effective thread counts, or None if parallelism
    has not been configured yet.

    The dict is keyed 'numba', 'numexpr', 'blas'; a value of None means
    "all available cores". Also includes 'host' (host core count).
    """
    return _effective


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
    """
    Return the number of logical CPUs that the current job is permitted to use.

    The routine recognises two common HPC workload managers:

    * **SLURM** – uses the environment variables
      `SLURM_TASKS_PER_NODE` (tasks per node) and `SLURM_CPUS_PER_TASK`
      (CPUs allocated to each task).  If only `SLURM_NTASKS` is defined
      (single‑node jobs without `--ntasks-per-node`), it is used as a fallback.

    * **PBS** – uses `PBS_NP` (total number of allocated CPUs) or,
      when a node‑wise layout is requested, the combination of
      `PBS_NUM_NODES` and `PBS_NUM_PPN` (processes per node).

    If none of the above variables are present, the function returns
    `os.cpu_count()` (the total logical cores on the node).

    The return value is always an ``int`` ≥ 1.
    """
    import os

    # --------------------------------------------------------------
    # 1. SLURM – most detailed information available
    # --------------------------------------------------------------
    try:
        # SLURM may expose a comma‑separated list when heterogeneous
        # allocations are used (e.g. "28(x2),14").
        tasks_per_node = os.getenv("SLURM_TASKS_PER_NODE")
        cpus_per_task  = os.getenv("SLURM_CPUS_PER_TASK")
        ntasks         = os.getenv("SLURM_NTASKS")          # fallback

        if tasks_per_node:
            # Keep the first numeric entry before any '(' or ','.
            first_entry = tasks_per_node.split(',')[0].split('(')[0]
            tasks_per_node = int(first_entry)
            cpus_per_task = int(cpus_per_task) if cpus_per_task else 1
            return max(1, tasks_per_node * cpus_per_task)

        if ntasks:
            # When only SLURM_NTASKS is set (e.g. a simple `srun` without
            # explicit per‑node control) we assume one CPU per task.
            return max(1, int(ntasks))
    except Exception:
        # Any parsing problem – fall through to the next detector.
        pass

    # --------------------------------------------------------------
    # 2. PBS
    # --------------------------------------------------------------
    try:
        # PBS_NP provides the total number of processors allocated to the job.
        pbs_np = os.getenv("PBS_NP")
        if pbs_np:
            return max(1, int(pbs_np))

        # When PBS_NP is not set, the classic layout variables can be used.
        # PBS_NUM_NODES = number of allocated nodes
        # PBS_NUM_PPN   = processes (CPUs) per node
        num_nodes = os.getenv("PBS_NUM_NODES")
        ppn       = os.getenv("PBS_NUM_PPN")
        if num_nodes and ppn:
            return max(1, int(num_nodes) * int(ppn))
    except Exception:
        pass

    # --------------------------------------------------------------
    # 3. Fallback – physical core count of the node
    # --------------------------------------------------------------
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
    global _blas_limiter, _effective

    # --- numba (soilloop + kinematic-wave/MCT routing kernels) ---
    # None means "leave numba at its default" (all cores); a concrete N caps it.
    numba_threads = resolve_numba_threads(binding, num_pixels)

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
        # Desired number of threads from the settings (None → “all cores”)
        target = numexpr_threads if numexpr_threads is not None else host

        # Hard limit imposed by NumExpr (defaults to 64 when the variable
        # is not defined).
        try:
            max_threads = int(os.getenv("NUMEXPR_MAX_THREADS"))
        except (TypeError, ValueError):
            max_threads = 64

        # Ensure a sensible value: ≥1, ≤ host cores and ≤ NumExpr limit.
        target = max(1, min(target, host, max_threads))

        # Apply and keep the environment variable in sync for any child
        # processes that might import numexpr later.
        try:
            numexpr.set_num_threads(target)
            os.environ["NUMEXPR_NUM_THREADS"] = str(target)
        except Exception:  # pragma: no cover - defensive
            pass

        # *** store the *effective* value that was really set ***
        effective_numexpr = target
    else:
        effective_numexpr = None

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
        "numba": numba_threads,       
        "numexpr": effective_numexpr,
        "blas": blas_threads,
        "host": host,
    }
    _effective = effective

    if verbose:
        def fmt(v):
            return "all" if v is None else str(v)
        print("[X] Parallelization: numba={}, numexpr={}, BLAS={} (host cores={})".format(
            fmt(numba_threads), fmt(effective_numexpr), fmt(blas_threads), host))

    return effective
