from __future__ import absolute_import
import os

from lisfloodutilities.compare.nc import NetCDFComparator

from lisflood.main import lisfloodexe

from .test_utils import setoptions, mk_path_out, ETRS89TestCase


class TestWaterAbstraction(ETRS89TestCase):
    def test_waterabstraction_24h(self):
      dt_sec = 86400
      self.run_lisflood_waterabstraction(dt_sec)

    def test_waterabstraction_6h(self):
      dt_sec = 21600
      self.run_lisflood_waterabstraction(dt_sec)

    def run_lisflood_waterabstraction(self, dt_sec):
        case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_ETRS89_UseCase')
        out_dir = os.path.join(case_dir, 'out')
        mk_path_out(out_dir)

        settings_file = os.path.join(case_dir, 'settings', 'full.xml')
        out_dir_a = os.path.join(case_dir, 'out', 'a')
        out_dir_b = os.path.join(case_dir, 'out', 'b')
        
        settings_a = setoptions(settings_file,
                                opts_to_set=('TransientWaterDemandChange', 'useWaterDemandAveYear'),
                                vars_to_set={'StepStart': '30/07/2016 00:00', 'StepEnd': '01/08/2016 00:00',
                                             'DtSec': dt_sec, 'PathOut': '$(PathRoot)/out/a',
                                             'PathWaterUse': '$(PathRoot)/maps/waterdemand'
                                             })
        mk_path_out(out_dir_a)
        lisfloodexe(settings_a)

        settings_b = setoptions(settings_file,
                                opts_to_set=('TransientWaterDemandChange'),
                                opts_to_unset=('useWaterDemandAveYear'),
                                vars_to_set={'StepStart': '30/07/2016 00:00', 'StepEnd': '01/08/2016 00:00',
                                             'DtSec': dt_sec, 'PathOut': '$(PathRoot)/out/b',
                                             'PathWaterUse': '$(PathRoot)/maps/waterdemand19902019'})
        mk_path_out(out_dir_b)
        lisfloodexe(settings_b)

        comparator = NetCDFComparator(settings_a.maskpath, array_equal=True)
        comparator.compare_dirs(out_dir_b, out_dir_a)
