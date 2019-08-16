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
from __future__ import (absolute_import, division, print_function, unicode_literals)

import copy
import getopt
import sys

import datetime
from future.backports import OrderedDict
from future.utils import with_metaclass
from nine import (IS_PYTHON2, str, range, map, nine)
import os
import pprint
import inspect

import xml.dom.minidom
from netCDF4 import Dataset, date2num, num2date

from .decorators import cached
from .default_options import default_options
from lisflood.global_modules.utils import LisfloodWarning, datetoInt

project_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../..'))


class Singleton(type):
    """
    Singleton metaclass to keep single instances by init arguments
    """
    _instances = {}
    _init = {}
    _current = {}

    def __init__(cls, name, bases, dct):
        cls._init[cls] = dct.get('__init__', None)
        super(Singleton, cls).__init__(name, bases, dct)

    def __call__(cls, *args, **kwargs):
        init = cls._init[cls]
        if init is not None:
            key = (cls, frozenset(inspect.getcallargs(init, None, *args, **kwargs).items()))
        else:
            key = cls

        if key not in cls._instances:
            cls._instances[key] = super(Singleton, cls).__call__(*args, **kwargs)
        cls._current[cls] = cls._instances[key]
        return cls._instances[key]

    def instance(cls):
        return cls._current[cls]


@nine
class LisSettings(with_metaclass(Singleton)):
    printer = pprint.PrettyPrinter(indent=4, width=120)

    def __init__(self, settings_file):
        dom = xml.dom.minidom.parse(settings_file)
        self.settings_path = os.path.normpath(os.path.dirname((os.path.abspath(settings_file))))
        self.flags = self._flags()
        user_settings, bindings = self._bindings(dom)
        self.output_dir = self._out_dirs(user_settings)
        self.ncores = self._ncores(user_settings)
        self.binding = bindings
        self.options = self._options(dom)
        self.report_steps = self._report_steps(user_settings, bindings)
        self.filter_steps = self._filter_steps(user_settings)
        self.ens_members = self._ens_members(user_settings)
        self.report_timeseries = self._report_tss()
        self.report_maps_steps, self.report_maps_all, self.report_maps_end = self._reported_maps()

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
    def _out_dirs(user_settings):
        # if pathout has some placeholders, they are replace here
        output_dirs = []
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
        output_dirs.append(pathout)
        return output_dirs

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
        args = sys.argv[2:]
        return _flags(args)

    def _bindings(self, dom):
        binding = {}

        #  built-in user variables
        user = {
            'ProjectDir': project_dir, 'ProjectPath': project_dir,
            'SettingsDir': self.settings_path, 'SettingsPath': self.settings_path,
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
        with Dataset(binding["PrecipitationMaps"] + ".nc") as nc:
            binding["calendar_type"] = get_calendar_type(nc)

        return user, binding

    @staticmethod
    def _report_steps(user_settings, bindings):

        res = {}
        repsteps = user_settings['ReportSteps'].split(',')
        if repsteps[-1] == 'endtime':
            repsteps[-1] = bindings['StepEnd']
        jjj = []
        for i in repsteps:
            if '..' in i:
                j = list(map(int, i.split('..')))
                for jj in range(j[0], j[1] + 1):
                    jjj.append(jj)
            else:
                jjj.append(i)
        res['rep'] = list(map(int, jjj))
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

            stependint = datetoInt(self.binding['StepEnd'])
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
        for ts in timeseries:
            rep_opt = ts.repoption.split(',') if ts.repoption else []
            rest_opt = ts.restrictoption.split(',') if ts.restrictoption else []
            self._set_active_options(ts, report_time_series_act, rep_opt, rest_opt)

        return report_time_series_act

    def _reported_maps(self):
        report_maps_steps = {}
        report_maps_all = {}
        report_maps_end = {}

        # running through all maps
        reportedmaps = self.options['reportedmaps']
        for rm in reportedmaps:
            rep_opt_all = rm.all.split(',') if rm.all else []
            rep_opt_steps = rm.steps.split(',') if rm.steps else []
            rep_opt_end = rm.end.split(',') if rm.end else []
            restricted_options = rm.restrictoption.split(',') if rm.restrictoption else []

            self._set_active_options(rm, report_maps_all, rep_opt_all, restricted_options)
            self._set_active_options(rm, report_maps_steps, rep_opt_steps, restricted_options)
            self._set_active_options(rm, report_maps_end, rep_opt_end, restricted_options)

        return report_maps_steps, report_maps_all, report_maps_end

    def _set_active_options(self, obj, reported, report_options, restricted_options):
        key = obj.name
        for rep in report_options:
            if self.options.get(rep):
                # option is set so temporarily allow = True
                allow = True
                # checking that restricted_options are not set
                for ro in restricted_options:
                    if ro in self.options and not self.options[ro]:
                        allow = False
                        break
                if allow:
                    reported[key] = obj


def get_calendar_type(nc):
    """Get the type of calendar of the open netCDF file passed as argument (http://cfconventions.org/)"""
    try:
        calendar_type = nc.variables["time"].calendar
    except AttributeError:
        calendar_type = "proleptic_gregorian"
        print(LisfloodWarning("""
The 'calendar' attribute of the 'time' variable of {} is not set: the default '{}' is used
(http://cfconventions.org/Data/cf-conventions/cf-conventions-1.7/cf-conventions.pdf)
""".format(nc, calendar_type)))
    return calendar_type


def calendar_inconsistency_warning(filename, file_calendar, precipitation_calendar):
    return LisfloodWarning("In file {}, time.calendar attribute ({}) differs from that of precipitation ({})!".format(filename, file_calendar, precipitation_calendar))
