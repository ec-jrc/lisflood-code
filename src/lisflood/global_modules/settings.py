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

from future.backports import OrderedDict
from future.utils import with_metaclass
from nine import (IS_PYTHON2, str, range, map, nine)
import os
import pprint
import inspect

import xml.dom.minidom

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
        self.flags = self.config_flags()
        user_settings, bindings = self.get_binding(dom)
        self.binding = bindings
        self.options = self.get_options(dom)
        self.report_steps = self._report_steps(user_settings, bindings)
        self.report_timeseries = self._report_tss()
        self.report_maps_steps, self.report_maps_all, self.report_maps_end = self._reported_maps()

    @staticmethod
    def config_flags():
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

    def get_binding(self, dom):
        binding = {}

        #  built-in user variables
        user = {
            'ProjectDir': project_dir, 'ProjectPath': project_dir,
            'SettingsDir': self.settings_path, 'SettingsPath': self.settings_path,
        }

    @staticmethod
    def get_options(dom):
        options = copy.deepcopy(default_options)
        # getting option set in the specific settings file
        # and resetting them to their choice value
        lfoptions_elem = dom.getElementsByTagName("lfoptions")[0]
        option_setting = {}
        for optset in lfoptions_elem.getElementsByTagName("setoption"):
            option_setting[optset.attributes['name'].value] = bool(int(optset.attributes['choice'].value))
        # overwrite defaults
        options.update(option_setting)
        return options
