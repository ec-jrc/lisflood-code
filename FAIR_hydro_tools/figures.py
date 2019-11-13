import os
import pyproj
import pandas as pd
import xarray as xr
from sys import argv
from collections import OrderedDict
from pylab import *
from catchment.match_stations_pixels import findStationPixel, decodeFlowMatrix, streamLookups, streamCumulate

DIR_BENCH = '/DATA/gelatem/FAIR_workshop/benchmark_discharge_simulations/'
SIM_DIS = {'WFDEI_0.1deg': os.path.join(DIR_BENCH, 'E2O_Tier1_WFDEI_100_dis.nc'),
           'MSWEP_0.1deg': os.path.join(DIR_BENCH, 'E2O_Tier2_MSWEP_100_dis.nc'),
           'EMO5_5km': os.path.join(DIR_BENCH, 'Europe_5km_dis.nc')}

def dischargePlot(riv, data, info, simulation, dir_out):
    df = data.loc[:,riv].copy()
    df.Observed.loc[df.Observed < 0] = nan # TEMPORARY: REMOVE AFTER 1990-1996 SIMULATION IS RE-RUN
    df.Simulated *= info.loc[riv,'Catchment area'] / info.loc[riv,'Drained_A_model']
    ok = df.Observed.notnull()
    stats = OrderedDict()
    stats['bias'] = df.loc[ok,'Simulated'].mean() / df.loc[ok,'Observed'].mean() - 1
    stats['std err'] = df.loc[ok,'Simulated'].std() / df.loc[ok,'Observed'].std() - 1
    stats['corr'] = df.loc[ok].corr().values[0,1]
    stats['KGE'] = 1 - sqrt(stats['bias']**2 + stats['std err']**2 + (1 - stats['corr'])**2)
    stats['NSE'] = 1 - sum((df.loc[ok,'Simulated'] - df.loc[ok,'Observed'])**2) / sum((df.loc[ok,'Observed'] - df.loc[ok,'Observed'].mean())**2)
    fig, ax = subplots()
    df.plot(ax=ax)
    ax.set_ylabel('River discharge $\\left({\\rm m}^{3}{\\rm s}^{-1}\\right)$')
    ax.set_title('{} simulation\n{} at {}\n'.format(simulation, riv, info.loc[riv,'Station']) +
                 ', '.join(['{}: {:.2f}'.format(k, v) for k, v in stats.items()]))
    path_fig = os.path.join(dir_out, '{}_{}.pdf'.format(simulation, riv)
    fig.savefig(path_fig)
    print('Discharge plot written to ' + path_fig)
    close(fig)
    del fig


if __name__ == "__main__":
    dir_out = argv[1]
    path_time_series = os.path.join(dir_out, 'discharge_comparison.pickle')
    # ERA5 at 0.1 degree
    info = pd.read_json('/DATA/gelatem/FAIR_workshop/Lisflood01degree/station-pixel_matches.json')
    discharge = pd.read_pickle(path_time_series).astype(float)
    for riv in info.index:
        dischargePlot(riv, discharge, info, 'ERA5_0.1deg', dir_out)
    # WFDEI and MSWEP at 0.1 degree
    for name in ('WFDEI_0.1deg', 'MSWEP_0.1deg'):
        sim = xr.open_dataset(SIM_DIS[name]).dis.loc[str(discharge.index[0]):str(discharge.index[-1])].load()
        dis = discharge.copy()
        dis.loc[:,dis.columns.get_level_values(1) == 'Simulated'] = nan
        for riv in info.index:
            dis.loc[:,(riv, 'Simulated')] = sim[:,info.loc[riv,'Row_model'],info.loc[riv,'Col_model']].values
            dischargePlot(riv, dis, info, name, dir_out)
    # Europe at 5 km
    name = 'EMO5_5km'
    sim = xr.open_dataset(SIM_DIS[name]).dis.loc[str(discharge.index[0]):str(discharge.index[-1])].load()
    with xr.open_dataset('/H01_FRESH_WATER/Europe/LisfloodEurope/maps_netcdf/area.nc') as nc:
        projection = pyproj.Proj(nc.laea.proj4_params)
        mask = ~isnan(nc.area.values)
        X_model, Y_model = meshgrid(nc.x.values, nc.y.values)
    #    half_pix = (nc.x.values[1] - nc.x.values[0]) / 2. # CHECK STATION MATCH
    A_pixel = full(mask.shape, 25.)
    ldd = xr.open_dataset('/H01_FRESH_WATER/Europe/LisfloodEurope/maps_netcdf/ldd.nc').ldd.values
    #downstream_lookup, upstream_lookup = streamLookups(decodeFlowMatrix(ldd, 'lisflood'), mask) # CHECK STATION MATCH
    #A_drained_model_map = full(mask.shape, nan) # CHECK STATION MATCH
    #A_drained_model_map[mask] = streamCumulate(A_pixel[mask], downstream_lookup, upstream_lookup) # CHECK STATION MATCH
    #coords_plot = meshgrid(linspace(X_model.min() - half_pix, X_model.max() + half_pix, X_model.shape[1] + 1),
    #                       linspace(Y_model.max() + half_pix, Y_model.min() - half_pix, X_model.shape[0] + 1))  # CHECK STATION MATCH
    #fig, ax = subplots() # CHECK STATION MATCH
    #ax.pcolormesh(coords_plot[0], coords_plot[1], log10(A_drained_model_map), cmap= 'Blues') # CHECK STATION MATCH
    dis = discharge.copy()
    dis.loc[:,dis.columns.get_level_values(1) == 'Simulated'] = nan
    for riv, _data in info.iterrows():
        if riv not in ('MAAS', 'RHINE'):
            continue
        x_station, y_station = projection(_data.Longitude, _data.Latitude)
        row, col, ups_a = findStationPixel(x_station, y_station, _data['Catchment area'], X_model, Y_model, mask, ldd, A_pixel, 9)
        dis.loc[:,(riv, 'Simulated')] = sim[:,row,col].values
        dischargePlot(riv, dis, info, name, dir_out)
    #    # CHECK STATION MATCH WITH INTERACTIVE FIGURE
    #    ax.plot(x_station, y_station, 'ms', markersize=8)
    #    ax.plot(X_model[row,col], Y_model[row,col], 'm*', markersize=8)
    #    ax.text(x_station, y_station, riv + ' (GRDC)')
    #    ax.text(X_model[row,col], Y_model[row,col], riv + ' (model)')
    #import ipdb; ipdb.set_trace()
    #show(fig)
