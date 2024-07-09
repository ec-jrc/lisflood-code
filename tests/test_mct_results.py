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


class TestTSSResults():

    case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_MCT_UseCase')

    def run_mct(self, date_start, date_end, dtsec, dtsec_chan, type):
        # generate lisflood results
        out_path_ref = os.path.join(self.case_dir, 'reference', 'output_reference_mct_'+type)
        self.out_path_run = os.path.join(self.case_dir, 'out', 'output_'+type)
        settings_file = os.path.join(self.case_dir, 'settings', 'mct_cold.xml')
        settings = setoptions(settings_file,
                              opts_to_set = ['MCTRouting'],
                              opts_to_unset=['SplitRouting'],
                              vars_to_set={'StepStart': date_start,
                                           'StepEnd': date_end,
                                           'CalendarDayStart': date_start,
                                           'DtSec' : dtsec,
                                           'DtSecChannel' : dtsec_chan,        # single routing step
                                           'PathOut': self.out_path_run})

        mk_path_out(self.out_path_run)
        lisfloodexe(settings)

        # set precisioon for the test
        atol = 0.00001
        rtol = 0.0001
        comparator = TSSComparator(atol,rtol)

        # compare results for average discharge output
        reference =  os.path.join(out_path_ref, 'disX.tss')
        output_tss =  os.path.join(self.out_path_run, 'disX.tss')
        comparator.compare_files(reference, output_tss)

        # compare results for instant discharge output
        reference =  os.path.join(out_path_ref, 'chanqX.tss')
        output_tss =  os.path.join(self.out_path_run, 'chanqX.tss')
        comparator.compare_files(reference, output_tss)

        # compare mass balance error
        reference =  os.path.join(out_path_ref, 'mbError.tss')
        output_tss =  os.path.join(self.out_path_run, 'mbError.tss')
        comparator.compare_files(reference, output_tss)

    def run_mcts(self, date_start, date_end, dtsec, dtsec_chan, type):
        # generate lisflood results
        out_path_ref = os.path.join(self.case_dir, 'reference', 'output_reference_mcts_'+type)
        self.out_path_run = os.path.join(self.case_dir, 'out', 'output_'+type)
        settings_file = os.path.join(self.case_dir, 'settings', 'mct_cold.xml')
        settings = setoptions(settings_file,
                              opts_to_set = ['MCTRouting',
                                             'SplitRouting'],
                              vars_to_set={'StepStart': date_start,
                                           'StepEnd': date_end,
                                           'CalendarDayStart': date_start,
                                           'DtSec' : dtsec,
                                           'DtSecChannel' : dtsec_chan,        # single routing step
                                           'PathOut': self.out_path_run})

        mk_path_out(self.out_path_run)
        lisfloodexe(settings)

        # set precisioon for the test
        atol = 0.00001
        rtol = 0.0001
        comparator = TSSComparator(atol,rtol)

        # compare results for average discharge output
        reference =  os.path.join(out_path_ref, 'disX.tss')
        output_tss =  os.path.join(self.out_path_run, 'disX.tss')
        comparator.compare_files(reference, output_tss)

        # compare results for instant discharge output
        reference =  os.path.join(out_path_ref, 'chanqX.tss')
        output_tss =  os.path.join(self.out_path_run, 'chanqX.tss')
        comparator.compare_files(reference, output_tss)

        # compare mass balance error
        reference =  os.path.join(out_path_ref, 'mbError.tss')
        output_tss =  os.path.join(self.out_path_run, 'mbError.tss')
        comparator.compare_files(reference, output_tss)

        # compare split routing mass balance error
        reference =  os.path.join(out_path_ref, 'mbErrorSplitRoutingM3.tss')
        output_tss =  os.path.join(self.out_path_run, 'mbErrorSplitRoutingM3.tss')
        comparator.compare_files(reference, output_tss)

        # compare split routing outlet mass balance error
        reference =  os.path.join(out_path_ref, 'OutletDischargeErrorSplitRoutingM3S.tss')
        output_tss =  os.path.join(self.out_path_run, 'OutletDischargeErrorSplitRoutingM3S.tss')
        comparator.compare_files(reference, output_tss)

    def run_kin(self, date_start, date_end, dtsec, dtsec_chan, type):
        # generate lisflood results
        out_path_ref = os.path.join(self.case_dir, 'reference', 'output_reference_kin_'+type)
        self.out_path_run = os.path.join(self.case_dir, 'out', 'output_'+type)
        settings_file = os.path.join(self.case_dir, 'settings', 'mct_cold.xml')
        settings = setoptions(settings_file,
                              opts_to_unset=['MCTRouting',
                                             'SplitRouting'],
                              vars_to_set={'StepStart': date_start,
                                           'StepEnd': date_end,
                                           'CalendarDayStart': date_start,
                                           'DtSec' : dtsec,
                                           'DtSecChannel' : dtsec_chan,        # single routing step
                                           'PathOut': self.out_path_run})

        mk_path_out(self.out_path_run)
        lisfloodexe(settings)

        # set precisioon for the test
        atol = 0.00001
        rtol = 0.0001
        comparator = TSSComparator(atol,rtol)

        # compare results for average discharge output
        reference =  os.path.join(out_path_ref, 'disX.tss')
        output_tss =  os.path.join(self.out_path_run, 'disX.tss')
        comparator.compare_files(reference, output_tss)

        # compare results for instant discharge output
        reference =  os.path.join(out_path_ref, 'chanqX.tss')
        output_tss =  os.path.join(self.out_path_run, 'chanqX.tss')
        comparator.compare_files(reference, output_tss)

        # compare mass balance error
        reference =  os.path.join(out_path_ref, 'mbError.tss')
        output_tss =  os.path.join(self.out_path_run, 'mbError.tss')
        comparator.compare_files(reference, output_tss)

    def run_split(self, date_start, date_end, dtsec, dtsec_chan, type):
        # generate lisflood results
        out_path_ref = os.path.join(self.case_dir, 'reference', 'output_reference_split_'+type)
        self.out_path_run = os.path.join(self.case_dir, 'out', 'output_'+type)
        settings_file = os.path.join(self.case_dir, 'settings', 'mct_cold.xml')
        settings = setoptions(settings_file,
                              opts_to_set = ['SplitRouting'],
                              opts_to_unset=['MCTRouting'],
                              vars_to_set={'StepStart': date_start,
                                           'StepEnd': date_end,
                                           'CalendarDayStart': date_start,
                                           'DtSec' : dtsec,
                                           'DtSecChannel' : dtsec_chan,        # single routing step
                                           'PathOut': self.out_path_run})

        mk_path_out(self.out_path_run)
        lisfloodexe(settings)

        # set precision for the test
        atol = 0.00001
        rtol = 0.0001
        comparator = TSSComparator(atol,rtol)

        # compare results for average discharge output
        reference =  os.path.join(out_path_ref, 'disX.tss')
        output_tss =  os.path.join(self.out_path_run, 'disX.tss')
        comparator.compare_files(reference, output_tss)

        # compare results for instant discharge output
        reference =  os.path.join(out_path_ref, 'chanqX.tss')
        output_tss =  os.path.join(self.out_path_run, 'chanqX.tss')
        comparator.compare_files(reference, output_tss)

        # compare mass balance error
        reference =  os.path.join(out_path_ref, 'mbError.tss')
        output_tss =  os.path.join(self.out_path_run, 'mbError.tss')
        comparator.compare_files(reference, output_tss)

        # compare split routing mass balance error
        reference =  os.path.join(out_path_ref, 'mbErrorSplitRoutingM3.tss')
        output_tss =  os.path.join(self.out_path_run, 'mbErrorSplitRoutingM3.tss')
        comparator.compare_files(reference, output_tss)

        # compare split routing outlet mass balance error
        reference =  os.path.join(out_path_ref, 'OutletDischargeErrorSplitRoutingM3S.tss')
        output_tss =  os.path.join(self.out_path_run, 'OutletDischargeErrorSplitRoutingM3S.tss')
        comparator.compare_files(reference, output_tss)

    def teardown_method(self):
        print('Cleaning directories')
        out_path = os.path.join(self.case_dir, self.out_path_run)
        shutil.rmtree(out_path, ignore_errors=True)


class TestMCTResults(TestTSSResults):

    run_type = 'short'

    ###########################################
    # test results of MCT+KIN routing
    def test_MCT_6h(self):
        self.run_mct("02/01/2016 06:00", "02/07/2016 06:00", 21600, 21600,'6h')
    def test_MCT_6h_1h(self):
        self.run_mct("02/01/2016 06:00", "02/07/2016 06:00", 21600, 3600,'6h_1h')
    def test_MCT_daily(self):
         self.run_mct("02/01/2016 06:00", "02/07/2016 06:00", 86400, 86400,'daily')
    def test_MCT_daily_6h(self):
         self.run_mct("02/01/2016 06:00", "02/07/2016 06:00", 86400, 21600,'daily_6h')
    def test_MCT_daily_1h(self):
         self.run_mct("02/01/2016 06:00", "02/07/2016 06:00", 86400, 3600, 'daily_1h')

    ###########################################
    # test results of MCT+SPLIT routing
    def test_MCTS_6h(self):
        self.run_mcts("02/01/2016 06:00", "02/07/2016 06:00", 21600, 21600,'6h')
    def test_MCTS_6h_1h(self):
        self.run_mcts("02/01/2016 06:00", "02/07/2016 06:00", 21600, 3600,'6h_1h')
    def test_MCTS_daily(self):
         self.run_mcts("02/01/2016 06:00", "02/07/2016 06:00", 86400, 86400,'daily')
    def test_MCTS_daily_6h(self):
         self.run_mcts("02/01/2016 06:00", "02/07/2016 06:00", 86400, 21600,'daily_6h')
    def test_MCTS_daily_1h(self):
         self.run_mcts("02/01/2016 06:00", "02/07/2016 06:00", 86400, 3600, 'daily_1h')

    # #########################################
    # test results of Kinemating routing
    def test_KIN_6h(self):
        self.run_kin("02/01/2016 06:00", "02/07/2016 06:00", 21600, 21600,'6h')
    def test_KIN_6h_1h(self):
        self.run_kin("02/01/2016 06:00", "02/07/2016 06:00", 21600, 3600,'6h_1h')
    def test_KIN_daily(self):
         self.run_kin("02/01/2016 06:00", "02/07/2016 06:00", 86400, 86400,'daily')
    def test_KIN_daily_6h(self):
         self.run_kin("02/01/2016 06:00", "02/07/2016 06:00", 86400, 21600,'daily_6h')
    def test_KIN_daily_1h(self):
         self.run_kin("02/01/2016 06:00", "02/07/2016 06:00", 86400, 3600, 'daily_1h')

    # #########################################
    # test results of Split routing
    def test_SPLIT_6h(self):
        self.run_split("02/01/2016 06:00", "02/07/2016 06:00", 21600, 21600, '6h')
    def test_SPLIT_6h_1h(self):
        self.run_split("02/01/2016 06:00", "02/07/2016 06:00", 21600, 3600, '6h_1h')
    def test_SPLIT_daily(self):
        self.run_split("02/01/2016 06:00", "02/07/2016 06:00", 86400, 86400, 'daily')
    def test_SPLIT_daily_6h(self):
        self.run_split("02/01/2016 06:00", "02/07/2016 06:00", 86400, 21600, 'daily_6h')
    def test_SPLIT_daily_1h(self):
        self.run_split("02/01/2016 06:00", "02/07/2016 06:00", 86400, 3600, 'daily_1h')


    def cleaning(self):
        self.teardown_method()


# @pytest.mark.slow
# class TestInflowLong(TestInflow):
#
#     run_type = 'long'
#
#     def test_inflow_short(self):
#         self.run("02/01/1986 00:00", "01/01/2018 00:00")
