"""

Copyright 2019-2020 European Union

Licensed under the EUPL, Version 1.2 or as soon they will be approved by the European Commission  subsequent versions of the EUPL (the "Licence");

You may not use this work except in compliance with the Licence.
You may obtain a copy of the Licence at:

https://joinup.ec.europa.eu/sites/default/files/inline-files/EUPL%20v1_2%20EN(1).txt

Unless required by applicable law or agreed to in writing, software distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and limitations under the Licence.

"""

from __future__ import absolute_import
import os
from datetime import datetime, timedelta

from netCDF4 import Dataset

from lisfloodutilities.compare import NetCDFComparator

from lisflood.global_modules.settings import MaskInfo
from lisflood.main import lisfloodexe

from tests import TestSettings


def mk_path_out(p):
    path_out = os.path.join(os.path.dirname(__file__), p)
    if not os.path.exists(path_out):
        os.mkdir(path_out)
    return path_out


class TestWarmStartDays(TestSettings):
    settings_files = {
        'prerun': os.path.join(os.path.dirname(__file__), 'data/settings/prerun.xml'),
        'cold': os.path.join(os.path.dirname(__file__), 'data/settings/cold.xml'),
        'warm': os.path.join(os.path.dirname(__file__), 'data/settings/warm.xml')
    }

    def test_warmstart(self):
        step_start = '01/01/2000 06:00'
        step_end = '01/02/2000 06:00'
        dt_sec = 86400
        path_out = mk_path_out('data/TestCatchment/outputs/init')
        settings_prerun = self.setoptions(self.settings_files['prerun'],
                                          vars_to_set={'DtSec': dt_sec, 'PathOut': path_out,
                                                       'StepStart': step_start,
                                                       'StepEnd': step_end})
        step_start_dt = settings_prerun.step_start_dt
        step_end_dt = settings_prerun.step_end_dt
        lisfloodexe(settings_prerun)

        lzavin_path = settings_prerun.binding['LZAvInflowMap']
        avgdis_path = settings_prerun.binding['AvgDis']
        path_out = mk_path_out('data/TestCatchment/outputs/longrun_reference')
        settings_longrun = self.setoptions(self.settings_files['cold'],
                                           vars_to_set={'StepStart': step_start,
                                                        'StepEnd': step_end,
                                                        'LZAvInflowMap': lzavin_path,
                                                        'PathOut': path_out,
                                                        'AvgDis': avgdis_path, 'DtSec': '86400'})
        lisfloodexe(settings_longrun)

        # warm run (1. Cold start)
        run_number = 1
        cold_start_step_end = step_start
        path_out = mk_path_out('data/TestCatchment/outputs/run_{}'.format(run_number))
        settings_coldstart = self.setoptions(self.settings_files['cold'],
                                             vars_to_set={'StepStart': step_start,
                                                          'StepEnd': cold_start_step_end,
                                                          'LZAvInflowMap': lzavin_path,
                                                          'PathOut': path_out,
                                                          'AvgDis': avgdis_path, 'DtSec': dt_sec})
        lisfloodexe(settings_coldstart)

        # warm run (2. warm starts with initial conditions)
        prev_settings = settings_coldstart
        warm_step_start = prev_settings.step_end_dt + timedelta(seconds=dt_sec)
        warm_step_end = warm_step_start
        timestep_init = prev_settings.step_end_dt.strftime('%d/%m/%Y %H:%M')
        while warm_step_start <= step_end_dt:
            run_number += 1
            path_init = prev_settings.output_dir
            path_out = mk_path_out('data/TestCatchment/outputs/run_{}'.format(run_number))

            settings_warmstart = self.setoptions(self.settings_files['warm'],
                                                 vars_to_set={'StepStart': warm_step_start.strftime('%d/%m/%Y %H:%M'),
                                                              'StepEnd': warm_step_end.strftime('%d/%m/%Y %H:%M'),
                                                              'LZAvInflowMap': lzavin_path,
                                                              'PathOut': path_out,
                                                              'PathInit': path_init,
                                                              'timestepInit': timestep_init,
                                                              'AvgDis': avgdis_path, 'DtSec': dt_sec})
            lisfloodexe(settings_warmstart)
            prev_settings = settings_warmstart

            warm_step_start = prev_settings.step_end_dt + timedelta(seconds=dt_sec)
            warm_step_end = warm_step_start
            timestep_init = prev_settings.step_end_dt.strftime('%d/%m/%Y %H:%M')

        # TODO
        assert False
