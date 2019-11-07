import os
from sys import argv
import pylab as pl
import xarray as xr
from ipdb import set_trace as bp

#$ python2 mask_input_maps.py /DATA/gelatem/FAIR_workshop/Lisflood01degree/ lorentz_6 settings4bmi

isInputMap = lambda f: any([f.endswith(x) for x in ['.nc', '.map']])
isInSettings = lambda f, xml_lines: any([f.split('.')[0] in l for l in xml_lines])

def maskNetCDF(path_in, path_out, mask_out):
    nc = xr.open_dataset(path_in).copy()
    data_var = [v for v in nc.data_vars.keys() if nc[v].shape == mask_out.shape]
    if len(data_var):
        try:
            nc[data_var[0]].values[mask_out] = pl.nan
        except:
            nc[data_var[0]].values[mask_out] = nc[data_var[0]].min()
        nc.to_netcdf(path_out)
        nc.close()
        print('{} masked to {}'.format(path_in, path_out))

if __name__ == '__main__':
    # shell arguments
    dir_setup, name_mask, name_settings = argv[1:]
    path_settings = os.path.join(os.path.split(os.path.dirname(os.path.abspath(__file__)))[0], 'settings_Lisflood', name_settings + '.xml')
    path_mask = os.path.join(dir_setup, 'areamaps', name_mask + '_bool.nc')
    # new setup folder name
    subdir_in = [dd for dd in dir_setup.split(os.sep) if len(dd)][-1]
    subdir_out = subdir_in + '_masked'
    # load settings and mask
    lines_settings = open(path_settings, 'r').readlines()
    mask_out = ~xr.open_dataarray(path_mask).values
    # walk through dir_setup, check if file name (without extension) appears in the settings file; if so, load it, mask it, write to netcdf in clone directory tree
    branches = [(_dir, _files) for _dir, _, _files in os.walk(dir_setup) if len(_files) and any([isInputMap(f) and isInSettings(f, lines_settings) for f in _files])]
    for folder_in, files in branches:
        folder_out = folder_in.replace(subdir_in, subdir_out)
        if not os.path.exists(folder_out):
            os.makedirs(folder_out)
        for f_in in files:
            if f_in.endswith('.map'):
                f_out = f_in.replace('.map', '.nc')
                os.system('python2 pcr2nc.py {} {}'.format(*[os.path.join(folder_in, k) for k in (f_in, f_out)]))
                data = maskNetCDF(os.path.join(folder_in, f_out), os.path.join(folder_out, f_out), mask_out)
            elif f_in.endswith('.nc'):
                data = maskNetCDF(os.path.join(folder_in, f_in), os.path.join(folder_out, f_in), mask_out)
