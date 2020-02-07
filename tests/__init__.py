"""

Copyright 2019 European Union

Licensed under the EUPL, Version 1.2 or as soon they will be approved by the European Commission  subsequent versions of the EUPL (the "Licence");

You may not use this work except in compliance with the Licence.
You may obtain a copy of the Licence at:

https://joinup.ec.europa.eu/sites/default/files/inline-files/EUPL%20v1_2%20EN(1).txt

Unless required by applicable law or agreed to in writing, software distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and limitations under the Licence.

Run tests with coverage report:
export PYTHONPATH=/opt/pcraster36/python && pytest tests/

"""
from __future__ import absolute_import, division
from nine import IS_PYTHON2

import os
import sys
import uuid
from copy import copy

if IS_PYTHON2:
    from pathlib2 import Path
else:
    from pathlib import Path

from bs4 import BeautifulSoup
from pyexpat import *

from lisfloodutilities.compare import NetCDFComparator

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '../src/')
if os.path.exists(src_dir):
    sys.path.append(src_dir)

import lisflood
from lisflood.global_modules.add1 import loadmap
from lisflood.global_modules.settings import LisSettings, MaskInfo
from lisflood.main import lisfloodexe


class TestSettings(object):

    @classmethod
    def dummyloadmap(cls, *args, **kwargs):
        return loadmap(*args, **kwargs)

    @classmethod
    def dummywritenet(cls, *args, **kwargs):
        return (list(args), dict(**kwargs))

    @classmethod
    def setoptions(cls, settings_file, opts_to_set=None, opts_to_unset=None, vars_to_set=None):
        if isinstance(opts_to_set, str):
            opts_to_set = [opts_to_set]
        if isinstance(opts_to_unset, str):
            opts_to_unset = [opts_to_unset]

        opts_to_set = [] if opts_to_set is None else opts_to_set
        opts_to_unset = [] if opts_to_unset is None else opts_to_unset
        vars_to_set = {} if vars_to_set is None else vars_to_set
        with open(settings_file) as tpl:
            soup = BeautifulSoup(tpl, 'lxml-xml')
            for opt in opts_to_set:
                for tag in soup.find_all("setoption", {'name': opt}):
                    tag['choice'] = '1'
                    break
            for opt in opts_to_unset:
                for tag in soup.find_all("setoption", {'name': opt}):
                    tag['choice'] = '0'
                    break
            for textvar, value in vars_to_set.items():
                for tag in soup.find_all("textvar", {'name': textvar}):
                    tag['value'] = value
                    break

        # Generating XML settings_files on fly from template
        uid = uuid.uuid4()
        filename = os.path.join(os.path.dirname(settings_file), './settings_{}.xml'.format(uid))
        with open(filename, 'w') as dest:
            dest.write(soup.prettify())
        settings = LisSettings(filename)
        os.unlink(filename)
        return settings

    def _reported_tss(self, settings_file, opts_to_set=None, opts_to_unset=None, tss_to_check=None, mocker=None):
        if isinstance(tss_to_check, str):
            tss_to_check = [tss_to_check]
        settings = self.setoptions(settings_file, opts_to_set, opts_to_unset)
        mock_api = mocker.MagicMock(name='timeseries')
        mocker.patch('lisflood.global_modules.output.TimeoutputTimeseries', new=mock_api)
        lisfloodexe(settings)
        assert len(lisflood.global_modules.output.TimeoutputTimeseries.call_args_list) > 0
        to_check = copy(tss_to_check)
        for c in lisflood.global_modules.output.TimeoutputTimeseries.call_args_list:
            args, kwargs = c
            for tss in tss_to_check:
                if tss in args[0]:
                    to_check.remove(tss)
                    if not to_check:
                        break
        assert not to_check


    def _not_reported_tss(self, settings_file, opts_to_set=None, opts_to_unset=None, tss_to_check=None, mocker=None):
        if isinstance(tss_to_check, str):
            tss_to_check = [tss_to_check]
        settings = self.setoptions(settings_file, opts_to_set, opts_to_unset)
        mock_api = mocker.MagicMock(name='timeseries')
        mocker.patch('lisflood.global_modules.output.TimeoutputTimeseries', new=mock_api)
        lisfloodexe(settings)
        assert len(lisflood.global_modules.output.TimeoutputTimeseries.call_args_list) > 0
        res = True
        for c in lisflood.global_modules.output.TimeoutputTimeseries.call_args_list:
            args, kwargs = c
            if any(tss == args[0] for tss in tss_to_check):
                res = False
                break
        assert res

    def _reported_map(self, settings_file, opts_to_set=None, opts_to_unset=None,
                      map_to_check=None, mocker=None, files_to_check=None):
        """
        Check that writenet function was called for the list of maps to check and that files are correctly named
        :param settings_file:
        :param opts_to_set:
        :param opts_to_unset:
        :param map_to_check:
        :param mocker:
        :param files_to_check:
        :return:
        """
        if isinstance(map_to_check, str):
            # single map to check in writenet calls args
            map_to_check = [map_to_check]
        elif not map_to_check:
            map_to_check = []

        if not files_to_check:
            files_to_check = []

        settings = self.setoptions(settings_file, opts_to_set, opts_to_unset)
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        assert len(lisflood.global_modules.output.writenet.call_args_list) > 0
        to_check = copy(map_to_check)
        f_to_check = copy(files_to_check)
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            for m in map_to_check:
                if m == args[4] and m in to_check:
                    to_check.remove(m)
                    if not to_check:
                        break
            path = Path(args[2]).name
            for f in files_to_check:
                if f == path and f in f_to_check:
                    f_to_check.remove(f)
                    if not f_to_check:
                        break
        assert not to_check
        assert not f_to_check


    def _not_reported_map(self, settings_file, opts_to_set=None, opts_to_unset=None, map_to_check=None, mocker=None):
        if isinstance(map_to_check, str):
            # single map to check in writenet calls args
            map_to_check = [map_to_check]
        settings = self.setoptions(settings_file, opts_to_set, opts_to_unset)
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        res = True
        assert len(lisflood.global_modules.output.writenet.call_args_list) > 0
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            if any(m == args[4] for m in map_to_check):
                res = False
                break
        assert res


class TestLis(object):
    reference_files = {
        'dis_1': {'path': os.path.join(current_dir, 'data/TestCatchment1/reference/dis.nc'),
                  'report_map': 'DischargeMaps',
                  'report_tss': 'DisTS'
                  },
        'dis_2': {'path': os.path.join(current_dir, 'data/TestCatchment2/reference/dis.nc'),
                  'report_map': 'DischargeMaps',
                  'report_tss': 'DisTS'
                  }
    }

    domain = None
    settings_path = None

    @classmethod
    def setup_class(cls):
        lisfloodexe(cls.settings_path)

    @classmethod
    def teardown_class(cls):
        settings = LisSettings.instance()
        binding = settings.binding
        for var, obj in cls.reference_files.items():
            output_nc = binding[cls.reference_files[var]['report_map']]
            output_nc = output_nc + '.nc'
            if os.path.exists(output_nc):
                os.remove(output_nc)
            output_tss = binding[cls.reference_files[var]['report_tss']]
            if os.path.exists(output_tss):
                os.remove(output_tss)
        filelist = Path(settings.output_dir[0]).glob('*.nc')
        for f in filelist:
            try:
                os.remove(str(f))
            except OSError:
                pass

    @classmethod
    def listest(cls, variable):
        settings = LisSettings.instance()
        maskinfo = MaskInfo.instance()
        binding = settings.binding
        reference_path = cls.reference_files[variable]['path']
        output_path = os.path.normpath(binding[cls.reference_files[variable]['report_map']]) + '.nc'
        print('>>> Reference: {} - Current Output: {}'.format(reference_path, output_path))
        comparator = NetCDFComparator(maskinfo.info.mask)
        errors = comparator.compare_files(reference_path, output_path)
        assert not errors
