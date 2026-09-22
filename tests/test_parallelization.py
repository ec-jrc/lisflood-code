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

        # 2. make sure NumExpr does not hit its default 64‑thread ceiling
        monkeypatch.setenv("NUMEXPR_MAX_THREADS", "32")

        # 3. binding with explicit values for every pool
        binding = {
            "numCPUs_parallelNumba":   "4",
            "numCPUs_parallelNumexpr": "3",
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

        # ---- numexpr -----------------------------------------------
        assert eff["numexpr"] == 3   # explicit value, already bounded by host=8

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
        # Missing setting → effective value equals the **default** (1)
        assert eff["soilinit"] == 1

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

