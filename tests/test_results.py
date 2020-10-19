"""

Copyright 2019 European Union

Licensed under the EUPL, Version 1.2 or as soon they will be approved by the European Commission  subsequent versions of the EUPL (the "Licence");

You may not use this work except in compliance with the Licence.
You may obtain a copy of the Licence at:

https://joinup.ec.europa.eu/sites/default/files/inline-files/EUPL%20v1_2%20EN(1).txt

Unless required by applicable law or agreed to in writing, software distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and limitations under the Licence.

"""
from __future__ import absolute_import, print_function

import os
import shutil

import pytest
from lisfloodutilities.compare import NetCDFComparator, TSSComparator

from lisflood.global_modules.errors import LisfloodError
from lisflood.global_modules.settings import LisSettings, MaskInfo
from lisflood.main import lisfloodexe

from tests import setoptions, mk_path_out

current_dir = os.path.dirname(os.path.abspath(__file__))


class MixinTestLis(object):
    reference_files = {
        'dis': {
            'report_map': 'DischargeMaps',
            'report_tss': 'DisTS',
            '86400': {
                'path_map': os.path.join(current_dir, 'data/LF_ETRS89_UseCase/reference/dis_daily/dis.nc'),
                'path_tss': os.path.join(current_dir, 'data/LF_ETRS89_UseCase/reference/dis_daily/dis.tss'),
            },
            '21600': {
                'path_map': os.path.join(current_dir, 'data/LF_ETRS89_UseCase/reference/dis_6h/dis.nc'),
                'path_tss': os.path.join(current_dir, 'data/LF_ETRS89_UseCase/reference/dis_6h/dis.tss'),
            },

        },
        'chanq': {
            'report_map': None,
            'report_tss': 'ChanqTS',
            '86400': {
                'path_map': None,
                'path_tss': os.path.join(current_dir, 'data/LF_ETRS89_UseCase/reference/dis_daily/chanqWin.tss'),
            },
            '21600': {
                'path_map': None,
                'path_tss': os.path.join(current_dir, 'data/LF_ETRS89_UseCase/reference/dis_6h/chanqWin.tss'),
            },

        },
        'avgdis': {
            'report_map': 'AvgDis',
            'report_tss': None,
            '86400': {
                'path_map': os.path.join(current_dir, 'data/LF_ETRS89_UseCase/reference/init_daily/avgdis.nc'),
                'path_tss': None,
            },
            '21600': {
                'path_map': os.path.join(current_dir, 'data/LF_ETRS89_UseCase/reference/init_6h/avgdis.nc'),
                'path_tss': None,
            },

        },
        'lzavin': {
            'report_map': 'LZAvInflowMap',
            'report_tss': None,
            '86400': {
                'path_map': os.path.join(current_dir, 'data/LF_ETRS89_UseCase/reference/init_daily/lzavin.nc'),
                'path_tss': None,
            },
            '21600': {
                'path_map': os.path.join(current_dir, 'data/LF_ETRS89_UseCase/reference/init_6h/lzavin.nc'),
                'path_tss': None,
            },

        },
    }

    def teardown_method(self):
        settings = LisSettings.instance()
        output_dir = settings.output_dir
        shutil.rmtree(output_dir)

    @classmethod
    def compare_reference(cls, variable='dis', check='map', step_length='86400'):
        """
        :param variable: variable to check. Default 'dis' (Discharge)
        :param check: either 'map' or 'tss'. Default 'map'
        :param step_length: DtSec (86400 for daily and 21600 for 6h run)
        """

        settings = LisSettings.instance()
        maskinfo = MaskInfo.instance()
        binding = settings.binding
        reference = cls.reference_files[variable][step_length]['path_{}'.format(check)]

        if check == 'map':
            output_map = os.path.normpath(binding[cls.reference_files[variable]['report_map']]) + '.nc'
            comparator = NetCDFComparator(maskinfo.info.mask)
            comparator.compare_files(reference, output_map)
        elif check == 'tss':
            output_tss = binding[cls.reference_files[variable]['report_tss']]
            comparator = TSSComparator()
            comparator.compare_files(reference, output_tss)
        # If there are differences, test fails before reaching this line (AssertionError(s) in comparator methods)
        assert True


class TestCatch(MixinTestLis):
    modules_to_set = (
        'SplitRouting',
        'simulateReservoirs',
        'simulateLakes',
        'groundwaterSmooth',
        'TransientWaterDemandChange',
        'drainedIrrigation',
        'openwaterevapo'
        'useWaterDemandAveYear',
        'riceIrrigation',
        'indicator',
    )
    settings_files = {
        'base': os.path.join(current_dir, 'data/LF_ETRS89_UseCase/settings/base.xml'),
        'prerun': os.path.join(current_dir, 'data/LF_ETRS89_UseCase/settings/prerun.xml')
    }

    # TODO check streamflow_simulated_best.csv as reference

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
                                           'PathOut': output_dir})
        lisfloodexe(settings)

    def test_dis_daily(self):
        self.run('86400', '02/01/2000 06:00', '02/07/2000 06:00')
        self.compare_reference('dis', check='map', step_length='86400')
        self.compare_reference('dis', check='tss', step_length='86400')
        self.compare_reference('chanq', check='tss', step_length='86400')

    def test_dis_6h(self):
        self.run('21600', '02/01/2000 06:00', '02/07/2000 06:00')
        self.compare_reference('dis', check='map', step_length='21600')
        self.compare_reference('dis', check='tss', step_length='21600')
        self.compare_reference('chanq', check='tss', step_length='21600')

    def test_initvars(self):
        output_dir = mk_path_out('data/LF_ETRS89_UseCase/out/test_results_initvars')
        opts_to_unset = (
            "repStateSites", "repRateSites", "repStateUpsGauges", "repRateUpsGauges", "repMeteoUpsGauges",
            "repsimulateLakes", "repStateMaps",
            "repsimulateReservoirs", "repSnowMaps", "repPFMaps", "repLZMaps", "repUZMaps",
            "repGwPercUZLZMaps", "repRWS", "repTotalWUse", "repWIndex",
            "repSurfaceRunoffMaps", "repRainMaps", "repSnowMaps", "repSnowCoverMaps", "repSnowMeltMaps", "repThetaMaps",
            "repThetaForestMaps", "repLZMaps", "repUZMaps", "repDischargeTs", "repDischargeMaps",
            "repGwPercUZLZMaps", "repRWS", "repPFMaps", "repPFForestMaps"
        )
        settings = setoptions(self.settings_files['base'],
                              opts_to_set=('repEndMaps',) + self.modules_to_set,
                              opts_to_unset=opts_to_unset,
                              vars_to_set={'StepStart': '02/02/2000 06:00',
                                           'StepEnd': '05/02/2000 06:00',
                                           'PathOut': output_dir})
        lisfloodexe(settings)
        initcond_files = ('ch2cr.end.nc', 'chcro.end.nc', 'chside.end.nc', 'cseal.end.nc', 'cum.end.nc', 'cumf.end.nc',
                          'cumi.end.nc', 'dis.end.nc', 'dslf.end.nc', 'dsli.end.nc', 'dslr.end.nc', 'frost.end.nc',
                          'lz.end.nc',
                          'rsfil.end.nc', 'scova.end.nc', 'scovb.end.nc', 'scovc.end.nc', 'tha.end.nc', 'thb.end.nc',
                          'thc.end.nc', 'thfa.end.nc', 'thfb.end.nc', 'thfc.end.nc', 'thia.end.nc', 'thib.end.nc',
                          'thic.end.nc', 'uz.end.nc', 'uzf.end.nc', 'uzi.end.nc', 'wdept.end.nc')
        for f in initcond_files:
            assert os.path.exists(os.path.join(output_dir, f))

    def run_init(self, dt_sec, step_start, step_end):
        modules_to_unset = [
            'simulateLakes',
            'repsimulateLakes',
            'wateruse',
            'useWaterDemandAveYear',
        ]
        path_out_init = mk_path_out('data/LF_ETRS89_UseCase/out/test_init_{}'.format(dt_sec))
        settings = setoptions(self.settings_files['prerun'], opts_to_unset=modules_to_unset,
                              vars_to_set={'DtSec': dt_sec,
                                           'PathOut': path_out_init,
                                           'StepStart': step_start,
                                           'StepEnd': step_end,
                                           })
        lisfloodexe(settings)

    def test_init_daily(self):
        self.run_init('86400', '31/12/1999 06:00', '06/01/2001 06:00')
        self.compare_reference('avgdis', check='map', step_length='86400')
        self.compare_reference('lzavin', check='map', step_length='86400')

    def test_init_6h(self):
        self.run_init('21600', '31/12/1999 06:00', '06/01/2001 06:00')
        self.compare_reference('avgdis', check='map', step_length='21600')
        self.compare_reference('lzavin', check='map', step_length='21600')


class TestWrongTimestepInit:

    def test_raisexc(self):
        settings_path = os.path.join(current_dir, 'data/LF_ETRS89_UseCase/settings/warm.xml')
        with pytest.raises(LisfloodError) as e:
            setoptions(settings_path, vars_to_set={'timestepInit': 'PDAY'})
        assert 'Option timestepInit was not parsable.' in str(e.value)
