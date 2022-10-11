from __future__ import absolute_import
import os
import datetime
import shutil

from lisfloodutilities.compare.nc import NetCDFComparator

from lisflood.main import lisfloodexe

from .test_utils import setoptions, mk_path_out


class TestStepsDates():
    settings_files = {
        'full': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/full.xml')
    }

    def test_dates_before_1970(self):
        settings = setoptions(self.settings_files['full'],
                                     opts_to_set=['repStateMaps', 'repEndMaps', 'repDischargeMaps',
                                                  'repSnowMaps', 'repLZMaps', 'repUZMaps'],
                                     vars_to_set={'StepStart': '01/01/1951 06:00', 'StepEnd': '05/01/1951 06:00',
                                                  'CalendarDayStart': '01/01/1900 00:00', 'DtSec': '21600',
                                                  'PathOut': '$(PathRoot)/out/0', 'PathMeteo': '$(PathRoot)/meteo_1950'}
                                     )
        mk_path_out('data/LF_ETRS89_UseCase/out/0')
        lisfloodexe(settings)
        assert settings.step_start_int == 74510
        assert settings.step_end_int == 74526
        assert settings.step_start_dt == datetime.datetime(1951, 1, 1, 6, 0)
        assert settings.step_end_dt == datetime.datetime(1951, 1, 5, 6, 0)


    def test_dates_steps_daily(self):
        settings_a = setoptions(self.settings_files['full'],
                                opts_to_set=['repStateMaps', 'repEndMaps', 'repDischargeMaps',
                                             'repSnowMaps', 'repLZMaps', 'repUZMaps'],
                                vars_to_set={'StepStart': '30/07/2016 06:00', 'StepEnd': '01/08/2016 06:00',
                                             'PathOut': '$(PathRoot)/out/1'}
                                )
        mk_path_out('data/LF_ETRS89_UseCase/out/1')
        lisfloodexe(settings_a)
        settings_b = setoptions(self.settings_files['full'],
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

        comparator = NetCDFComparator(settings_a.maskpath, array_equal=True)
        out_a = settings_a.output_dir
        out_b = settings_b.output_dir
        comparator.compare_dirs(out_a, out_b)

    def test_dates_steps_6h(self):
        settings_a = setoptions(self.settings_files['full'],
                                opts_to_set=['repStateMaps', 'repEndMaps', 'repDischargeMaps',
                                             'repSnowMaps', 'repLZMaps', 'repUZMaps'],
                                vars_to_set={'StepStart': '30/07/2016 06:00', 'StepEnd': '31/07/2016 18:00',
                                             'DtSec': '21600',
                                             'PathOut': '$(PathRoot)/out/1'}
                                )
        mk_path_out('data/LF_ETRS89_UseCase/out/1')
        lisfloodexe(settings_a)
        settings_b = setoptions(self.settings_files['full'],
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

        comparator = NetCDFComparator(settings_a.maskpath, array_equal=True)
        out_a = settings_a.output_dir
        out_b = settings_b.output_dir
        comparator.compare_dirs(out_a, out_b)

    def teardown_method(self):
        path_out_0 = os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/out/0')
        path_out_a = os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/out/1')
        path_out_b = os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/out/2')
        for folder in (path_out_0, path_out_a, path_out_b):
            if os.path.exists(folder):
                shutil.rmtree(folder)
