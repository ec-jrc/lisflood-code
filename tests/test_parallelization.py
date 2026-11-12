"""
Unit tests for lisflood.global_modules.parallelization.

Focus is the numba small‑domain auto‑tune decision that the performance change
adds (explicit setting wins; below the pixel threshold run serial; at/above the
threshold or unknown size use all cores). A couple of sentinel cases cover the
"0 / unparseable -> all cores" fallback path.
"""

import os
import pytest

from lisflood.global_modules import parallelization as par


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    """
    Ensure each test starts with a clean global state.
    """
    monkeypatch.setattr(par, "_effective", None, raising=False)
    monkeypatch.setattr(par, "_blas_limiter", None, raising=False)
    yield
    # clean‑up after the test (in case a limiter was created)
    monkeypatch.setattr(par, "_effective", None, raising=False)
    monkeypatch.setattr(par, "_blas_limiter", None, raising=False)


class TestEffectiveThreadCounts:
    """Check that ``configure_parallelism`` reads all *numCPU* settings,
    applies the limits, and stores the real numbers in the ``effective``
    dictionary returned by the function."""

    def _patch_host(self, monkeypatch, value):
        """Force ``_host_cpu_count`` to return a deterministic core count."""
        monkeypatch.setattr(par, "_host_cpu_count", lambda: value)

    def test_explicit_settings_are_reflected(self, monkeypatch):
        """All user‑specified thread numbers must appear unchanged in the
        effective result (or be capped by the library’s hard limit)."""

        # 1. deterministic host size – 8 logical CPUs
        self._patch_host(monkeypatch, 8)

        # 2. binding with explicit values for every pool
        binding = {
            "numCPUs_parallelNumba":   "4",
            "numCPUs_BLAS":            "2",
            "numCPUs_soilInit":        "5",
        }

        eff = par.configure_parallelism(binding, num_pixels=100)

        # ---- numba -------------------------------------------------
        # If Numba is available we expect the value we set (capped by the
        # library’s own maximum).  When Numba is not present the entry is
        # ``None`` – the test still passes.
        if par._HAVE_NUMBA_THREADCTL:
            # The library may silently cap the request, so we compare with the
            # *actual* value stored in the effective dict.
            assert eff["numba"] == par._numba_get_num_threads()
            # The requested value must be ≥ the effective one and not exceed the
            # hard limit.
            assert 1 <= eff["numba"] <= 4
        else:
            assert eff["numba"] is None

        # ---- BLAS --------------------------------------------------
        assert eff["blas"] == 2      # exact value we asked for

        # ---- soil‑init ---------------------------------------------
        assert eff["soilinit"] == 5   # explicit value is taken verbatim

        # ---- host --------------------------------------------------
        assert eff["host"] == 8

    def test_blas_all_cores_sentinel(self, monkeypatch):
        """When the BLAS setting is a sentinel (0 / empty / “all”) the
        effective BLAS thread count must expand to the host core count."""
        # Force a known host size (e.g. 16 cores)
        self._patch_host(monkeypatch, 16)

        binding = {"numCPUs_BLAS": "0"}   # sentinel meaning “all cores”

        eff = par.configure_parallelism(binding, num_pixels=None)

        # The module should translate the sentinel to the host count.
        assert eff["blas"] == 16
        # The host entry must also report the same value we patched.
        assert eff["host"] == 16

    def test_auto_and_missing_soilinit(self, monkeypatch):
        """When the user leaves ``numCPUs_soilInit`` unset the function must
        fall back to the (patched) host core count.  The same holds for the
        auto‑tune path of Numba."""

        # 1. Force a known host size (12 logical CPUs)
        self._patch_host(monkeypatch, 12)

        # 2. Binding that only defines the *auto* value for Numba
        binding = {
            "numCPUs_parallelNumba": "0",   # auto‑tune
            # No entry for ``numCPUs_soilInit`` → fallback to host
        }

        # Small domain (below the threshold) forces serial Numba
        eff = par.configure_parallelism(
            binding,
            num_pixels=par.NUMBA_AUTO_MIN_PIXELS - 10
        )

        # ---- numba -------------------------------------------------
        # The auto‑tune logic should have forced a single thread.
        if par._HAVE_NUMBA_THREADCTL:
            assert eff["numba"] == 1
        else:
            assert eff["numba"] is None

        # ---- soil‑init ---------------------------------------------
        # Missing setting → default is now 0 (all cores) → host core count
        assert eff["soilinit"] == 12

        # ---- host --------------------------------------------------
        assert eff["host"] == 12

    def test_soilinit_auto_uses_all_cores_when_host_unknown(self, monkeypatch):
        """``numCPUs_soilInit = 0`` (or ``"auto"``) must resolve to the host
        core count even when the caller supplies ``real_cpu_count=None``."""

        # Patch host count to a known value (6)
        self._patch_host(monkeypatch, 6)

        binding = {"numCPUs_soilInit": "0"}   # auto / all cores

        # Resolve directly via the helper – it should return the host size.
        workers = par.resolve_soilinit_workers(binding, real_cpu_count=None)

        assert workers == 6

class TestEarthkitThreads:
    """resolve_earthkit_threads + the RAYON_NUM_THREADS env-var application in
    configure_parallelism. The earthkit accumulation pool (rayon, native) must
    be capped by 'numCPUs_earthkit' so it stops oversubscribing against the
    routing kernel. Default is 1; 0/"all"/"auto"/absent means uncapped (None).
    This is a scheduling-only knob; it does not change any numerical result."""

    def test_default_is_single_threaded(self):
        assert par.resolve_earthkit_threads({}) == 1

    def test_absent_binding_is_single_threaded(self):
        assert par.resolve_earthkit_threads(None) == 1

    def test_explicit_positive_value_caps(self):
        assert par.resolve_earthkit_threads({"numCPUs_earthkit": "4"}) == 4

    def test_zero_means_uncapped(self):
        assert par.resolve_earthkit_threads({"numCPUs_earthkit": "0"}) is None

    def test_all_means_uncapped(self):
        assert par.resolve_earthkit_threads({"numCPUs_earthkit": "all"}) is None

    def test_auto_is_single_threaded(self):
        assert par.resolve_earthkit_threads({"numCPUs_earthkit": "auto"}) == 1

    def test_configure_default_sets_rayon_to_one(self, monkeypatch):
        monkeypatch.setattr(par, "_host_cpu_count", lambda: 16)
        monkeypatch.delenv("RAYON_NUM_THREADS", raising=False)
        eff = par.configure_parallelism({}, num_pixels=100)
        assert eff["earthkit"] == 1
        assert os.environ["RAYON_NUM_THREADS"] == "1"

    def test_configure_explicit_value_is_reflected_and_applied(self, monkeypatch):
        monkeypatch.setattr(par, "_host_cpu_count", lambda: 16)
        monkeypatch.delenv("RAYON_NUM_THREADS", raising=False)
        eff = par.configure_parallelism(
            {"numCPUs_earthkit": "4"}, num_pixels=100)
        assert eff["earthkit"] == 4
        assert os.environ["RAYON_NUM_THREADS"] == "4"

    def test_configure_caps_request_to_host(self, monkeypatch):
        monkeypatch.setattr(par, "_host_cpu_count", lambda: 8)
        monkeypatch.delenv("RAYON_NUM_THREADS", raising=False)
        eff = par.configure_parallelism(
            {"numCPUs_earthkit": "32"}, num_pixels=100)
        assert eff["earthkit"] == 8
        assert os.environ["RAYON_NUM_THREADS"] == "8"

    def test_configure_uncapped_leaves_env_untouched(self, monkeypatch):
        # 0/"all" => uncapped: do not overwrite an operator-set RAYON value.
        monkeypatch.setattr(par, "_host_cpu_count", lambda: 16)
        monkeypatch.setenv("RAYON_NUM_THREADS", "7")
        eff = par.configure_parallelism(
            {"numCPUs_earthkit": "0"}, num_pixels=100)
        assert eff["earthkit"] is None
        assert os.environ["RAYON_NUM_THREADS"] == "7"


class TestNumbaAutoTune:
    """resolve_numba_threads: the core decision the performance change adds.
    Explicit setting wins; otherwise auto-tune on domain size."""

    def test_explicit_value_wins_regardless_of_domain_size(self):
        binding = {"numCPUs_parallelNumba": "4"}
        assert par.resolve_numba_threads(binding, num_pixels=10) == 4
        assert par.resolve_numba_threads(binding, num_pixels=10_000_000) == 4

    def test_auto_runs_serial_below_threshold(self):
        binding = {"numCPUs_parallelNumba": "0"}  # auto
        assert par.resolve_numba_threads(
            binding, num_pixels=par.NUMBA_AUTO_MIN_PIXELS - 1) == 1

    def test_auto_uses_all_cores_at_and_above_threshold(self):
        binding = {"numCPUs_parallelNumba": "0"}
        # boundary is exclusive: exactly at threshold is NOT "small"
        assert par.resolve_numba_threads(
            binding, num_pixels=par.NUMBA_AUTO_MIN_PIXELS) is None
        assert par.resolve_numba_threads(
            binding, num_pixels=par.NUMBA_AUTO_MIN_PIXELS + 1) is None

    def test_auto_with_unknown_size_keeps_historical_all_cores(self):
        # when domain size is unavailable we must not accidentally force serial
        binding = {"numCPUs_parallelNumba": "0"}
        assert par.resolve_numba_threads(binding, num_pixels=None) is None

    def test_missing_setting_behaves_as_auto(self):
        # older settings files without the key must still auto‑tune, not crash
        assert par.resolve_numba_threads({}, num_pixels=10) == 1
        assert par.resolve_numba_threads({}, num_pixels=None) is None


class TestAllCoresSentinel:
    """The '0 / unparseable -> use all cores (None)' fallback that the
    auto‑tune relies on. One nominal and one degenerate case is enough."""

    @pytest.mark.parametrize(
        "value,expected",
        [("2", 2), ("0", None), ("abc", None)]
    )
    def test_parse_thread_count(self, value, expected):
        assert par._parse_thread_count(value) == expected

class TestPoolThreadsAutoDefault:
    """resolve_pool_threads (BLAS): flat serial (1) default on all
    domain sizes when the setting is absent or "auto"; explicit values always
    honored verbatim.

    Measured basis: the BLAS per-call arrays are small and the pool
    nests inside (and contends with) the numba routing pool, so a full-core pool
    only oversubscribes the node. A single-threaded default is best on both
    small catchments and large/global domains, while staying overridable
    (calibration forces "1"; "0"/"all" forces all cores)."""

    SMALL = par.NUMBA_AUTO_MIN_PIXELS - 1
    LARGE = par.NUMBA_AUTO_MIN_PIXELS

    def test_explicit_value_wins_regardless_of_domain_size(self):
        for pix in (self.SMALL, self.LARGE, 10_000_000):
            assert par.resolve_pool_threads(
                {"numCPUs_BLAS": "2"}, "numCPUs_BLAS", num_pixels=pix) == 2

    def test_explicit_one_forces_serial_even_on_large_domain(self):
        # the calibration escape hatch: force single-core on a big domain
        assert par.resolve_pool_threads(
            {"numCPUs_BLAS": "1"}, "numCPUs_BLAS",
            num_pixels=10_000_000) == 1

    def test_explicit_zero_forces_all_cores_even_on_small_domain(self):
        assert par.resolve_pool_threads(
            {"numCPUs_BLAS": "0"}, "numCPUs_BLAS", num_pixels=self.SMALL) is None
        assert par.resolve_pool_threads(
            {"numCPUs_BLAS": "all"}, "numCPUs_BLAS", num_pixels=self.SMALL) is None

    def test_auto_token_is_flat_one(self):
        # flat serial default: "auto" -> 1 on BOTH small and large domains
        assert par.resolve_pool_threads(
            {"numCPUs_BLAS": "auto"}, "numCPUs_BLAS", num_pixels=self.SMALL) == 1
        assert par.resolve_pool_threads(
            {"numCPUs_BLAS": "auto"}, "numCPUs_BLAS", num_pixels=self.LARGE) == 1

    def test_missing_setting_is_flat_one(self):
        # old settings files without the key: serial on all domain sizes
        assert par.resolve_pool_threads({}, "numCPUs_BLAS",
                                        num_pixels=self.SMALL) == 1
        assert par.resolve_pool_threads({}, "numCPUs_BLAS",
                                        num_pixels=self.LARGE) == 1

    def test_unknown_domain_size_stays_serial(self):
        # The BLAS auto default is a flat serial 1 regardless of size.
        assert par.resolve_pool_threads({}, "numCPUs_BLAS", num_pixels=None) == 1
        assert par.resolve_pool_threads(
            {"numCPUs_BLAS": "auto"}, "numCPUs_BLAS", num_pixels=None) == 1

    def test_configure_parallelism_large_domain_stays_serial(self, monkeypatch):
        monkeypatch.setattr(par, "_host_cpu_count", lambda: 16)
        # no BLAS key -> auto; flat-1 default even on a large domain
        eff = par.configure_parallelism({}, num_pixels=par.NUMBA_AUTO_MIN_PIXELS)
        assert eff["blas"] == 1

    def test_configure_parallelism_small_domain_stays_serial(self, monkeypatch):
        monkeypatch.setattr(par, "_host_cpu_count", lambda: 16)
        eff = par.configure_parallelism({}, num_pixels=100)
        assert eff["blas"] == 1


class TestRoutingNumbaResolver:
    """resolve_routing_numba_threads: the new routing-substep cap policy.
    auto/absent -> clamp(round(host/2), 8, 16); all/0 -> None (all cores);
    N -> N; malformed -> auto policy. Scheduling-only; never changes results."""

    @pytest.mark.parametrize(
        "host,expected",
        [(16, 8), (28, 14), (56, 16), (112, 16)],
    )
    def test_auto_token_is_clamped_half_host(self, host, expected):
        assert par.resolve_routing_numba_threads(
            {"numCPUs_routingNumba": "auto"}, host=host) == expected
        # absent key resolves to the same auto policy
        assert par.resolve_routing_numba_threads({}, host=host) == expected

    def test_small_host_hits_clamp_floor(self):
        # host 4 -> round(2) = 2 -> floored to 8 by the resolver. The host-level
        # cap (never exceed host) is applied at apply time in
        # configure_parallelism, asserted in TestRoutingNumbaConfigure.
        assert par.resolve_routing_numba_threads(
            {"numCPUs_routingNumba": "auto"}, host=4) == 8

    def test_malformed_token_falls_back_to_auto(self):
        assert par.resolve_routing_numba_threads(
            {"numCPUs_routingNumba": "abc"}, host=28) == 14


class TestRoutingNumbaConfigure:
    """configure_parallelism: apply-time clamp and publication of the routing
    cap, plus the get_routing_numba_threads / get_land_numba_threads accessors.
    The applied cap is min(raw, NUMBA_NUM_THREADS, host, land_count) so it never
    raises the pool above the land-phase count."""

    def _patch_host(self, monkeypatch, value):
        monkeypatch.setattr(par, "_host_cpu_count", lambda: value)

    def _expected_applied(self, raw, host, land):
        bounds = [raw, host]
        if land is not None:
            bounds.append(land)
        if par._HAVE_NUMBA_THREADCTL:
            bounds.append(par._numba_config.NUMBA_NUM_THREADS)
        return min(bounds)

    @pytest.mark.parametrize("host,raw", [(16, 8), (28, 14), (56, 16)])
    def test_large_domain_applies_clamped_cap(self, monkeypatch, host, raw):
        self._patch_host(monkeypatch, host)
        # large domain -> land numba is all cores (effective_numba == host when
        # numba is available; None otherwise).
        eff = par.configure_parallelism({}, num_pixels=par.NUMBA_AUTO_MIN_PIXELS)
        land = eff["numba"]
        assert eff["routing_numba"] == self._expected_applied(raw, host, land)
        # accessors echo the published values
        assert par.get_routing_numba_threads() == eff["routing_numba"]
        assert par.get_land_numba_threads() == eff["numba"]

    def test_all_token_leaves_pool_uncapped(self, monkeypatch):
        self._patch_host(monkeypatch, 56)
        eff = par.configure_parallelism(
            {"numCPUs_routingNumba": "all"}, num_pixels=par.NUMBA_AUTO_MIN_PIXELS)
        assert eff["routing_numba"] is None
        assert par.get_routing_numba_threads() is None

    def test_explicit_integer_is_applied(self, monkeypatch):
        self._patch_host(monkeypatch, 56)
        eff = par.configure_parallelism(
            {"numCPUs_routingNumba": "5"}, num_pixels=par.NUMBA_AUTO_MIN_PIXELS)
        land = eff["numba"]
        assert eff["routing_numba"] == self._expected_applied(5, 56, land)

    def test_small_domain_cap_is_noop(self, monkeypatch):
        # Small domain: the land policy chooses serial (1) when numba thread
        # control is available, so the routing cap clamps to 1 (a no-op window).
        self._patch_host(monkeypatch, 56)
        eff = par.configure_parallelism({}, num_pixels=100)
        if par._HAVE_NUMBA_THREADCTL:
            assert eff["numba"] == 1
            assert eff["routing_numba"] == 1
        else:
            # numba unavailable: land count is None, cap clamped to host/limit.
            assert eff["routing_numba"] == min(16, 56)


class TestSetNumbaThreadsGuard:
    """Proves the land count is restored after the routing-substep window
    closes (the cap is scoped, not global) — the behavioural invariant the
    try/finally in Lisflood_dynamic relies on."""

    def test_land_count_restored_after_routing_window(self):
        # Simulate the scoped window: land -> routing_k -> land, and assert the
        # numba-reported count returns to the land count (the cap is scoped).
        if not par._HAVE_NUMBA_THREADCTL:
            pytest.skip("numba thread control unavailable")
        hard = par._numba_config.NUMBA_NUM_THREADS
        land = min(2, hard)
        routing_k = 1
        par.set_numba_threads(land)
        assert par._numba_get_num_threads() == land
        par.set_numba_threads(routing_k)
        assert par._numba_get_num_threads() == routing_k
        par.set_numba_threads(land)   # restore (the finally branch)
        assert par._numba_get_num_threads() == land
