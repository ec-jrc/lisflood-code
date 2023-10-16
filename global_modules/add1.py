# -------------------------------------------------------------------------
# Name:        addmodule1
# Purpose:
#
# Author:      burekpe
#
# Created:     26/02/2014
# Copyright:   (c) burekpe 2014
# Licence:     <your licence>
# -------------------------------------------------------------------------
from future.utils import listitems, listvalues
from netCDF4 import num2date, date2num
from xarray import DataArray
import numpy as np
import time as xtime
import os
from .zusatz import *
from . import globals
np.seterr(divide='ignore', invalid='ignore')

# ------------------------------

def readInputWithBackup(name, values_if_failure=None):
    """Read input map/value if name is not None; else the provided backup values are used"""
    if name is None:
        return values_if_failure
    else:
        try:
            return loadmap(name)
        except:
            return name

def valuecell(mask, coordx, coordstr):
    """
    to put a value into a pcraster map -> invert of cellvalue
    pcraster map is converted into a numpy array first
    """
    coord = []
    for xy in coordx:
        try:
            coord.append(float(xy))
        except:
            msg = "Gauges: " + xy + " in " + coordstr + " is not a coordinate"
            raise LisfloodError(msg)

    null = np.zeros((pcraster.clone().nrRows(), pcraster.clone().nrCols()))
    null[null == 0] = -9999

    for i in range(int(len(coord) / 2)):
        col = int(
            (coord[i * 2] - pcraster.clone().west()) / pcraster.clone().cellSize())
        row = int(
            (pcraster.clone().north() - coord[i * 2 + 1]) / pcraster.clone().cellSize())
        #if col >= 0 and row >= 0 and col < pcraster.clone().nrCols() and row < pcraster.clone().nrRows():
        if col >= 0 and row >= 0 and col < pcraster.clone().nrCols() and row < pcraster.clone().nrRows():
            null[row, col] = i + 1
        else:
            msg = "Coordinates: " + str(coord[i * 2]) + ',' + str(
                coord[i * 2 + 1]) + " to put value in is outside mask map - col,row: " + str(col) + ',' + str(row)
            raise LisfloodError(msg)

    map = numpy2pcr(Nominal, null, -9999)
    return map


def metaNetCDF():
    """
    get the map metadata from netcdf
    """
    try:
        # using ncdftemplate
        filename = os.path.splitext(binding['netCDFtemplate'])[0] + '.nc'
        nf1 = iterOpenNetcdf(filename, "", 'r')
        for var in nf1.variables:
           metadataNCDF[var] = nf1.variables[var].__dict__
        nf1.close()
        return
    except:
        pass
    # if no template .nc is give the e.nc file is used
    filename = os.path.splitext(binding['E0Maps'])[0] + '.nc'
    nf1 = iterOpenNetcdf(filename, "Trying to get metadata from netcdf \n", 'r')
    for var in nf1.variables:
       metadataNCDF[var] = nf1.variables[var].__dict__
    nf1.close()


def mapattrNetCDF(name):
    """
    get the map attributes like col, row etc from a ntcdf map
    and define the rectangular of the mask map inside the netcdf map
    """
    filename = os.path.splitext(name)[0] + '.nc'
    nf1 = iterOpenNetcdf(filename, "Checking netcdf map \n", 'r')
    spatial_dims = ('x', 'y') if 'x' in nf1.variables else ('lon', 'lat')
    x1, x2, y1, y2 = [np.round(nf1.variables[v][j], 5) for v in spatial_dims for j in (0, 1)]
    nf1.close()
    if maskmapAttr['cell'] != np.round(np.abs(x2 - x1), 5) or maskmapAttr['cell'] != np.round(np.abs(y2 - y1), 5):
        raise LisfloodError("Cell size different in maskmap {} and {}".format(binding['MaskMap'], filename))
    half_cell = maskmapAttr['cell'] / 2
    x = x1 - half_cell # |
    y = y1 + half_cell # | coordinates of the upper left corner of the input file upper left pixel
    cut0 = int(np.round(np.abs(maskmapAttr['x'] - x) / maskmapAttr['cell'], 5))
    cut1 = cut0 + maskmapAttr['col']
    cut2 = int(np.round(np.abs(maskmapAttr['y'] - y) / maskmapAttr['cell'], 5))
    cut3 = cut2 + maskmapAttr['row']
    return cut0, cut1, cut2, cut3 # input data will be sliced using [cut0:cut1,cut2:cut3]


def loadsetclone(name):
    """
    load the maskmap and set as clone
    """
    filename = binding[name]
    coord = filename.split()
    if len(coord) == 5:
        # changed order of x, y i- in setclone y is first in Lisflood
        # settings x is first
        # setclone row col cellsize xupleft yupleft
        setclone(int(coord[1]), int(coord[0]), float(coord[2]), float(coord[3]), float(coord[4]))
        mapnp = np.ones((int(coord[1]), int(coord[0])))
        #mapnp[mapnp == 0] = 1
        map = numpy2pcr(Boolean, mapnp, -9999)
    elif len(coord) == 1:
        try:
            # try to read a pcraster map
            iterSetClonePCR(filename)
            map = boolean(iterReadPCRasterMap(filename))
            flagmap = True
            mapnp = pcr2numpy(map,np.nan)
        except:
            filename = os.path.splitext(binding[name])[0] + '.nc'
            nf1 = iterOpenNetcdf(filename, "", "r")
            value = listitems(nf1.variables)[-1][0]  # get the last variable name
            x1 = listvalues(nf1.variables)[0][0]
            x2 = listvalues(nf1.variables)[0][1]
            xlast = listvalues(nf1.variables)[0][-1]
            y1 = listvalues(nf1.variables)[1][0]
            ylast = listvalues(nf1.variables)[1][-1]
            cell_size = np.round(np.abs(x2 - x1),4)
            nr_rows, nr_cols = nf1.variables[value].shape
            x = x1 - cell_size / 2
            y = y1 + cell_size / 2
            mapnp = np.array(nf1.variables[value])
            nf1.close()
            # setclone  row col cellsize xupleft yupleft
            setclone(nr_rows, nr_cols, cell_size, x, y)
            map = numpy2pcr(Boolean, mapnp, 0)
            #map = boolean(map)
            flagmap = True
        if Flags['check']:
            checkmap(name, filename, map, flagmap, 0)
    else:
        msg = "Maskmap: " + Mask + \
            " is not a valid mask map nor valid coordinates"
        raise LisfloodError(msg)
    # Definition of cellsize, coordinates of the meteomaps and maskmap
    # need some love for error handling
    maskmapAttr['x'] = pcraster.clone().west()
    maskmapAttr['y'] = pcraster.clone().north()
    maskmapAttr['col'] = pcraster.clone().nrCols()
    maskmapAttr['row'] = pcraster.clone().nrRows()
    maskmapAttr['cell'] = pcraster.clone().cellSize()
    # put in the ldd map
    # if there is no ldd at a cell, this cell should be excluded from modelling
    ldd = loadmap('Ldd',pcr=True)
    maskldd = pcr2numpy(ldd,np.nan)
    maskarea = np.bool8(mapnp)
    mask = np.logical_not(np.logical_and(maskldd,maskarea))
#    mask=np.isnan(mapnp)
#    mask[mapnp==0] = True # all 0 become mask out
    mapC = np.ma.compressed(np.ma.masked_array(mask,mask))
    # Definition of compressed array and info how to blow it up again
    maskinfo['mask']=mask
    maskinfo['shape']=mask.shape
    maskinfo['maskflat']=mask.ravel()    # map to 1D not compresses
    maskinfo['shapeflat']=maskinfo['maskflat'].shape   #length of the 1D array
    maskinfo['mapC']=mapC.shape                        # length of the compressed 1D array
    maskinfo['maskall'] =np.ma.masked_all(maskinfo['shapeflat'])  # empty map 1D but with mask
    maskinfo['maskall'].mask = maskinfo['maskflat']
    globals.inZero=np.zeros(maskinfo['mapC'])
    return map


def compressArray(map,pcr=True,name="None"):
        if pcr:
            mapnp = pcr2numpy(map,np.nan).astype(np.float64)
            mapnp1 = np.ma.masked_array(mapnp,maskinfo['mask'])
        else:
            mapnp1 = np.ma.masked_array(map,maskinfo['mask'])
        mapC = np.ma.compressed(mapnp1)
        #if fill: mapC[np.isnan(mapC)]=0
        if name != "None":
            if np.max(np.isnan(mapC)):
                msg = name + " has less valid pixels than area or ldd \n"
                raise LisfloodError(msg)
                # test if map has less valid pixel than area.map (or ldd)
        return mapC

def decompress(map):
     #dmap=np.ma.masked_all(maskinfo['shapeflat'], dtype=map.dtype)
     dmap=maskinfo['maskall'].copy()
     dmap[~maskinfo['maskflat']] = map[:]
     dmap = dmap.reshape(maskinfo['shape'])
     # check if integer map (like outlets, lakes etc
     try:
        checkint=str(map.dtype)
     except:
        checkint="x"
     if checkint in ["int16", "int32", "int64"]:
          dmap[dmap.mask]=-9999
          map = numpy2pcr(Nominal, dmap, -9999)
     elif checkint=="int8":
          dmap[dmap<0]=-9999
          map = numpy2pcr(Nominal, dmap, -9999)
     else:
          dmap[dmap.mask]=-9999
          map = numpy2pcr(Scalar, dmap, -9999)
     return map


def makenumpy(map):
    if not('numpy.ndarray' in str(type(map))):
        out = np.empty(maskinfo['mapC'])
        out.fill(map)
        return out
    else: return map


def loadmap(name, pcr=False, lddflag=False, force_array=False):
    """
    load a static map either value or pcraster map or netcdf
    """
    value = binding[name]
    filename = value
    pcrmap = False
    try:
        mapC = float(value)
        if force_array:
            mapC = np.full(maskinfo['mapC'], mapC)
        flagmap = False
        load = True
        if pcr: map=mapC
    except ValueError:
        try:
            # try to read a pcraster map
            map = iterReadPCRasterMap(value)
            flagmap = True
            load = True
            pcrmap = True
        except:
            load = False
    if load and pcrmap:
        try:
           test = pcraster.scalar(map) + pcraster.scalar(map)    # test if map is same size as clone map, if not it will make an error
        except:
           msg = value +" might be of a different size than clone size "
           raise LisfloodError(msg)
    if not(load):
        # read a netcdf  (single one not a stack)
        filename = os.path.splitext(value)[0] + '.nc'
         # get mapextend of netcdf map and calculate the cutting
        cut0, cut1, cut2, cut3 = mapattrNetCDF(filename)
        # load netcdf map but only the rectangle needed
        nf1 = iterOpenNetcdf(filename, "", 'r')
        value = listitems(nf1.variables)[-1][0]  # get the last variable name
        if not timestepInit:
            mapnp = nf1.variables[value][cut2:cut3, cut0:cut1]
        else:
            if 'time' in nf1.variables:
                timestepI = Calendar(timestepInit[0])
                if isinstance(timestepI, datetime.datetime) or isinstance(timestepI, NC_DATE_TYPE):
                    timestepI = date2num(timestepI, nf1.variables['time'].units, binding["CalendarConvention"])
                else: timestepI = int(timestepI) -1
                if not(timestepI in nf1.variables['time'][:]):
                    msg = "time step " + str(int(timestepI)+1)+" not stored in "+ filename
                    raise LisfloodError(msg)
                itime = np.where(nf1.variables['time'][:] == timestepI)[0][0]
                mapnp = nf1.variables[value][itime,cut2:cut3, cut0:cut1]
            else:
                mapnp = nf1.variables[value][cut2:cut3, cut0:cut1]
        try:
            if any(maskinfo): mapnp.mask = maskinfo['mask']
        except: x=1
        nf1.close()
        # if a map should be pcraster
        if pcr:
            # check if integer map (like outlets, lakes etc
            checkint=str(mapnp.dtype)
            if checkint in ["int16", "int32", "int64"]:
                mapnp[mapnp.mask]=-9999
                map = numpy2pcr(Nominal, mapnp, -9999)
            elif checkint=="int8":
                mapnp[mapnp<0]=-9999
                map = numpy2pcr(Nominal, mapnp, -9999)
            elif "float" in checkint:
                map = numpy2pcr(Scalar, mapnp, np.nan)
            else:
                raise Exception("Data type not among foreseen types (int8, int16, int32, float*)!")
            # if the map is a ldd
            #if value.split('.')[0][:3] == 'ldd':
            if lddflag: map = ldd(nominal(map))
        else:
            mapC = compressArray(mapnp,pcr=False,name=filename)
        flagmap = True
    # pcraster map but it has to be an array
    if pcrmap and not(pcr):
        mapC = compressArray(map,name=filename)
    if Flags['check']:
        print(name, filename)
        if flagmap == False: checkmap(name, filename, mapC, flagmap, 0)
        elif pcr: checkmap(name, filename, map, flagmap, 0)
        else:
            print(name, mapC.size)
            if mapC.size >0:
                map= decompress(mapC)
                checkmap(name, filename, map, flagmap, 0)
    if pcr:
        return map
    elif isinstance(mapC, np.ndarray):
        return mapC.astype(float)
    else:
        return mapC


def loadLAI(value, pcrvalue, i,pcr=False):
    """
    load Leaf are map stacks  or water use maps stacks
    """
    pcrmap = False
    try:
        map = iterReadPCRasterMap(pcrvalue)
        filename = pcrvalue
        pcrmap = True
    except:
        filename = os.path.splitext(value)[0] + '.nc'
        # get mapextend of netcdf map
        # and calculate the cutting
        cut0, cut1, cut2, cut3 = mapattrNetCDF(filename)
        nf1 = iterOpenNetcdf(filename, "", 'r')
        value = listitems(nf1.variables)[-1][0]  # get the last variable name
        mapnp = nf1.variables[value][i, cut2:cut3, cut0:cut1]
        nf1.close()
        mapC = compressArray(mapnp,pcr=False,name=filename)
        # mapnp[np.isnan(mapnp)] = -9999
        # map = numpy2pcr(Scalar, mapnp, -9999)
        # if check use a pcraster map
        if Flags['check' or pcr]:
            map = decompress(mapC)
    if pcrmap: mapC = compressArray(map,name=filename)
    if Flags['check']:
        checkmap(os.path.basename(pcrvalue), filename, map, True, 0)
    if pcr: return map
    return mapC


def readmapsparse(name, time, oldmap):
    """
    load stack of maps 1 at each timestamp in Pcraster format
    """
    filename = generateName(name, time)
    try:
        map = iterReadPCRasterMap(filename)
        find = 1
    except:
        find = 2
        if oldmap is None:
            for i in range(time - 1, 0, -1):
                altfilename = generateName(name, i)
                if os.path.exists(altfilename):
                    map = iterReadPCRasterMap(altfilename)
                    find = 1
                    # break
            if find == 2:
                msg = "no map in stack has a smaller time stamp than: " + filename
                raise LisfloodError(msg)
        else:
            map = oldmap
            if Flags['loud']:
                s = " last_%s" % (os.path.basename(name))
                print(s)
    if Flags['check']:
        checkmap(os.path.basename(name), filename, map, True, find)
    mapC = compressArray(map,name=filename)
    return mapC


def readnetcdf(name, time):
    """
      load stack of maps 1 at each timestamp in netcdf format
    """
    filename = name + ".nc"
    nf1 = iterOpenNetcdf(filename, "Netcdf map stacks: \n", "r")
    variable_name = [k for k in nf1.variables if len(nf1.variables[k].dimensions) == 3][0] # get the variable with 3 dimensions (variable order not relevant)
    mapnp = nf1.variables[variable_name][time - 1,cutmap[2]:cutmap[3],cutmap[0]:cutmap[1]]
    nf1.close()
    try:
        mapC = compressArray(mapnp,pcr=False,name=filename)
    except: # TEMPORARY WORKAROUND TO READ OUTDATED EPIC DATABASE FORCING (CONTAINING NAN ON LAND)
        mapC = mapnp[~maskinfo["mask"]]
    timename = os.path.basename(name) + str(time)
    if Flags['check']:
       map = decompress(mapC)
       checkmap(timename, filename, map, True, 1)
    if np.isnan(mapC).any():
        print(LisfloodWarning('Warning: NaN values on simulated domain in ' + filename))
    return mapC


def readnetcdfsparse(name, time, oldmap):
    """
    load stack of maps 1 at each timestamp in Netcdf format
    """
    try:
        mapC = readnetcdf(name, time)
        find = 1
        # print(name+str(time)+"   "+str(find))
    except:
        find = 2
        if oldmap is None:
            for i in range(time - 1, 0, -1):
                try:
                    mapC = readnetcdf(name, i)
                    find = 1
                    break
                except:
                    pass
                # print(name+"   "+str(time)+"   "+str(find)+"   "+str(i))
            if find == 2:
                msg = "no map in stack has a smaller time stamp than: " + str(time)
                raise LisfloodError(msg)
        else:
            mapC = oldmap
            if Flags['loud']:
                s = " last_" + (os.path.basename(name)) + str(time)
                # print(s)
    return mapC


def generateName(name, time):
    """Returns a filename based on the name and time step passed in.
    The resulting name obeys the 8.3 DOS style format. The time step
    will be added to the end of the filename and be prepended by 0's if
    needed.
    The time step normally ranges from [1, nrTimeSteps].
    The length of the name should be max 8 characters to leave room for
    the time step.
    The name passed in may contain a directory name.
    See also: generateNameS(), generateNameST()
    """
    head, tail = os.path.split(name)
    if re.search("\.", tail):
        msg = "File extension given in '" + name + "' not allowed"
        raise LisfloodError(msg)
    if len(tail) == 0:
        msg = "No filename specified"
        raise LisfloodError(msg)
#    if len(tail) > 8:
#        msg = "Filename '" + name + "' must be shorter than 8 characters"
#        raise LisfloodError(msg)
    if time < 0:
        msg = "Timestep must be larger than 0"
        raise LisfloodError(msg)

    nr = "%d" % (time)
    space = 11 - (len(tail) + len(nr))
#    assert space >= 0
    result = "%s%s%s" % (tail, space * "0", nr)
    result = "%s.%s" % (result[:8], result[8:])
#    assert len(result) == 12
    return os.path.join(head, result)


def writenet(flag, inputmap, netfile, timestep, value_standard_name, value_long_name, value_unit, startdate, frequency=None):
    """
    write a netcdf stack
    """
    # Fill value (for missing values)
    fill_value = -9999 if "int" in str(inputmap.dtype) else np.nan
    #prefix = netfile.split('/')[-1].split('\\')[-1].split('.')[0]
    prefix = os.path.basename(netfile)
    netfile += ".nc"
    row, col = maskinfo['shape']
    if flag == 0:
        nf1 = iterOpenNetcdf(netfile, "", 'w', format='NETCDF4')
        # general Attributes
        nf1.settingsfile = os.path.realpath(sys.argv[1])
        nf1.date_created = xtime.ctime(xtime.time())
        #nf1.xmlstring = xmlstring[0]
        nf1.Source_Software = 'Lisflood Python'
        nf1.institution ="European Commission DG Joint Research Centre (JRC)"
        nf1.creator_name ="Peter Burek, A de Roo, Johan van der Knijff"
        nf1.source = 'Lisflood output maps'
        nf1.keywords = "Lisflood, EFAS, GLOFAS"
        nf1.Conventions = 'CF-1.6'
        # Spatial dimensions
        if "x" in metadataNCDF.keys() and "y" in metadataNCDF.keys():
            dimensions = ("y", "x")
        elif "lon" in metadataNCDF.keys() and "lat" in metadataNCDF.keys():
            dimensions = ("lat", "lon")
        else:
            raise Exception("Bad spatial dimension names in precipitation input file! Allowed values: ('x', 'y') or ('lon', 'lat')")
        space_coords = {}
        for dim, name, size in zip(dimensions, ["Y", "X"], [row, col]):
            nf1.createDimension(dim, size)
            space_coords[name] = nf1.createVariable(dim, 'f8', (dim,))
            for key in np.setdiff1d(list(metadataNCDF[dim]), ['_FillValue']):
                space_coords[name].setncattr(key, metadataNCDF[dim][key])
        # Other dimensions (if the variable is a xarray.DataArray)
        if isinstance(inputmap, DataArray):
            inner_dims = inputmap.dims[:-1]
            for dim in inner_dims:
                nf1.createDimension(dim, inputmap[dim].size)
                var_dim = nf1.createVariable(dim, inputmap[dim].dtype, (dim,))
                var_dim[:] = inputmap[dim].values
            dimensions = inner_dims + dimensions
        # projection
        if 'laea' in metadataNCDF.keys():
            proj = nf1.createVariable('laea', 'i4')
            for i in metadataNCDF['laea']:
                exec("{} = '{}'".format("proj." + i, metadataNCDF['laea'][i]))
        if 'lambert_azimuthal_equal_area' in metadataNCDF.keys():
            proj = nf1.createVariable('lambert_azimuthal_equal_area', 'i4')
            for i in metadataNCDF['lambert_azimuthal_equal_area']:
                exec("{} = '{}'".format("proj." + i, metadataNCDF['lambert_azimuthal_equal_area'][i]))
        """
        EUROPE
        proj.grid_mapping_name='lambert_azimuthal_equal_area'
        proj.false_easting=4321000.0
        proj.false_northing=3210000.0
        proj.longitude_of_projection_origin = 10.0
        proj.latitude_of_projection_origin = 52.0
        proj.semi_major_axis = 6378137.0
        proj.inverse_flattening = 298.257223563
        proj.proj4_params = "+proj=laea +lat_0=52 +lon_0=10 +x_0=4321000 +y_0=3210000 +ellps=GRS80 +units=m +no_defs"
        proj.EPSG_code = "EPSG:3035"
        """
        # Create data variable and assign values to all variables
        cell = np.round(pcraster.clone().cellSize(),5)
        xl = np.round((pcraster.clone().west() + cell / 2),5)
        xr = np.round((xl + col * cell),5)
        yu = np.round((pcraster.clone().north() - cell / 2),5)
        yd = np.round((yu - row * cell),5)
        space_coords["Y"][:] = np.linspace(yu, yd, row, endpoint=False)
        space_coords["X"][:] = np.linspace(xl, xr, col, endpoint=False)
        chunksizes = None
        if frequency is not None: # output file with "time" dimension
            units_time = 'days since %s' % startdate.strftime("%Y-%m-%d %H:%M:%S.0")
            steps = (int(binding["DtSec"]) / 86400.) * np.arange(int(binding["StepStart"]) - 1, int(binding["StepEnd"]))
            if frequency != "all":
                dates = num2date(steps, units_time, binding["CalendarConvention"])
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
            time.units = units_time
            time.calendar = binding["CalendarConvention"]
            nf1.variables["time"][:] = steps
            dimensions = ("time", ) + dimensions
            chunksizes = (1, ) + inputmap.shape[:-1] + (row, col)
        value = nf1.createVariable(prefix, inputmap.dtype, dimensions, zlib=True, fill_value=fill_value, chunksizes=chunksizes)
        value.standard_name = value_standard_name
        value.long_name = value_long_name
        value.units = value_unit
        for var in metadataNCDF.keys():
            if "esri_pe_string" in metadataNCDF[var].keys():
                value.esri_pe_string = metadataNCDF[var]['esri_pe_string']
    else:
        nf1 = iterOpenNetcdf(netfile, "", 'a')
    # Create output array with spatial dimensions and fill it with inputmap values, which are defined only over simulated pixels (see MaskMap in settings file)
    output = fill_value * np.ones(inputmap.shape[:-1] + maskinfo['shape'], inputmap.dtype)
    output[...,~maskinfo['mask']] = inputmap.values if isinstance(inputmap, DataArray) else inputmap
    # Write the output array to the netCDF file
    if frequency is not None:
        nf1.variables[prefix][flag] = output
    else:
        nf1.variables[prefix][:] = output
    nf1.close()

def dumpObject(name, var, num):
  path1 = os.path.join(str(num), 'stateVar',name)
  file_object1 = open(path1, 'w')
  pickle.dump(var, file_object1)
  file_object1.close()

def loadObject(name, num):
  path1 = os.path.join(str(num), 'stateVar', name)
  filehandler1 = open(path1, 'r')
  var = pickle.load(filehandler1)
  filehandler1.close()
  return(var)

def perturbState(var, method = "normal", minVal=0, maxVal=1, mu=0, sigma=1, spatial=True, single=True):
  try:
    numVals = len(var)
  except:
    numVals = 1
  if method == "normal":
    if spatial:
      domain = len(var[0])
      out = var
      for i in range(numVals):
        out[i] = np.minimum(np.maximum(np.random.normal(mu, sigma, domain), minVal), maxVal)
    else:
      if single:
        out = np.minimum(np.maximum(np.random.normal(mu, sigma, numVals), minVal), maxVal)
      else:
        out = list(np.minimum(np.maximum(np.random.normal(mu, sigma, numVals), minVal), maxVal))
  if method == "uniform":
    if spatial:
      domain = len(var[0])
      out = var
      for i in range(numVals):
        out[i] = np.random.uniform(minVal, maxVal, domain)
    else:
      if single:
        out = np.random.uniform(minVal, maxVal, numVals)
      else:
        out = list(np.random.uniform(minVal, maxVal, numVals))
  return(out)

def sumOverAreas(values, area_ids):
    """Sum values over areas indentified by the same ID
    Arguments:
        values: data to be aggregated (np.ndarray of size self.var.num_pixel)
        area_ids: area ID of each model grid cell, i.e. cells with the same ID belong to the same area (np.ndarray of size self.num_pixel)
    Returns: the sum over the area to which the grid cell belongs (np.ndarray of size self.var.num_pixel)"""
    return np.take(np.bincount(area_ids, weights=values), area_ids)

def quickMap(vec, cmap='plasma_r', vmin=None, vmax=None):
    land_mask = ~maskinfo['mask']
    mat = np.full(land_mask.shape, np.nan)
    mat[land_mask] = vec
    return DataArray(mat, coords={'y': np.arange(mat.shape[0])[::-1], 'x': np.arange(mat.shape[1])}, dims=('y', 'x')).plot(cmap=cmap, vmin=vmin, vmax=vmax)
