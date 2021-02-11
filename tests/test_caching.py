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


class TestCaching(MixinTestSettings):
    settings_files = {
        'full': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/full.xml')
    }

    def test_caching_24h(self):
      dt_sec = 86400
      self.run_lisflood_caching(dt_sec)

    def test_caching_6h(self):
      dt_sec = 21600
      self.run_lisflood_caching(dt_sec)

    def run_lisflood_caching(self, dt_sec):
        
        settings_a = self.setoptions(self.settings_files['full'],
                                     vars_to_set={'StepStart': '30/07/2016 06:00', 'StepEnd': '01/08/2016 06:00',
                                                  'DtSec': dt_sec, 'PathOut': '$(PathRoot)/out/a',
                                                  'MapsCaching': 'True'})
        mk_path_out('data/LF_ETRS89_UseCase/out/a')
        lisfloodexe(settings_a)

        cache_size_a = cache_size()
        cache_found_a = cache_found()
        print('Cache size is {}'.format(cache_size_a))
        print('Items found: {}'.format(cache_found_a))

        assert cache_found_a == 0

        settings_b = self.setoptions(self.settings_files['full'],
                                     vars_to_set={'StepStart': '30/07/2016 06:00', 'StepEnd': '01/08/2016 06:00',
                                                  'DtSec': dt_sec, 'PathOut': '$(PathRoot)/out/b',
                                                  'MapsCaching': 'True'})
        mk_path_out('data/LF_ETRS89_UseCase/out/b')

        lisfloodexe(settings_b)

        cache_size_b = cache_size()
        cache_found_b = cache_found()
        print('Cache size is {}'.format(cache_size_b))
        print('Items found: {}'.format(cache_found_b))

        cache_info()

        assert cache_found_b == cache_size_b
        assert cache_size_a == cache_size_b

        comparator = NetCDFComparator(settings_a.maskpath, array_equal=True)
        out_a = settings_a.output_dir
        out_b = settings_b.output_dir
        comparator.compare_dirs(out_a, out_b)

    def teardown_method(self):
        print('Cleaning directories and cache')
        path_out_a = os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/out/a')
        path_out_b = os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/out/b')
        shutil.rmtree(path_out_a, ignore_errors=True)
        shutil.rmtree(path_out_b, ignore_errors=True)
        cache_clear()


@pytest.mark.slow
class TestCachingSlow(MixinTestLis, MixinTestSettings):
    modules_to_set = (
        'SplitRouting',
        'simulateReservoirs',
        'groundwaterSmooth',
        'drainedIrrigation',
        'openwaterevapo',
        'riceIrrigation',
        'indicator',
    )
    settings_files = {
        'base': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/base.xml'),
        'prerun': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/prerun.xml')
    }

    def run(self, dt_sec, step_start, step_end):
        output_dir = mk_path_out('data/LF_ETRS89_UseCase/out/test_results{}'.format(dt_sec))
        opts_to_unset = (
            "repStateSites", "repRateSites", "repStateUpsGauges", "repRateUpsGauges", "repMeteoUpsGauges",
            "repsimulateLakes", "repStateMaps",
            "repsimulateReservoirs", "repSnowMaps", "repPFMaps", "repLZMaps", "repUZMaps",
            "repGwPercUZLZMaps", "repRWS", "repTotalWUse", "repWIndex",
            "repSurfaceRunoffMaps", "repRainMaps", "repSnowMaps", "repSnowCoverMaps", "repSnowMeltMaps", "repThetaMaps",
            "repThetaForestMaps", "repLZMaps", "repUZMaps",
            "repGwPercUZLZMaps", "repRWS", "repPFMaps", "repPFForestMaps"
        )
        settings = self.setoptions(self.settings_files['base'],
                              opts_to_set=('repDischargeTs', 'repDischargeMaps',) + self.modules_to_set,
                              opts_to_unset=opts_to_unset,
                              vars_to_set={'StepStart': step_start,
                                           'StepEnd': step_end,
                                           'DtSec': dt_sec,
                                           'PathOut': output_dir,
                                           'MapsCaching': 'True'})
        lisfloodexe(settings)

        cache_size_a = cache_size()
        cache_found_a = cache_found()
        print('Cache size is {}'.format(cache_size_a))
        print('Items found: {}'.format(cache_found_a))

        assert cache_found_a == 1  # apparently one map is called twice

        lisfloodexe(settings)

        cache_size_b = cache_size()
        cache_found_b = cache_found()
        print('Cache size is {}'.format(cache_size_b))
        print('Items found: {}'.format(cache_found_b))

        cache_info()

        assert cache_found_b == cache_size_b + 2
        assert cache_size_a == cache_size_b

        self.compare_reference('dis', check='map', step_length=dt_sec)
        self.compare_reference('dis', check='tss', step_length=dt_sec)
        self.compare_reference('chanq', check='tss', step_length=dt_sec)

    def test_dis_daily(self):
        self.run('86400', '02/01/2016 06:00', '02/07/2016 06:00')

    def test_dis_6h(self):
        self.run('21600', '02/01/2016 06:00', '02/07/2016 06:00')

    def teardown_method(self):
        print('Cleaning directories and cache')
        settings = LisSettings.instance()
        output_dir = settings.output_dir
        shutil.rmtree(output_dir)
        cache_clear()
