"""
Unit tests for lisflood.global_modules.parallelization.

Focus is the numba small-domain auto-tune decision that the performance change
adds (explicit setting wins; below the pixel threshold run serial; at/above the
threshold or unknown size use all cores). A couple of sentinel cases cover the
"0 / unparseable -> all cores" fallback path.
"""

import pytest

from lisflood.global_modules import parallelization as par


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
        # older settings files without the key must still auto-tune, not crash
        assert par.resolve_numba_threads({}, num_pixels=10) == 1
        assert par.resolve_numba_threads({}, num_pixels=None) is None


class TestAllCoresSentinel:
    """The '0 / unparseable -> use all cores (None)' fallback that the
    auto-tune relies on. One nominal and one degenerate case is enough."""

    @pytest.mark.parametrize("value,expected", [("2", 2), ("0", None), ("abc", None)])
    def test_parse_thread_count(self, value, expected):
        assert par._parse_thread_count(value) == expected
