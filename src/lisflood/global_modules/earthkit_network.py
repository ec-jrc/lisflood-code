"""

Copyright 2019 European Union

Licensed under the EUPL, Version 1.2 or as soon they will be approved by the European Commission  subsequent versions of the EUPL (the "Licence");

You may not use this work except in compliance with the Licence.
You may obtain a copy of the Licence at:

https://joinup.ec.europa.eu/sites/default/files/inline-files/EUPL%20v1_2%20EN(1).txt

Unless required by applicable law or agreed to in writing, software distributed
under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and limitations under the Licence.

"""
import numpy as np
from decimal import Decimal
import numpy as np

from .errors import LisfloodWarning

# ------------------------------------------------------------------------
# earthkit-hydro bridge (opt-in via the `useEarthkitHydro` setoption)
# ------------------------------------------------------------------------
# Replaces the slow single-threaded PCRaster engine reductions on the
# reporting path (catchmenttotal/accuflux/areaaverage) with earthkit-hydro's
# parallel, numpy-native topological accumulation on a RiverNetwork built
# once from the model Ldd. Verified against PCRaster accuflux:
#   - earthkit node order == LISFLOOD compressed 1D (maskflat) order,
#   - accumulation results BIT-IDENTICAL on finite (in-domain) cells
#     (see tests/test_earthkit_network.py).
# The PCRaster path is kept verbatim behind the flag (default False).

try:
    import earthkit.hydro as _ekh
    from earthkit.hydro._readers import from_d8 as _ek_from_d8
    from earthkit.hydro.data_structures._network import RiverNetwork as _EKRiverNetwork

    _EKH_IMPORT_ERROR = None
except Exception as _e:  # pragma: no cover - optional dependency
    # ImportError (package missing) or AttributeError (the private layout moved
    # in a newer earthkit-hydro release): the bridge is pinned to the 1.x
    # private layout, so degrade to "unavailable" and let callers fall back to
    # the PCRaster path instead of crashing the import chain.
    _ekh = None
    _ek_from_d8 = None
    _EKRiverNetwork = None
    _EKH_IMPORT_ERROR = '%s: %s' % (type(_e).__name__, _e)


# Return type used for all earthkit operations. 'masked' returns a 1D array
# over the network nodes (== LISFLOOD compressed order) with NaN outside the
# network domain. Since LISFLOOD's Ldd is exactly the network domain, all
# in-domain cells are finite.
_EK_RETURN_TYPE = 'masked'

# Storage-level key of the currently built network, to detect Ldd changes
# across instances (defensive; within one process the Ldd never changes).
_EK_CACHE_KEY = None
_EK_CACHE_NETWORK = None


def earthkit_available():
    """ True if earthkit-hydro is importable in this environment. """
    return _ekh is not None


def _storage_mask(storage):
    """ Boolean flat mask of the network domain (True = in-domain).

    earthkit's storage.mask is an int64 INDEX array over the flat grid
    (used as v.flat[mask] in the xarray decorator), not a boolean mask, so
    materialise the boolean explicitly.
    """
    idx = np.asarray(storage.mask).ravel()
    if idx.dtype == bool:
        return idx
    boolean = np.zeros(int(storage.shape[0]) * int(storage.shape[1]), dtype=bool)
    boolean[idx] = True
    return boolean


def _network_from_ldd(ldd_np):
    """ Build an earthkit RiverNetwork from a numpy Ldd (PCRaster d8 codes,
    0/-9999 outside the model mask).

    The network node order equals the row-major (C-order) in-domain cell
    order, which is exactly LISFLOOD's compressed 1D array order
    (MaskInfo.info.maskflat, True = outside). The two masks are asserted
    equal at build time so any mismatch fails loudly rather than silently
    scrambling the reduction.
    """
    global _EK_CACHE_KEY, _EK_CACHE_NETWORK

    ldd_np = np.asarray(ldd_np)
    shape = ldd_np.shape
    key = (shape, ldd_np.tobytes())

    if _EK_CACHE_NETWORK is not None and _EK_CACHE_KEY == key:
        return _EK_CACHE_NETWORK

    storage = _ek_from_d8(ldd_np, 'pcr_d8')

    # node order must match the LISFLOOD compressed order: earthkit keeps
    # cells whose d8 value is a valid pcr code (1..9); the model mask is
    # derived from the same Ldd, so the two must coincide exactly.
    ek_valid = _storage_mask(storage)
    lis_valid = (ldd_np > 0) & (ldd_np <= 9)   # same rule used by lddmask/boolean(Ldd)
    if not np.array_equal(ek_valid, lis_valid.ravel()):
        raise LisfloodWarning(
            'earthkit-hydro network mask does not match the model Ldd mask; '
            'falling back to PCRaster reductions.'
        )

    net = _EKRiverNetwork(storage)
    net.set_default_return_type(_EK_RETURN_TYPE)
    # coords are only used by the xarray decorator for metadata; supply a
    # minimal dict so the numpy path does not fail on None.items().
    net.coords = {'y': np.arange(shape[0]), 'x': np.arange(shape[1])}

    _EK_CACHE_KEY = key
    _EK_CACHE_NETWORK = net
    return net


def get_earthkit_network(ldd_np):
    """ Public entry: build (or fetch the cached) earthkit RiverNetwork for
    the given numpy Ldd. Raises ImportError if earthkit-hydro is missing so
    callers can fall back to the PCRaster path with a clear message.
    """
    if _ekh is None:
        raise ImportError(
            'useEarthkitHydro=True requires the earthkit-hydro package '
            '(pip install earthkit-hydro): %s' % _EKH_IMPORT_ERROR
        )
    return _network_from_ldd(ldd_np)


def ek_upstream_sum(net, field_1d, node_weights=None):
    """ earthkit equivalent of PCRaster accuflux / catchmenttotal over the
    full Ldd: for every node, the sum of the field over its whole upstream
    subnetwork (node itself included).

    field_1d      : 1D compressed array (LISFLOOD order == earthkit node order)
    node_weights  : optional per-node weights (e.g. PixelArea for m3 sums)
    returns       : 1D array over the same compressed order (values at
                    outside-network nodes are NaN by construction of the
                    masked return type; with LISFLOOD's Ldd there are none)
    """
    out = _ekh.upstream.sum(net, field_1d, node_weights=node_weights,
                            return_type=_EK_RETURN_TYPE)
    return np.asarray(out)


def model_precision():
    """ np dtype of the configured model precision
    (parallelization.get_model_dtype).

    Indirected here so that (a) bridge consumers do not each import the
    parallelization module and (b) tests can monkeypatch a deterministic
    dtype. Only callable when the import shim exposed it, i.e. earthkit-hydro
    is installed; guard call sites with earthkit_available().
    """
    from .parallelization import get_model_dtype
    return get_model_dtype()


def ek_upstream_mean(net, field_1d, node_weights, uparea_1d):
    """ earthkit equivalent of the PCRaster upstream-average pattern
        compressArray(catchmenttotal(x * PixelAreaPcr, Ldd) * InvUpArea).
    Returns the upstream-weighted mean directly, without ever building a
    2D PCRaster map (no decompress / numpy2pcr / pcrMul round-trips).
    Callers should cast the result to model_precision() where the historical
    compressArray dtype (the model dtype) matters downstream.
    """
    tot = ek_upstream_sum(net, field_1d, node_weights=node_weights)
    return tot * uparea_1d


def ek_zone_mean_at_gauges(net, field_1d, zone_codes_flat, n_codes):
    """ Numpy equivalent of PCRaster areaaverage(expr, spatialId): for each
    gauge-zone code, the mean of the field over the cells bearing that code
    (the zone cells themselves, NOT the upstream catchment).

    zone_codes_flat : 1D int array over the compressed cells; 0/negative =
                      not a gauge cell (mirrors the pcr2numpy gauge map with
                      nan replaced by -9999)
    n_codes         : number of gauge codes (max code)

    Returns a 1D array of length n_codes+1 where entry k is the zone-k mean
    (entry 0 unused). Cast to float32 by the caller to match PCRaster's
    engine output precision (same convention as sample_compressed).
    """
    valid = zone_codes_flat > 0
    codes = zone_codes_flat[valid].astype(np.int64)
    # codes may be non-contiguous (e.g. 5, 17, 42): size the arrays by the
    # largest actual code so every caller-side code index is addressable
    n_bins = max(int(codes.max()) + 1 if codes.size else 1, n_codes + 1)
    counts = np.bincount(codes, minlength=n_bins)
    sums = np.bincount(codes, weights=np.asarray(field_1d)[valid],
                       minlength=n_bins)
    with np.errstate(invalid='ignore', divide='ignore'):
        means = sums / counts
    return means


def compute_gauge_zone_codes(outletsmapnp, maskflat, n_codes):
    """ Zone codes over the compressed cells for multi-cell gauge zones.

    Equivalent of the PCRaster spatialId map flattened to LISFLOOD's compressed
    1D order: cells whose gauge code is finite and positive keep their code,
    every other in-domain cell becomes 0 (= not a gauge cell).

    outletsmapnp : 2D numpy gauge map (pcr2numpy of the spatialId, nan outside)
    maskflat     : MaskInfo.info.maskflat (True = outside the model domain)
    n_codes      : number of distinct gauge codes (self._ncodesId)

    Returns (zone_codes, n_codes) for ek_sample_zone_means /
    ek_zone_mean_at_gauges. Kept next to the sampling helper so all earthkit
    logic lives in this module (zusatz only calls it).
    """
    codes_flat_full = np.asarray(outletsmapnp).ravel(order='C')
    zone_codes = np.asarray(codes_flat_full[~np.asarray(maskflat, dtype=bool)])
    zone_codes = np.where(np.isfinite(zone_codes) & (zone_codes > 0),
                          zone_codes, 0).astype(np.int64)
    return zone_codes, int(n_codes)


def ek_sample_zone_means(tss_obj, array_1d):
    """ Standalone numpy replacement for TimeoutputTimeseries.sample() on
    MULTI-CELL gauge zones (the pcraster.areaaverage(expr, spatialId) path),
    operating on the 1D compressed array without any 2D map round-trip.

    tss_obj must carry the zone attributes prepared in
    TimeoutputTimeseries.__init__ via compute_gauge_zone_codes
    (_ek_zone_codes, _ek_n_codes). Semantics match the inherited .sample():
    per-zone mean for Scalar series, values stored as float32 (PCRaster engine
    output precision, verified against the engine in
    tests/test_earthkit_network.py), invalid/NaN stored as Decimal('NaN')
    (written as 1e31), and the tss file written on the final time step.
    """
    arrayRowPos = tss_obj._userModel.currentTimeStep() - tss_obj._userModel.firstTimeStep()
    # tss header datatype: the .sample() path records the expression's
    # PCRaster dataType; for the Scalar series routed here it is 'VALUESCALE.Scalar'.
    if tss_obj._spatialDatatype is None:
        tss_obj._spatialDatatype = 'VALUESCALE.Scalar'
    vals = np.asarray(array_1d, dtype=np.float64)
    # per-zone mean over the zone cells (entry 0 = not-a-zone, discarded)
    with np.errstate(invalid='ignore'):
        zone_means = ek_zone_mean_at_gauges(None, vals, tss_obj._ek_zone_codes,
                                            tss_obj._ek_n_codes)
    row = tss_obj._sampleValues[arrayRowPos]
    nan = Decimal("NaN")
    # map each gauge code to its column: codesId[k] is the k-th code
    # (sorted ascending, as produced by np.unique); column order in the
    # tss row follows codesId order exactly like the inherited .sample().
    for col in range(tss_obj._ncodesId):
        code = tss_obj._codesId[col]
        m = zone_means[code] if 0 < code < zone_means.size else np.nan
        # PCRaster areaaverage returns float32; cast for identical %14g
        m32 = np.float32(m) if np.isfinite(m) else m
        row[col] = float(m32) if np.isfinite(m32) else nan
    # Write the tss on the final step, mirroring the inherited .sample().
    if tss_obj._userModel.currentTimeStep() == tss_obj._userModel.nrTimeSteps():
        tss_obj._writeTssFile()