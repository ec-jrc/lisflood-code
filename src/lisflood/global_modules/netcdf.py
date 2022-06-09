import os
import glob
import xarray as xr
import numpy as np
import datetime
import pcraster
from netCDF4 import num2date, date2num
import time as xtime
from nine import range
from pyproj import Proj

from .settings import (calendar_inconsistency_warning, get_calendar_type, calendar, MaskAttrs, CutMap, NetCDFMetadata,
                       LisSettings, MaskInfo)
from .errors import LisfloodWarning, LisfloodError
from .decorators import Cache, cached
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
                                 dask_gufunc_kwargs = dict(output_sizes={'z': n_data}),
                                 kwargs={'mask': mask, 'crop': crop})
    return masked_data


def compress_xarray(mask, crop, data):
    core_dims = get_core_dims(data.dims)
    masked_data = mask_array(data, mask, crop, core_dims=core_dims)
    return masked_data


def uncompress_array(masked_data):
    maskinfo = MaskInfo.instance()
    data = maskinfo.info.maskall.copy()
    data[~maskinfo.info.maskflat] = masked_data[:]
    #mapnp = mapnp.reshape(maskinfo['shape']).data
    data = data.reshape(maskinfo.info.shape)
    return data


def find_main_var(ds, path):
    variable_names = [k for k in ds.variables if len(ds.variables[k].dims) == 3]
    if len(variable_names) > 1:
        raise LisfloodWarning('More than one variable in dataset {}'.format(path))
    elif len(variable_names) == 0:
        raise LisfloodWarning('Could not find a valid variable in dataset {}'.format(path))
    else:
        var_name = variable_names[0]
    return var_name


def check_dataset_calendar_type(ds, path):

    settings = LisSettings.instance()
    binding = settings.binding

    # check calendar type
    # if using multiple files, the encoding will be droppped (bug in xarray), let's check the calendar fom the first file
    if '*' in path:
        ds = xr.open_dataset(glob.glob(path)[0], chunks={'time': -1})
    
    calendar = ds.time.encoding['calendar']
    if calendar != binding['calendar_type']:
        print('WARNING! Wrong calendar type in dataset {}, is \"{}\" and should be \"{}\"\n Please double check your forcing datasets and update them to use the correct calendar type'.format(path, ds.time.encoding['calendar'], binding['calendar_type']))


def date_from_step(binding, timestep):
    start = calendar(binding['CalendarDayStart'], binding['calendar_type'])
    dt_sec = float(binding['DtSec'])
    dt_day = float(dt_sec / 86400)
    # get date of current simulation step
    currentDate = calendar(timestep, binding['calendar_type'])
    if type(currentDate) is not datetime.datetime:
        currentDate = start + datetime.timedelta(days=(currentDate - 1) * dt_day)

    return currentDate


def run_date_range(binding):

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


def dataset_date_range(run_dates, dataset, indexer):
    if indexer is None:
        date_range = np.arange(*run_dates, dtype='datetime64')
    else:
        begin = dataset.time.sel(time=run_dates[0], method=indexer).values
        end = dataset.time.sel(time=run_dates[1], method=indexer).values
        # using nearest date, dt is max between dataset and model
        ds_dt = (dataset.time[1]-dataset.time[0]).values
        run_dt = run_dates[2]
        if run_dt > ds_dt:
            date_range = np.arange(begin, end, run_dt, dtype='datetime64')
        else:
            date_range = slice(begin, end)

    return date_range


def replace_dates_year(dates, year):
    dates_new  = [np.datetime64(str(year)+'-'+np.datetime_as_string(date)[5:]) for date in dates]
    return dates_new


def map_dates_index(dates, time, indexer, climatology=False):

    dates_run = np.arange(*dates, dtype='datetime64')

    if climatology:  # use 2020 as a leap year reference
        dates_run = replace_dates_year(dates_run, 2020)
        dates_dataset = replace_dates_year(time.values, 2020)
        time = time.assign_coords({'time': dates_dataset})

    run_dates = time.sel(time=dates_run, method=indexer).values

    dates_map = dict(zip(time.values, range(len(time))))
    index_map = [dates_map[date] for date in run_dates]

    return index_map


class XarrayChunked():

    def __init__(self, data_path, time_chunk, dates, indexer=None, climatology=False):

        # load dataset using xarray
        if time_chunk != 'auto' and time_chunk is not None:
            time_chunk = int(time_chunk)
        data_path = data_path + ".nc" if not data_path.endswith('.nc') else data_path
        ds = xr.open_mfdataset(data_path, engine='netcdf4', chunks={'time': time_chunk}, combine='by_coords')

        # check calendar type
        check_dataset_calendar_type(ds, data_path)

        # extract main variable
        var_name = find_main_var(ds, data_path)
        da = ds[var_name]

        # extract time range
        if not climatology and dates[0] < da.time[-1].values:
            date_range = dataset_date_range(dates, da, indexer)  # array of dates
            da = da.sel(time=date_range)
        self.index_map = map_dates_index(dates, da.time, indexer, climatology)

        # compress dataset (remove missing values and flatten the array)
        maskinfo = MaskInfo.instance()
        mask = np.logical_not(maskinfo.info.mask)
        cutmap = CutMap.instance()
        crop = cutmap.cuts
        self.dataset = compress_xarray(mask, crop, da) # final dataset to store

        # initialise class variables and load first chunk
        self.init_chunks(self.dataset, time_chunk)

    def init_chunks(self, dataset, time_chunk):
        # compute chunks indexes in dataset
        chunks = self.dataset.chunks[0]  # list of chunks indexes in dataset
        if (time_chunk==-1) or time_chunk is None:  # ensure we only have one chunk when dealing with multiple files
            chunks = [np.sum(chunks)]
        self.chunk_indexes = []
        for i in range(len(chunks)):
            self.chunk_indexes.append(int(np.sum(chunks[:i])))
        self.chunk_indexes.append(int(np.sum(chunks)))

        # load first chunk
        self.ichunk = -1
        self.load_next_chunk()

    def load_next_chunk(self):
        self.ichunk += 1
        begin = self.chunk_indexes[self.ichunk]
        end = self.chunk_indexes[self.ichunk+1]
        
        chunk = self.dataset.isel(time=range(begin, end))
        self.dataset_chunk = chunk.load()  # triggers xarray computation

    def __getitem__(self, step):

        dataset_index = self.index_map[step]

        # if at the end of chunk, load new chunk
        if dataset_index == self.chunk_indexes[self.ichunk+1]:
            self.load_next_chunk()

        local_index = dataset_index - self.chunk_indexes[self.ichunk]

        if local_index < 0:
            msg = 'local step cannot be negative! step: {}, chunk: {} - {}', local_index, self.chunk_index[self.ichunk], self.chunk_index[self.ichunk+1]
            LisfloodError(msg)

        data = self.dataset_chunk.values[local_index]
        return data


@Cache
class XarrayCached(XarrayChunked):

    def __init__(self, data_path, dates, indexer=None, climatology=False):
        super().__init__(data_path, None, dates, indexer, climatology)


def xarray_reader(dataname, indexer=None, climatology=False):
    """ Reads a netcdf time series using Xarray
    
    Parameters
    ----------
    dataname : str
        Name of data to read (used to extract file path from bindings)
    indexer : str
        How to index time data (None=exact date, ffill=latest date in dataset (following Xarray sel API))
    climatology : bool
        Climatology dataset: one-year time series, no chunking    
    
    Returns
    -------
    object
        Xarray reader object, can be accessed as a simple array/list
    """

    # get bindings
    settings = LisSettings.instance()
    binding = settings.binding

    data_path = binding[dataname]

    # extract run date range from bindings -> (begin, end, step)
    dates = run_date_range(binding)

    # extract chunk from bindings
    time_chunk = binding['NetCDFTimeChunks']  # -1 to load everything, 'auto' to let xarray decide

    if binding['MapsCaching'] == "True":
        data = XarrayCached(data_path, dates, indexer, climatology)
    else:
        if climatology:  # for climatology, load the entire dataset
            data = XarrayChunked(data_path, None, dates, indexer, climatology)
        else:
            data = XarrayChunked(data_path, time_chunk, dates, indexer, climatology)
    
    return data


def coordinatesLand(eastings_forcing, northings_forcing):
    """"""
    maskattrs = MaskAttrs.instance()
    half_cell = maskattrs['cell'] / 2.
    top_row = np.where(np.round(northings_forcing, 5) == np.round(maskattrs['y'] - half_cell, 5))[0][0]
    left_col = np.where(np.round(eastings_forcing, 5) == np.round(maskattrs['x'] + half_cell, 5))[0][0]
    row_slice = slice(top_row, top_row + maskattrs['row'])
    col_slice = slice(left_col, left_col + maskattrs['col'])
    maskinfo = MaskInfo.instance()
    return [co[row_slice, col_slice][~maskinfo.info.mask] for co in np.meshgrid(eastings_forcing, northings_forcing)]


@Cache
def read_lat_from_template_cached(netcdf_template, proj4_params):
    return read_lat_from_template_base(netcdf_template, proj4_params)


def read_lat_from_template_base(netcdf_template, proj4_params):
    nc_template = netcdf_template + ".nc" if not netcdf_template.endswith('.nc') else netcdf_template
    with xr.open_dataset(nc_template) as nc:
        if all([co in nc.dims for co in ("x", "y")]):
            try:
                # look for the projection variable
                proj_var = [v for v in nc.data_vars.keys() if 'proj4_params' in nc[v].attrs.keys()][0]
                # proj4 string
                proj4_params = nc[proj_var].attrs['proj4_params']
                # projection object obtained from the PROJ4 string
            except IndexError:
                if proj4_params is None:
                    raise Exception("If using projected coordinates (x, y), a variable with the 'proj4_params' "
                                    "attribute must be included in the precipitation file or in settings file!")

            # projection object obtained from the PROJ4 string
            projection = Proj(proj4_params)
            _, lat_deg = projection(*coordinatesLand(nc.x.values, nc.y.values), inverse=True)  # latitude (degrees)
        else:
            _, lat_deg = coordinatesLand(nc.lon.values, nc.lat.values)  # latitude (degrees)

    return lat_deg


def read_lat_from_template(binding):
    netcdf_template = binding["netCDFtemplate"]
    proj4_params = binding.get('proj4_params', None)

    if binding['MapsCaching'] == "True":
        lat_deg = read_lat_from_template_cached(netcdf_template, proj4_params)
    else:
        lat_deg = read_lat_from_template_base(netcdf_template, proj4_params)

    return lat_deg


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
            dates = num2date(steps-binding["StepStartInt"]+1, units_time, binding["calendar_type"])
            next_date_times = np.array([j + datetime.timedelta(seconds=int(binding["DtSec"])) for j in dates])
            if frequency == "monthly":
                months_end = np.array([dates[j].month != next_date_times[j].month for j in range(repstepend - repstepstart +1)])
                steps_monthly = steps[months_end]
                time_stamps_monthly = dates[months_end==True]
            elif frequency == "annual":
                years_end = np.array([dates[j].year != next_date_times[j].year for j in range(steps.size)])
                steps = steps[years_end]
        if frequency == "all":
           nf1.createDimension('time', steps.size)
           time = nf1.createVariable('time', float, ('time'))
           time.standard_name = 'time'
        if frequency == "monthly":
           nf1.createDimension('time', steps_monthly.size)
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
 
        if frequency == "all":
           nf1.variables["time"][:] = date2num(time_stamps, time.units, time.calendar)
        if frequency == "monthly":
           nf1.variables["time"][:] = date2num(time_stamps_monthly, time.units, time.calendar)                  
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
