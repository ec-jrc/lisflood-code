from __future__ import absolute_import
import os
import datetime
import shutil
import pytest

from lisfloodutilities.compare.nc import NetCDFComparator

from lisflood.main import lisfloodexe
from lisflood.cache import cache_clear, cache_size, cache_info, cache_found
from lisflood.global_modules.settings import LisSettings

from . import MixinTestSettings, mk_path_out, MixinTestLis


class TestChunking(MixinTestSettings):
    settings_files = {
        'full': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/full.xml')
    }

    def test_chunking_24h(self):
      dt_sec = 86400
      self.run_lisflood_chunking(dt_sec)

    def test_chunking_6h(self):
      dt_sec = 21600
      self.run_lisflood_chunking(dt_sec)

    def run_lisflood_chunking(self, dt_sec):
        
        settings_a = self.setoptions(self.settings_files['full'],
                                     vars_to_set={'StepStart': '30/07/2016 06:00', 'StepEnd': '01/09/2016 06:00',
                                                  'DtSec': dt_sec, 'PathOut': '$(PathRoot)/out/a',
                                                  'NetCDFTimeChunks': '1'})
        mk_path_out('data/LF_ETRS89_UseCase/out/a')
        lisfloodexe(settings_a)
        comparator = NetCDFComparator(settings_a.maskpath, array_equal=True)
        out_a = settings_a.output_dir

        settings_b = self.setoptions(self.settings_files['full'],
                                     vars_to_set={'StepStart': '30/07/2016 06:00', 'StepEnd': '01/09/2016 06:00',
                                                  'DtSec': dt_sec, 'PathOut': '$(PathRoot)/out/b',
                                                  'NetCDFTimeChunks': '10'})
        mk_path_out('data/LF_ETRS89_UseCase/out/b')
        lisfloodexe(settings_b)
        out_b = settings_b.output_dir
        comparator.compare_dirs(out_a, out_b)

        settings_c = self.setoptions(self.settings_files['full'],
                                     vars_to_set={'StepStart': '30/07/2016 06:00', 'StepEnd': '01/09/2016 06:00',
                                                  'DtSec': dt_sec, 'PathOut': '$(PathRoot)/out/c',
                                                  'NetCDFTimeChunks': 'auto'})
        mk_path_out('data/LF_ETRS89_UseCase/out/c')
        lisfloodexe(settings_c)
        out_c = settings_c.output_dir
        comparator.compare_dirs(out_a, out_c)

        settings_d = self.setoptions(self.settings_files['full'],
                                     vars_to_set={'StepStart': '30/07/2016 06:00', 'StepEnd': '01/09/2016 06:00',
                                                  'DtSec': dt_sec, 'PathOut': '$(PathRoot)/out/d',
                                                  'NetCDFTimeChunks': '-1'})
        mk_path_out('data/LF_ETRS89_UseCase/out/d')
        lisfloodexe(settings_d)
        out_d = settings_d.output_dir
        comparator.compare_dirs(out_a, out_d)

    def teardown_method(self):
        print('Cleaning directories')
        path_out_a = os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/out/a')
        path_out_b = os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/out/b')
        path_out_c = os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/out/c')
        path_out_d = os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/out/d')
        shutil.rmtree(path_out_a, ignore_errors=True)
        shutil.rmtree(path_out_b, ignore_errors=True)
        shutil.rmtree(path_out_c, ignore_errors=True)
        shutil.rmtree(path_out_d, ignore_errors=True)
