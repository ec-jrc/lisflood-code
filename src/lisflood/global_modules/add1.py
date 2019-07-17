"""

Copyright 2019 European Union

Licensed under the EUPL, Version 1.2 or as soon they will be approved by the European Commission  subsequent versions of the EUPL (the "Licence");

You may not use this work except in compliance with the Licence.
You may obtain a copy of the Licence at:

https://joinup.ec.europa.eu/sites/default/files/inline-files/EUPL%20v1_2%20EN(1).txt

Unless required by applicable law or agreed to in writing, software distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and limitations under the Licence.

"""

from pcraster._pcraster import Scalar

from zusatz import *
from netCDF4 import num2date, date2num, default_fillvals
from pandas import date_range
import numpy as np
import time as xtime
import os
import globals
from bisect import bisect_left

# ------------------------------

def defsoil(name1, name2=None, name3=None):
    """ loads 3 array in a list
    """
    try:
        in1 = loadmap(name1)
    except:
        in1 = name1
    if name2 is None:
        in2 = in1
    else:
        try:
            in2 = loadmap(name2)
        except:
            in2 = name2
    if name3 is None:
        in3 = in1
    else:
        try:
            in3 = loadmap(name3)
        except:
            in3 = name3
    return [in1, in2, in3]

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

    for i in xrange(int(len(coord) / 2)):
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
    """ Get metadata information from netcdf map.
    
    metaNetCDF gets metadata information from netCDF template file. Name and path of template file are stored
    in settings.xml file using key "netCDFtemplate". If template file is not available, information is read
    from "E0Maps".
    
    :return: metadataNCDF as global dictionary
    """
    try:
        # using ncdftemplate
        filename = os.path.splitext(binding['netCDFtemplate'])[0] + '.nc'
        nf1 = iterOpenNetcdf(filename, "", 'r')
        for var in nf1.variables:
           metadataNCDF[var] = {k: v for k, v in nf1.variables[var].__dict__.iteritems() if k !='_FillValue'}
        nf1.close()
        return
    except:
        pass
    # if no template .nc is given the e.nc file is used
    filename = os.path.splitext(binding['E0Maps'])[0] + '.nc'
    nf1 = iterOpenNetcdf(filename, "Trying to get metadata from netcdf \n", 'r')
    for var in nf1.variables:
       metadataNCDF[var] = {k: v for k, v in nf1.variables[var].__dict__.iteritems() if k !='_FillValue'}
    nf1.close()


def mapattrNetCDF(name):
    """
    get the map attributes like col, row etc from a ntcdf map
    and define the rectangular of the mask map inside the netcdf map
    """
    filename = os.path.splitext(name)[0] + '.nc'
    nf1 = iterOpenNetcdf(filename, "Checking netcdf map \n", 'r')
    spatial_dims = ('x', 'y') if 'x' in nf1.variables else ('lon', 'lat')
    x1, x2, y1, y2 = [round(nf1.variables[v][j], 5) for v in spatial_dims for j in (0, 1)]
    nf1.close()
    if maskmapAttr['cell'] != round(np.abs(x2 - x1), 5) or maskmapAttr['cell'] != round(np.abs(y2 - y1), 5):
        raise LisfloodError("Cell size different in maskmap {} and {}".format(binding['MaskMap'], filename))
    half_cell = maskmapAttr['cell'] / 2
    x = x1 - half_cell # |
    y = y1 + half_cell # | coordinates of the upper left corner of the input file upper left pixel
    cut0 = int(round(np.abs(maskmapAttr['x'] - x) / maskmapAttr['cell'], 5))
    cut1 = cut0 + maskmapAttr['col']
    cut2 = int(round(np.abs(maskmapAttr['y'] - y) / maskmapAttr['cell'], 5))
    cut3 = cut2 + maskmapAttr['row']
    return cut0, cut1, cut2, cut3 # input data will be sliced using [cut0:cut1,cut2:cut3]


def loadsetclone(name):
    """ Load 'MaskMap' and set as clone
        
    :param name: name of the key in Settings.xml containing path and name of mask map as string
    :return: map: mask map (False=include in modelling; True=exclude from modelling) as pcraster
    """
    filename = os.path.normpath(binding[name])
    if not os.path.exists(filename):
        raise LisfloodError('File not existing: {}'.format(filename))
    coord = filename.split()    #returns a list of all the words in the string
    if len(coord) == 5:
        # changed order of x, y i- in setclone y is first in Lisflood
        # settings x is first
        # setclone row col cellsize xupleft yupleft
        try:
            setclone(int(coord[1]), int(coord[0]), float(coord[2]), float(coord[3]), float(coord[4]))   # CM: pcraster
        except:
            rem = "["+str(coord[0])+" "+ str(coord[1])+" "+ str(coord[2])+" "+ str(coord[3])+" "+str(coord[4])+"]"
            msg = "Maskmap: " + rem + \
                  " are not valid coordinates (col row cellsize xupleft yupleft)"
            raise LisfloodError(msg)
        mapnp = np.ones((int(coord[1]), int(coord[0])))
        #mapnp[mapnp == 0] = 1
        map = numpy2pcr(Boolean, mapnp, -9999)
    elif len(coord) == 1:
        #read information on clone map from map (pcraster or netcdf)
        try:
            # try to read a pcraster map
            iterSetClonePCR(filename)
            map = boolean(iterReadPCRasterMap(filename))
            flagmap = True
            mapnp = pcr2numpy(map,np.nan)

        except Exception as e:
            print(type(e))
            print(str(e))
            # try to read a netcdf file
            filename = os.path.splitext(binding[name])[0] + '.nc'
            nf1 = iterOpenNetcdf(filename, "", "r")
            value = nf1.variables.items()[-1][0]  # get the last variable name

            if 'x' in nf1.variables:
                x1 = nf1.variables['x'][0]
                x2 = nf1.variables['x'][1]
                xlast = nf1.variables['x'][-1]
                y1 = nf1.variables['y'][0]
                ylast = nf1.variables['y'][-1]
            else:
                x1 = nf1.variables['lon'][0]
                x2 = nf1.variables['lon'][1]
                y1 = nf1.variables['lat'][0]
                y2 = nf1.variables['lat'][1]
                xlast = nf1.variables['lat'][-1]
                ylast = nf1.variables['lon'][-1]

            cellSize = round(np.abs(x2 - x1),4)
            nrRows = int(0.5+np.abs(ylast - y1) / cellSize + 1)
            nrCols = int(0.5+np.abs(xlast - x1) / cellSize + 1)
            x = x1 - cellSize / 2
            y = y1 + cellSize / 2
            mapnp = np.array(nf1.variables[value][0:nrRows, 0:nrCols])
            nf1.close()
            # setclone  row col cellsize xupleft yupleft
            setclone(nrRows,nrCols, cellSize, x, y)
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
    maskmapAttr['x'] = pcraster.clone().west()          # mask map West bound
    maskmapAttr['y'] = pcraster.clone().north()         # mask map North bound
    maskmapAttr['col'] = pcraster.clone().nrCols()      # mask map number of columns
    maskmapAttr['row'] = pcraster.clone().nrRows()      # mask map number of rows
    maskmapAttr['cell'] = pcraster.clone().cellSize()   # mask map cell size

    # put in the ldd map
    # if there is no ldd at a cell, this cell should be excluded from modelling
    ldd = loadmap('Ldd',pcr=True)
    #convert ldd to numpy
    maskldd = pcr2numpy(ldd,np.nan)
    #convert numpy map to 8bit
    maskarea = np.bool8(mapnp)
    #compute mask (pixels in maskldd AND maskarea)
    mask = np.logical_not(np.logical_and(maskldd,maskarea))

    #return all the non-masked data as a 1-D array
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
    if Flags['nancheck']:
        nanCheckMap(ldd, binding['Ldd'], 'Ldd')
    return map


def compressArray(map, pcr=True, name=None):
        if pcr:
            mapnp = pcr2numpy(map,np.nan)
            mapnp1 = np.ma.masked_array(mapnp,maskinfo['mask'])
        else:
            mapnp1 = np.ma.masked_array(map,maskinfo['mask'])
        mapC = np.ma.compressed(mapnp1)

        if name is not None:
            if np.max(np.isnan(mapC)):
                msg = name + " has less valid pixels than area or ldd \n"
                raise LisfloodError(msg)
                # test if map has less valid pixel than area.map (or ldd)
        return mapC.astype(float)

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


def loadmap(name,pcr=False, lddflag=False, timestampflag='exact', averageyearflag=False):
    """ Load a static map either value or pcraster map or netcdf (single or stack)
    
    Load a static map either value or pcraster map or netcdf (single or stack)
    If a netCDF stack is loaded, map is read according to timestepInit date (i.e. model time step). If timestepInit is a
    step number, step number is converted to date (referred to CalendarDayStart in settings.xml). Then date is used to
    read time step from netCDF file.
    if timestampflag = 'closest' and loadmap is reading a NetCDF stack, the timestep with the closest timestamp will be
    loaded if the exact one is not available.
    
    :param name: name of key in Settings.xml input file containing path and name of the map file (as string)
    :param pcr: flag for output maps in pcraster format 
    :param lddflag: flag for local drain direction map (CM??)
    :param timestampflag: look for exact time stamp in netcdf file ('exact') or for the closest (left) time stamp available ('closest')
    :param averageyearflag: if True, use "average year" netcdf file over the entire model simulation period
    :return: map or mapC
    :except: pcr: maps must have the same size of clone.map
             netCDF: time step timestepInit must be included into the stack 
    """

    #name of the key in Settimgs.xml file containing path and name of the map file
    value = binding[name]
    #path and name of the map file
    filename = value
    load = False
    pcrmap = False
    #try reading in PCRaster map format
    try:
        #try reading pcraster map
        mapC = float(value)
        flagmap = False
        load = True
        if pcr: map=mapC
    except ValueError:
        try:
            #try reading pcraster map exploiting the iterAccess class
            map = iterReadPCRasterMap(value)
            flagmap = True
            load = True
            pcrmap = True
        except:
            load = False
    if load and pcrmap:
        #map is loaded and it is in pcraster format
        try:
           test = pcraster.scalar(map) + pcraster.scalar(map)    # test if map is same size as clone map, if not it will make an error
        except:
           msg = value +" might be of a different size than clone size "
           raise LisfloodError(msg)
    #if failed before try reading from netCDF map format
    if not(load):
        # read a netcdf  (single one not a stack)
        filename = os.path.splitext(value)[0] + '.nc'
        # get mapextend of netcdf map and calculate the cutting
        cut0, cut1, cut2, cut3 = mapattrNetCDF(filename)
        # load netcdf map but only the rectangle needed
        nf1 = iterOpenNetcdf(filename, "", 'r')
        value = nf1.variables.items()[-1][0]
        # get the last variable name (it must be the variable to be read by Lisflood)
        if not timestepInit:
            #if timestepInit is missing, read netcdf as single static map
            mapnp = nf1.variables[value][cut2:cut3, cut0:cut1]
        else:
            if 'time' in nf1.variables:
                #read a netcdf  (stack) - state files
                #get information from netCDF stack
                t_steps = nf1.variables['time'][:]  # get values for timesteps ([  0.,  24.,  48.,  72.,  96.])
                t_unit = nf1.variables['time'].units  # get unit (u'hours since 2015-01-01 06:00:00')
                t_cal = getCalendarType(nf1)
                #get year from time unit in case average year is used
                if averageyearflag:
                    #get date of the first step in netCDF file containing average year values
                    first_date = num2date(t_steps[0],t_unit,t_cal)
                    #get year of the first step in netCDF file containing average year values
                    t_ref_year = first_date.year

                #select timestep to use for reading from netCDF stack based on timestepInit (state file time step)
                timestepI = Calendar(timestepInit[0])
                if type(timestepI) is datetime.datetime:
                    #reading dates in XML settings file
                    #get step id number in netCDF stack for timestepInit date
                    if averageyearflag:
                        #if using an average year don't care about the year in timestepIDate and change it to the netCDF first time step year
                        try:
                            timestepI = timestepI.replace(year=t_ref_year)
                        except:
                            timestepI = timestepI.replace(day=28)
                            timestepI = timestepI.replace(year=t_ref_year)
                    timestepI = date2num(timestepI,nf1.variables['time'].units)
                else:
                    #reading step numbers in XML file
                    #timestepI = int(timestepI) -1
                    begin = Calendar(binding['CalendarDayStart'])
                    DtSec = float(binding['DtSec'])
                    DtDay = float(DtSec / 86400)
                    # Time step, expressed as fraction of day (same as self.var.DtSec and self.var.DtDay)
                    # get date for step number timestepI (referred to CalendarDayStart)
                    timestepIDate = begin + datetime.timedelta(days=(timestepI - 1) * DtDay)
                    #get step id number in netCDF stack for step timestepInit
                    #timestepInit refers to CalenradDayStart
                    #timestepI now refers to first date in netCDF stack
                    if averageyearflag:
                        #using an average year, don't care about the year in timestepIDate and change it to the netCDF time unit year
                        try:
                            timestepIDate = timestepIDate.replace(year=t_ref_year)
                        except:
                            #if simulation year is leap and average year is not, switch 29/2 with 28/2
                            timestepIDate = timestepIDate.replace(day=28)
                            timestepIDate = timestepIDate.replace(year=t_ref_year)
                    timestepI = date2num(timestepIDate,units = t_unit, calendar = t_cal)

                if not(timestepI in nf1.variables['time'][:]):
                    if (timestampflag == 'exact'):
                        #look for exact time stamp when loading data
                        msg = "time step " + str(int(timestepI)+1)+" is not stored in "+ filename
                        raise LisfloodError(msg)
                    elif (timestampflag == 'closest'):
                        #get the closest value
                        timestepInew = takeClosest(t_steps, timestepI)
                        #set timestepI to the closest available time step in netCDF file
                        timestepI = timestepInew

                itime = np.where(nf1.variables['time'][:] == timestepI)[0][0]
                mapnp = nf1.variables[value][itime,cut2:cut3, cut0:cut1]
            else:
                # read a netcdf  (single one)
                mapnp = nf1.variables[value][cut2:cut3, cut0:cut1]

        #masking
        try:
            if any(maskinfo):
                mapnp.mask = maskinfo['mask']
        except:
            pass
        nf1.close()
        # if a map should be pcraster
        if pcr:
            # check if integer map (like outlets, lakes etc
            checkint=str(mapnp.dtype)
            if checkint=="int16" or checkint=="int32":
                mapnp[mapnp.mask]=-9999
                map = numpy2pcr(Nominal, mapnp, -9999)
            elif checkint=="int8":
                mapnp[mapnp<0]=-9999
                map = numpy2pcr(Nominal, mapnp, -9999)
            else:
                mapnp[np.isnan(mapnp)] = -9999
                map = numpy2pcr(Scalar, mapnp, -9999)
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
        print name, filename
        if flagmap == False:
            checkmap(name, filename, mapC, flagmap, 0)
        elif pcr:
            checkmap(name, filename, map, flagmap, 0)
        else:
            print name, mapC.size
            if mapC.size >0:
                map= decompress(mapC)
                checkmap(name, filename, map, flagmap, 0)
    if pcr:
        if Flags['nancheck'] and name != 'Ldd': 
            nanCheckMap(map, filename, name)
        return map
    elif isinstance(mapC, np.ndarray):
        return mapC.astype(float)
    else:
        if Flags['nancheck'] and name != 'Ldd': 
            nanCheckMap(mapC, filename, name)
        return mapC



def takeClosest(myList, myNumber):
    """ Returns the closest left value to myNumber in myList
    
    Assumes myList is sorted. Returns closest left value to myNumber.
    If myList is sorted in raising order, it returns the closest smallest value.
    https://stackoverflow.com/questions/12141150/from-list-of-integers-get-number-closest-to-a-given-value
    
    :param myList: list of ordered values
    :param myNumber: number to be searche in myList
    :return: closest left number to myNumber in myList
    """
    pos = bisect_left(myList, myNumber)
    if pos == 0:
        return myList[0]
    if pos == len(myList):
        return myList[-1]
    before = myList[pos - 1]
    # after = myList[pos]
    # if after - myNumber < myNumber - before:
    #    return after
    # else:
    return before




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
        value = nf1.variables.items()[-1][0]  # get the last variable name
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
    if pcr:
        if Flags['nancheck']: 
            nanCheckMap(map, filename, "'LAI*Maps' or 'WFractionMaps'")
        return map
    else:
        if Flags['nancheck']: 
            nanCheckMap(mapC, filename, "'LAI*Maps' or 'WFractionMaps'")
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
                print s,
    if Flags['check']:
        checkmap(os.path.basename(name), filename, map, True, find)
    if Flags['nancheck']: 
        nanCheckMap(map, filename, name)
    mapC = compressArray(map,name=filename)
    return mapC


def readnetcdf(name, time, timestampflag='exact', averageyearflag=False):
    """ Read maps from netCDF stacks (forcings, fractions, water demand)

    Read maps from netCDF stacks (forcings, fractions, water demand).
    Maps are read by date, so stacks can start at every date also different from CalendarDayStart.
    Units for stacks can be different from model timestep.
    It can read sub-daily steps.
    timestampflag indicates whether to load data with the exact time stamp ('exact'), or the data with the closest time
    stamp when the exact one is not available ('closest').
    averageyearflag indicates whether to load data from a netcdf file containing one single "average" year (it's used for
    water demand and landuse changes in time).

    :param name: string containing path and name of netCDF file to be read
    :param time: current simulation timestep of the model as integer number (referred to CalendarStartDay)
    :param timestampflag: look for exact time stamp in netcdf file ('exact') or for the closest (left) time stamp available ('closest')
    :param averageyearflag: if True, use "average year" netcdf file over the entire model simulation period
    :returns: content of netCDF map for timestep "time" (mapC)
    :except: if current simulation timestep is not stored in the stack, it stops with error message (if timestampflag='exact')
    """

    filename = name + ".nc" if not name.endswith('.nc') else name
    nf1 = iterOpenNetcdf(filename, "Netcdf map stacks: \n", "r")

    # read information from netCDF file
    variable_name = [k for k in nf1.variables if len(nf1.variables[k].dimensions) == 3][0] # get the variable with 3 dimensions (variable order not relevant)
    t_steps = nf1.variables['time'][:]    # get values for timesteps ([  0.,  24.,  48.,  72.,  96.])
    t_unit = nf1.variables['time'].units  # get unit (u'hours since 2015-01-01 06:00:00')
    t_cal = getCalendarType(nf1)
    # CM: get year from time unit in case average year is used
    if averageyearflag:
        # CM: get date of the first step in netCDF file containing average year values
        first_date = num2date(t_steps[0], t_unit, t_cal)
        # CM: get year of the first step in netCDF file containing average year values
        t_ref_year = first_date.year

    begin = Calendar(binding['CalendarDayStart'])
    DtSec = float(binding['DtSec'])
    DtDay = float(DtSec / 86400)
    # Time step, expressed as fraction of day (same as self.var.DtSec and self.var.DtDay)

    # get date of current simulation step
    currentDate = Calendar(time)
    if type(currentDate) is not datetime.datetime:
        currentDate = begin + datetime.timedelta(days=(currentDate - 1) * DtDay)

    # if reading from an average year NetCDF stack, ignore the year in current simulation date and change it to the netCDF time unit year
    if averageyearflag:
        try:
            currentDate = currentDate.replace(year=t_ref_year)
        except:
            # CM: if simulation year is leap and average year is not, switch 29/2 with 28/2
            currentDate = currentDate.replace(day=28)
            currentDate = currentDate.replace(year=t_ref_year)

    # get timestep in netCDF file corresponding to current simulation date
    current_ncdf_step = date2num(currentDate, units=t_unit, calendar=t_cal)

    # read netCDF map
    if not (current_ncdf_step in t_steps):
        if (timestampflag == 'exact'):
            # look for exact time stamp when loading data
            msg = "Date " + str(currentDate) + " not stored in " + filename
            raise LisfloodError(msg)
        elif (timestampflag == 'closest'):
            # CM: get the closest value
            current_ncdf_step_new = takeClosest(t_steps, current_ncdf_step)
            # CM: set current_ncdf_step to the closest available time step in netCDF file
            current_ncdf_step = current_ncdf_step_new

    # get index of timestep in netCDF file corresponding to current simulation date
    current_ncdf_index = np.where(t_steps == current_ncdf_step)[0][0]
    mapnp = nf1.variables[variable_name][current_ncdf_index, cutmap[2]:cutmap[3], cutmap[0]:cutmap[1]]
    nf1.close()

    mapC = compressArray(mapnp, pcr=False, name=filename)
    if Flags['check']:
        timename = os.path.basename(name) + str(time)
        checkmap(timename, filename, decompress(mapC), True, 1)
    if Flags['nancheck']: 
        nanCheckMap(mapC, filename, name)
    return mapC


def readnetcdfsparse(name, time, oldmap):
    """
    NO LONGER USED
    load stack of maps 1 at each timestamp in Netcdf format
    """
    try:
        mapC = readnetcdf(name, time)
        find = 1
        # print name+str(time)+"   "+str(find)
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
                # print name+"   "+str(time)+"   "+str(find)+"   "+str(i)
            if find == 2:
                msg = "no map in stack has a smaller time stamp than: " + str(time)
                raise LisfloodError(msg)
        else:
            mapC = oldmap
            if Flags['loud']:
                s = " last_" + (os.path.basename(name)) + str(time)
                # print s,
    return mapC


def checknetcdf(name, start, end):
    """ Check available time steps in netCDF input file
    
    Check available timesteps in netCDF file. Get first and last available timestep in netCDF file and compare with
    first and last computation timestep of the model.
    It can use sub-daily steps.
    
    :param name: string containing path and name of netCDF file
    :param start: initial date or step number of model simulation
    :param end: final date or step of model simulation  
    :return: none
    :raises Exception: stop if netCDF maps do not cover simulation time period
    """

    filename = name + ".nc"
    nf1 = iterOpenNetcdf(filename, "Netcdf map stacks: \n", "r")

    # read information from netCDF file
    t_steps = nf1.variables['time'][:]    # get values for timesteps ([  0.,  24.,  48.,  72.,  96.])
    t_unit = nf1.variables['time'].units  # get unit (u'hours since 2015-01-01 06:00:00')
    t_cal = getCalendarType(nf1)
    if t_cal != binding['calendar_type']:
        print(CalendarInconsistencyWarning(filename, t_cal, binding['calendar_type']))

    # get date of first available timestep in netcdf file
    date_first_step_in_ncdf = num2date(t_steps[0], units=t_unit, calendar=t_cal)
    # get date of last available timestep in netcdf file
    date_last_step_in_ncdf = num2date(t_steps[-1], units=t_unit, calendar=t_cal)

    nf1.close()

    #calendar date start (CalendarDayStart)
    begin = Calendar(binding['CalendarDayStart'])
    DtSec = float(binding['DtSec'])
    DtDay = float(DtSec / 86400)
    # Time step, expressed as fraction of day (same as self.var.DtSec and self.var.DtDay)


    date_first_sim_step = Calendar(start)
    if type(date_first_sim_step) is not datetime.datetime:
        date_first_sim_step = begin + datetime.timedelta(days=(date_first_sim_step - 1) * DtDay)
    if (date_first_sim_step < date_first_step_in_ncdf):
        msg = "First simulation time step is before first time step in netCDF input data file \n" \
              "File name: "+ filename +"\n" \
              "netCDF start date: "+ date_first_step_in_ncdf.strftime('%d/%m/%Y %H:%M') +"\n" \
              "simulation start date: "+ date_first_sim_step.strftime('%d/%m/%Y %H:%M')
        raise LisfloodError(msg)
        quit(1)

    date_last_sim_step = Calendar(end)
    if type(date_last_sim_step) is not datetime.datetime:
        date_last_sim_step = begin + datetime.timedelta(days=(date_last_sim_step - 1) * DtDay)
    if (date_last_sim_step > date_last_step_in_ncdf):
        msg = "Last simulation time step is after last time step in netCDF input data file \n" \
              "File name: " + filename +"\n" \
              "netCDF last date: " + date_last_step_in_ncdf.strftime('%d/%m/%Y %H:%M') +"\n" \
              "simulation last date: " + date_last_sim_step.strftime('%d/%m/%Y %H:%M')
        raise LisfloodError(msg)
        quit(1)

    return



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
    if len(tail) > 8:
        msg = "Filename '" + name + "' must be shorter than 8 characters"
        raise LisfloodError(msg)
    if time < 0:
        msg = "Timestep must be larger than 0"
        raise LisfloodError(msg)

    nr = "%d" % (time)
    space = 11 - (len(tail) + len(nr))
    assert space >= 0
    result = "%s%s%s" % (tail, space * "0", nr)
    result = "%s.%s" % (result[:8], result[8:])
    assert len(result) == 12
    return os.path.join(head, result)


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
    prefix = os.path.basename(netfile)
    netfile += ".nc"
    row = np.abs(cutmap[3] - cutmap[2])
    col = np.abs(cutmap[1] - cutmap[0])
    if flag == 0:
        nf1 = iterOpenNetcdf(netfile, "", 'w', format='NETCDF4')
        # general Attributes
        nf1.settingsfile = os.path.realpath(sys.argv[1])
        nf1.date_created = xtime.ctime(xtime.time())
        nf1.Source_Software = 'Lisflood Python'
        nf1.institution = "European Commission DG Joint Research Centre (JRC) - E1, D2 Units"
        nf1.creator_name = "Peter Burek, A de Roo, Johan van der Knijff"
        nf1.source = 'Lisflood output maps'
        nf1.keywords = "Lisflood, EFAS, GLOFAS"
        nf1.Conventions = 'CF-1.6'
        # Dimension
        if 'x' in metadataNCDF.keys():
            lon = nf1.createDimension('x', col)  # x 1000
            longitude = nf1.createVariable('x', 'f8', ('x',), fill_value=metadataNCDF['x']['_FillValue'])
            for i in metadataNCDF['x']:
                if i != '_FillValue': exec('%s="%s"') % ("longitude." + i, metadataNCDF['x'][i])

        if 'lon' in metadataNCDF.keys():
            lon = nf1.createDimension('lon', col)
            longitude = nf1.createVariable('lon', 'f8', ('lon',), fill_value=metadataNCDF['lon']['_FillValue'])
            for i in metadataNCDF['lon']:
                if i != '_FillValue': exec('%s="%s"') % ("longitude." + i, metadataNCDF['lon'][i])


        if 'y' in metadataNCDF.keys():
            lat = nf1.createDimension('y', row)  # x 950
            latitude = nf1.createVariable('y', 'f8', ('y',), fill_value=metadataNCDF['y']['_FillValue'])
            for i in metadataNCDF['y']:
                if i != '_FillValue': exec('%s="%s"') % ("longitude." + i, metadataNCDF['y'][i])


        if 'lat' in metadataNCDF.keys():
            lat = nf1.createDimension('lat', row)  # x 950
            latitude = nf1.createVariable('lat', 'f8', ('lat',), fill_value=metadataNCDF['lat']['_FillValue'])
            for i in metadataNCDF['lat']:
                if i != '_FillValue': exec('%s="%s"') % ("longitude." + i, metadataNCDF['lat'][i])

            # projection

        if 'laea' in metadataNCDF.keys():
            proj = nf1.createVariable('laea', 'i4')
            for i in metadataNCDF['laea']:
                exec('%s="%s"') % ("proj." + i, metadataNCDF['laea'][i])

        if 'lambert_azimuthal_equal_area' in metadataNCDF.keys():
            proj = nf1.createVariable('lambert_azimuthal_equal_area', 'i4')
            for i in metadataNCDF['lambert_azimuthal_equal_area']:
                exec('%s="%s"') % ("proj." + i, metadataNCDF['lambert_azimuthal_equal_area'][i])
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
        # Fill variables
        cell = round(pcraster.clone().cellSize(),5)
        xl = round((pcraster.clone().west() + cell / 2),5)
        xr = round((xl + col * cell),5)
        yu = round((pcraster.clone().north() - cell / 2),5)
        yd = round((yu - row * cell),5)
        #lats = np.arange(yu, yd, -cell)
        #lons = np.arange(xl, xr, cell)
        lats = np.linspace(yu, yd, row, endpoint=False)
        lons = np.linspace(xl, xr, col, endpoint=False)
        latitude[:] = lats
        longitude[:] = lons
        if frequency is not None: # output file with "time" dimension
            #Get initial and final dates for data to be stored in nerCDF file
            first_date, last_date = [startdate + datetime.timedelta(days=(int(k) - 1)*DtDay) for k in
                                     (repstepstart, repstepend)]
            # CM: Create time stamps for each step stored in netCDF file
            time_stamps = [first_date + datetime.timedelta(days=d*DtDay) for d in xrange(repstepend - repstepstart +1)]

            units_time = 'days since %s' % startdate.strftime("%Y-%m-%d %H:%M:%S.0")
            steps = (int(binding["DtSec"]) / 86400.) * np.arange(int(binding["StepStart"]) - 1, int(binding["StepEnd"]))
            if frequency != "all":
                dates = num2date(steps, units_time, binding["calendar_type"])
                next_date_times = np.array([j + datetime.timedelta(seconds=int(binding["DtSec"])) for j in dates])
                if frequency == "monthly":
                    months_end = np.array([dates[j].month != next_date_times[j].month for j in xrange(steps.size)])
                    steps = steps[months_end]
                elif frequency == "annual":
                    years_end = np.array([dates[j].year != next_date_times[j].year for j in xrange(steps.size)])
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
            if 'x' in metadataNCDF.keys():
                value = nf1.createVariable(prefix, data_format, ('time', 'y', 'x'), zlib=True, fill_value=-9999, chunksizes=(1, row, col))
            if 'lon' in metadataNCDF.keys():
                value = nf1.createVariable(prefix, data_format, ('time', 'lat', 'lon'), zlib=True, fill_value=-9999, chunksizes=(1, row, col))
        else:
            if 'x' in metadataNCDF.keys():
                value = nf1.createVariable(prefix, data_format, ('y', 'x'), zlib=True, fill_value=-9999)
            if 'lon' in metadataNCDF.keys():
                # for world lat/lon coordinates
                value = nf1.createVariable(prefix, data_format, ('lat', 'lon'), zlib=True, fill_value=-9999)

        value.standard_name = value_standard_name
        value.long_name = value_long_name
        value.units = value_unit
        for var in metadataNCDF.keys():
            if "esri_pe_string" in metadataNCDF[var].keys():
                value.esri_pe_string = metadataNCDF[var]['esri_pe_string']
    else:
        nf1 = iterOpenNetcdf(netfile, "", 'a',format='NETCDF4')
    if Flags['nancheck']:
        nanCheckMap(inputmap, netfile, value_standard_name)
    mapnp = maskinfo['maskall'].copy()
    mapnp[~maskinfo['maskflat']] = inputmap[:]
    #mapnp = mapnp.reshape(maskinfo['shape']).data
    mapnp = mapnp.reshape(maskinfo['shape'])
    if frequency is not None:
        nf1.variables[prefix][flag, :, :] = mapnp
        #value[flag,:,:]= mapnp
    else:
        # without timeflag
        nf1.variables[prefix][:, :] = mapnp
    nf1.close()

def dumpObject(name, var, num):
  path1 = os.path.join(str(num), 'stateVar',name)
  file_object1 = open(path1, 'w')
  pickle.dump(var, file_object1)
  file_object1.close()

def loadObject(name, num):
  path1 = os.path.join(str(num), 'stateVar', name)
  filehandler1 = open(path1, 'r')
  #read a string from the open file object file and interpret it as a pickle data stream, rec
  var = pickle.load(filehandler1)
  filehandler1.close()
  return(var)

def dumpPCRaster(name, var, num):
  path1 = os.path.join(str(num), 'stateVar',name)
  report(var, path1)

def loadPCRaster(name, num):
  path1 = os.path.join(str(num), 'stateVar',name)
  var = iterReadPCRasterMap(path1)
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


def read_tss_header(tssfilename):
    """ Read header of a tss file (used in inflow)
        :param tssfilename  path and name of the tss
        :returns outlets_id  list of column names in tss file 
    """
    with open(tssfilename) as fp:
        rec = fp.readline()
        if rec.split()[0] == 'timeseries':
            # LISFLOOD tss file with header
            # get total number of outlets
            outlets_tot_number = int(fp.readline())
            fp.readline()
            outlets_id = []
            for i in range(0, outlets_tot_number - 1):
                rec = fp.readline()
                rec = int(rec.strip())
                outlets_id.append(rec)  #Lisflood ID code for output points
            # read tss data
            # tssdata = pd.read_table(tssfilename, delim_whitespace=True, header=None, names=outlets_id, index_col=0,
            #                        skiprows=outlets_tot_number + 2)

        else:
            # LISFLOOD tss file without header (table)
            numserie = len(rec.split())
            outlets_id = []
            for i in range(1, numserie):
                outlets_id.append(i)  #Lisflood progressive ID code for output points
            # read tss data
            # tssdata = pd.read_table(tssfilename, delim_whitespace=True, header=None, names=outlets_id, index_col=0)
    fp.close()
    return outlets_id

def nanCheckMap(data, filename, name):
    """Checks for numpy.nan on simulated pixels: if any is found, a warning is raised"""
    is_nan = np.isnan(compressArray(data) if isinstance(data, pcraster._pcraster.Field) else data)
    if is_nan.any():
        print(LisfloodWarning("Warning: {} of {} land values of {} (binding: '{}') are NaN".format(is_nan.sum(), is_nan.size, filename, name)))
