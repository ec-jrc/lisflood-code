import os
import glob
from re import L
import xarray as xr
import numpy as np
import datetime
import pcraster
from netCDF4 import num2date, date2num
import time as xtime
from nine import range
from pyproj import Proj

from .settings import (calendar_inconsistency_warning, get_calendar_type, calendar, MaskAttrs, CutMap, NetCDFMetadata,
                       LisSettings, MaskInfo, CDFFlags, inttodate)
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


def write_netcdf_header(var_name, netfile, DtDay,
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
            elif frequency == "yearly":
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

    :param flag: 0 -> one value map, 1-5 -> time serie (all steps, monthly, yearly, etc.)
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
    :param frequency:[None,'all','monthly','yearly'] save to netCDF stack; None save to netCDF single
    :return: 
    """
    # prefix = netfile.split('/')[-1].split('\\')[-1].split('.')[0]
    flags = LisSettings.instance().flags
    var_name = os.path.basename(netfile)
    netfile += ".nc"
    if flag == 0:
        nf1 = write_netcdf_header(var_name, netfile, DtDay,
                                  value_standard_name, value_long_name, value_unit, data_format,
                                  startdate, repstepstart, repstepend, frequency)
    else:
        nf1 = iterOpenNetcdf(netfile, "", 'a', format='NETCDF4')
    if flags['nancheck']:
        nanCheckMap(inputmap, netfile, value_standard_name)
    
    map_np = uncompress_array(inputmap)
    if frequency is not None:
        cdfflags = CDFFlags.instance()
        step = cdfflags[flag]

        nf1.variables[var_name][step, :, :] = map_np
    else:
        nf1.variables[var_name][:, :] = map_np

    nf1.close()


class Writer():

    def write(self, map_data, start_date, start_step, end_step):
        raise NotImplementedError


class NetcdfWriter(Writer):

    def __init__(self, var, map_key, map_value, map_path, frequency=None):

        self.var = var

        self.map_key = map_key
        self.map_value = map_value
        self.map_path = map_path
        self.map_name = os.path.basename(self.map_path)
        self.map_path = map_path+'.nc'

        self.frequency = frequency

    def write(self, map_data, start_date, start_step, end_step):
        
        nf1 = write_netcdf_header(self.map_name, self.map_path, self.var.DtDay,
                                  self.map_key, self.map_value.output_var, self.map_value.unit, 'd', 
                                  start_date, start_step, end_step, self.frequency)

        flags = LisSettings.instance().flags
        if flags['nancheck']:
            nanCheckMap(map_data, self.map_name, self.map_key)
        
        map_np = uncompress_array(map_data)
        
        nf1.variables[self.map_name][:, :] = map_np

        nf1.close()


class NetcdfStepsWriter(NetcdfWriter):

    def __init__(self, var, map_key, map_value, map_path, frequency, flag):

        self.flag = flag
        self.chunks = 1
        self.step_range = []
        self.data_steps = []

        super().__init__(var, map_key, map_value, map_path, frequency)

    def checkpoint(self):
        write = False
        end_run = self.var.currentTimeStep() == self.var.nrTimeSteps()
        if len(self.data_steps) == self.chunks or end_run:
            write = True
        return write

    def write(self, map_data, start_date, start_step, end_step):
        
        cdfflags = CDFFlags.instance()
        step = cdfflags[self.flag]

        flags = LisSettings.instance().flags
        if flags['nancheck']:
            nanCheckMap(map_data, self.map_name, self.map_key)

        map_np = uncompress_array(map_data)

        self.step_range.append(step)
        self.data_steps.append(map_np)

        if self.checkpoint():

            if self.step_range[0] == 0:
                nf1 = write_netcdf_header(self.map_name, self.map_path, self.var.DtDay,
                                        self.map_key, self.map_value.output_var, self.map_value.unit, 'd', 
                                        start_date, start_step, end_step, self.frequency)
            else:
                nf1 = iterOpenNetcdf(self.map_path, "", 'a', format='NETCDF4')
                        
            nf1.variables[self.map_name][self.step_range, :, :] = np.array(self.data_steps)

            nf1.close()

            # clear lists for next chunk
            self.step_range.clear()
            self.data_steps.clear()


class PCRasterWriter(Writer):

    def __init__(self, map_path):
        self.map_path = map_path

    def write(self, map_data, start_date, start_step, end_step):
            self.var.report(decompress(map_data), str(self.map_path))


class MapOutput():

    def __init__(self, var, out_type, frequency, map_key, map_value):

        settings = LisSettings.instance()
        option = settings.options

        self.var = var

        cdfflags = CDFFlags.instance()
        self.flag = cdfflags.get_flag(out_type, frequency)
        self.frequency = frequency

        self.map_key = map_key
        self.map_value = map_value
        self.map_path = self.extract_path(settings)

        if self.is_valid():
            if option['writeNetcdf'] or option['writeNetcdfStack']:
                if self.flag == 0:
                    self.writer = NetcdfWriter(self.var, self.map_key, self.map_value, self.map_path)
                else:
                    self.writer = NetcdfStepsWriter(self.var, self.map_key, self.map_value, self.map_path, self.frequency, self.flag)
            else:  # PCRaster
                self.writer = PCRasterWriter(self.map_path)

    def is_valid(self):
        valid = True
        map_data = self.extract_map()
        if map_data is None or self.map_path is None:
            valid = False
        return valid

    def extract_map(self):
        what = 'self.var.' + self.map_value.output_var
        try:
            map_data = eval(what)
        except:
            map_data = None
            print(f'Warning! {self.map_key} could not be found for outputs')
        return map_data

    def extract_path(self, settings):
        binding = settings.binding
        # report end map filename
        if settings.mc_set:
            # MonteCarlo model
            map_path = os.path.join(str(self.var.currentSampleNumber()), binding[self.map_key].split("/")[-1])
        else:
            map_path = binding.get(self.map_key)
        return map_path

    def frequency_check(self):
        if self.frequency == 'all':
            check = True
        elif self.frequency == 'monthly':
            check = self.var.monthend
        elif self.frequency == 'yearly':
            check = self.var.yearend
        else:
            raise ValueError(f'Output frequency {self.frequency} not recognised! Valid values are: (all, monthly, yearly)')
        return check
    
    def output_checkpoint(self):
        raise NotImplementedError

    @property
    def start_date(self):
        raise NotImplementedError

    def step_range(self):
        raise NotImplementedError

    def write(self):

        if self.output_checkpoint():

            start_step, end_step = self.step_range()

            map_data = self.extract_map()
            self.writer.write(map_data, self.start_date, start_step, end_step)


class MapOutputEnd(MapOutput):

    def __init__(self, var, map_key, map_value):
        out_type = 'end'
        frequency = None
        super().__init__(var, out_type, frequency, map_key, map_value)
    
    def output_checkpoint(self):
        check = self.var.currentTimeStep() == self.var.nrTimeSteps()
        return check
    
    @property
    def start_date(self):
        start_date = inttodate(self.var.currentTimeStep() - 1, self.var.CalendarDayStart)
        return start_date
    
    def step_range(self):
        start_step = self.var.currentTimeStep()
        end_step = self.var.currentTimeStep()
        return start_step, end_step


class MapOutputSteps(MapOutput):

    def __init__(self, var, map_key, map_value, frequency):
        out_type = 'steps'
        if len(var.ReportSteps) > 0:
            self._start_date = inttodate(var.ReportSteps[0] - 1, var.CalendarDayStart)
        super().__init__(var, out_type, frequency, map_key, map_value)
    
    def is_valid(self):
        valid = False
        if len(self.var.ReportSteps) > 0:
            valid = True
        return valid and super().is_valid()


    def output_checkpoint(self):
        check = self.var.currentTimeStep() in self.var.ReportSteps and self.frequency_check()
        return check

    @property
    def start_date(self):
        return self._start_date

    def step_range(self):
        start_step = 1
        end_step = self.var.ReportSteps[-1] - self.var.ReportSteps[0] + 1
        return start_step, end_step


class MapOutputAll(MapOutput):

    def __init__(self, var, map_key, map_value, frequency):
        out_type = 'all'
        settings = LisSettings.instance()
        binding = settings.binding
        self._start_date = inttodate(binding['StepStartInt'] - 1, var.CalendarDayStart)
        self._start_step = 1
        self._end_step = binding['StepEndInt'] - binding['StepStartInt'] + 1
        super().__init__(var, out_type, frequency, map_key, map_value)
    
    def output_checkpoint(self):
        check = self.frequency_check()
        return check

    @property
    def start_date(self):
        return self._start_date

    def step_range(self):
        return self._start_step, self._end_step


def output_maps_factory(var):

    settings = LisSettings.instance()

    report_maps_end = settings.report_maps_end
    report_maps_steps = settings.report_maps_steps
    report_maps_all = settings.report_maps_all

    outputs = []
    
    for map_key, map_value in report_maps_end.items():
        out = MapOutputEnd(var, map_key, map_value)
        if out.is_valid():
            outputs.append(out)

    for map_key, map_value in report_maps_steps.items():
        if map_value.monthly:
            out = MapOutputSteps(var, map_key, map_value, frequency='monthly')
        elif map_value.yearly:
            out = MapOutputSteps(var, map_key, map_value, frequency='yearly')
        else:
            out = MapOutputSteps(var, map_key, map_value, frequency='all')
        if out.is_valid():
            outputs.append(out)
        
    for map_key, map_value in report_maps_all.items():
        if map_value.monthly:
            out = MapOutputAll(var, map_key, map_value, frequency='monthly')
        elif map_value.yearly:
            out = MapOutputAll(var, map_key, map_value, frequency='yearly')
        else:
            out = MapOutputAll(var, map_key, map_value, frequency='all')
        if out.is_valid():
            outputs.append(out)

    check_duplicates = []
    outputs_clean = []
    for out in outputs:
        if out.map_path in check_duplicates:
            print(f'Warning! Output map {out.map_path} is duplicated, check list of outputs')
        else:
            check_duplicates.append(out.map_path)
            outputs_clean.append(out)

    return outputs_clean