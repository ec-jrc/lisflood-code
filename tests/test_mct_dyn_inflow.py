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


class TestInflow():

    case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_MCT_UseCase')

    def run(self, date_start, date_end, dtsec, type):
        # generate inflow (inflow.tss) one pixel upstream of inflow point
        out_path_ref = os.path.join(self.case_dir, 'reference_mct_dyn')
        out_path_run = os.path.join(self.case_dir, 'reference_mct_dyn', 'inflow_'+type)
        settings_file = os.path.join(self.case_dir, 'settings', 'mct_inflow.xml')
        settings = setoptions(settings_file,
                              opts_to_unset = ['inflow'],
                              vars_to_set={'StepStart': date_start,
                                           'StepEnd': date_end,
                                           'CalendarDayStart': date_start,
                                           'DtSec' : dtsec,
                                           # 'DtSecChannel' : dtsec,        # single routing step
                                           'MaskMap': '$(PathRoot)/maps/mask.nc',
                                           # 'Gauges': '4317500 2447500  4322500 2447500  4322500 2442500',
                                           'Gauges': '4292500 2377500',  # one cell upstream of inflow point
                                           'ChanqTS': out_path_run+'/inflow.tss',
                                           'PathOut': out_path_run})
        mk_path_out(out_path_ref)
        mk_path_out(out_path_run)
        lisfloodexe(settings)

        # generate control run at inflow point
        out_path_run = os.path.join(self.case_dir, 'reference_mct_dyn', 'inflow_'+type)
        settings_file = os.path.join(self.case_dir, 'settings', 'mct_inflow.xml')
        settings = setoptions(settings_file,
                              opts_to_unset = ['inflow'],
                              vars_to_set={'StepStart': date_start,
                                           'StepEnd': date_end,
                                           'CalendarDayStart': date_start,
                                           'DtSec' : dtsec,
                                           # 'DtSecChannel': dtsec,     # single routing step
                                           'MaskMap': '$(PathRoot)/maps/mask.nc',
                                           # 'Gauges': '4322500 2447500  4322500 2442500',
                                           # 'Gauges': '4322500 2447500  4447500 2422500',    # inflow and outlet
                                           'Gauges': '4297500 2372500',                       # inflow point
                                           'PathOut': out_path_run})
        # mk_path_out(out_path_run)
        lisfloodexe(settings)

        # run with inflow from dynamic reference and generate outflow at inflow point
        out_path_ref = os.path.join(self.case_dir, 'reference_mct_dyn', 'inflow_'+type)
        out_path_run = os.path.join(self.case_dir, self.run_type)
        settings_file = os.path.join(self.case_dir, 'settings', 'mct_inflow.xml')
        settings = setoptions(settings_file,
                              opts_to_set=['inflow'],
                              # opts_to_unset=['SplitRouting'],
                              vars_to_set={'StepStart': date_start,
                                           'StepEnd': date_end,
                                           'CalendarDayStart': date_start,
                                           'DtSec' : dtsec,
                                           # 'DtSecChannel': dtsec,     # single routing step
                                           'MaskMap': '$(PathRoot)/maps/interbasin_mask.nc',
                                           'InflowPoints': '$(PathRoot)/maps/inflow.nc',
                                           'QInTS': out_path_ref+'/inflow.tss',
                                           # 'Gauges': '4322500 2447500  4322500 2442500',
                                           # 'Gauges': '4322500 2447500  4447500 2422500',    # inflow and outlet
                                           'Gauges': '4297500 2372500',                       # inflow point
                                           'PathOut': out_path_run})
        mk_path_out(out_path_run)
        lisfloodexe(settings)

        # set precisioon for the test
        atol = 3.
        rtol = 0.005
        comparator = TSSComparator(atol,rtol)

        # test when DtSec = DtSecChannel
        # reference =  os.path.join(out_path_ref, 'dis.tss')
        # output_tss =  os.path.join(out_path_run, 'dis.tss')

        # test when DtSec != DtSecChannel
        reference =  os.path.join(out_path_ref, 'chanqX.tss')
        output_tss =  os.path.join(out_path_run, 'chanqX.tss')

        comparator.compare_files(reference, output_tss)

    def teardown_method(self):
        print('Cleaning directories')
        ref_path = os.path.join(self.case_dir, 'reference_mct_dyn', 'inflow_'+ str(type))
        shutil.rmtree(ref_path, ignore_errors=True)
        out_path = os.path.join(self.case_dir, self.run_type)
        shutil.rmtree(out_path, ignore_errors=True)


class TestInflowShort(TestInflow):

    run_type = 'short'

    def test_inflow_6h(self):
        self.run("01/03/2016 06:00", "30/03/2016 06:00", 21600,'6h')

    def test_inflow_daily(self):
         self.run("02/01/2016 06:00", "30/01/2016 06:00", 86400,'daily')


# @pytest.mark.slow
# class TestInflowLong(TestInflow):
#
#     run_type = 'long'
#
#     def test_inflow_short(self):
#         self.run("02/01/1986 00:00", "01/01/2018 00:00")
