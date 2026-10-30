"""
Unit tests for the earthkit-hydro bridge (lisflood.global_modules.
earthkit_network) behind the opt-in useEarthkitHydro reporting path.

The end-to-end suite cannot catch a regression here: the flag defaults to
False and the PCRaster fallback silently takes over. These tests pin the two
contracts the bridge must uphold:

  1. Accumulation - a RiverNetwork built by the bridge from a numpy Ldd must
     reproduce PCRaster accuflux on the in-domain (compressed) cells.
  2. Zone means - ek_sample_zone_means must reproduce the inherited
     TimeoutputTimeseries.sample() tss values for multi-cell gauge zones
     (the pcraster.areaaverage(expr, spatialId) path), including
     Decimal('NaN') handling and the final-step file write.

Characterization tests: they pin current behaviour so an earthkit-hydro
upgrade that breaks the bridge is caught by the suite, not by a silently
different run. No settings files or test datasets are required.
"""

import types
from decimal import Decimal

import numpy as np
import pcraster
import pytest

from lisflood.global_modules.earthkit_network import (
    compute_gauge_zone_codes,
    earthkit_available,
    ek_sample_zone_means,
    ek_upstream_sum,
    ek_zone_mean_at_gauges,
    get_earthkit_network,
)

requires_earthkit = pytest.mark.skipif(
    not earthkit_available(), reason='earthkit-hydro not installed')


def east_flow_ldd(nrows=10, ncols=10):
    """Sound Ldd: every cell flows east (pcr keypad code 6), last column pits (5)."""
    ldd = np.zeros((nrows, ncols), dtype=np.int32)
    for r in range(nrows):
        for c in range(ncols):
            ldd[r, c] = 6 if c < ncols - 1 else 5
    return ldd


def compress_like_lisflood(array_2d, ldd_2d):
    """Flatten to LISFLOOD's compressed order (row-major valid d8 cells)."""
    valid = (ldd_2d > 0) & (ldd_2d <= 9)
    return np.asarray(array_2d, dtype=np.float64).ravel(order='C')[valid.ravel()]


class TestRiverNetworkAccumulation:

    @requires_earthkit
    def test_upstream_sum_matches_pcraster_accuflux(self):
        pcraster.setclone(10, 10, 1.0, 0.0, 0.0)
        ldd = east_flow_ldd()
        field = np.random.default_rng(42).random((10, 10))
        ldd_pcr = pcraster.ldd(pcraster.numpy2pcr(pcraster.Nominal, ldd, 0))
        acc_pcr = pcraster.pcr2numpy(
            pcraster.accuflux(ldd_pcr,
                              pcraster.numpy2pcr(pcraster.Scalar, field, np.nan)),
            np.nan)
        net = get_earthkit_network(ldd)
        acc_ek = ek_upstream_sum(net, compress_like_lisflood(field, ldd))
        # PCRaster Scalar accumulates in float32, earthkit in float64: allow
        # float32-level rounding differences.
        np.testing.assert_allclose(
            acc_ek, compress_like_lisflood(acc_pcr, ldd), rtol=1e-6, atol=1e-9)

    @requires_earthkit
    def test_network_is_cached_per_ldd(self):
        pcraster.setclone(8, 8, 1.0, 0.0, 0.0)
        ldd = east_flow_ldd(8, 8)
        assert get_earthkit_network(ldd) is get_earthkit_network(ldd.copy())


class TestZoneMeans:

    def test_zone_mean_matches_numpy_oracle(self):
        field = np.array([1.0, 2.0, 3.0, 4.0, 10.0, 20.0, 5.0])
        # non-contiguous codes on purpose (5 and 17)
        codes = np.array([5, 5, 0, 17, 17, 0, 5], dtype=np.int64)
        means = ek_zone_mean_at_gauges(None, field, codes, 2)
        assert means[5] == pytest.approx(8.0 / 3.0)
        assert means[17] == pytest.approx(7.0)

    def test_zone_mean_nan_cells_are_propagated(self):
        means = ek_zone_mean_at_gauges(None, np.array([1.0, np.nan]),
                                       np.array([1, 1], dtype=np.int64), 1)
        assert np.isnan(means[1])

    def test_compute_gauge_zone_codes_maps_nan_to_zero(self):
        gauge_map = np.array([[1.0, np.nan], [3.0, 3.0]])
        maskflat = np.array([False, False, True, False])
        zone_codes, n_codes = compute_gauge_zone_codes(gauge_map, maskflat, 3)
        np.testing.assert_array_equal(zone_codes, [1, 0, 3])
        assert n_codes == 3



class TestEkSampleZoneMeans:
    """tss-row equivalence with the PCRaster .sample() path."""

    @staticmethod
    def _fake_tss(zone_codes, n_codes, codes_id, n_rows=3, final_step=3):
        """Minimal TimeoutputTimeseries stand-in with the zone attributes
        prepared in __init__ (compute_gauge_zone_codes) and a write recorder."""
        tss = types.SimpleNamespace(
            _userModel=types.SimpleNamespace(
                currentTimeStep=lambda: tss.current_step[0],
                firstTimeStep=lambda: 1,
                nrTimeSteps=lambda: final_step),
            _spatialDatatype=None,
            _sampleValues=[[None] * len(codes_id) for _ in range(n_rows)],
            _codesId=codes_id,
            _ncodesId=len(codes_id),
            _ek_zone_codes=zone_codes,
            _ek_n_codes=n_codes,
            current_step=[1],
            written=[],
        )
        tss._writeTssFile = lambda: tss.written.append(tss.current_step[0])
        return tss

    @requires_earthkit
    def test_row_matches_pcraster_areaaverage(self):
        # zone 5 at flat cells 0,1; zone 17 at flat cell 5 of a 2x3 domain
        # (all in-mask, so the compressed field covers all 6 cells);
        # exactly representable values so the float32 casts agree bit-for-bit.
        gauge_map = np.array([[5.0, 5.0, np.nan], [np.nan, np.nan, 17.0]])
        zone_codes, n_codes = compute_gauge_zone_codes(
            gauge_map, np.zeros(6, dtype=bool), 2)
        tss = self._fake_tss(zone_codes, n_codes, [5, 17])
        ek_sample_zone_means(tss, np.array([2.0, 6.0, 0.0, 0.0, 0.0, 10.0]))
        np.testing.assert_array_equal(tss._sampleValues[0], [4.0, 10.0])
        assert tss._spatialDatatype == 'VALUESCALE.Scalar'

    @requires_earthkit
    def test_nan_values_become_decimal_nan(self):
        gauge_map = np.array([[5.0, np.nan], [np.nan, 17.0]])
        zone_codes, n_codes = compute_gauge_zone_codes(
            gauge_map, np.zeros(4, dtype=bool), 2)
        tss = self._fake_tss(zone_codes, n_codes, [5, 17])
        ek_sample_zone_means(tss, np.array([np.nan, 0.0, 0.0, 8.0]))
        # Decimal('NaN') compares unequal to itself (IEEE rules), which is why
        # _writeTssFile treats it as a sentinel: test via is_nan(), not ==.
        assert isinstance(tss._sampleValues[0][0], Decimal)
        assert tss._sampleValues[0][0].is_nan()
        assert tss._sampleValues[0][1] == 8.0

    @requires_earthkit
    def test_tss_written_only_on_final_step(self):
        gauge_map = np.array([[5.0, np.nan], [np.nan, 17.0]])
        zone_codes, n_codes = compute_gauge_zone_codes(
            gauge_map, np.zeros(4, dtype=bool), 2)
        tss = self._fake_tss(zone_codes, n_codes, [5, 17])
        for step, vals in [(1, [2.0, 0.0, 0.0, 8.0]),
                           (2, [4.0, 0.0, 0.0, 8.0]),
                           (3, [6.0, 0.0, 0.0, 8.0])]:
            tss.current_step[0] = step
            ek_sample_zone_means(tss, np.array(vals, dtype=np.float64))
        assert tss.written == [3]
