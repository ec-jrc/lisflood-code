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

import xml.dom.minidom
import datetime
import time as xtime
import os
from netCDF4 import Dataset, netcdftime, date2num, num2date
from dateutil import parser
from platform import system as operating_system
from pandas._libs.tslibs.parsing import parse_time_string

from pcraster import*
from pcraster.framework import *

from globals import *

import numpy as np
MAX_READ_TRIALS = 100 # max number of trial allowed re-read an input file: to avoid crashes due to temporary network interruptions
READ_PAUSE = 0.1      # pause (seconds) between each re-read trial over the network
try:
    NC_DATE_TYPE = netcdftime._netcdftime.datetime
except:
    NC_DATE_TYPE = netcdftime.datetime # work-around for older versions of the netCDF4 library (< 1.2.7 ?)


project_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))


class LisfloodError(Exception):
    """
    the error handling class
    prints out an error
    """
    def __init__(self, msg):
        header = "\n\n ========================== LISFLOOD ERROR =============================\n"
        try:
           self._msg = header + msg +"\n" +  sys.exc_info()[1].message
        except:
           self._msg = header + msg +"\n"

    def __str__(self):
        return self._msg


class LisfloodFileError(LisfloodError):
    """
    the error handling class
    prints out an error
    """
    def __init__(self, filename,msg=""):
        path, name = os.path.split(filename)
        path = os.path.normpath(path)
        if os.path.exists(path):
            text1 = "path: " + path + " exists\nbut filename: " + name + " does not\n"
            text1 += "file name extension can be .map or .nc\n"
        else:
            text1 = "searching: " + filename
            text1 += "\npath: " + path + " does not exists\n"

        header = "\n\n ======================== LISFLOOD FILE ERROR ===========================\n"
        self._msg = header + msg + text1


class LisfloodWarning(Warning):
    """
    the error handling class
    prints out an error
    """
    def __init__(self, msg):
        header = "\n\n ========================== LISFLOOD Warning =============================\n"
        self._msg = header + msg

    def __str__(self):
        return self._msg


class LisfloodRunInfo(Warning):
    """
    the error handling class
    prints out an error
    """
    def __init__(self, mode, outputDir, Steps = 1, ensMembers=1, Cores=1):
        header = "\n\n ========================== LISFLOOD Simulation Information and Setting =============================\n"
        msg = "   LISFLOOD is used in the "+str(mode)+"\n"
        if ensMembers > 1:
            msg += "   It uses "+str(ensMembers)+" ensemble members for the simulation\n"
        if Steps > 1:
            msg += "   The model will be updated at "+str(Steps)+" time step during the simulation\n"
        if Cores > 1:
            msg += "   The simulation will try to use "+str(Cores)+" processors simultaneous\n"
        msg += "   The simulation output as specified in the settings file can be found in "+str(outputDir)+"\n"
        self._msg = header + msg

    def __str__(self):
        return self._msg


def optionBinding(settingsfile, optionxml):
    """ Read XML settings and options files 
    
    Read Settings.XML and Options.XML input files and return:
    binding = key and value (filename or value)
    option  = control of Lisflood to use certain subroutines
    ReportSteps = maps are reported at these time steps
    
    :param settingsfile: path and name of Settings.xml
    :param optionxml: path and name of Options.xml
    :return: binding, option, ReportSteps (as global variables)
    """
    settings_path = os.path.normpath(os.path.abspath(os.path.dirname(settingsfile)))
    optionSetting = {}

    # user defined path, parameters, calibration parameters, dates, ect from settingsxml
    # we add here some built-in user variables
    user = {
        'ProjectDir': project_dir, 'ProjectPath': project_dir,
        'SettingsDir': settings_path, 'SettingsPath': settings_path,
    }
    repTimeserie = {}
    repMaps = {}

    # domopt = xml.dom.minidom.parseString(optionxml)

    #read xml optionxml i.e. OptionTserieMaps.xml file
    try:
        f=open(optionxml)
        f.close()
    except:
        msg = "Cannot find option file: " + optionxml
        raise LisfloodFileError(optionxml,msg)
    try:
        #DOM object representing content of optionxml file
        domopt = xml.dom.minidom.parse(optionxml)
    except:
        msg = "Error using option file: " + optionxml
        raise LisfloodError(msg)

    #read file settings (settingsfile)
    try:
       f = open(settingsfile,'r')
       xmlstring1 = ""
       while 1:
          line = f.readline()
          if not line:break
          xmlstring1 += line
       f.close()
       xmlstring.append(xmlstring1)
    except:
        msg = "Cannot find settings file: " + settingsfile
        raise LisfloodFileError(settingsfile,msg)
    try:
        #DOM object representing content of settings file
        dom = xml.dom.minidom.parse(settingsfile)
    except:
        msg = "Error using: " + settingsfile
        raise LisfloodError(msg)

    # getting all posssible option from the general optionxml
    # and setting them to their default value
    # list of elements "lfoptions" in optionxml file
    optDef = domopt.getElementsByTagName("lfoptions")[0]
    for optset in optDef.getElementsByTagName("setoption"):
        option[optset.attributes['name'].value] = bool(
            int(optset.attributes['default'].value))

    # getting option set in the specific settings file
    # and resetting them to their choice value
    # list of elements "lfoptions" in settings file
    optSet = dom.getElementsByTagName("lfoptions")[0]
    for optset in optSet.getElementsByTagName("setoption"):
        optionSetting[optset.attributes['name'].value] = bool(
            int(optset.attributes['choice'].value))
    for key in optionSetting.keys():
        # set the same value for corresponding keys, settings overwrites optionxml
        option[key] = optionSetting[key]

    # reverse the initLisflood option to use it as a restriction for output
    # eg. produce output if not(initLisflood)
    option['nonInit'] = not(option['InitLisflood'])
# -----------------------------------------

    # get all the bindings in the first part of the settingsfile = lfuser
    # list of elements "lfuser" in settings file
    lfuse = dom.getElementsByTagName("lfuser")[0]
    for userset in lfuse.getElementsByTagName("textvar"):
        user[userset.attributes['name'].value] = str(userset.attributes['value'].value)

    # get all the binding in the last part of the settingsfile  = lfbinding
    # list of elements "lfbinding" in settings file
    bind = dom.getElementsByTagName("lfbinding")[0]
    for bindset in bind.getElementsByTagName("textvar"):
        binding[bindset.attributes['name'].value] = str(bindset.attributes['value'].value)

    # replace/add the information from lfuser to lfbinding
    for i in binding.keys():
        expr = binding[i]
        while expr.find('$(') > -1:
            a1 = expr.find('$(')
            a2 = expr.find(')')
            try:
                s2 = user[expr[a1 + 2:a2]]
            except KeyError:
                print 'no ', expr[a1 + 2:a2],'for',binding[i] ,' in lfuser defined'
            expr = expr.replace(expr[a1:a2 + 1], s2)
        binding[i] = expr

    # if pathout has some placeholders, they are replace here
    pathout = user["PathOut"]
    while pathout.find('$(') > -1:
        a1 = pathout.find('$(')
        a2 = pathout.find(')')
        try:
            s2 = user[pathout[a1 + 2:a2]]
        except KeyError:
            print 'no ', expr[a1 + 2:a2],'for',pathout,' in lfuser defined'
        pathout = pathout.replace(pathout[a1:a2 + 1], s2)

    #CM: output folder
    outputDir.append(pathout)
    #outputDir.append(user["PathOut"])

    # Read the calendar type from the precipitation forcing NetCDF file
    with Dataset(binding["PrecipitationMaps"] + ".nc") as nc:
        binding["calendar_type"] = getCalendarType(nc)

# ---------------------------------------------
    # Split the string ReportSteps into an int array
    # replace endtime with number
    # replace .. with sequence

    try:
        repsteps = user['ReportSteps'].split(',')
    except:
        repsteps = 'endtime'
    if repsteps[-1] == 'endtime':
        repsteps[-1] = binding['StepEnd']
    jjj = []
    for i in repsteps:
        if '..' in i:
            j = map(int, i.split('..'))
            for jj in xrange(j[0], j[1] + 1):
                jjj.append(jj)
        else:
            jjj.append(i)
    ReportSteps['rep'] = map(datetoInt, jjj)
    # maps are reported at these time steps

# -----------------------------------------------

    # Get output Directory from settings file
    try:
        nrCores.append(int(user["nrCores"]))
    except:
        nrCores.append(int(1))

# -------------------------------------------

    # Split the string FilterSteps into an int array
    # remove endtime if present
    # replace .. with sequence

    try:
        filterSteps = user['FilterSteps'].split(',')
    except:
        filterSteps = int(0)
    #try:
    #    filterSteps = user['FilterSteps'].split(' ')
    #except:
    #    filterSteps = int(0)
    if filterSteps[-1] == 'endtime' or filterSteps[-1] == binding['StepEnd'] or filterSteps[-1] == binding['StepEnd']:
        filterSteps[-1] = int(0)
    for i in filterSteps:
        try:
            timeDif = datetime.datetime.strptime(i, "%d/%m/%Y") - datetime.datetime.strptime(binding['CalendarDayStart'], "%d/%m/%Y")
            val = int(timeDif.days)
        except:
            val = int(i)
        stependint = datetoInt(binding['StepEnd'])
        #if int(val) < int(binding['StepEnd']):
        if int(val) < stependint:
            try:
                FilterSteps.append(int(i))
            except:
                FilterSteps.append(int(timeDif.days))
    # maps are reported at these time steps

#----------------------------------------------

    # Number of Ensemble members for MonteCarlo or EnKF
    try:
        EnsMembers.append(int(user["EnsMembers"]))
    except:
        EnsMembers.append(int(1))

    # Number of cores for MonteCarlo or EnKF
    try:
        nrCores.append(int(user["nrCores"]))
    except:
        nrCores.append(int(1))

# -------------------------
    # running through all times series
    # list of elements "lftime" in optionxml file
    reportTimeSerie = domopt.getElementsByTagName("lftime")[0]
    for repTime in reportTimeSerie.getElementsByTagName("setserie"):
        d = {}
        for key in repTime.attributes.keys():
            if key != 'name':
                value = repTime.attributes[key].value
                d[key] = value.split(',')
        key = repTime.attributes['name'].value
        repTimeserie[key] = d
        repOpt = repTimeserie[key]['repoption']
        try:
            restOpt = repTimeserie[key]['restrictoption']
        except:
            # add restricted option if not in already
            repTimeserie[key]['restrictoption'] = ['']
            restOpt = repTimeserie[key]['restrictoption']
        try:
            test = repTimeserie[key]['operation']
        except:
            # add operation if not in already
            repTimeserie[key]['operation'] = ['']

        # sort out if this option is not active
        # put in if one of this option is active
        for i in repOpt:
            for o1key in option.keys():
                if option[o1key]:  # if option is active = 1
                    # print o1key, option[o1key],i
                    if o1key == i:
                        # option is active and time series has this option to select it
                        # now test if there is any restrictions
                        allow = True
                        for j in restOpt:
                            for o2key in option.keys():
                                if o2key == j:
                                    # print o2key, option[o2key],j
                                    if not(option[o2key]):
                                        allow = False
                        if allow:
                            reportTimeSerieAct[key] = repTimeserie[key]

# -------------------------
    # running through all maps

    reportMap = domopt.getElementsByTagName("lfmaps")[0]

    for repMap in reportMap.getElementsByTagName("setmap"):
        d = {}
        for key in repMap.attributes.keys():
            if key != 'name':
                value = repMap.attributes[key].value
                d[key] = value.split(',')
        key = repMap.attributes['name'].value
        repMaps[key] = d
        try:
            repAll = repMaps[key]['all']
        except:
            repMaps[key]['all'] = ['']
            repAll = ['']
        try:
            repSteps = repMaps[key]['steps']
        except:
            repMaps[key]['steps'] = ['']
            repSteps = ['']
        try:
            repEnd = repMaps[key]['end']
        except:
            repMaps[key]['end'] = ['']
            repEnd = ['']
        try:
            restOpt = repMaps[key]['restrictoption']
        except:
            # add restricted option if not in already
            repMaps[key]['restrictoption'] = ['']
            restOpt = repMaps[key]['restrictoption']
        try:
            repUnit = repMaps[key]['unit']
        except:
            repMaps[key]['unit'] = ['-']
        #  -------- All -----------------
        # sort out if this option is not active
        # put in if one of this option is active
        for i in repAll:
            # run through all the output option
            for o1key in option.keys():
                # run through all the options
                if option[o1key]:  # if option is active = 1
                    # print o1key, option[o1key],i
                    if o1key == i:
                        # option is active and time series has this option to select it
                        # now test if there is any restrictions
                        allow = True
                        for j in restOpt:
                            # running through all the restrictions
                            for o2key in option.keys():
                                if (o2key == j) and (not(option[o2key])):
                                    allow = False
                        if allow:
                            reportMapsAll[key] = repMaps[key]

        #  -------- Steps -----------------
        for i in repSteps:
            for o1key in option.keys():
                if option[o1key]:  # if option is active = 1
                    if o1key == i:
                        allow = True
                        for j in restOpt:
                            for o2key in option.keys():
                                if (o2key == j) and (not(option[o2key])):
                                    allow = False
                        if allow:
                            reportMapsSteps[key] = repMaps[key]

        #  -------- End -----------------
        for i in repEnd:
            for o1key in option.keys():
                if option[o1key]:  # if option is active = 1
                    if o1key == i:
                        allow = True
                        for j in restOpt:
                            for o2key in option.keys():
                                if (o2key == j) and (not(option[o2key])):
                                    allow = False
                        if allow:
                            reportMapsEnd[key] = repMaps[key]

    # return option,binding,ReportSteps
    # return option,ReportSteps
    # return ReportSteps
    return


def counted(fn):
    def wrapper(*args, **kwargs):
        wrapper.called+= 1
        return fn(*args, **kwargs)
    wrapper.called= 0
    wrapper.__name__= fn.__name__
    return wrapper

@counted
def checkmap(name, value, map, flagmap, find):
    """ Check if maps fit to the mask map
    
    :param name: key in Settings.xml containing path and name of the map to be checked as string (map name)
    :param value: name and path of the map to be checked as string
    :param map: map to be used for checking in pcraster format
    :param flagmap: flag for maps
    :param find: 
    :return: 
    """
    s = [name, value]
    if flagmap:
        amap = scalar(defined(MMaskMap))
        try:
            smap = scalar(defined(map))
        except:
            msg = "Map: " + name + " in " + value + " does not fit"
            if name == "LZAvInflowMap":
                msg +="\nMaybe run initial run first"
            raise LisfloodError(msg)

        mvmap = maptotal(smap)
        mv = cellvalue(mvmap, 1, 1)[0]
        s.append(mv)

        less = maptotal(ifthenelse(defined(MMaskMap), amap - smap, scalar(0)))
        s.append(cellvalue(less, 1, 1)[0])
        less = mapminimum(scalar(map))
        s.append(cellvalue(less, 1, 1)[0])
        less = maptotal(scalar(map))
        if mv > 0:
            s.append(cellvalue(less, 1, 1)[0] / mv)
        else:
            s.append('0')
        less = mapmaximum(scalar(map))
        s.append(cellvalue(less, 1, 1)[0])
        if find > 0:
            if find == 2:
                s.append('last_Map_used')
            else:
                s.append('')

    else:
        s.append(0)
        s.append(0)
        s.append(float(map))
        s.append(float(map))
        s.append(float(map))

    # print check results
    if checkmap.called == 1:
        print "%-25s%-40s%11s%11s%11s%11s%11s" %("Name","File/Value","nonMV","MV","min","mean","max")
    print "%-25s%-40s%11i%11i%11.2f%11.2f%11.2f" %(s[0],s[1][-39:],s[2],s[3],s[4],s[5],s[6])
    return


def timemeasure(name,loops=0, update = False, sample = 1):
    # returns the current processor time
    timeMes.append(xtime.clock())
    if loops == 0:
        s = name
    else:
        s = name+"_%i" %(loops)
    timeMesString.append(s)
    return


def Calendar(input):
    """ Get date or number of steps from input.

    Get date from input string using one of the available formats or get time step number from input number or string.
    Used to get the date from CalendarDayStart (input) in the settings xml

    :param input: string containing a date in one of the available formats or time step number as number or string
    :rtype: datetime object or float number
    :returns: date as datetime or time step number as float 
    :raises ValueError: stop if input is not a step number AND it is in wrong date format
    """

    try:
        # try reading step number from number or string
        return float(input)
    except:
        # try reading a date in one of available formats
        try:
            _t_units = "hours since 1970-01-01 00:00:00" # units used for date type conversion (datetime.datetime -> calendar-specific if needed)
            date = parse_time_string(input, dayfirst=True)[0]  # datetime.datetime type
            step = date2num(date, _t_units, binding["calendar_type"]) # float type
            return num2date(step, _t_units, binding["calendar_type"]) # calendar-dependent type from netCDF4.netcdftime._netcdftime module
        except:    
            # if cannot read input then stop
            msg = "Wrong step or date format in XML settings file\n" \
                  "Input " + str(input)
            raise LisfloodError(msg)


def datetoInt(dateIn,both=False):
    """ Get number of steps between dateIn and CalendarDayStart.
    
    Get the number of steps between dateIn and CalendarDayStart and return it as integer number.
    It can now compute the number of sub-daily steps.
    dateIn can be either a date or a number. If dateIn is a number, it must be the number of steps between
    dateIn and CalendarDayStart.
    
    :param dateIn: date as string or number
    :param both: if true it returns both the number of steps as integer and the input date as string. If false only
    the number of steps as integer is returned
    :return: number of steps as integer and input date as string
    """

    # get reference date to be used with step numbers from 'CalendarDayStart' in Settings.xml file
    date1 = Calendar(dateIn)
    begin = Calendar(binding['CalendarDayStart'])
    # get model time step as float form 'DtSec' in Settings.xml file
    DtSec = float(binding['DtSec'])
    # compute fraction of day corresponding to model time step as float
    DtDay = float(DtSec / 86400.)
    # Time step, expressed as fraction of day (same as self.var.DtSec and self.var.DtDay)

    if type(date1) is datetime.datetime:
         str1 = date1.strftime("%d/%m/%Y %H:%M")
         # get total number of seconds corresponding to the time interval between dateIn and CalendarDayStart
         timeinterval_in_sec = int((date1 - begin).total_seconds())
         # get total number of steps between dateIn and CalendarDayStart
         int1 = int(timeinterval_in_sec/DtSec +1)
         # int1 = (date1 - begin).days + 1
    else:
        int1 = int(date1)
        str1 = str(date1)
    if both: return int1,str1
    else: return int1


def inttoDate(intIn,refDate):
    """ Get date corresponding to a number of steps from a reference date.

    Get date corresponding to a number of steps from a reference date and return it as datetime.
    It can now use sub-daily steps.
    intIn is a number of steps from the reference date refDate.

    :param intIn: number of steps as integer
    :param refDate: reference date as datetime
    :return: stepDate: date as datetime corresponding to intIn steps from refDate
    """

    # CM: get model time step as float form 'DtSec' in Settings.xml file
    DtSec = float(binding['DtSec'])
    # CM: compute fraction of day corresponding to model time step as float
    DtDay = float(DtSec / 86400)
    # Time step, expressed as fraction of day (same as self.var.DtSec and self.var.DtDay)

    # CM: compute date corresponding to intIn steps from reference date refDate
    stepDate = refDate + datetime.timedelta(days=(intIn*DtDay))

    return stepDate


def checkifDate(start,end):
    """ Check simulation start and end dates or timesteps
    
    Check simulation start and end dates/timesteps to be later than begin date (CalendarStartDay).
    If dates are used for binding[start] and binding[end], it substitutes dates with time step numbers.
    
    :param start: start date for model run (# or date as string)
    :param end: end date for model run (# or date as string)
    :returns: modelSteps (modelSteps[0] = intStart 
    modelSteps.append(intEnd)
    """
    # calendar date start (CalendarDayStart)
    begin = Calendar(binding['CalendarDayStart'])

    intStart,strStart = datetoInt(binding[start],True)
    # overwrite date with time step
    binding[start] = intStart
    intEnd,strEnd = datetoInt(binding[end],True)
    binding[end] = intEnd

    # test if start and end > begin
    if (intStart<0) or (intEnd<0) or ((intEnd-intStart)<0):
        strBegin = begin.strftime("%d/%m/%Y %H:%M")
        msg="Simulation start date and/or simulation end date are wrong or do not match CalendarStartDate!\n"+ \
            "CalendarStartDay: "+strBegin +"\n" + \
            "Simulation start: "+strStart + " - "+str(intStart)+"\n" + \
            "Simulation end: "+strEnd + " - "+str(intEnd)
        raise LisfloodError(msg)
    modelSteps.append(intStart)
    modelSteps.append(intEnd)
    return


class DynamicFramework(DynamicFramework):
    """
    Framework class for dynamic models.
    `userModel`
    Instance that models the :ref:`Dynamic Model Concept <dynamicModelConcept>`.
    `lastTimeStep`   Last timestep to run.
    `firstTimestep`  Sets the starting timestep of the model (optional, default is 1).
    Updated by zusatz.py
    """

    def run(self):
        """
        Run the dynamic user model.

        .. todo::
        This method depends on the filter frameworks concept. Shouldn't its run
        method call _runSuspend()?
        """
        self._atStartOfScript()
        if(hasattr(self._userModel(), "resume")):
            #if self._userModel().firstTimeStep() == 1:
            # replaced this because starting date is not always the 1
            if self._userModel().firstTimeStep() == datetoInt(binding['StepStart']):
               self._runInitial()
            else:
               self._runResume()
        else:
            self._runInitial()

        self._runDynamic()

        # Only execute this section while running filter frameworks.
        if hasattr(self._userModel(), "suspend") and \
        hasattr(self._userModel(), "filterPeriod"):
          self._runSuspend()

        return 0




    """Adjusting the def _atStartOfTimeStep defined in DynamicFramework
       for a real quiet output
    """
    rquiet = False
    rtrace = False

    def _atStartOfTimeStep(self, step):
        self._userModel()._setInTimeStep(True)
        if not self.rquiet:
            if not self.rtrace:
                msg = u"#"

            else:
                msg = u"%s<time step=\"%s\">\n" % (self._indentLevel(), step)
            sys.stdout.write(msg)
            sys.stdout.flush()


class EnsKalmanFilterFramework(EnsKalmanFilterFramework):
  """
   Framework for particle filter runs
   Updated by zusatz
  """
  def _startEndOfPeriod(self, currentPeriod, lastPeriod):
    # determine start end end timestep of current period
    if currentPeriod == 0:
      #startTimestep = 1  # use first timestep instead of hardcode 1
      startTimestep = self._userModel().firstTimeStep()

      endTimestep = self._userModel()._d_filterTimesteps[currentPeriod]
    elif currentPeriod == lastPeriod:
      startTimestep = self._userModel()._d_filterTimesteps[currentPeriod -1] + 1
      endTimestep = self._d_totalTimesteps
    else:
      startTimestep = self._userModel()._d_filterTimesteps[currentPeriod - 1] + 1
      endTimestep = self._userModel()._d_filterTimesteps[currentPeriod]

    assert startTimestep <= endTimestep
    return startTimestep, endTimestep


class TimeoutputTimeseries(TimeoutputTimeseries):
    """
    Class to create pcrcalc timeoutput style timeseries
    Updated py zusatz.py
    """
    def _writeFileHeader(self, outputFilename):
        """
        writes header part of tss file
        """
        outputFile = open(outputFilename, "w")
        # header
        #outputFile.write("timeseries " + self._spatialDatatype.lower() + "\n")
        outputFile.write("timeseries " + self._spatialDatatype.lower() + " settingsfile: "+os.path.realpath(sys.argv[1])+" date: " + xtime.ctime(xtime.time())+ "\n")
        sys.argv[1]
        # write number of outlets points +1
        outputFile.write(str(self._ncodesId + 1) + "\n")
        outputFile.write("timestep\n")

        for colId in range(0, self._ncodesId):
            outputFile.write(str(self._codesId[colId]) + "\n")
        outputFile.close()

    def _configureOutputFilename(self, filename):
        """
        generates filename
        appends timeseries file extension if necessary
        prepends sample directory if used in stochastic
        """

        # test if suffix or path is given
        head, tail = os.path.split(filename)

        if not re.search("\.tss", tail):
            # content,sep,comment = filename.partition("-")
            # filename = content + "Tss" + sep + comment + ".tss"
            filename = tail + ".tss"

        # for stochastic add sample directory
        if hasattr(self._userModel, "nrSamples"):
            try:
                filename = os.path.join(str(self._userModel.currentSampleNumber()), filename)
            except:
                pass

        return filename

    def _writeTssFile(self):
        """
        writing timeseries to disk
        """
        #
        outputFilename =  self._configureOutputFilename(self._outputFilename)
        a= option['EnKF']
        outputFile = None
        if option['EnKF']:
            if os.path.exists(outputFilename) == False:
               if self._writeHeader == True:
                  self._writeFileHeader(outputFilename)
                  outputFile = open(outputFilename, "a")
               else:
                  outputFile = open(outputFilename, "w")
            else:
                outputFile = open(outputFilename, "a")
        else:
            if self._writeHeader == True:
                  self._writeFileHeader(outputFilename)
                  outputFile = open(outputFilename, "a")
            else:
                  outputFile = open(outputFilename, "w")


        assert outputFile

        start = self._userModel.firstTimeStep()
        end = self._userModel.nrTimeSteps() + 1

        for timestep in range(start, end):
            row = ""
            row += " %8g" % timestep
            if self._spatialIdGiven:
                for cellId in range(0, self._ncodesId):
                    value = self._sampleValues[timestep - start][cellId]
                    if isinstance(value, Decimal):
                        row += "           1e31"
                    else:
                        row += " %14g" % (value)
                row += "\n"
            else:
                value = self._sampleValues[timestep - start]
                if isinstance(value, Decimal):
                    row += "           1e31"
                else:
                    row += " %14g" % (value)
                row += "\n"

            outputFile.write(row)

        outputFile.close()

    def __init__(self, tssFilename, model, idMap=None, noHeader=False):
        """

        """

        if not isinstance(tssFilename, str):
            raise Exception(
                "timeseries output filename must be of type string")

        self._outputFilename = tssFilename
        self._maxId = 1
        self._ncodesId = 1
        self._spatialId = None
        self._spatialDatatype = None
        self._spatialIdGiven = False
        self._userModel = model
        self._writeHeader = not noHeader
        # array to store the timestep values
        self._sampleValues = None

        _idMap = False
        if isinstance(idMap, str) or isinstance(idMap, pcraster._pcraster.Field):
            _idMap = True

        #nrRows = 10000 - self._userModel.firstTimeStep() + 1
        #nrRows = self._userModel.nrTimeSteps() - self._userModel.firstTimeStep() + 1

        # if header reserve rows from 1 to endstep
        # if noheader only from startstep - endstep
        #if noHeader:
        #    nrRows = int(binding['StepEnd']) - int(binding['StepStart']) - self._userModel.firstTimeStep() + 2
        #else: nrRows = int(binding['StepEnd']) - int(binding['StepStart']) - self._userModel.firstTimeStep() + 2
        if noHeader:
            nrRows = datetoInt(binding['StepEnd']) - datetoInt(binding['StepStart']) - self._userModel.firstTimeStep() + 2
        else: nrRows = datetoInt(binding['StepEnd']) - datetoInt(binding['StepStart']) - self._userModel.firstTimeStep() + 2



        if _idMap:
            self._spatialId = idMap
            if isinstance(idMap, str):
                self._spatialId = iterReadPCRasterMap(idMap)

            _allowdDataTypes = [
                pcraster.Nominal, pcraster.Ordinal, pcraster.Boolean]
            if self._spatialId.dataType() not in _allowdDataTypes:
                #raise Exception(
                #    "idMap must be of type Nominal, Ordinal or Boolean")
                # changed into creating a nominal map instead of bailing out
                self._spatialId = pcraster.nominal(self._spatialId)

            if self._spatialId.isSpatial():
                self._maxId, valid = pcraster.cellvalue(
                    pcraster.mapmaximum(pcraster.ordinal(self._spatialId)), 1)
                # convert to numpy array
                outletsmapnp = pcr2numpy(self._spatialId,np.nan)
                # get outlets codes from outlets map
                codesId = numpy.unique(outletsmapnp)
                # drop negative values (= missing data in pcraster map)
                codesId = codesId[codesId > 0]
                # get number of outlets points
                self._ncodesId = len(codesId)
                # prepare array to store outlets codes
                self._codesId = [-9999 for i in xrange(self._ncodesId)]

            else:
                self._maxId = 1
                self._codesId = [1]
                self._ncodesId = len(self._codesId)

            # cell indices of the sample locations

            # #self._sampleAddresses = []
            # for cellId in range(1, self._maxId + 1):
            # self._sampleAddresses.append(self._getIndex(cellId))


            # prepare array to store outlets points raster numbers
            self._sampleAddresses = [-9999 for i in xrange(self._ncodesId)]
            # init with the left/top cell - could also be 0 but then you have to catch it in
            # the sample routine and put an exeption in
           # number of cells in map
            nrCells = pcraster.clone().nrRows() * pcraster.clone().nrCols()
            for cell in xrange(1, nrCells + 1):
                if (pcraster.cellvalue(self._spatialId, cell)[1]):
                    # get point code from outlets map for pixel cell
                    outlet_code = pcraster.cellvalue(self._spatialId, cell)[0]
                    # get index of the point code in the sorted list of outlets codes
                    outlet_idx = np.where(codesId == outlet_code)[0][0]
                    # store point code
                    self._codesId[outlet_idx] = outlet_code
                    # store outlets location (cell)
                    self._sampleAddresses[outlet_idx] = cell

            self._spatialIdGiven = True

            nrCols = self._ncodesId
            self._sampleValues = [
                [Decimal("NaN")] * nrCols for _ in [0] * nrRows]
        else:
            self._sampleValues = [[Decimal("NaN")] * 1 for _ in [0] * nrRows]

    def firstout(self,expression):
        """
        returns the first cell as output value
        """
        try:
            cellIndex = self._sampleAddresses[0]
            tmp = pcraster.areaaverage(pcraster.spatial(expression), pcraster.spatial(self._spatialId))
            value, valid = pcraster.cellvalue(tmp, cellIndex)
            if not valid:
               value = Decimal("NaN")
        except:
            value = Decimal("NaN")
        return value



#####################################################################################################################
# TOOLS TO OPEN/READ INPUT FILES ITERATIVELY, IN CASE OF NETWORK TEMPORARILY DOWN
#####################################################################################################################

def iterOpenNetcdf(file_path, error_msg, mode, **kwargs):
    """Wrapper around netCDF4.Dataset function exploiting the iterAccess class to access file_path according to the specified mode"""
    access_function = lambda path: Dataset(path, mode, **kwargs)
    return remoteInputAccess(access_function, file_path, error_msg)


def iterReadPCRasterMap(file_path, error_msg=""):
    """Wrapper around pcraster.readmap function exploiting the iterAccess class to open file_path."""
    return remoteInputAccess(pcraster.readmap, file_path, error_msg)


def iterSetClonePCR(file_path, error_msg=""):
    """Wrapper around pcraster.setclone function exploiting the iterAccess class to access file_path."""
    return remoteInputAccess(pcraster.setclone, file_path, error_msg)


def remoteInputAccess(function, file_path, error_msg):
    """
    Wrapper around the provided file access function.
    It allows re-trying the open/read operation if network is temporarily down.
    Arguments:
        function: function to be called to read/open the file.
        file_path: path of the file to be read/open.
    """
    num_trials = 1
    bad_sep = "/" if operating_system() == "Windows" else "\\"
    file_path = file_path.replace(bad_sep, os.path.sep)
    root = os.path.sep.join(file_path.split(os.path.sep)[:4])
    while num_trials <= MAX_READ_TRIALS:
        try:
            obj = function(file_path)
            if num_trials > 1:
                print("File {0} succesfully accessed after {1} attempts".format(file_path, num_trials))
            num_trials = MAX_READ_TRIALS + 1
        except IOError:
            if os.path.exists(root) and not os.path.exists(file_path):
                raise LisfloodFileError(file_path, error_msg)
            elif num_trials == MAX_READ_TRIALS:
                raise Exception("Cannot access file {0}!\nNetwork down for too long OR bad root directory {1}!".format(file_path, root))
            else:
                num_trials += 1
                print("Trying to access file {0}: attempt n. {1}".format(file_path, num_trials))
                xtime.sleep(READ_PAUSE)
    return obj

def getCalendarType(nc):
    """Get the type of calendar of the open netCDF file passed as argument (http://cfconventions.org/)"""
    try:
        calendar_type = nc.variables["time"].calendar
    except AttributeError:
        calendar_type = "proleptic_gregorian"
        print(LisfloodWarning("""The 'calendar' attribute of the 'time' variable of {} is not set: the default '{}' is used
                              (http://cfconventions.org/Data/cf-conventions/cf-conventions-1.7/cf-conventions.pdf)""".format(path_nc, calendar_type)))
    return calendar_type


def CalendarInconsistencyWarning(filename, file_calendar, precipitation_calendar):
    return LisfloodWarning("In file {}, time.calendar attribute ({}) differs from that of precipitation ({})!".format(filename, file_calendar, precipitation_calendar))
