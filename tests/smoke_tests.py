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
from __future__ import absolute_import, print_function, division

import os
import warnings

import pytest

from lisflood.global_modules.errors import LisfloodWarning, LisfloodError
from lisflood.main import lisfloodexe
from tests import TestLis

current_dir = os.path.dirname(os.path.abspath(__file__))

warnings.simplefilter('ignore', LisfloodWarning)


class TestCatch1(TestLis):
    settings_path = os.path.join(current_dir, 'data/TestCatchment1/settings/cold_day_base.xml')

    def test_dis(self):
        return self.listest('dis_1')

    def test_initvars(self):
        out_dir = os.path.join(current_dir, 'data/TestCatchment1/outputs')
        initcond_files = ('ch2cr.end.nc', 'chcro.end.nc', 'chside.end.nc', 'cseal.end.nc', 'cum.end.nc', 'cumf.end.nc',
                          'cumi.end.nc', 'dis.end.nc', 'dslf.end.nc', 'dsli.end.nc', 'dslr.end.nc', 'frost.end.nc', 'lz.end.nc',
                          'rsfil.end.nc', 'scova.end.nc', 'scovb.end.nc', 'scovc.end.nc', 'tha.end.nc', 'thb.end.nc',
                          'thc.end.nc', 'thfa.end.nc', 'thfb.end.nc', 'thfc.end.nc', 'thia.end.nc', 'thib.end.nc',
                          'thic.end.nc', 'uz.end.nc', 'uzf.end.nc', 'uzi.end.nc', 'wdept.end.nc')
        for f in initcond_files:
            assert os.path.exists(os.path.join(out_dir, f))


class TestCatch2(TestLis):
    settings_path = os.path.join(current_dir, 'data/TestCatchment2/settings/prerun.xml')

    def test_dis(self):
        return self.listest('dis_2')

    def test_initvars(self):
        out_dir = os.path.join(current_dir, 'data/TestCatchment2/outputs')
        initcond_files = ('avgdis.nc', 'lzavin.nc',)
        for f in initcond_files:
            assert os.path.exists(os.path.join(out_dir, f))


class TestWrongTimestepInit:
    settings_path = os.path.join(current_dir, 'data/TestCatchment1/settings/warm_day_wrong_timestepinit.xml')

    def test_raisexc(self):
        with pytest.raises(LisfloodError) as e:
            assert lisfloodexe(self.settings_path)
        assert 'Option timestepInit was not parsable.' in str(e.value)
