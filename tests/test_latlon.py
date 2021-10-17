import os
import shutil
import pytest

from lisfloodutilities.compare.pcr import TSSComparator

from lisflood.main import lisfloodexe
from lisflood.global_modules.settings import LisSettings

from .test_utils import setoptions, mk_path_out


class TestLatLon():

    case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_lat_lon_UseCase')

    def run(self, date_start, date_end):

        out_path = os.path.join(self.case_dir, self.run_type)
        settings_file = os.path.join(self.case_dir, 'run_lat_lon.xml')
        settings = setoptions(settings_file,
                              vars_to_set={'StepStart': date_start,
                                           'StepEnd': date_end,
                                           'PathOut': '$(PathRoot)/'+self.run_type})
        mk_path_out(out_path)
        lisfloodexe(settings)

        comparator = TSSComparator()
        reference =  os.path.join(self.case_dir, 'reference', 'dis_{}.tss'.format(self.run_type))
        output_tss =  os.path.join(out_path, 'dis_run.tss')
        comparator.compare_files(reference, output_tss)

    def teardown_method(self):
        print('Cleaning directories')
        out_path = os.path.join(self.case_dir, self.run_type)
        shutil.rmtree(out_path, ignore_errors=True)


class TestLatLonShort(TestLatLon):

    run_type = 'short'

    def test_lat_lon_short(self):
        self.run("01/01/2016 00:00", "01/02/2016 00:00")


@pytest.mark.slow
class TestLatLonLong(TestLatLon):

    run_type = 'long'

    def test_lat_lon_long(self):
        self.run("02/01/1986 00:00", "01/01/2018 00:00")
