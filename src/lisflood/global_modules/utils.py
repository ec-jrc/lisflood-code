import datetime
import sys

import os
from cftime._cftime import date2num, num2date
from pandas._libs.tslibs.parsing import parse_time_string

from lisflood.global_modules.globals import binding


class LisfloodError(Exception):
    """
    the error handling class
    prints out an error
    """

    def __init__(self, msg):
        header = "\n\n ========================== LISFLOOD ERROR =============================\n"
        try:
            self._msg = header + msg + "\n" + sys.exc_info()[1].message
        except:
            self._msg = header + msg + "\n"

    def __str__(self):
        return self._msg


class LisfloodFileError(LisfloodError):
    """
    the error handling class
    prints out an error
    """

    def __init__(self, filename, msg=""):
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

    def __init__(self, mode, outputDir, Steps=1, ensMembers=1, Cores=1):
        header = "\n\n ========================== LISFLOOD Simulation Information and Setting =============================\n"
        msg = "   LISFLOOD is used in the " + str(mode) + "\n"
        if ensMembers > 1:
            msg += "   It uses " + str(ensMembers) + " ensemble members for the simulation\n"
        if Steps > 1:
            msg += "   The model will be updated at " + str(Steps) + " time step during the simulation\n"
        if Cores > 1:
            msg += "   The simulation will try to use " + str(Cores) + " processors simultaneous\n"
        msg += "   The simulation output as specified in the settings file can be found in " + str(outputDir) + "\n"
        self._msg = header + msg

    def __str__(self):
        return self._msg


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
