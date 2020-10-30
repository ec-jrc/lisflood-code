from __future__ import absolute_import
import os
import datetime
import shutil

from lisfloodutilities.compare import NetCDFComparator

from lisflood.global_modules.settings import MaskInfo
from lisflood.main import lisfloodexe

from . import MixinTestSettings, mk_path_out


class TestStepsDates(MixinTestSettings):
    settings_files = {
        'full': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/full.xml')
    }

    def test_dates_steps_day(self):
        settings_a = self.setoptions(self.settings_files['full'],
                                     opts_to_set=['repStateMaps', 'repEndMaps', 'repDischargeMaps',
                                                  'repSnowMaps', 'repLZMaps', 'repUZMaps'],
                                     vars_to_set={'StepStart': '30/07/2016 06:00', 'StepEnd': '01/08/2016 06:00',
                                                  'PathOut': '$(PathRoot)/out/1'}
                                     )
        mk_path_out('data/LF_ETRS89_UseCase/out/1')
        lisfloodexe(settings_a)
        settings_b = self.setoptions(self.settings_files['full'],
                                     opts_to_set=['repStateMaps', 'repEndMaps', 'repDischargeMaps',
                                                  'repSnowMaps', 'repLZMaps', 'repUZMaps'],
                                     vars_to_set={'StepStart': 6057, 'StepEnd': 6059,
                                                  'PathOut': '$(PathRoot)/out/2'})
        mk_path_out('data/LF_ETRS89_UseCase/out/2')

        lisfloodexe(settings_b)

        assert settings_a.step_start_int == 6057
        assert settings_a.step_end_int == 6059
        assert settings_a.step_start == settings_a.step_start_dt.strftime('%d/%m/%Y %H:%M')
        assert settings_a.step_end == settings_a.step_end_dt.strftime('%d/%m/%Y %H:%M')
        assert settings_b.step_start_dt == datetime.datetime(2016, 7, 30, 6, 0)
        assert settings_b.step_end_dt == datetime.datetime(2016, 8, 1, 6, 0)

        maskinfo = MaskInfo.instance()
        comparator = NetCDFComparator(maskinfo.info.mask)
        out_a = settings_a.output_dir
        out_b = settings_b.output_dir
        comparator.compare_dirs(out_a, out_b)

    def test_dates_steps_6h(self):
        settings_a = self.setoptions(self.settings_files['full'],
                                     opts_to_set=['repStateMaps', 'repEndMaps', 'repDischargeMaps',
                                                  'repSnowMaps', 'repLZMaps', 'repUZMaps'],
                                     vars_to_set={'StepStart': '30/07/2016 06:00', 'StepEnd': '31/07/2016 18:00',
                                                  'DtSec': '21600',
                                                  'PathOut': '$(PathRoot)/out/1'}
                                     )
        mk_path_out('data/LF_ETRS89_UseCase/out/1')
        lisfloodexe(settings_a)
        settings_b = self.setoptions(self.settings_files['full'],
                                     opts_to_set=['repStateMaps', 'repEndMaps', 'repDischargeMaps',
                                                  'repSnowMaps', 'repLZMaps', 'repUZMaps'],
                                     vars_to_set={'StepStart': 24225, 'StepEnd': 24231,
                                                  'DtSec': '21600',
                                                  'PathOut': '$(PathRoot)/out/2'})
        mk_path_out('data/LF_ETRS89_UseCase/out/2')

        lisfloodexe(settings_b)

        assert settings_a.step_start_int == 24225
        assert settings_a.step_end_int == 24231
        assert settings_a.step_start == settings_a.step_start_dt.strftime('%d/%m/%Y %H:%M')
        assert settings_a.step_end == settings_a.step_end_dt.strftime('%d/%m/%Y %H:%M')
        assert settings_b.step_start_dt == datetime.datetime(2016, 7, 30, 6, 0)
        assert settings_b.step_end_dt == datetime.datetime(2016, 7, 31, 18, 0)

        maskinfo = MaskInfo.instance()
        comparator = NetCDFComparator(maskinfo.info.mask)
        out_a = settings_a.output_dir
        out_b = settings_b.output_dir
        comparator.compare_dirs(out_a, out_b)

    def teardown_method(self):
        path_out_a = os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/out/1')
        path_out_b = os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/out/2')
        shutil.rmtree(path_out_a)
        shutil.rmtree(path_out_b)
