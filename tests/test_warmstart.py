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

import pytest

from lisfloodutilities.compare import NetCDFComparator, TSSComparator

from lisflood.global_modules.settings import MaskInfo
from lisflood.main import lisfloodexe

from . import TestSettings, mk_path_out


@pytest.mark.slow
class TestWarmStartDays(TestSettings):
    settings_files = {
        'prerun': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/prerun.xml'),
        'cold': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/cold.xml'),
        'warm': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/warm.xml')
    }

    def test_warmstart_daily(self):
        step_start = '02/01/2000 06:00'
        step_end = '30/12/2000 06:00'  # '30/12/2000 06:00'
        dt_sec = 86400
        report_steps = '3650..4100'
        self.run_warmstart_by_dtsec(dt_sec, step_end, step_start, report_steps=report_steps)

    def test_warmstart_6hourly(self):
        step_start = '01/03/2000 06:00'
        step_end = '31/07/2000 06:00'
        dt_sec = 21600
        report_steps = '14800..16000'
        self.run_warmstart_by_dtsec(dt_sec, step_end, step_start, suffix='_6h', report_steps=report_steps)

    def run_warmstart_by_dtsec(self, dt_sec, step_end, step_start, suffix='_daily', report_steps='1..9999'):
        modules_to_unset = [
            # 'SplitRouting',
            # 'simulateReservoirs',
            'simulateLakes',
            'repsimulateLakes',
            'wateruse',
            'useWaterDemandAveYear',
        ]
        check_every = 13  # steps
        # init
        path_out_init = mk_path_out('data/LF_ETRS89_UseCase/out/init{}'.format(suffix))
        settings_prerun = self.setoptions(self.settings_files['prerun'], opts_to_unset=modules_to_unset,
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
        path_out_reference = mk_path_out('data/LF_ETRS89_UseCase/out/longrun_reference{}'.format(suffix))
        settings_longrun = self.setoptions(self.settings_files['cold'], opts_to_unset=modules_to_unset,
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
        path_out = mk_path_out('data/LF_ETRS89_UseCase/out/run{}_{}'.format(suffix, run_number))
        settings_coldstart = self.setoptions(self.settings_files['cold'], opts_to_unset=modules_to_unset,
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
        maskinfo = MaskInfo.instance()
        nc_comparator = NetCDFComparator(maskinfo.info.mask)
        tss_comparator = TSSComparator(array_equal=True)
        while warm_step_start <= step_end_dt:
            run_number += 1
            path_init = prev_settings.output_dir
            path_out = mk_path_out('data/LF_ETRS89_UseCase/out/run{}_{}'.format(suffix, run_number))

            settings_warmstart = self.setoptions(self.settings_files['warm'], opts_to_unset=modules_to_unset,
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
            # remove previous output/current init dirs (we don't need it anymore after this point)
            shutil.rmtree(path_init)

        # cleaning after (FIXME move to teardown method)
        shutil.rmtree(path_out)

    def teardown_method(self):
        super().teardown_method()
        for suffix in ('_daily', '_6h'):
            if os.path.exists('data/LF_ETRS89_UseCase/out/longrun_reference{}'.format(suffix)):
                shutil.rmtree('data/LF_ETRS89_UseCase/out/longrun_reference{}'.format(suffix))
            if os.path.exists('data/LF_ETRS89_UseCase/out/init{}'.format(suffix)):
                shutil.rmtree('data/LF_ETRS89_UseCase/out/init{}'.format(suffix))
