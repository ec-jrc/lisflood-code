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
from __future__ import (absolute_import, print_function, unicode_literals)

from future.backports import OrderedDict
from future.utils import with_metaclass
from nine import (iteritems, str, range, map, nine)

import warnings
import copy
import getopt
import sys
import datetime
import os
import pprint
import inspect
from collections import namedtuple

import xml.dom.minidom
import pcraster
from netCDF4 import Dataset, date2num, num2date
from pandas.core.tools.datetimes import parse_time_string
import numpy as np

from .errors import LisfloodError, LisfloodWarning, LisfloodFileError
from .decorators import cached
from .default_options import default_options

project_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../..'))


class Singleton(type):
    """
    Singleton metaclass to keep single instances by init arguments
    """
    _instances = {}
    _init = {}
    _current = {}

    def __init__(cls, name, bases, dct):
        cls._init[cls] = dct.get('__init__', None)  # set __init__ method for the class
        super(Singleton, cls).__init__(name, bases, dct)

    def __call__(cls, *args, **kwargs):
        init = cls._init[cls]  # get __init__ method
        if init is not None:
            init_args = inspect.getcallargs(init, None, *args, **kwargs).items()
            new_init_args = []
            for a in init_args:
                if isinstance(a[1], np.ndarray):
                    new_init_args.append((a[0], a[1].tostring()))
                else:
                    new_init_args.append(a)
            key = (cls, frozenset(new_init_args))
        else:
            key = cls

        if key not in cls._instances:
            cls._instances[key] = super(Singleton, cls).__call__(*args, **kwargs)
        cls._current[cls] = cls._instances[key]
        return cls._instances[key]

    def instance(cls):
        return cls._current[cls]


@nine
class CDFFlags(with_metaclass(Singleton)):
    """
    Flags for netcdf output for end, steps, all, monthly (steps), yearly (steps), monthly , yearly
    flagcdf = 0
    flagcdf = 1  # index flag for writing nedcdf = 1 (=steps) -> indicated if a netcdf is created or maps are appended
    flagcdf = 2
    flagcdf = 4  # set to yearly (step) flag
    flagcdf = 3  # set to monthly (step) flag
    flagcdf = 5  # set to monthly flag
    flagcdf = 6  # set to yearly flag
    """
    def __init__(self, uid):
        self.uid = uid
        # FIXME magic numbers. replace indexes with descriptive keys (end, steps, all, monthly (steps), etc.)
        self.flags = [0, 0, 0, 0, 0, 0, 0]

    def inc(self, idx):
        self.flags[idx] += 1

    def set(self, data):
        self.flags = data

    def __getitem__(self, item):
        return self.flags[item]


@nine
class MaskAttrs(with_metaclass(Singleton)):
    def __init__(self, maskname):
        self.name = maskname
        self._attrs = {
            'x': pcraster.clone().west(),
            'y': pcraster.clone().north(),
            'col': pcraster.clone().nrCols(),
            'row': pcraster.clone().nrRows(),
            'cell': pcraster.clone().cellSize(),
        }

    def __getitem__(self, item):
        return self._attrs.get(item)


@nine
class CutMap(with_metaclass(Singleton)):
    def __init__(self, cut1, cut2, cut3, cut4):
        self.cuts = (cut1, cut2, cut3, cut4)


@nine
class MaskInfo(with_metaclass(Singleton)):
    Info = namedtuple('Info', 'mask, shape, maskflat, shapeflat, mapC, maskall')

    def __init__(self, mask, maskmap):
        self.flat = mask.ravel()
        self.mask_compressed = np.ma.compressed(np.ma.masked_array(mask, mask))  # mapC
        self.mask_all = np.ma.masked_all(self.flat.shape)
        self.mask_all.mask = self.flat
        self.info = self.Info(mask, mask.shape, self.flat, self.flat.shape, self.mask_compressed.shape, self.mask_all)
        self._in_zero = np.zeros(self.mask_compressed.shape)
        self.maskmap = maskmap

    def in_zero(self):
        return self._in_zero.copy()

    def __iter__(self):
        return iter(self.info)


@nine
class NetCDFMetadata(with_metaclass(Singleton)):
    def __init__(self, uid):
        from .zusatz import iterOpenNetcdf
        self.uid = uid
        self.data = {}
        settings = LisSettings.instance()
        binding = settings.binding
        try:
            # using ncdftemplate
            filename = os.path.splitext(binding['netCDFtemplate'])[0] + '.nc'
            nf1 = iterOpenNetcdf(filename, "Trying to get metadata from netcdf template \n", 'r')
            for var in nf1.variables:
                self.data[var] = {k: v for k, v in iteritems(nf1.variables[var].__dict__) if k != '_FillValue'}
            nf1.close()
            return
        except (KeyError, IOError, IndexError, Exception):
            pass
        # if no template .nc is given the e.nc file is used
        filename = os.path.splitext(binding['E0Maps'])[0] + '.nc'
        nf1 = iterOpenNetcdf(filename, "Trying to get metadata from E0 maps \n", 'r')
        for var in nf1.variables:
            self.data[var] = {k: v for k, v in iteritems(nf1.variables[var].__dict__) if k != '_FillValue'}
        nf1.close()


@nine
class LisSettings(with_metaclass(Singleton)):
    printer = pprint.PrettyPrinter(indent=4, width=120)

    def __str__(self):
        res = """
    Binding: {binding}
    Options: {options}
    report_steps: {report_steps}
    report_timeseries: {report_timeseries}
    report_maps_steps: {report_maps_steps}
    report_maps_all: {report_maps_all}
    report_maps_end: {report_maps_end}
    """.format(binding=self.printer.pformat(self.binding), options=self.printer.pformat(self.options),
               report_steps=self.printer.pformat(self.report_steps),
               report_timeseries=self.printer.pformat(self.report_timeseries),
               report_maps_steps=self.printer.pformat(self.report_maps_steps),
               report_maps_all=self.printer.pformat(self.report_maps_all),
               report_maps_end=self.printer.pformat(self.report_maps_end))
        return res

    def __init__(self, settings_file):
        dom = xml.dom.minidom.parse(settings_file)
        self.settings_dir = os.path.normpath(os.path.dirname((os.path.abspath(settings_file))))
        self.settings_path = os.path.normpath(os.path.abspath(settings_file))
        user_settings, bindings = self._bindings(dom)
        self.timestep_init = None if not bindings.get('timestepInit') else bindings['timestepInit']
        self._check_timestep_init()
        self.output_dir = self._out_dir(user_settings)
        self.ncores = self._ncores(user_settings)
        self.binding = bindings
        self.options = self._options(dom)
        self.flags = self._flags()
        self.model_steps = self._model_steps()
        self.report_steps = self._report_steps(user_settings, bindings)
        self.filter_steps = self._filter_steps(user_settings)
        self.ens_members = self._ens_members(user_settings)
        self.report_timeseries = self._report_tss()
        self.report_maps_steps, self.report_maps_all, self.report_maps_end = self._reported_maps()
        self.report_timeseries = {k: v for k, v in iteritems(self.report_timeseries) if v}
        self.report_maps_steps = {k: v for k, v in iteritems(self.report_maps_steps) if v}
        self.report_maps_all = {k: v for k, v in iteritems(self.report_maps_all) if v}
        self.report_maps_end = {k: v for k, v in iteritems(self.report_maps_end) if v}
        self.enkf_set, self.mc_set = self.montecarlo_kalman_settings()
        self.step_start, self.step_end = self.binding['StepStart'], self.binding['StepEnd']
        self.step_start_int, self.step_end_int = self.binding['StepStartInt'], self.binding['StepEndInt']
        ref_date_start = calendar(self.binding['CalendarDayStart'], self.binding['calendar_type'])
        self.step_start_dt = inttodate(self.step_start_int - 1, ref_date_start, binding=self.binding)
        self.step_end_dt = inttodate(self.step_end_int - 1, ref_date_start, binding=self.binding)


    def montecarlo_kalman_settings(self):
        # Ensemble Kalman filter
        enkf_set = self.options.get('EnKF', 0) if not self.options['InitLisflood'] else 0
        # MonteCarlo
        mc_set = self.options.get('MonteCarlo', 0) if not self.options['InitLisflood'] else 0
        if enkf_set and not mc_set:
            msg = "Trying to run EnKF with only 1 ensemble member \n"
            raise LisfloodError(msg)
        if enkf_set and self.filter_steps[0] == 0:
            msg = "Trying to run EnKF without filter timestep specified \nRunning LISFLOOD in Monte Carlo mode \n"
            warnings.warn(LisfloodWarning(msg))
            enkf_set = 0
        if mc_set and self.ens_members[0] <= 1:
            msg = "Trying to run Monte Carlo simulation with only 1 member \nRunning LISFLOOD in deterministic mode \n"
            warnings.warn(LisfloodWarning(msg))
            mc_set = 0
        return enkf_set, mc_set

    def _check_timestep_init(self):
        try:
            float(self.timestep_init)
        except ValueError:
            try:
                parse_time_string(self.timestep_init, dayfirst=True)
            except ValueError:
                raise LisfloodError('Option timestepInit was not parsable. Must be integer or date string: {}'.format(self.timestep_init))
            else:
                return True
        else:
            return True

    def _check_simulation_dates(self):
        """ Check simulation start and end dates or timesteps

        Check simulation start and end dates/timesteps to be later than begin date (CalendarStartDay).
        If dates are used for binding[start] and binding[end], it substitutes dates with time step numbers.

        :return int_start, int_end
        :rtype tuple
        :raise LisfloodError if dates are not compatible
        """
        begin = calendar(self.binding['CalendarDayStart'], self.binding['calendar_type'])

        int_start, str_start = datetoint(self.binding['StepStart'], self.binding)
        int_end, str_end = datetoint(self.binding['StepEnd'], self.binding)

        # test if start and end > begin
        if (int_start < 0) or (int_end < 0) or ((int_end - int_start) < 0):
            str_begin = begin.strftime("%d/%m/%Y %H:%M")
            msg = "Simulation start date and/or simulation end date are wrong or do not match CalendarStartDate!\n" + \
                  "CalendarStartDay: " + str_begin + "\n" + \
                  "Simulation start: " + str_start + " - " + str(int_start) + "\n" + \
                  "Simulation end: " + str_end + " - " + str(int_end)
            raise LisfloodError(msg)
        self.binding['StepStartInt'] = int_start
        self.binding['StepEndInt'] = int_end
        return int_start, int_end

    def _model_steps(self):
        int_start, int_end = self._check_simulation_dates()
        return [int_start, int_end]

    @staticmethod
    def _ncores(user_settings):
        # Number of cores for MonteCarlo or EnKF
        nr_cores = []
        try:
            nr_cores.append(int(user_settings['nrCores']))
        except (KeyError, ValueError):
            nr_cores.append(1)
        return nr_cores

    @staticmethod
    def _ens_members(user_settings):
        # Number of Ensemble members for MonteCarlo or EnKF
        res = []
        try:
            res.append(int(user_settings["EnsMembers"]))
        except (KeyError, ValueError):
            res.append(1)
        return res

    @staticmethod
    def _out_dir(user_settings):
        # if pathout has some placeholders, they are replaced here
        pathout = user_settings["PathOut"]
        while pathout.find('$(') > -1:
            a1 = pathout.find('$(')
            a2 = pathout.find(')')
            try:
                s2 = user_settings[pathout[a1 + 2:a2]]
            except KeyError:
                print('no ', pathout[a1 + 2:a2], 'for', pathout, ' in lfuser defined')
            else:
                pathout = pathout.replace(pathout[a1:a2 + 1], s2)

        # CM: output folder
        return pathout

    @staticmethod
    def _flags():
        flags = OrderedDict([('quiet', False), ('veryquiet', False), ('loud', False),
                             ('checkfiles', False), ('noheader', False), ('printtime', False),
                             ('debug', False), ('nancheck', False)])
        if 'test' in sys.argv[0] or 'test' in sys.argv[1]:
            # return defaults during tests
            return flags

        @cached
        def _flags(argz):
            try:
                opts, arguments = getopt.getopt(argz, 'qvlchtdn', list(flags.keys()))
            except getopt.GetoptError:
                from ..main import usage
                usage()
            else:
                for o, a in opts:
                    for opt in (('-q', '--quiet'), ('-v', '--veryquiet'),
                                ('-l', '--loud'), ('-c', '--checkfiles'),
                                ('-h', '--noheader'), ('-t', '--printtime')):
                        if o in opt:
                            flags[opt[1].lstrip('--')] = True
                            break
            return flags

        args = sys.argv[2:]
        return _flags(args)

    def _bindings(self, dom):
        binding = {}

        #  built-in user variables
        user = {
            'ProjectDir': project_dir, 'ProjectPath': project_dir,
            'SettingsDir': self.settings_dir, 'SettingsPath': self.settings_dir,
        }
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
        for i in binding:
            expr = binding[i]
            while expr.find('$(') > -1:
                a1 = expr.find('$(')
                a2 = expr.find(')')
                try:
                    s2 = user[expr[a1 + 2:a2]]
                except KeyError:
                    print('no ', expr[a1 + 2:a2], 'for', binding[i], ' in lfuser defined')
                expr = expr.replace(expr[a1:a2 + 1], s2)
            binding[i] = expr

        # Read the calendar type from the precipitation forcing NetCDF file
        precipitation_map_path = binding["PrecipitationMaps"] + '.nc'
        if not os.path.exists(precipitation_map_path):
            raise LisfloodFileError(precipitation_map_path)
        with Dataset(precipitation_map_path) as nc:
            binding["calendar_type"] = get_calendar_type(nc)
        return user, binding

    @staticmethod
    def _report_steps(user_settings, bindings):

        res = {}
        repsteps = user_settings['ReportSteps'].split(',')
        if repsteps[0] == 'starttime':
            repsteps[0] = bindings['StepStartInt']
        if repsteps[-1] == 'endtime':
            repsteps[-1] = bindings['StepEndInt']
        jjj = []
        for i in repsteps:
            if '..' in i:
                j = list(map(int, i.split('..')))
                jjj = list(range(j[0], j[1] + 1))
            else:
                jjj.append(i)
        res['rep'] = list(map(int, jjj))
        if res['rep'][0] > bindings['StepEndInt'] or res['rep'][-1] < bindings['StepStartInt']:
            warnings.warn(LisfloodWarning('No maps are reported as report steps configuration is outside simulation time interval'))
        return res

    @staticmethod
    def _options(settingsfile_dom):
        options = copy.deepcopy(default_options)
        # getting option set in the specific settings file
        # and resetting them to their choice value
        lfoptions_elem = settingsfile_dom.getElementsByTagName("lfoptions")[0]
        option_setting = {}
        for optset in lfoptions_elem.getElementsByTagName("setoption"):
            option_setting[optset.attributes['name'].value] = bool(int(optset.attributes['choice'].value))
        # overwrite defaults
        options.update(option_setting)
        options['nonInit'] = not options['InitLisflood']
        return options

    def _filter_steps(self, user_settings):
        # Split the string FilterSteps into an int array
        # remove endtime if present
        # replace .. with sequence
        res = []
        try:
            filter_steps = user_settings['FilterSteps'].split(',')
        except KeyError:
            filter_steps = 0

        if filter_steps[-1] in ('endtime', self.binding['StepEnd']):
            filter_steps[-1] = 0

        for i in filter_steps:
            try:
                time_dif = datetime.datetime.strptime(i, "%d/%m/%Y") - datetime.datetime.strptime(self.binding['CalendarDayStart'], "%d/%m/%Y")
                val = time_dif.days
            except:
                val = int(i)

            stependint = self.binding['StepEndInt']
            # if int(val) < int(binding['StepEnd']):
            if val < stependint:
                try:
                    res.append(int(i))
                except:
                    res.append(time_dif.days)
        return res

    def _report_tss(self):
        report_time_series_act = {}
        # running through all times series
        timeseries = self.options['timeseries']
        for ts in timeseries.values():
            key = ts.name
            report_time_series_act[key] = self._set_active_options(ts, ts.repoption, ts.restrictoption)

        return report_time_series_act

    def _reported_maps(self):
        report_maps_steps = {}
        report_maps_all = {}
        report_maps_end = {}

        # running through all maps
        reportedmaps = self.options['reportedmaps']
        for rm in reportedmaps.values():
            key = rm.name
            report_maps_all[key] = self._set_active_options(rm, rm.all, rm.restrictoption)
            report_maps_steps[key] = self._set_active_options(rm, rm.steps, rm.restrictoption)
            report_maps_end[key] = self._set_active_options(rm, rm.end, rm.restrictoption)

        return report_maps_steps, report_maps_all, report_maps_end

    def _set_active_options(self, obj, report_options, restricted_options):
        """
        Check report options (when to report/write the map/tss: at least one true)
        and restricted_options (all options must be enabled)
        Return ReportMap tuple if is to write, according report and restrict options
        :param obj: `lisflood.global_modules.default_options.ReportedMap/TimeSeries` tuple
        :param report_options: list of option keys enabling report
        :param restricted_options: list of option keys disabling report (has precedence over report_options)
        :return: obj or None
        """
        allow = any(self.options.get(repopt) for repopt in report_options)
        # checking that at least one restricted_options is set
        if allow and restricted_options:
            allow = all(self.options.get(ro) for ro in restricted_options)
        return obj if allow else None


def get_calendar_type(nc):
    """Get the type of calendar of the open netCDF file passed as argument (http://cfconventions.org/)"""
    try:
        calendar_type = nc.variables["time"].calendar
    except AttributeError:
        calendar_type = "proleptic_gregorian"
        warnings.warn(LisfloodWarning("""
The 'calendar' attribute of the 'time' variable of {} is not set: the default '{}' is used
(http://cfconventions.org/Data/cf-conventions/cf-conventions-1.7/cf-conventions.pdf)
""".format(nc, calendar_type)))
    return calendar_type


def calendar_inconsistency_warning(filename, file_calendar, precipitation_calendar):
    return LisfloodWarning("In file {}, time.calendar attribute ({}) differs from that of precipitation ({})!".format(filename, file_calendar, precipitation_calendar))


def calendar(date_in, calendar_type='proleptic_gregorian'):
    """ Get date or number of steps from input.

    Get date from input string using one of the available formats or get time step number from input number or string.
    Used to get the date from CalendarDayStart (input) in the settings xml

    :param date_in: string containing a date in one of the available formats or time step number as number or string
    :param calendar_type:
    :rtype: datetime object or float number
    :returns: date as datetime or time step number as float
    :raises ValueError: stop if input is not a step number AND it is in wrong date format
    """
    try:
        # try reading step number from number or string
        return float(date_in)
    except ValueError:
        # try reading a date in one of available formats
        try:
            _t_units = "hours since 1970-01-01 00:00:00"  # units used for date type conversion (datetime.datetime -> calendar-specific if needed)
            date = parse_time_string(date_in, dayfirst=True)[0]  # datetime.datetime type
            step = date2num(date, _t_units, calendar_type)  # float type
            return num2date(step, _t_units, calendar_type)  # calendar-dependent type from netCDF4.netcdftime._netcdftime module
        except:
            # if cannot read input then stop
            msg = "Wrong step or date format in XML settings file\n Input {}".format(date_in)
            raise LisfloodError(msg)


def datetoint(date_in, binding=None):
    """ Get number of steps between dateIn and CalendarDayStart.

    Get the number of steps between dateIn and CalendarDayStart and return it as integer number.
    It can now compute the number of sub-daily steps.
    dateIn can be either a date or a number. If dateIn is a number, it must be the number of steps between
    dateIn and CalendarDayStart.

    :param date_in: date as string or number
    :param binding: obptional binding dictionary
    :return number of steps as integer and input date as string
    :rtype tuple(<int>, <str>)
    """
    if not binding:
        settings = LisSettings.instance()
        binding = settings.binding
    # get reference date to be used with step numbers from 'CalendarDayStart' in Settings.xml file
    date1 = calendar(date_in, binding['calendar_type'])
    begin = calendar(binding['CalendarDayStart'], binding['calendar_type'])
    # get model time step as float form 'DtSec' in Settings.xml file
    dt_sec = float(binding['DtSec'])
    # compute fraction of day corresponding to model time step as float
    # DtDay = float(DtSec / 86400.)
    # Time step, expressed as fraction of day (same as self.var.DtSec and self.var.DtDay)

    if type(date1) is datetime.datetime:
        str1 = date1.strftime("%d/%m/%Y %H:%M")
        # get total number of seconds corresponding to the time interval between dateIn and CalendarDayStart
        timeinterval_in_sec = int((date1 - begin).total_seconds())
        # get total number of steps between dateIn and CalendarDayStart
        int1 = int(timeinterval_in_sec/dt_sec + 1)
        # int1 = (date1 - begin).days + 1
    else:
        int1 = int(date1)
        str1 = str(date1)
    return int1, str1


def inttodate(int_in, ref_date, binding=None):
    """ Get date corresponding to a number of steps from a reference date.

    Get date corresponding to a number of steps from a reference date and return it as datetime.
    It can now use sub-daily steps.
    intIn is a number of steps from the reference date refDate.

    :param int_in: number of steps as integer
    :param ref_date: reference date as datetime
    :return: stepDate: date as datetime corresponding to intIn steps from refDate
    """
    if not binding:
        settings = LisSettings.instance()
        binding = settings.binding

    # CM: get model time step as float form 'DtSec' in Settings.xml file
    DtSec = float(binding['DtSec'])
    # CM: compute fraction of day corresponding to model time step as float
    DtDay = DtSec / 86400.
    # Time step, expressed as fraction of day (same as self.var.DtSec and self.var.DtDay)

    # CM: compute date corresponding to intIn steps from reference date refDate
    stepDate = ref_date + datetime.timedelta(days=(int_in * DtDay))

    return stepDate


class LisfloodRunInfo(Warning):
    """
    the error handling class
    prints out an error
    """
    modes = {
        'MonteCarloFramework': 'Monte Carlo',
        'EnsKalmanFilterFramework': '"Ensemble Kalman Filter',
        'DynamicFramework': 'Deterministic',
    }

    def __init__(self, model):

        header = "\n\n ========================== LISFLOOD Simulation Information and Setting =============================\n"
        msg = ''
        settings = LisSettings.instance()
        option = settings.options
        out_dir = settings.output_dir
        ens_members = settings.ens_members[0]
        nr_cores = settings.ncores[0]
        steps = len(settings.filter_steps)
        mode = self.modes[model.__class__.__name__]

        msg += "\t[X] LISFLOOD is used in the {}\n".format(mode)
        if option['InitLisflood']:
            msg += "\t[X] INITIALISATION RUN\n"

        if mode in (self.modes['EnsKalmanFilterFramework'], self.modes['MonteCarloFramework']) and ens_members > 1:
            msg += "\t[X] It uses {} ensemble members for the simulation\n".format(str(ens_members))

        if mode in (self.modes['EnsKalmanFilterFramework']) and steps > 1:
            msg += "\t[X] The model will be updated at {} time step during the simulation\n".format(str(steps))

        if mode in (self.modes['EnsKalmanFilterFramework'], self.modes['MonteCarloFramework']) and nr_cores > 1:
            msg += "\t[X] The simulation will try to use {} processors simultaneous\n".format(str(nr_cores))
        msg += "\t[X] The simulation output as specified in the settings file can be found in {}\n".format(out_dir)
        self._msg = '{}{}'.format(header, msg)

    def __str__(self):
        return self._msg
