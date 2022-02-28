from __future__ import absolute_import
import os
import datetime
import shutil
import pytest

from lisfloodutilities.compare.nc import NetCDFComparator

from lisflood.main import lisfloodexe
from lisflood.global_modules.settings import LisSettings

from .test_utils import setoptions, mk_path_out, ETRS89TestCase


class TestChunking(ETRS89TestCase):
    case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_ETRS89_UseCase')
    settings_file = os.path.join(case_dir, 'settings', 'full.xml')
    out_dir_a = os.path.join(case_dir, 'out', 'a')
    out_dir_b = os.path.join(case_dir, 'out', 'b')
    out_dir_c = os.path.join(case_dir, 'out', 'c')
    out_dir_d = os.path.join(case_dir, 'out', 'd')

    def test_chunking_24h(self):
      dt_sec = 86400
      self.run_lisflood_chunking(dt_sec)

    def test_chunking_6h(self):
      dt_sec = 21600
      self.run_lisflood_chunking(dt_sec)

    def run_lisflood_chunking(self, dt_sec):
        
        settings_a = setoptions(self.settings_file,
                                vars_to_set={'StepStart': '30/07/2016 06:00', 'StepEnd': '01/09/2016 06:00',
                                             'DtSec': dt_sec, 'PathOut': '$(PathRoot)/out/a',
                                             'NetCDFTimeChunks': '1'})
        mk_path_out(self.out_dir_a)
        lisfloodexe(settings_a)
        comparator = NetCDFComparator(settings_a.maskpath, array_equal=True)
        out_a = settings_a.output_dir

        settings_b = setoptions(self.settings_file,
                                vars_to_set={'StepStart': '30/07/2016 06:00', 'StepEnd': '01/09/2016 06:00',
                                             'DtSec': dt_sec, 'PathOut': '$(PathRoot)/out/b',
                                             'NetCDFTimeChunks': '10'})
        mk_path_out(self.out_dir_b)
        lisfloodexe(settings_b)
        out_b = settings_b.output_dir
        comparator.compare_dirs(out_a, out_b)

        settings_c = setoptions(self.settings_file,
                                vars_to_set={'StepStart': '30/07/2016 06:00', 'StepEnd': '01/09/2016 06:00',
                                             'DtSec': dt_sec, 'PathOut': '$(PathRoot)/out/c',
                                             'NetCDFTimeChunks': 'auto'})
        mk_path_out(self.out_dir_c)
        lisfloodexe(settings_c)
        out_c = settings_c.output_dir
        comparator.compare_dirs(out_a, out_c)

        settings_d = setoptions(self.settings_file,
                                vars_to_set={'StepStart': '30/07/2016 06:00', 'StepEnd': '01/09/2016 06:00',
                                             'DtSec': dt_sec, 'PathOut': '$(PathRoot)/out/d',
                                             'NetCDFTimeChunks': '-1'})
        mk_path_out(self.out_dir_d)
        lisfloodexe(settings_d)
        out_d = settings_d.output_dir
        comparator.compare_dirs(out_a, out_d)

    def teardown_method(self):
        print('Cleaning directories')
        shutil.rmtree(self.out_dir_a, ignore_errors=True)
        shutil.rmtree(self.out_dir_b, ignore_errors=True)
        shutil.rmtree(self.out_dir_c, ignore_errors=True)
        shutil.rmtree(self.out_dir_d, ignore_errors=True)
