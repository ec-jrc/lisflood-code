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
class TestWarmStartLong():

    case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_ETRS89_UseCase')

    settings_files = {
        'cold': os.path.join(case_dir, 'settings', 'mct_cold.xml'),
        'warm': os.path.join(case_dir, 'settings', 'mct_warm.xml')
    }

    def test_mct_only_warmstart_daily(self):
        calendar_day_start = '02/01/1990 06:00'
        step_start = '02/01/2016 06:00'
        step_end = '31/12/2016 06:00'
        dt_sec = 86400
        dt_sec_channel = 3600
        report_steps = '9496..9861'
        self.run_warmstart_by_dtsec('mct', dt_sec, dt_sec_channel, step_end, step_start, calendar_day_start,report_steps=report_steps)

    def test_mct_warmstart_daily(self):
        calendar_day_start = '02/01/1990 06:00'
        step_start = '02/01/2016 06:00'
        step_end = '31/12/2016 06:00'
        dt_sec = 86400
        dt_sec_channel = 3600
        report_steps = '9496..9861'
        self.run_warmstart_by_dtsec('mct_all', dt_sec, dt_sec_channel, step_end, step_start, calendar_day_start,report_steps=report_steps)

    def test_mct_only_warmstart_6h(self):
        calendar_day_start = '02/01/1990 06:00'
        step_start = '01/03/2016 06:00'
        step_end = '31/07/2016 06:00'
        dt_sec = 21600
        dt_sec_channel = 3600
        report_steps = '38220..38830'
        self.run_warmstart_by_dtsec('mct', dt_sec, dt_sec_channel, step_end, step_start, calendar_day_start,report_steps=report_steps)

    def test_mct_warmstart_6h(self):
        calendar_day_start = '02/01/1990 06:00'
        step_start = '01/03/2016 06:00'
        step_end = '31/07/2016 06:00'
        dt_sec = 21600
        dt_sec_channel = 3600
        report_steps = '38220..38830'
        self.run_warmstart_by_dtsec('mct_all', dt_sec, dt_sec_channel, step_end, step_start, calendar_day_start,report_steps=report_steps)

    def run_warmstart_by_dtsec(self, mct_case, dt_sec, dt_sec_channel, step_end, step_start, calendar_day_start,report_steps='1..9999'):

        mk_path_out(os.path.join(self.case_dir, 'out'))

        check_every = 13  # steps

        self.path_out_reference = os.path.join(self.case_dir, 'out', 'longrun_reference{}'.format(dt_sec))

        if mct_case == 'mct':
            opts_to_set = ['repDischargeMaps',
                           'repStateMaps']
            opts_to_unset = ['repMBTs', 'simulateReservoirs', 'simulateLakes']
        elif mct_case == 'mct_all':
            opts_to_set = ['repDischargeMaps',
                           'repStateMaps',
                           'wateruse',
                           'drainedIrrigation',
                           'riceIrrigation',
                           'openwaterevapo',
                           'simulateLakes'
                           ]
            opts_to_unset = ['repMBTs',
                             'simulateReservoirs']

        settings_longrun = setoptions(self.settings_files['cold'],
                                    opts_to_set=opts_to_set,
                                    opts_to_unset=opts_to_unset,
                                    vars_to_set={'StepStart': step_start,
                                                   'StepEnd': step_end,
                                                   'CalendarDayStart': calendar_day_start,
                                                   'PathOut': self.path_out_reference,
                                                   'ReportSteps': report_steps,
                                                   'DtSec': dt_sec,
                                                   'DtSecChannel': dt_sec_channel})
        # ** execute
        mk_path_out(self.path_out_reference)
        lisfloodexe(settings_longrun)


        # warm run (1. Cold start)
        run_number = 1
        cold_start_step_end = step_start

        self.path_out = os.path.join(self.case_dir, 'out', 'run{}_{}'.format(dt_sec, run_number))

        settings_coldstart = setoptions(self.settings_files['cold'],
                                        opts_to_set=opts_to_set,
                                        opts_to_unset=opts_to_unset,
                                        vars_to_set={'StepStart': step_start,
                                                        'StepEnd': cold_start_step_end,
                                                        'CalendarDayStart': calendar_day_start,
                                                        'PathOut': self.path_out,
                                                        'ReportSteps': report_steps,
                                                        'DtSec': dt_sec,
                                                        'DtSecChannel': dt_sec_channel})
        # ** execute
        mk_path_out(self.path_out)
        lisfloodexe(settings_coldstart)

        # warm run (2. single step warm start/stop with initial conditions from previous run)
        prev_settings = settings_coldstart
        warm_step_start = prev_settings.step_end_dt + timedelta(seconds=dt_sec)
        warm_step_end = warm_step_start
        timestep_init = prev_settings.step_end_dt.strftime('%d/%m/%Y %H:%M')

        # run only 5*13 steps to speed up computation
        step_limit = warm_step_start + 5*check_every*timedelta(seconds=dt_sec)
        print('running until {}'.format(step_limit))
        
        nc_comparator = NetCDFComparator(settings_longrun.maskpath)
        tss_comparator = TSSComparator(array_equal=True)
        while warm_step_start <= step_limit:
            run_number += 1
            path_init = prev_settings.output_dir
            self.path_out = (os.path.join(self.case_dir, 'out', 'run{}_{}'.format(dt_sec, run_number)))

            settings_warmstart = setoptions(self.settings_files['warm'],
                                            opts_to_set=opts_to_set,
                                            opts_to_unset=opts_to_unset,
                                            vars_to_set={'StepStart': warm_step_start.strftime('%d/%m/%Y %H:%M'),
                                                            'StepEnd': warm_step_end.strftime('%d/%m/%Y %H:%M'),
                                                            'CalendarDayStart': calendar_day_start,
                                                            'PathOut': self.path_out,
                                                            'PathInit': path_init,
                                                            'timestepInit': timestep_init,
                                                            'ReportSteps': report_steps,
                                                            'DtSec': dt_sec,
                                                            'DtSecChannel': dt_sec_channel})
            # ** execute
            mk_path_out(self.path_out)
            lisfloodexe(settings_warmstart)

            # checking values at current timestep (using datetime)
            if not (run_number % check_every):
                # ****** compare *******
                # compare every 13 timesteps to speed up test
                timestep_dt = settings_warmstart.step_end_dt  # NetCDFComparator takes datetime.datetime as timestep
                timestep = settings_warmstart.step_end_int
                nc_comparator.compare_dirs(self.path_out, self.path_out_reference, timestep=timestep_dt)
                tss_comparator.compare_dirs(self.path_out, self.path_out_reference, timestep=timestep)

            # setup for next warm start/stop
            prev_settings = settings_warmstart
            warm_step_start = prev_settings.step_end_dt + timedelta(seconds=dt_sec)
            warm_step_end = warm_step_start
            timestep_init = prev_settings.step_end_dt.strftime('%d/%m/%Y %H:%M')

    ## do not switch this on or next test will fail
    # def teardown_method(self):
    #     print('Cleaning directories')
    #     out_path = os.path.join(self.case_dir, 'out')
    #     if os.path.exists(out_path) and os.path.isdir(out_path):
    #         shutil.rmtree(out_path, ignore_errors=True)