from __future__ import absolute_import
import os
import datetime
import shutil
import pytest

from lisfloodutilities.compare.nc import NetCDFComparator

from lisflood.main import lisfloodexe
from lisflood.global_modules.decorators import Cache
from lisflood.global_modules.settings import LisSettings

from .test_utils import setoptions, mk_path_out, ETRS89TestCase


class TestCaching(ETRS89TestCase):
    case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_ETRS89_UseCase')
    settings_file = os.path.join(case_dir, 'settings', 'full.xml')
    path_out = os.path.join(case_dir, 'out') 
    if not os.path.exists(path_out):
        os.mkdir(path_out)
    out_dir_a = os.path.join(case_dir, 'out', 'a')
    out_dir_b = os.path.join(case_dir, 'out', 'b')

    def test_caching_24h(self):
      dt_sec = 86400
      self.run_lisflood_caching(dt_sec)

    def test_caching_6h(self):
      dt_sec = 21600
      self.run_lisflood_caching(dt_sec)
    
    def test_cache_extract(self):
      dt_sec = 86400
      self.run_lisflood_caching(dt_sec, test_extract=True)

    def run_lisflood_caching(self, dt_sec, test_extract=False):
        
        settings_a = setoptions(self.settings_file,
                                vars_to_set={'StepStart': '30/07/2016 06:00', 'StepEnd': '01/08/2016 06:00',
                                             'DtSec': dt_sec, 'PathOut': '$(PathRoot)/out/a',
                                             'MapsCaching': 'True'})
        mk_path_out(self.out_dir_a)
        lisfloodexe(settings_a)

        cache_size_a = Cache.size()
        cache_found_a = Cache.values_found()
        print('Cache size is {}'.format(cache_size_a))
        print('Items found: {}'.format(cache_found_a))

        assert cache_found_a == 0

        if test_extract:
            cache_backup = Cache.extract()
            Cache.clear()
            assert Cache.size() == 0
            Cache.apply(cache_backup)
            assert Cache.size() == cache_size_a

        settings_b = setoptions(self.settings_file,
                                vars_to_set={'StepStart': '30/07/2016 06:00', 'StepEnd': '01/08/2016 06:00',
                                             'DtSec': dt_sec, 'PathOut': '$(PathRoot)/out/b',
                                             'MapsCaching': 'True'})
        mk_path_out(self.out_dir_b)
        lisfloodexe(settings_b)

        cache_size_b = Cache.size()
        cache_found_b = Cache.values_found()
        print('Cache size is {}'.format(cache_size_b))
        print('Items found: {}'.format(cache_found_b))

        Cache.info()

        assert cache_found_b == cache_size_b
        assert cache_size_a == cache_size_b

        comparator = NetCDFComparator(settings_a.maskpath, array_equal=True)
        comparator.compare_dirs(self.out_dir_b, self.out_dir_a)

    def teardown_method(self):
        print('Cleaning directories and cache')
        shutil.rmtree(self.out_dir_a, ignore_errors=True)
        shutil.rmtree(self.out_dir_b, ignore_errors=True)
        Cache.clear()


@pytest.mark.slow
class TestCachingSlow(ETRS89TestCase):
    case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_ETRS89_UseCase')

    modules_to_set = (
        'SplitRouting',
        'simulateReservoirs',
        'simulateLakes',
        'drainedIrrigation',
        'openwaterevapo',
        'riceIrrigation',
        'wateruse',
        'useWaterDemandAveYear',
        'wateruseRegion',
        'TransientWaterDemandChange',
    )
    settings_files = {
        'base': os.path.join(case_dir, 'settings/base.xml'),
        'prerun': os.path.join(case_dir, 'settings/prerun.xml')
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
        settings = setoptions(self.settings_files['base'],
                              opts_to_set=('repDischargeTs', 'repDischargeMaps',) + self.modules_to_set,
                              opts_to_unset=opts_to_unset,
                              vars_to_set={'StepStart': step_start,
                                           'StepEnd': step_end,
                                           'DtSec': dt_sec,
                                           'PathOut': output_dir,
                                           'MapsCaching': 'True'})
        lisfloodexe(settings)

        cache_size_a = Cache.size()
        cache_found_a = Cache.values_found()
        print('Cache size is {}'.format(cache_size_a))
        print('Items found: {}'.format(cache_found_a))

        assert cache_found_a == 1  # apparently one map is called twice

        lisfloodexe(settings)

        cache_size_b = Cache.size()
        cache_found_b = Cache.values_found()
        print('Cache size is {}'.format(cache_size_b))
        print('Items found: {}'.format(cache_found_b))

        Cache.info()

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
        Cache.clear()
