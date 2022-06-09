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

    case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_ETRS89_UseCase')

    def run(self, date_start, date_end, dtsec, type):
        # run with inflow from reference
        out_path_ref = os.path.join(self.case_dir, 'reference', 'inflow_'+type)
        out_path_run = os.path.join(self.case_dir, self.run_type)
        settings_file = os.path.join(self.case_dir, 'settings', 'inflow.xml')
        settings = setoptions(settings_file,
                              opts_to_set=['inflow'],
                              vars_to_set={'StepStart': date_start,
                                           'StepEnd': date_end,
                                           'CalendarDayStart': date_start,
                                           'DtSec' : dtsec,
                                           'MaskMap': '$(PathRoot)/maps/intercatchment_mask.map',
                                           'InflowPoints': '$(PathRoot)/maps/inflow_point_1.nc',
                                           'QInTS': '$(PathRoot)/'+'reference/inflow_'+type+'/inflow.tss',
                                           'PathOut': out_path_run})
        mk_path_out(out_path_run)
        lisfloodexe(settings)

        comparator = TSSComparator()
        reference =  os.path.join(out_path_ref, 'dis.tss')
        output_tss =  os.path.join(out_path_run, 'dis.tss')
        comparator.compare_files(reference, output_tss)

    def teardown_method(self):
        print('Cleaning directories')
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
