from __future__ import absolute_import
import os
import datetime
import shutil
import pytest

from lisfloodutilities.compare.nc import NetCDFComparator
from lisfloodutilities.compare.pcr import TSSComparator

from lisflood.main import lisfloodexe
from lisflood.global_modules.settings import LisSettings

from .test_utils import setoptions, mk_path_out

@pytest.mark.slow
class TestInflow():

    case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_ETRS89_UseCase')

    def run(self, date_start, date_end, dtsec, type):

        # generate inflow (inflow.tss) one pixel upstream of inflow point

        out_path_ref = os.path.join(self.case_dir, 'reference_mct_dyn')
        out_path_run = os.path.join(self.case_dir, 'reference_mct_dyn', 'inflow_'+type)
        settings_file = os.path.join(self.case_dir, 'settings', 'mct_inflow.xml')
        settings = setoptions(settings_file,
                              opts_to_set = ['MCTRouting'],
                               opts_to_unset = ['inflow',
                                               'SplitRouting'],
                              vars_to_set={'StepStart': date_start,
                                           'StepEnd': date_end,
                                           'CalendarDayStart': date_start,
                                           'DtSec' : dtsec,
                                           # 'DtSecChannel' : dtsec,        # single routing step
                                           'BankFullPerc': '0.1',
                                           'MaskMap': '$(PathRoot)/maps/mask.nc',
                                           'Gauges': '4317500 2447500',  # one cell upstream of inflow point
                                           'ChanqavgdtTS': out_path_run+'/inflow.tss',  # use chanqavgdt as inflow
                                           'PathOut': out_path_run})
        mk_path_out(out_path_ref)
        mk_path_out(out_path_run)
        lisfloodexe(settings)

        # generate control run at inflow point

        out_path_run = os.path.join(self.case_dir, 'reference_mct_dyn', 'inflow_'+type)
        settings_file = os.path.join(self.case_dir, 'settings', 'mct_inflow.xml')
        settings = setoptions(settings_file,
                              opts_to_set = ['MCTRouting'],
                              opts_to_unset = ['inflow',
                                               'SplitRouting'],
                              vars_to_set={'StepStart': date_start,
                                           'StepEnd': date_end,
                                           'CalendarDayStart': date_start,
                                           'DtSec' : dtsec,
                                           # 'DtSecChannel': dtsec,     # single routing step
                                           'BankFullPerc': '0.1',
                                           'MaskMap': '$(PathRoot)/maps/mask.nc',
                                           'Gauges': '4322500 2447500', # inflow point
                                           'PathOut': out_path_run})

        lisfloodexe(settings)

        # run with inflow from dynamic reference and generate outflow at inflow point

        out_path_ref = os.path.join(self.case_dir, 'reference_mct_dyn', 'inflow_'+type)
        out_path_run = os.path.join(self.case_dir, self.run_type)
        settings_file = os.path.join(self.case_dir, 'settings', 'mct_inflow.xml')
        settings = setoptions(settings_file,
                              opts_to_set=['inflow',
                                           'MCTRouting'],
                              opts_to_unset=['SplitRouting'],
                              vars_to_set={'StepStart': date_start,
                                           'StepEnd': date_end,
                                           'CalendarDayStart': date_start,
                                           'DtSec' : dtsec,
                                           # 'DtSecChannel': dtsec,     # single routing step
                                           'BankFullPerc': '0.1',
                                           'MaskMap': '$(PathRoot)/maps/interbasin_mask.nc',
                                           'InflowPoints': '$(PathRoot)/maps/inflow_point_1.nc',
                                           'QInTS': out_path_ref+'/inflow.tss',
                                           'Gauges': '4322500 2447500',  # inflow point
                                           'PathOut': out_path_run})
        mk_path_out(out_path_run)
        lisfloodexe(settings)

        # set precision for the test and number of steps to skip at the beginning of the time series
        atol = 505.
        rtol = 0.01
        init_steps_to_skip = 20
        comparator = TSSComparator(atol,rtol,init_steps_to_skip)

        # test when DtSec = DtSecChannel
        reference =  os.path.join(out_path_ref, 'disWin.tss')
        output_tss =  os.path.join(out_path_run, 'disWin.tss')
        comparator.compare_files(reference, output_tss)

        # test when DtSec != DtSecChannel
        reference =  os.path.join(out_path_ref, 'chanqWin.tss')
        output_tss =  os.path.join(out_path_run, 'chanqWin.tss')
        comparator.compare_files(reference, output_tss)

        # test when DtSec != DtSecChannel
        reference =  os.path.join(out_path_ref, 'chanqavgdt.tss')
        output_tss =  os.path.join(out_path_run, 'chanqavgdt.tss')
        comparator.compare_files(reference, output_tss)


    def teardown_method(self, type):
        print('Cleaning directories')

        ref_path = os.path.join(self.case_dir, 'reference_mct_dyn')
        if os.path.exists(ref_path) and os.path.isdir(ref_path):
            shutil.rmtree(ref_path, ignore_errors=True)

        out_path = os.path.join(self.case_dir, self.run_type)
        if os.path.exists(out_path) and os.path.isdir(out_path):
            shutil.rmtree(out_path, ignore_errors=True)


class TestInflowLong(TestInflow):

    run_type = 'long'

    def test_inflow_6h(self):
        self.run("02/01/2016 06:00", "30/12/2016 06:00", 21600,'6h')

    def test_inflow_daily(self):
         self.run("02/01/2016 06:00", "30/12/2016 06:00", 86400,'daily')

    # cleaning folders
    def cleaning(self,):
        self.teardown_method()

