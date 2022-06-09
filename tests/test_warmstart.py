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
import shutil
from datetime import timedelta
import glob

import pytest

from lisfloodutilities.compare.nc import NetCDFComparator
from lisfloodutilities.compare.pcr import TSSComparator

from lisflood.main import lisfloodexe

from .test_utils import setoptions, mk_path_out


@pytest.mark.slow
class TestWarmStart():
    settings_files = {
        'prerun': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/prerun.xml'),
        'cold': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/cold.xml'),
        'warm': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/warm.xml')
    }
    
    def test_warmstart_daily(self):
        step_start = '02/01/2016 06:00'
        step_end = '31/12/2016 06:00'
        dt_sec = 86400
        report_steps = '9496..9861'
        self.run_warmstart_by_dtsec(dt_sec, step_end, step_start, report_steps=report_steps)
    
    def test_warmstart_6h(self):
        step_start = '01/03/2016 06:00'
        step_end = '31/07/2016 06:00'
        dt_sec = 21600
        report_steps = '38220..38830'
        self.run_warmstart_by_dtsec(dt_sec, step_end, step_start, report_steps=report_steps)

    def run_warmstart_by_dtsec(self, dt_sec, step_end, step_start, report_steps='1..9999'):
        modules_to_unset = [
            'simulateReservoirs',
            'repsimulateReservoirs',
        ]
        check_every = 13  # steps
        # init
        path_out_init = mk_path_out('data/LF_ETRS89_UseCase/out/init{}'.format(dt_sec))
        settings_prerun = setoptions(self.settings_files['prerun'], opts_to_unset=modules_to_unset,
                                     vars_to_set={'DtSec': dt_sec,
                                                  'PathOut': path_out_init,
                                                  'StepStart': step_start,
                                                  'ReportSteps': report_steps,
                                                  'StepEnd': step_end})
        step_end_dt = settings_prerun.step_end_dt
        # ** execute
        lisfloodexe(settings_prerun)

        # long run
        lzavin_path = settings_prerun.binding['LZAvInflowMap']
        avgdis_path = settings_prerun.binding['AvgDis']
        path_out_reference = mk_path_out('data/LF_ETRS89_UseCase/out/longrun_reference{}'.format(dt_sec))
        settings_longrun = setoptions(self.settings_files['cold'], opts_to_unset=modules_to_unset,
                                      vars_to_set={'StepStart': step_start,
                                                   'StepEnd': step_end,
                                                   'LZAvInflowMap': lzavin_path,
                                                   'PathOut': path_out_reference,
                                                   'AvgDis': avgdis_path,
                                                   'ReportSteps': report_steps,
                                                   'DtSec': dt_sec})
        # ** execute
        lisfloodexe(settings_longrun)

        # warm run (1. Cold start)
        run_number = 1
        cold_start_step_end = step_start
        path_out = mk_path_out('data/LF_ETRS89_UseCase/out/run{}_{}'.format(dt_sec, run_number))
        settings_coldstart = setoptions(self.settings_files['cold'], opts_to_unset=modules_to_unset,
                                        vars_to_set={'StepStart': step_start,
                                                     'StepEnd': cold_start_step_end,
                                                     'LZAvInflowMap': lzavin_path,
                                                     'PathOut': path_out,
                                                     'AvgDis': avgdis_path,
                                                     'ReportSteps': report_steps,
                                                     'DtSec': dt_sec})
        # ** execute
        lisfloodexe(settings_coldstart)

        # warm run (2. single step warm start/stop with initial conditions from previous run)
        prev_settings = settings_coldstart
        warm_step_start = prev_settings.step_end_dt + timedelta(seconds=dt_sec)
        warm_step_end = warm_step_start
        timestep_init = prev_settings.step_end_dt.strftime('%d/%m/%Y %H:%M')

        # run only 5*13 steps to speed up computation
        step_limit = warm_step_start + 5*check_every*timedelta(seconds=dt_sec)
        print('running until {}'.format(step_limit))
        
        nc_comparator = NetCDFComparator(settings_prerun.maskpath)
        tss_comparator = TSSComparator(array_equal=True)
        while warm_step_start <= step_limit:
            run_number += 1
            path_init = prev_settings.output_dir
            path_out = mk_path_out('data/LF_ETRS89_UseCase/out/run{}_{}'.format(dt_sec, run_number))

            settings_warmstart = setoptions(self.settings_files['warm'], opts_to_unset=modules_to_unset,
                                            vars_to_set={'StepStart': warm_step_start.strftime('%d/%m/%Y %H:%M'),
                                                         'StepEnd': warm_step_end.strftime('%d/%m/%Y %H:%M'),
                                                         'LZAvInflowMap': lzavin_path,
                                                         'PathOut': path_out,
                                                         'PathInit': path_init,
                                                         'timestepInit': timestep_init,
                                                         'AvgDis': avgdis_path,
                                                         'ReportSteps': report_steps,
                                                         'DtSec': dt_sec})
            # ** execute
            lisfloodexe(settings_warmstart)

            # checking values at current timestep (using datetime)
            if not (run_number % check_every):
                # ****** compare *******
                # compare every 13 timesteps to speed up test
                timestep_dt = settings_warmstart.step_end_dt  # NetCDFComparator takes datetime.datetime as timestep
                timestep = settings_warmstart.step_end_int
                nc_comparator.compare_dirs(path_out, path_out_reference, timestep=timestep_dt)
                tss_comparator.compare_dirs(path_out, path_out_reference, timestep=timestep)

            # setup for next warm start/stop
            prev_settings = settings_warmstart
            warm_step_start = prev_settings.step_end_dt + timedelta(seconds=dt_sec)
            warm_step_end = warm_step_start
            timestep_init = prev_settings.step_end_dt.strftime('%d/%m/%Y %H:%M')

    def teardown_method(self):
        folders_list = glob.glob(os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/out/run*')) + \
            glob.glob(os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/out/longrun_reference*')) + \
            glob.glob(os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/out/init*'))
        for folder in folders_list:
            shutil.rmtree(folder)
