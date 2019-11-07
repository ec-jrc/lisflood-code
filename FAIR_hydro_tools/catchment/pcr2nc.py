from sys import argv
import pcraster as pcr
from collections import OrderedDict
from xarray import DataArray
from numpy import linspace, nan

if __name__ == '__main__':
    path_in, path_out = argv[1:]
    # info
    pcr.setclone(path_in)
    info = {}
    info['cell'] = pcr.clone().cellSize()
    info['x'] = pcr.clone().west()
    info['y'] = pcr.clone().north()
    info['col'] = pcr.clone().nrCols()
    info['row'] = pcr.clone().nrRows()
    # to netcdf
    ul_y = info['y'] - info['cell'] / 2.
    ul_x = info['x'] + info['cell'] / 2.
    coords = OrderedDict([('lat', linspace(ul_y, ul_y - (info['row'] - 1) * info['cell'], info['row'])),
                          ('lon', linspace(ul_x, ul_x + (info['col'] - 1) * info['cell'], info['col']))])
    DataArray(pcr.pcr2numpy(pcr.readmap(path_in), nan), coords, coords.keys()).to_netcdf(path_out)
