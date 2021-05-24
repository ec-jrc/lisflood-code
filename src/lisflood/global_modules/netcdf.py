import os
import xarray as xr
import numpy as np
import datetime
import pcraster
from netCDF4 import num2date, date2num
import time as xtime
from nine import range

from .settings import (calendar_inconsistency_warning, get_calendar_type, calendar, MaskAttrs, CutMap, NetCDFMetadata,
                       LisSettings, MaskInfo)
from .errors import LisfloodWarning, LisfloodError
from .decorators import iocache
from .zusatz import iterOpenNetcdf
# from .add1 import *
from .add1 import nanCheckMap, decompress


def get_core_dims(dims):
    if 'x' in dims and 'y' in dims:
        core_dims = ('y', 'x')
    elif 'lat' in dims and 'lon' in dims:
        core_dims = ('lat', 'lon')
    else:
        msg = 'Core dimension in netcdf file not recognised! Expecting (y, x) or (lat, lon), have '+str(dims)
        LisfloodError(msg)
    return core_dims


def mask_array_np(data, mask, crop):
    data_cut = data[:, crop[2]:crop[3], crop[0]:crop[1]]
    return data_cut[:, mask]



def mask_array(data, mask, crop, core_dims):
    n_data = int(mask.sum())
    masked_data = xr.apply_ufunc(mask_array_np, data,
                                 dask='parallelized',
                                 input_core_dims=[core_dims],
                                 exclude_dims=set(core_dims),
                                 output_dtypes=[data.dtype],
                                 output_core_dims=[['z']],
                                 output_sizes={'z': n_data},
                                 kwargs={'mask': mask, 'crop': crop})
    return masked_data


def compress_xarray(data):
    core_dims = get_core_dims(data.dims)
    maskinfo = MaskInfo.instance()
    mask = np.logical_not(maskinfo.info.mask)
    cutmap = CutMap.instance()
    crop = cutmap.cuts
    masked_data = mask_array(data, mask, crop, core_dims=core_dims)
    return masked_data


def uncompress_array(masked_data):
    maskinfo = MaskInfo.instance()
    data = maskinfo.info.maskall.copy()
    data[~maskinfo.info.maskflat] = masked_data[:]
    #mapnp = mapnp.reshape(maskinfo['shape']).data
    data = data.reshape(maskinfo.info.shape)
    return data


def date_from_step(binding, timestep):
    start = calendar(binding['CalendarDayStart'], binding['calendar_type'])
    dt_sec = float(binding['DtSec'])
    dt_day = float(dt_sec / 86400)
    # get date of current simulation step
    currentDate = calendar(timestep, binding['calendar_type'])
    if type(currentDate) is not datetime.datetime:
        currentDate = start + datetime.timedelta(days=(currentDate - 1) * dt_day)

    return currentDate


def date_range(binding):
    begin = calendar(binding['StepStart'])
    end = calendar(binding['StepEnd'])
    if type(begin) is float: 
        begin = date_from_step(binding, begin)
    if type(end) is float: 
        end = date_from_step(binding, end)

    # Not sure this is the best way but the calendar object does not help
    begin = np.datetime64(begin.strftime('%Y-%m-%d %H:%M'))
    end = np.datetime64(end.strftime('%Y-%m-%d %H:%M'))
    dt = np.timedelta64(int(binding['DtSec']),'s')

    return (begin, end+dt, dt)


def find_main_var(ds, path):
    variable_names = [k for k in ds.variables if len(ds.variables[k].dims) == 3]
    if len(variable_names) > 1:
        raise LisfloodWarning('More than one variable in dataset {}'.format(path))
    elif len(variable_names) == 0:
        raise LisfloodWarning('Could not find a valid variable in dataset {}'.format(path))
    else:
        var_name = variable_names[0]
    return var_name


class XarrayChunked():

    def __init__(self, data_path, dates, time_chunk):

        # load dataset using xarray
        if time_chunk != 'auto':
            time_chunk = int(time_chunk)
        data_path = data_path + ".nc" if not data_path.endswith('.nc') else data_path
        ds = xr.open_mfdataset(data_path, engine='netcdf4', chunks={'time': time_chunk}, combine='by_coords')
        var_name = find_main_var(ds, data_path)
        da = ds[var_name]

        # extract time range from binding
        # binding = LisSettings.instance().binding
        # dates = date_range(binding)  # extract date range from bindings
        date_range = np.arange(*dates, dtype='datetime64')
        da = da.sel(time=date_range)

        # compress dataset (remove missing values)
        self.masked_da = compress_xarray(da)

        # initialise class variables and load first chunk
        self.chunks = self.masked_da.chunks[0]
        self.ichunk = None
        self.chunk_index = None
        self.chunked_array = None
        self.load_chunk(timestep=0)

    def load_chunk(self, timestep):
        if self.ichunk is None:  # initialisation
            self.ichunk = 0
            self.chunk_index = [0, self.chunks[self.ichunk]]
        else:
            self.ichunk += 1
            self.chunk_index[0] = sum(self.chunks[:self.ichunk])
            self.chunk_index[1] = sum(self.chunks[:self.ichunk+1])

        chunked_dataset = self.masked_da.isel(time=range(self.chunk_index[0], self.chunk_index[1]))
        self.chunked_array = chunked_dataset.values  # triggers xarray computation
        # print('chunk {} loaded'.format(self.ichunk))

    def __getitem__(self, timestep):

        local_step = timestep - self.chunk_index[0]

        # if at the end of chunk, load new chunk
        if local_step == self.chunks[self.ichunk]:
            self.load_chunk(timestep)
            local_step = timestep - self.chunk_index[0]
            # print('loading array {} at step {}'.format(self.masked_da.name, timestep))

        if local_step < 0:
            msg = 'local step cannot be negative! timestep: {}, chunk: {} - {}', timestep, self.chunk_index[0], self.chunk_index[1]
            LisfloodError(msg)

        data = self.chunked_array[local_step]
        return data


@iocache
class XarrayCached(XarrayChunked):

    def __init__(self, data_path, dates):

        super().__init__(data_path, dates, '-1')


def get_core_dims(dims):
    if 'x' in dims and 'y' in dims:
        core_dims = ('y', 'x')
    elif 'lat' in dims and 'lon' in dims:
        core_dims = ('lat', 'lon')
    else:
        msg = 'Core dimension in netcdf file not recognised! Expecting (y, x) or (lat, lon), have '+str(dims)
        LisfloodError(msg)
    return core_dims


def get_space_coords(nrow, ncol, dim_lat_y, dim_lon_x):
    cell = pcraster.clone().cellSize()
    xl = pcraster.clone().west() + cell / 2
    xr = xl + ncol * cell
    yu = pcraster.clone().north() - cell / 2
    yd = yu - nrow * cell
    #lats = np.arange(yu, yd, -cell)
    #lons = np.arange(xl, xr, cell)
    coordinates = {}
    coordinates[dim_lat_y] = np.linspace(yu, yd, nrow, endpoint=False)
    coordinates[dim_lon_x] = np.linspace(xl, xr, ncol, endpoint=False)

    return coordinates


def write_header(var_name, netfile, DtDay,
                 value_standard_name, value_long_name, value_unit, data_format,
                 startdate, repstepstart, repstepend, frequency):

    nf1 = iterOpenNetcdf(netfile, "", 'w', format='NETCDF4')

    settings = LisSettings.instance()
    binding = settings.binding

    # general Attributes
    nf1.settingsfile = os.path.realpath(settings.settings_path)
    nf1.date_created = xtime.ctime(xtime.time())
    nf1.Source_Software = 'Lisflood Python'
    nf1.institution = "European Commission DG Joint Research Centre (JRC) - E1, D2 Units"
    nf1.creator_name = "Peter Burek, A de Roo, Johan van der Knijff"
    nf1.source = 'Lisflood output maps'
    nf1.keywords = "Lisflood, EFAS, GLOFAS"
    nf1.Conventions = 'CF-1.6'
    # Dimension
    not_valid_attrs = ('_FillValue', )
    meta_netcdf = NetCDFMetadata.instance()

    # projection
    if 'laea' in meta_netcdf.data:
        proj = nf1.createVariable('laea', 'i4')
        for i in meta_netcdf.data['laea']:
            setattr(proj, i, meta_netcdf.data['laea'][i])

    if 'lambert_azimuthal_equal_area' in meta_netcdf.data:
        proj = nf1.createVariable('lambert_azimuthal_equal_area', 'i4')
        for i in meta_netcdf.data['lambert_azimuthal_equal_area']:
            setattr(proj, i, meta_netcdf.data['lambert_azimuthal_equal_area'][i])

    # Space coordinates

    cutmap = CutMap.instance()
    nrow = np.abs(cutmap.cuts[3] - cutmap.cuts[2])
    ncol = np.abs(cutmap.cuts[1] - cutmap.cuts[0])

    dim_lat_y, dim_lon_x = get_core_dims(meta_netcdf.data)
    latlon_coords = get_space_coords(nrow, ncol, dim_lat_y, dim_lon_x)

    if dim_lon_x in meta_netcdf.data:
        lon = nf1.createDimension(dim_lon_x, ncol)  # x 1000
        longitude = nf1.createVariable(dim_lon_x, 'f8', (dim_lon_x,))
        valid_attrs = [i for i in meta_netcdf.data[dim_lon_x] if i not in not_valid_attrs]
        for i in valid_attrs:
            setattr(longitude, i, meta_netcdf.data[dim_lon_x][i])
    longitude[:] = latlon_coords[dim_lon_x]

    if dim_lat_y in meta_netcdf.data:
        lat = nf1.createDimension(dim_lat_y, nrow)  # x 950
        latitude = nf1.createVariable(dim_lat_y, 'f8', (dim_lat_y,))
        valid_attrs = [i for i in meta_netcdf.data[dim_lat_y] if i not in not_valid_attrs]
        for i in valid_attrs:
            setattr(latitude, i, meta_netcdf.data[dim_lat_y][i])
    latitude[:] = latlon_coords[dim_lat_y]


    if frequency is not None:  # output file with "time" dimension
        #Get initial and final dates for data to be stored in nerCDF file
        first_date, last_date = [startdate + datetime.timedelta(days=(int(k) - 1)*DtDay) for k in
                                 (repstepstart, repstepend)]
        # CM: Create time stamps for each step stored in netCDF file
        time_stamps = [first_date + datetime.timedelta(days=d*DtDay) for d in range(repstepend - repstepstart +1)]

        units_time = 'days since %s' % startdate.strftime("%Y-%m-%d %H:%M:%S.0")
        steps = (int(binding["DtSec"]) / 86400.) * np.arange(binding["StepStartInt"] - 1, binding["StepEndInt"])
        if frequency != "all":
            dates = num2date(steps, units_time, binding["calendar_type"])
            next_date_times = np.array([j + datetime.timedelta(seconds=int(binding["DtSec"])) for j in dates])
            if frequency == "monthly":
                months_end = np.array([dates[j].month != next_date_times[j].month for j in range(steps.size)])
                steps = steps[months_end]
            elif frequency == "annual":
                years_end = np.array([dates[j].year != next_date_times[j].year for j in range(steps.size)])
                steps = steps[years_end]
        nf1.createDimension('time', steps.size)
        time = nf1.createVariable('time', float, ('time'))
        time.standard_name = 'time'
        # time.units ='days since 1990-01-01 00:00:00.0'
        # time.units = 'hours since %s' % startdate.strftime("%Y-%m-%d %H:%M:%S.0")
        # CM: select the time unit according to model time step
        DtDay_in_sec = DtDay * 86400
        if DtDay_in_sec >= 86400:
            # Daily model time steps or larger
            time.units = 'days since %s' % startdate.strftime("%Y-%m-%d %H:%M:%S.0")
        elif DtDay_in_sec >= 3600 and DtDay_in_sec < 86400:
            # CM: hours to days model time steps
            time.units = 'hours since %s' % startdate.strftime("%Y-%m-%d %H:%M:%S.0")
        elif DtDay_in_sec >= 60 and DtDay_in_sec <3600:
            # CM: minutes to hours model time step
            time.units = 'minutes since %s' % startdate.strftime("%Y-%m-%d %H:%M:%S.0")

        time.calendar = binding["calendar_type"]
        nf1.variables["time"][:] = date2num(time_stamps, time.units, time.calendar)
        # for i in metadataNCDF['time']: exec('%s="%s"') % ("time."+i, metadataNCDF['time'][i])
        value = nf1.createVariable(var_name, 'd', ('time', dim_lat_y, dim_lon_x), zlib=True, fill_value=-9999, chunksizes=(1, nrow, ncol))
    else:
        value = nf1.createVariable(var_name, 'd', (dim_lat_y, dim_lon_x), zlib=True, fill_value=-9999)

    value.standard_name = value_standard_name
    value.long_name = value_long_name
    value.units = value_unit
    for var in meta_netcdf.data:
        if "esri_pe_string" in meta_netcdf.data[var]:
            value.esri_pe_string = meta_netcdf.data[var]['esri_pe_string']

    return nf1


def writenet(flag, inputmap, netfile, DtDay,
             value_standard_name, value_long_name, value_unit, data_format,
             startdate, repstepstart, repstepend, frequency=None):

    """ Write a netcdf stack

    :param flag: 0 netCDF file format; ?
    :param inputmap: values to be written to NetCDF file
    :param netfile: name of output file in NetCDF format
    :param DtDay: model timestep (self.var.DtDay)
    :param value_standard_name: variable name to be put into netCDF file
    :param value_long_name: variable long name to be put into netCDF file
    :param value_unit: variable unit to be put into netCDF file
    :param data_format: data format
    :param startdate: reference date to be used to get start date and end date for netCDF file from start step and end step
    :param: repstepstart: first reporting step
    :param: repstepend: final reporting step
    :param frequency:[None,'all','monthly','annual'] save to netCDF stack; None save to netCDF single
    :return: 
    """
    # prefix = netfile.split('/')[-1].split('\\')[-1].split('.')[0]
    flags = LisSettings.instance().flags
    var_name = os.path.basename(netfile)
    netfile += ".nc"
    
    if flag == 0:
        nf1 = write_header(var_name, netfile, DtDay,
                           value_standard_name, value_long_name, value_unit, data_format,
                           startdate, repstepstart, repstepend, frequency)
    else:
        nf1 = iterOpenNetcdf(netfile, "", 'a', format='NETCDF4')
    if flags['nancheck']:
        nanCheckMap(inputmap, netfile, value_standard_name)
    
    map_np = uncompress_array(inputmap)
    if frequency is not None:
        nf1.variables[var_name][flag, :, :] = map_np
        #value[flag,:,:]= mapnp
    else:
        # without timeflag
        nf1.variables[var_name][:, :] = map_np

    nf1.close()
