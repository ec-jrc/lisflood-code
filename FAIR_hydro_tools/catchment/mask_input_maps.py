import os
from sys import argv, stdout
from shutil import copyfile
import pylab as pl
import xarray as xr
import netCDF4
from ipdb import set_trace as bp

#$ python2 mask_input_maps.py /DATA/gelatem/FAIR_workshop/Lisflood01degree/ /DATA/gelatem/FAIR_workshop/areamaps/lorentz_6_bool.nc settings4bmi

isInputMap = lambda f: any([f.endswith(x) for x in ['.nc', '.map']])
isInSettings = lambda f, xml_lines: any([f.split('.')[0] in l for l in xml_lines])

def maskNetCDF(path_in, path_out, mask_out):
    # file info
    with xr.open_dataset(path_in, decode_times=False) as nc:
        var_data = [v for v in nc.data_vars.keys() if len(nc[v].dims) > 1][0]
        if not all([x in nc[var_data].shape for x in mask_out.shape]):
            print(path_in + ' not masked (not a global file!)')
            return
        dims = nc[var_data].dims
        dtype = str(nc[var_data].dtype)
    # fill value
    if 'float' in dtype:
        fill = pl.nan
    elif 'bool' in dtype:
        fill = False
    elif 'int' in dtype:
        fill = pl.iinfo(dtype).min
    else:
        bp()
    # masking
    if len(dims) == 2:
        ds = xr.open_dataset(path_in, decode_times=False).load()
        ds[var_data].values[mask_out] = fill
        ds.to_netcdf(path_out, encoding={var_data: {'zlib': True, 'complevel': 4}})
    elif len(dims) == 3:
        print('processing 3D file {} ...'.format(path_in))
        copyfile(path_in, path_out)
        with netCDF4.Dataset(path_out, 'a') as nc:
            num_steps = nc.variables[var_data].shape[0]
            for t in xrange(num_steps):
                vals = nc.variables[var_data][t]
                vals[mask_out] = fill
                nc.variables[var_data][t] = vals
                showProgress(t, num_steps)
    else:
        bp()
    print('{} masked to {}'.format(path_in, path_out))

def showProgress(iter_ix, num_iters, bar_len=49):
    '''
    Print progress bar with percentage.
    Arguments:
        iter_ix (int): iteration index (zero-based).
        num_iters (int): total number of iterations.
        bar_len (int): bar length.
    '''
    i = iter_ix + 1
    progress = float(i) / num_iters
    arrow_len = int(round((bar_len * progress)))
    percent = str(int(round(100 * progress))).zfill(2)
    stdout.write('\r[{0}>{1}] {2}% ({3} of {4})'.format('-' * arrow_len, ' ' * (bar_len - arrow_len), percent, str(i), str(num_iters)))
    stdout.flush()
    if i == num_iters:
        print('\n')

if __name__ == '__main__':
    # shell arguments
    dir_setup, path_mask, name_settings = argv[1:]
    path_settings = os.path.join(os.path.split(os.path.dirname(os.path.abspath(__file__)))[0], 'settings_Lisflood', name_settings + '.xml')
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
