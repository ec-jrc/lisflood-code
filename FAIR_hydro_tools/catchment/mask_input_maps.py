import os
from sys import argv
import xarray as xr

if __name__ == '__main__':
    dir_setup, path_mask, path_settings = argv[1:]
    # walk through dir_setup, check if file name (without extension) appears in the settings file; if so, load it, mask it, write to netcdf in clone directory tree
