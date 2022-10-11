from __future__ import absolute_import
import os
import datetime
import shutil
import pytest

from lisfloodutilities.compare.nc import NetCDFComparator

from lisflood.main import lisfloodexe
from lisflood.global_modules.settings import LisSettings

from .test_utils import setoptions, mk_path_out, ETRS89TestCase


class TestCaching(ETRS89TestCase):

    case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_ETRS89_UseCase')

    settings_file = os.path.join(case_dir, 'settings', 'full.xml')
    out_dir_a = os.path.join(case_dir, 'out', 'a')
    out_dir_b = os.path.join(case_dir, 'out', 'b')

    def test_waterabstraction_24h(self):
      dt_sec = 86400
      self.run_lisflood_waterabstraction(dt_sec)

    def test_waterabstraction_6h(self):
      dt_sec = 21600
      self.run_lisflood_waterabstraction(dt_sec)

    def run_lisflood_waterabstraction(self, dt_sec):
        
        settings_a = setoptions(self.settings_file,
                                opts_to_set=('TransientWaterDemandChange', 'useWaterDemandAveYear'),
                                vars_to_set={'StepStart': '30/07/2016 00:00', 'StepEnd': '01/08/2016 00:00',
                                             'DtSec': dt_sec, 'PathOut': '$(PathRoot)/out/a',
                                             'PathWaterUse': '$(PathRoot)/maps/waterdemand'
                                             })
        mk_path_out(self.out_dir_a)
        lisfloodexe(settings_a)

        settings_b = setoptions(self.settings_file,
                                opts_to_set=('TransientWaterDemandChange'),
                                opts_to_unset=('useWaterDemandAveYear'),
                                vars_to_set={'StepStart': '30/07/2016 00:00', 'StepEnd': '01/08/2016 00:00',
                                             'DtSec': dt_sec, 'PathOut': '$(PathRoot)/out/b',
                                             'PathWaterUse': '$(PathRoot)/maps/waterdemand19902019'})
        mk_path_out(self.out_dir_b)
        lisfloodexe(settings_b)

        comparator = NetCDFComparator(settings_a.maskpath, array_equal=True)
        comparator.compare_dirs(self.out_dir_b, self.out_dir_a)
