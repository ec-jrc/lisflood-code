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

  * ``numCPUs_parallelNumba``   - existing setting; land-phase numba thread
                                   count. absent/"auto" => auto policy (all
                                   cores on large domains, serial below
                                   NUMBA_AUTO_MIN_PIXELS); "all"/0 => all cores;
                                   N => N threads.
  * ``numCPUs_routingNumba``    - routing-substep numba thread cap. absent/
                                  "auto" => clamp(round(host/2), 8, 16);
                                  "all"/0 => all cores (no cap); N => N threads.
                                  Applied only around the routing substep loop
                                  (small per-substep payload collapses above a
                                  modest OpenMP worker count) and restored to
                                  the land-phase count afterwards; never raises
                                  the pool above the land count.
  * ``numCPUs_parallelNumexpr`` - numexpr thread count. absent/"auto" => 1
                                  (flat serial default on all domain sizes;
                                  small per-call arrays, nested pools would only
                                  oversubscribe against the numba pool);
                                  "all"/0 => all cores; N => N threads.
  * ``numCPUs_BLAS``            - BLAS/OpenMP thread count for numpy/scipy.
                                  absent/"auto" => 1 (flat serial default on all
                                  domain sizes; the only BLAS consumer is the
                                  cold soil-init scalar least_squares, idle in
                                  the dynamic loop); "all"/0 => all cores; N => N.
  * ``numCPUs_soilInit``        - soilInit thread count for soil initialization.
                                  Default: 0 (all cores).
  * ``numCPUs_earthkit``        - thread count for the earthkit-hydro upstream-
                                  accumulation pool (a native pool inside the
                                  Rust extension that reads its size once at
                                  first use via ``RAYON_NUM_THREADS`` and
                                  otherwise sizes itself to the host, thereby
                                  oversubscribing the node against the routing
                                  kernel). Only the opt-in earthkit reporting
                                  path builds this pool. Default: 1 (capped);
                                  0/"all"/"auto"/absent => uncapped (all cores).
A value of 0 (or empty/"all") means "use all available cores". For numexpr/BLAS,
"auto" (or an absent setting) is a flat serial default (1) on all domain sizes.

OMP_WAIT_POLICY is NOT set by this module. It is an energy lever (it trades idle
OpenMP worker spin for sleep at roughly equal wall time), not a speed lever, so
the default runtime behaviour is left untouched. An operator who wants to cut
CPU-hours at equal wall can export ``OMP_WAIT_POLICY=passive`` in the job
environment before launching LISFLOOD.
"""

import os
import numpy as np

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
    # get_num_threads returns the number of threads Numba will actually use.
    from numba import get_num_threads as _numba_get_num_threads
    _HAVE_NUMBA_THREADCTL = True
except ImportError:          # pragma: no cover – defensive
    _HAVE_NUMBA_THREADCTL = False


def _openmp_layer_available():
    """Return True if numba's OpenMP threading backend can be loaded.

    Probes the backend module directly (no parallel kernel compile), so it is
    cheap and side-effect free. Returns False if numba or the OpenMP pool is
    unavailable.
    """
    try:
        # Importing the backend module is enough to know the shared library is
        # present; it does not start the pool.
        from numba.np.ufunc import omppool  # noqa: F401
        return True
    except Exception:  # pragma: no cover - environment dependent
        return False


def _lock_and_verify_layer(intended):
    """Force numba to initialize its threading layer NOW (while we are still
    before any model parallel kernel) by running a trivial prange kernel, then
    return the layer numba actually locked. numba fixes the layer on first
    parallel use and ignores later changes, so locking it here deterministically
    prevents a stray earlier kernel (or the TBB-preferring default) from winning.
    Returns the actual locked layer string, or ``intended`` if the probe/readback
    is unavailable."""
    try:
        import numpy as _np
        from numba import njit as _njit, prange as _prange, threading_layer as _tl

        @_njit(parallel=True, cache=False)
        def _probe(a):
            s = 0.0
            for i in _prange(a.size):
                s += a[i]
            return s

        _probe(_np.ones(16))
        return str(_tl())
    except Exception:  # pragma: no cover - defensive; fall back to intent
        return intended


def select_numba_threading_layer():
    """Pin numba's threading layer to OpenMP when it is safe to do so.

    numba's ``default`` layer resolution prefers TBB over OpenMP when TBB is
    installed. On LISFLOOD workloads OpenMP is as fast or faster (measured:
    workqueue ~27% slower than OpenMP on the Congo benchmark; TBB at best on
    par), and an accidentally-installed TBB passenger package would otherwise
    silently take over. To make the layer deterministic we pin OpenMP, but
    **only** when:

      * the user has NOT set ``NUMBA_THREADING_LAYER`` (explicit choice wins),
      * numba is importable, and
      * the OpenMP backend is actually available.

    If the env var is set, or OpenMP is unavailable, we leave numba's own
    resolution untouched (it will fall back to whatever layer it can load).

    Returns the layer string that is now in effect for reporting, or None when
    numba is unavailable.
    """
    if not _HAVE_NUMBA_THREADCTL:
        return None

    # Respect an explicit user override via the environment. numba reads
    # NUMBA_THREADING_LAYER at import; mirror it into the live config so the
    # value we report matches what numba will use, and honor it as-is.
    env_layer = os.environ.get("NUMBA_THREADING_LAYER")
    if env_layer:
        try:
            _numba_config.THREADING_LAYER = env_layer.strip().lower()
        except Exception:  # pragma: no cover - defensive
            pass
        return str(_numba_config.THREADING_LAYER)

    # No explicit choice: pin OpenMP when its backend is available. numba's
    # default resolution prefers TBB when TBB is installed, but OpenMP is as
    # fast or faster on LISFLOOD workloads and avoids TBB's fork fragility.
    # This must run before the FIRST parallel kernel executes
    # (configure_parallelism is called once in Lisflood_initial.__init__,
    # before any module initial()/dynamic()), because numba locks the
    # threading layer on first parallel use and ignores later changes.
    intended = str(_numba_config.THREADING_LAYER)
    if _openmp_layer_available():
        try:
            _numba_config.THREADING_LAYER = "omp"
        except Exception:  # pragma: no cover - defensive
            pass
        # Belt-and-braces: also export the env var so any numba (re)read or a
        # forked worker that re-imports numba sees the same choice.
        os.environ.setdefault("NUMBA_THREADING_LAYER", "omp")
        intended = "omp"

    # Lock the layer NOW (before any model parallel kernel) and read back what
    # numba actually selected. This is the ground truth, not the intent: if a
    # stray earlier parallel call or a build quirk already locked another layer
    # (e.g. TBB, numba's default when TBB is installed), we detect it here
    # instead of silently running on the wrong layer.
    actual = _lock_and_verify_layer(intended)
    if actual != intended:
        try:
            import warnings
            from .errors import LisfloodWarning
            warnings.warn(LisfloodWarning(
                "numba threading layer is '{}' but '{}' was requested; the layer "
                "was already locked before it could be set. Set "
                "NUMBA_THREADING_LAYER={} in the environment before launching to "
                "force it.".format(actual, intended, intended)))
        except Exception:  # pragma: no cover - defensive
            pass
    return actual

# Keep a reference to any threadpoolctl limiter so the applied BLAS limits are
# not garbage-collected (and thus reverted) during the model run.
_blas_limiter = None

# Last-applied effective thread counts, so the startup banner can report the
# same numbers that were actually applied (see get_effective_parallelism).
_effective = None

# Resolved model floating-point dtype (np.float64 default). Set once at startup
# by configure_parallelism from the `modelPrecision` setting, and read by the
# array-creation funnels (MaskInfo.in_zero/in_one, add1.compressArray/decompress/
# loadmap_base) so that when modelPrecision=float32 the compressed state arrays
# are *born* float32 (avoiding the mixed-dtype upcast trap). float64 keeps every
# funnel bit-identical to today.
_model_dtype = np.float64


def get_model_dtype():
    """Return the resolved model dtype (np.float64 by default; np.float32 when
    modelPrecision=float32 was applied at startup)."""
    return _model_dtype


def set_model_dtype(dtype):
    """Set the process-wide model dtype. Called by configure_parallelism; exposed
    for tests. Only float32/float64 are meaningful."""
    global _model_dtype
    _model_dtype = np.dtype(dtype).type if not isinstance(dtype, type) else dtype
    return _model_dtype


def get_effective_parallelism():
    """Return the last-applied effective thread counts, or None if parallelism
    has not been configured yet.

    The dict is keyed 'numba', 'routing_numba', 'numexpr', 'blas', 'soilinit',
    'earthkit', 'numba_threading_layer', and 'host' (host core count). 'numba'
    is the concrete land-phase numba count (the restore target after the routing
    cap); 'routing_numba' is the applied routing-substep cap (an int), or None
    when the routing pool is left at all cores.
    """
    return _effective


def get_routing_numba_threads():
    """Return the applied routing-substep numba cap (an int), or None when the
    routing pool is left uncapped (explicit all/0) or parallelism has not been
    configured. The routing substep window uses this as the capped count."""
    if _effective is None:
        return None
    return _effective.get("routing_numba")


def get_land_numba_threads():
    """Return the concrete land-phase numba count published at startup, i.e. the
    count the routing-substep window restores to on exit. None when parallelism
    has not been configured or numba thread control is unavailable."""
    if _effective is None:
        return None
    return _effective.get("numba")


def set_numba_threads(n):
    """Thin, guarded wrapper over ``numba.set_num_threads``.

    Applies ``n`` only when numba thread control is available and
    ``0 < n <= NUMBA_NUM_THREADS`` (the same guard the startup path uses). A
    no-op when numba is unavailable or ``n`` is None/out of range, so the
    routing-substep window never raises a new failure mode. Thread count affects
    scheduling only, never results.
    """
    if not _HAVE_NUMBA_THREADCTL:
        return
    if n is None:
        return
    if 0 < n <= _numba_config.NUMBA_NUM_THREADS:
        _numba_set_num_threads(n)


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


# Routing-kernel numba cap bounds. The per-substep routing kernels have a small
# payload (one topological traversal of the river network per substep), so
# beyond a modest OpenMP worker count the fork/join cost dominates and wall time
# grows. The auto policy therefore caps the numba pool around the routing
# substep loop to clamp(round(host/2), 8, 16): half the host cores, but never
# fewer than 8 nor more than 16.
ROUTING_NUMBA_MIN_THREADS = 8
ROUTING_NUMBA_MAX_THREADS = 16


def _routing_numba_auto(host):
    """Auto policy value: clamp(round(host/2), MIN, MAX)."""
    if host is None:
        host = _host_cpu_count()
    k = int(round(host / 2))
    return min(max(k, ROUTING_NUMBA_MIN_THREADS), ROUTING_NUMBA_MAX_THREADS)


def resolve_routing_numba_threads(binding, host=None):
    """Decide the routing-kernel numba thread count (unified semantics).

    Controlled by the optional ``numCPUs_routingNumba`` setting:

      * absent / "" / "auto"  -> the auto policy
        ``clamp(round(host/2), ROUTING_NUMBA_MIN_THREADS,
        ROUTING_NUMBA_MAX_THREADS)`` (half the host cores, floored at 8, capped
        at 16). ``round`` is Python banker's rounding, but the documented
        anchors (host 16->8, 28->14, 56->16, 112->16) are all even so the
        half-case never arises.
      * "all" / "0"           -> None, meaning "all cores" (no routing-specific
        cap; the land-phase numba count is left to stand).
      * a positive integer N  -> that fixed count.
      * a malformed token     -> the auto policy (fail safe).

    ``host`` defaults to :func:`_host_cpu_count` when not supplied. Thread count
    affects scheduling only, never results. Returns an int >= 1 (the auto clamp
    result or an explicit N), or None meaning "all cores".
    """
    raw = binding.get("numCPUs_routingNumba") if binding is not None else None
    if isinstance(raw, str):
        raw = raw.strip().lower()

    if raw in (None, "", "auto"):
        return _routing_numba_auto(host)

    # "all" / "0" -> all cores (None); positive int N -> N.
    if raw in ("all", "0", 0):
        return None
    parsed = _parse_thread_count(raw)
    if parsed is None:
        # Unparseable token (e.g. "abc"): fail safe to the auto policy.
        return _routing_numba_auto(host)
    return parsed


def resolve_pool_threads(binding, key, num_pixels=None):
    """Decide the thread count for a shared library pool (numexpr / BLAS).

    These pools work on per-call arrays that are small relative to the whole
    domain, and they coexist with (and nest inside) the numba routing pool. A
    full-core numexpr/BLAS pool therefore oversubscribes the node against the
    numba OpenMP threads rather than adding useful throughput. The behaviour
    is:

    * If the user set a concrete number, honor it verbatim (e.g. ``1``, written
      by calibration templates to force a single-core instance; ``0``/``"all"``
      => unconditionally all cores regardless of domain size).
    * If the setting is **absent** or set to ``"auto"``, the default is a flat
      ``1`` (serial) on ALL domain sizes. The per-call arrays are small and the
      nested pools would merely contend with the numba routing pool for cores;
      a single-threaded pool is the measured best on both small catchments and
      large/global domains. ``num_pixels`` is accepted for signature
      compatibility (the land-numba resolver still uses
      ``NUMBA_AUTO_MIN_PIXELS``) but no longer influences this default.

    Returns an int >= 1, or None meaning "all available cores".
    """
    raw = binding.get(key) if binding is not None else None
    if isinstance(raw, str):
        raw = raw.strip().lower()

    auto = raw in (None, "", "auto")
    if not auto:
        # Explicit concrete number / "all" / "0": honor verbatim.
        return _parse_thread_count(raw)

    # auto (absent or "auto") -> flat serial default on all domain sizes.
    return 1


def resolve_soilinit_workers(binding, real_cpu_count):
    """Number of worker processes for the ColdStart soil-init solve.

    Controlled by the dedicated 'numCPUs_soilInit' setting (process-based
    parallelism for the per-pixel scipy least_squares solve; unrelated to the
    numba/numexpr/BLAS thread pools). Values: a positive integer, or
    0 / "all" / "auto" for all available cores. Defaults to 0 (all cores) when
    unset; the solve is bit-identical regardless of the worker count.
    """
    explicit =  _resolve(binding, "numCPUs_soilInit", None)
    if explicit is not None:
        return explicit
    return real_cpu_count if real_cpu_count is not None else _host_cpu_count()


def resolve_earthkit_threads(binding):
    """Thread count for the earthkit-hydro upstream-accumulation pool.

    That pool is a native (rayon) pool inside the earthkit-hydro Rust
    extension, sized once at first use from the ``RAYON_NUM_THREADS``
    environment variable and otherwise to the host core count. It is only built
    on the opt-in earthkit reporting path. Controlled by ``numCPUs_earthkit``:

      * absent / "" / "auto"  -> 1 (DEFAULT: single-threaded accumulation pool).
      * a positive integer    -> cap the pool to that many threads.
      * 0 / "all"             -> None, meaning "all cores" (leave uncapped).

    The accumulation is a depth-bounded topological traversal with little work
    per node; a bounded pool avoids oversubscribing the node against the routing
    kernel's OpenMP threads. Unlike :func:`resolve_pool_threads`, the default is
    a flat 1 and is NOT domain-size-aware: the contention is about pool
    coexistence with the routing kernel, not array size. Thread count affects
    scheduling only, never the result (the traversal order is deterministic and
    independent of the pool size).

    Returns an int >= 1, or None meaning "all cores / leave uncapped".
    """
    raw = binding.get("numCPUs_earthkit") if binding is not None else None
    if isinstance(raw, str):
        raw = raw.strip().lower()
    if raw in (None, "", "auto"):
        return 1                      # default: single-threaded rayon
    return _parse_thread_count(raw)   # int>0 => cap; 0/"all" => None


def resolve_model_dtype(binding):
    """Decide the floating-point dtype for LISFLOOD model state & kernels.

    Controlled by the optional ``modelPrecision`` setting (a string). This is a
    PRECISION/perf lever, separate from the thread-count knobs. It governs the
    whole model: the compressed state arrays (via the add1/MaskInfo creation
    funnels) and the kinematic-wave routing kernel.

      * absent / "" / "float64" / "f64" / "double"  -> np.float64 (DEFAULT).
        The historical, bit-identical path. The default MUST stay float64 so that
        unchanged settings files reproduce today's output bit-for-bit (Task 8.2).
      * "float32" / "f32" / "single"                -> np.float32.
        Opt-in faster path (halves memory traffic on the bandwidth-bound
        elementwise module bodies and the routing kernel; results stay within the
        project reference tolerance, not bit-identical).
      * any unknown value                           -> np.float64 (fail safe:
        never silently degrade precision on a typo).

    Returns a numpy dtype (np.float64 or np.float32).
    """
    raw = binding.get("modelPrecision") if binding is not None else None
    if isinstance(raw, str):
        raw = raw.strip().lower()
    if raw in ("float32", "f32", "single"):
        return np.float32
    return np.float64


# Backwards-compatible alias (the flag was briefly called routingPrecision).
def resolve_routing_dtype(binding):
    """Deprecated name for :func:`resolve_model_dtype`; also accepts the old
    ``routingPrecision`` key for settings files written against the earlier
    name. ``modelPrecision`` takes precedence when both are present."""
    if binding is not None:
        mp = binding.get("modelPrecision")
        if mp not in (None, ""):
            return resolve_model_dtype(binding)
        raw = binding.get("routingPrecision")
        if isinstance(raw, str):
            raw = raw.strip().lower()
        if raw in ("float32", "f32", "single"):
            return np.float32
    return np.float64


def configure_parallelism(binding, num_pixels=None):
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

    Returns
    -------
    dict
        The effective thread counts, keyed 'numba', 'routing_numba', 'numexpr',
        'blas', 'soilinit', 'earthkit', 'numba_threading_layer', and 'host'.
        'numba' is the concrete land-phase count (the routing cap's restore
        target); 'routing_numba' is the applied routing-substep cap (an int), or
        None when the routing pool is left at all cores. For the thread-count
        keys, None means "all cores".
    """
    global _blas_limiter, _effective

    # --- model floating-point precision (state + kernels) ---
    # Resolve once and publish so the array-creation funnels emit this dtype.
    global _model_dtype
    _model_dtype = resolve_model_dtype(binding)

    # --- numba threading layer ---
    # Pin OpenMP when the user has not overridden NUMBA_THREADING_LAYER and the
    # OpenMP backend is available (prevents an installed TBB from silently
    # taking priority; OpenMP is as fast or faster on LISFLOOD workloads). Must
    # happen before any parallel kernel compiles, i.e. here at startup.
    effective_threading_layer = select_numba_threading_layer()

    # --- numba (soilloop + kinematic-wave/MCT routing kernels) ---
    # None means "leave numba at its default" (all cores); a concrete N caps it.
    numba_threads = resolve_numba_threads(binding, num_pixels)
    
    if _HAVE_NUMBA_THREADCTL:
        # If the user asked for a concrete value, try to set it; otherwise
        # leave Numba at its default (which may already be “all cores”).
        if numba_threads is not None:
            # Numba cannot be asked for more threads than its own hard limit.
            if 0 < numba_threads <= _numba_config.NUMBA_NUM_THREADS:
                _numba_set_num_threads(numba_threads)
            # If the request is larger than the limit we simply ignore it –
            # Numba will keep its previous (default) setting.
        # *** query the **actual** number of threads Numba will use ***
        effective_numba = _numba_get_num_threads()
    else:
        effective_numba = None            # Numba not available

    # numexpr and BLAS: when the user does not set them, the default is a flat
    # serial 1 on all domain sizes. Their per-call arrays are small and the
    # pools nest inside (and contend with) the numba routing pool, so a
    # full-core pool only oversubscribes the node rather than adding throughput.
    # An explicit value in the settings is always honored verbatim.
    numexpr_threads = resolve_pool_threads(binding, "numCPUs_parallelNumexpr", num_pixels)
    blas_threads = resolve_pool_threads(binding, "numCPUs_BLAS", num_pixels)

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
    else:
        target = host
    effective_blas = target
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

    soilinit_workers = resolve_soilinit_workers(binding, host)

    # --- earthkit-hydro accumulation pool (rayon, native Rust extension) ---
    # The rayon global pool reads RAYON_NUM_THREADS ONCE, when it is built on
    # the first upstream accumulation in the dynamic loop, and ignores later
    # changes. It must therefore be set here at startup, before the first
    # earthkit call. Capping it stops the accumulation pool from oversubscribing
    # the node against the routing kernel's OpenMP threads. The value is a
    # validated integer string (no user string is interpolated unvalidated, and
    # no shell is involved). Thread count affects scheduling only, never results.
    earthkit_threads = resolve_earthkit_threads(binding)
    if earthkit_threads is not None:
        effective_earthkit = max(1, min(int(earthkit_threads), host))
        os.environ["RAYON_NUM_THREADS"] = str(effective_earthkit)
    else:
        # Uncapped: leave RAYON_NUM_THREADS untouched so an operator who set it
        # directly in the environment keeps control (mirrors the handling of
        # NUMBA_THREADING_LAYER above).
        effective_earthkit = None

    # --- routing-substep numba cap ---
    # The routing substep loop applies a lower numba count than the land phase
    # (small per-substep payload collapses above a modest OpenMP worker count)
    # and restores the land count afterwards. The land-phase numba count is the
    # restore target (effective_numba). INVARIANT: the routing cap never RAISES
    # the numba pool above the land count -- the apply-time min() clamps it to
    # the land count (so on a small domain where the land policy chose serial,
    # the window is a no-op), to the host core count, and to numba's hard limit.
    raw_routing = resolve_routing_numba_threads(binding, host)
    if raw_routing is None:
        routing_applied = None            # explicit all/0: no cap; land stands
    else:
        bounds = [raw_routing, host]
        if effective_numba is not None:
            bounds.append(effective_numba)
        if _HAVE_NUMBA_THREADCTL:
            bounds.append(_numba_config.NUMBA_NUM_THREADS)
        routing_applied = min(bounds)

    effective = {
        "numba": effective_numba,
        "routing_numba": routing_applied,
        "numexpr": effective_numexpr,
        "blas": effective_blas,
        "soilinit": soilinit_workers,
        "earthkit": effective_earthkit,
        "numba_threading_layer": effective_threading_layer,
        "host": host,
    }
    _effective = effective
    return effective
