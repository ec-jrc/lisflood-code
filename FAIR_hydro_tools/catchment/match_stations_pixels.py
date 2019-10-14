#! /usr/bin/python2
import os
import re
import numpy as np
import pandas as pd
import xarray as xr
from sys import argv
from collections import OrderedDict
from catchment import decodeFlowMatrix, streamLookups, streamCumulate

RIVER_GRDC = {'merrimack': 'MERRIMACK', 'meuse': 'MAAS', 'rhine': 'RHINE'}
RE_SHP = re.compile('([a-z]+)_hydrosheds[a-z0-9_]*\.shp')
RE_NUM = '.+:\s+([\d\-\.]+)'
RE_STR = ':\s+([A-Z,\s]+)\\r\\n'
RE_DATA = OrderedDict([(k, re.compile(k + v)) for k, v in zip(['Station', 'Longitude', 'Latitude', 'Catchment area'], [RE_STR] + 3*[RE_NUM])])
MATCH_COLS = ['Row_model', 'Col_model', 'Lon_model', 'Lat_model', 'Drained_A_model']

def findStationPixel(x_station, y_station, a_drained_station, X_model, Y_model, mask, ldd, A_pixel, num_pixels):
    """Find best-matching model pixel for a discharge station: among the closest <num_pixels> grid-cells,
    the one with the closest upstream drained area is chosen."""
    downstream_lookup, upstream_lookup = streamLookups(decodeFlowMatrix(ldd, 'lisflood'), mask)
    A_drained_model = streamCumulate(A_pixel[mask], downstream_lookup, upstream_lookup)
    ix_grid_nearest = ((x_station - X_model[mask])**2 + (y_station - Y_model[mask])**2).argsort()[:num_pixels]          #| choose the grid-cell with the closest
    best_land_pixel = ix_grid_nearest[np.abs(A_drained_model[ix_grid_nearest] - a_drained_station).argmin()]#| drained area among the nearest pixels
    row, col = [k[best_land_pixel] for k in np.where(mask)]
    return row, col, A_drained_model[best_land_pixel]

if __name__ == '__main__':
    # Shell arguments: GRDC data folder, catchment polygon folder, flow direction matrix (ldd) path, output path
    dir_grdc, dir_polygons, dir_setup = argv[1:]
    path_mask = os.path.join(dir_setup, 'areamaps', 'lorentz_bool.nc')
    path_ldd = os.path.join(dir_setup, 'maps_netcdf', 'ldd.nc')
    # GRDC names of river basins
    search_shapefiles = [re.match(RE_SHP, f) for f in os.listdir(dir_polygons)]
    names_rivers = [RIVER_GRDC[m.group(1)] for m in search_shapefiles if m is not None]
    # Station meta-data
    meta_data = pd.concat([pd.DataFrame(index=names_rivers, columns=['Observation_file'] + RE_DATA.keys()), pd.DataFrame(columns=MATCH_COLS)], 1)
    for riv in names_rivers:
        for _f in os.listdir(dir_grdc):
            path_obs = os.path.join(dir_grdc, _f)
            header = open(path_obs).readlines()[:35]
            if riv in ''.join(header):
                meta_data.loc[riv,'Observation_file'] = path_obs
                meta_data.loc[riv,RE_DATA.keys()] = [re.search(regex, [l for l in header if k in l][0]).group(1) for k, regex in RE_DATA.iteritems()]
    meta_data.iloc[:,2:] = meta_data.iloc[:,2:].astype(float)
    # Model domain simulated mask, coordinates, grid-cell areas, flow direction (ldd)
    with xr.open_dataarray(path_mask) as nc:
        mask = nc.values
        LON_model, LAT_model = np.meshgrid(nc.lon.values, nc.lat.values)
        half_pix = (nc.lon.values[1] - nc.lon.values[0]) / 2.
    area_gridcell = xr.open_dataset(os.path.join(dir_setup, 'maps_netcdf', 'pixarea.nc')).pixarea.values / 1e6 # km2
    ldd = xr.open_dataset(path_ldd).ldd1.values
    # Match GRDC stations to model grid-cells
    for riv, _data in meta_data.iterrows():
        row, col, ups_a = findStationPixel(_data.Longitude, _data.Latitude, _data['Catchment area'], LON_model, LAT_model, mask, ldd, area_gridcell, 9)
        meta_data.loc[riv,MATCH_COLS] = (row, col, LON_model[row,col], LAT_model[row,col], ups_a)
    # Save station-pixel match data
    path_out = os.path.join(dir_setup, 'station-pixel_matches.json')
    meta_data.to_json(path_out)
    print('\nThe station-pixel correspondence table to compare simulated and reported streamflow is saved to {}\n'.format(path_out))
#    # Interactive figure to check matches
#    from pylab import *
#    downstream_lookup, upstream_lookup = streamLookups(decodeFlowMatrix(ldd, 'lisflood'), mask)
#    A_drained_model_map = full(mask.shape, nan)
#    A_drained_model_map[mask] = streamCumulate(area_gridcell[mask], downstream_lookup, upstream_lookup)
#    coords_plot = meshgrid(linspace(LON_model.min() - half_pix, LON_model.max() + half_pix, LON_model.shape[1] + 1),
#                           linspace(LAT_model.max() + half_pix, LAT_model.min() - half_pix, LON_model.shape[0] + 1))
#    fig, ax = subplots()
#    ax.pcolormesh(coords_plot[0], coords_plot[1], log10(A_drained_model_map), cmap= 'Blues')
#    for riv, _data in meta_data.iterrows():
#        ax.plot(_data.Longitude, _data.Latitude, 'ms', markersize=8)
#        ax.plot(_data.Lon_model, _data.Lat_model, 'm*', markersize=8)
#        ax.text(_data.Longitude, _data.Latitude, riv + ' (GRDC)')
#        ax.text(_data.Lon_model, _data.Lat_model, riv + ' (model)')
#    show(fig)
#    import ipdb; ipdb.set_trace()
