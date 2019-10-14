from sys import argv
import pyximport; pyximport.install(reload_support=True)
import os
import numpy as np
import pandas as pd
import fiona
import xarray as xr
from shapely.geometry import shape, Point
from collections import OrderedDict
from pylab import show, subplots
import geopandas as gpd
from numba import njit
from catchment_tools import upDownLookups, downstreamToUpstreamLookup, streamCumul, setUpstreamRoutedKinematic

IX_ADDS = np.array([(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]) # flow directions (row and column shifts in coordinate mesh)
SEA_CODE = {'lisflood': 0, 'esri': 255}
FLOW_CODE = {'lisflood': [2, 3, 6, 9, 8, 7, 4, 1, 5], 'esri': [4, 2, 1, 128, 64, 32, 16, 8, 255]}


@njit
def drainedNodes(upstream_lookup, outlet_ix):
    is_drained = np.zeros(upstream_lookup.shape[0], np.bool_)
    to_visit = is_drained.copy()
    to_visit[outlet_ix] = True
    while to_visit.any():
        is_drained[to_visit] = True
        ups_ixs = upstream_lookup[to_visit].ravel()
        ups_ixs = ups_ixs[ups_ixs != -1]
        to_visit[:] = False
        to_visit[ups_ixs] = True
    return is_drained


# ----------------------------------------------
# PUBLIC FUNCTIONS
# ----------------------------------------------
def decodeFlowMatrix(coded_d8, encoding):
    ''''''
    if encoding not in FLOW_CODE.keys():
        raise Exception('Flow direction matrix encoding \"{}\" not valid!'.format(encoding))
    flow_d8 = np.empty(coded_d8.shape, int)
    coded_d8[coded_d8 == SEA_CODE[encoding]] = FLOW_CODE[encoding][8]
    for old, new in zip(FLOW_CODE[encoding], range(9)):
        flow_d8[coded_d8 == old] = new
    return flow_d8

def streamLookups(flow_d8, land_mask):
    '''
    Compute the downstream lookup vector for a D8 water flow channel network,
    i.e. the adjecency list of the directed graph describing flow direction from each pixel.
    Arguments:
        flow_d8 (numpy.ndarray): flow direction values (0 to 7, see IX_ADDS) on coordinate mesh; shape = num_lat, num_lon.
        land_mask (numpy.ndarray): land mask on coordinate mesh.
    Returns:
        downstream lookup (numpy.ndarray): for each pixel, index of downstream pixel (-1 = none); size = num_pixels
        upstream lookup (numpy.ndarray): each row gives the immediately upstream pixels (-1 = fill value); size = num_pixels, max_ups_pixs <= 8
    '''
    flow_dir = np.ascontiguousarray(flow_d8)
    flow_dir[~land_mask] = 8
    num_pixs = land_mask.sum()
    land_points = -np.ones(land_mask.shape, int)
    land_points[land_mask] = np.arange(num_pixs, dtype=int)
    downstream_lookup, upstream_lookup = upDownLookups(flow_dir, np.ascontiguousarray(land_mask).astype(np.uint8), land_points, num_pixs, IX_ADDS)
    max_num_ups_pixs = max(1, np.any(upstream_lookup != -1, 0).sum()) # maximum number of upstreams pixels
    return downstream_lookup, np.ascontiguousarray(upstream_lookup[:,:max_num_ups_pixs])

def indexedToStreamLookups(indexed_downstream_lookup):
    '''Return the normal postitional lookup tables given an index-based downstream lookup table'''
    positions = pd.Series(np.arange(indexed_downstream_lookup.size), indexed_downstream_lookup.index)
    downstream_lookup = positions.loc[indexed_downstream_lookup.values].values
    downstream_lookup[np.isnan(downstream_lookup)] = -1
    downstream_lookup = np.ascontiguousarray(downstream_lookup).astype(int)
    num_ups = indexed_downstream_lookup.groupby(indexed_downstream_lookup).count()
    max_num_ups = np.uint32(num_ups.loc[num_ups.index != -1].max())
    return downstream_lookup, downstreamToUpstreamLookup(downstream_lookup, max_num_ups)

def streamCumulate(data, downstream_lookup, upstream_lookup):
    '''Start from upstream pixels, add pixel value to downstream one only if it has been already summed all its upstreams pixels'''
    num_upstreams = (upstream_lookup != -1).sum(1).astype(np.uint32)
    completed = (upstream_lookup == -1).all(1).astype(np.uint8)
    headwaters = np.where(np.logical_and(completed, downstream_lookup != -1))[0].astype(np.uint64)
    return streamCumul(data.astype(float), downstream_lookup, upstream_lookup, completed, headwaters, num_upstreams, np.uint64(completed.sum()))

def upstreamNodes(upstream_lookup, node):
    ''''''
    drained_nodes = np.array([node])
    new_nodes = drained_nodes.copy()
    while new_nodes.size:
        aux = upstream_lookup[new_nodes]
        new_nodes = aux[aux != -1]
        drained_nodes = np.append(drained_nodes, new_nodes)
    return drained_nodes

def sliceUniMesh(x_axis, y_axis, x_lims, y_lims):
    ''''''
    pix_len_x = pixLenUniAxis(x_axis)
    pix_len_y = pixLenUniAxis(y_axis)
    row_slice = slice(np.where(y_axis - pix_len_y / 2 < y_lims[1])[0][0],
                      1 + np.where(y_axis+pix_len_y / 2 > y_lims[0])[0][-1])
    col_slice = slice(np.where(x_axis + pix_len_x / 2 > x_lims[0])[0][0],
                      1 + np.where(x_axis - pix_len_x / 2 < x_lims[1])[0][-1])
    return row_slice, col_slice

def pixLenUniAxis(axis):
    ''''''
    return abs(axis[-1] - axis[0]) / (axis.size - 1)


if __name__ == '__main__':
    ldd_path, polygon_dir, out_path = argv[1:]
    # flow direction, land mask and coordinates
    with xr.open_dataset(ldd_path) as nc:
        flow_d8 = decodeFlowMatrix(nc.ldd1.values, 'lisflood')
        land_mask = ~np.isnan(nc.ldd1.values)
        coord = OrderedDict([('lon', nc.lon.values), ('lat', nc.lat.values)])
        lon, lat = [c[land_mask] for c in np.meshgrid(nc.lon.values, nc.lat.values)]
    # number of upstream pixels
    downstream_lookup, upstream_lookup = streamLookups(flow_d8, land_mask)
    num_ups_pixs = streamCumulate(np.ones(land_mask.sum()), downstream_lookup, upstream_lookup)
    # allocate catchment mask stack
    polygon_files = [d for d in os.listdir(polygon_dir) if d.endswith('.shp')]
    catchment_masks = np.zeros((len(polygon_files), ) + land_mask.shape, bool)
    borders = []
    # loop through basin shapefiles
    for j, p_f in enumerate(polygon_files):
        # basin polygon and pixels in it (optimize using bounding box)
        raw_geometry = fiona.open(os.path.join(polygon_dir, p_f)).next()['geometry']
        basin_polygon = shape(raw_geometry)
        in_basin = gpd.GeoSeries([Point(x, y) for x, y in zip(lon, lat)]).within(basin_polygon)
        borders.append(np.array(raw_geometry['coordinates']).squeeze())
        # derive catchment mask as the area drained by the most downstream pixel in the polygon
        outlet_ix = np.where(in_basin, num_ups_pixs, np.zeros(land_mask.sum())).argmax()
        catchment_masks[j,land_mask] = drainedNodes(upstream_lookup, outlet_ix)
        print('shapefile {} processed'.format(p_f))
    # write union mask to netcdf
    union_mask = catchment_masks.any(0)
    b_path = os.path.join(os.path.dirname(out_path), '_bool.'.join(os.path.basename(out_path).split('.')))
    xr.DataArray(union_mask, dims=['lat','lon'], coords=coord).to_netcdf(b_path)
    # write nan mask to netcdf
    nan_mask = union_mask.astype(float)
    nan_mask[nan_mask == 0] = np.nan
    nan_mask = xr.DataArray(nan_mask, dims=['lat','lon'], coords=coord)
    n_path = os.path.join(os.path.dirname(out_path), '_nan.'.join(os.path.basename(out_path).split('.')))
    nan_mask.to_netcdf(n_path)

#    # test figure
#    fig, ax = subplots()
#    import ipdb; ipdb.set_trace()
#    nan_mask.plot(ax=ax)
#    for xy in borders:
#        ax.plot(xy[:,0], xy[:,1])
#    show(fig)
