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

from lisflood.global_modules.settings import LisSettings
from lisflood.main import lisfloodexe

from .test_utils import setoptions, mk_path_out, ETRS89TestCase


@pytest.mark.slow
class TestCatch(ETRS89TestCase):
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
        output_dir = mk_path_out(os.path.join(self.case_dir, 'out/test_results{}'.format(dt_sec)))
        opts_to_unset = (
            "repStateSites", "repRateSites", "repStateUpsGauges", "repRateUpsGauges", "repMeteoUpsGauges",
            "repsimulateLakes", "repStateMaps",
            "repsimulateReservoirs", "repSnowMaps", "repPFMaps", "repLZMaps", "repUZMaps",
            "repGwPercUZLZMaps", "repRWS", "repTotalWUse", "repWIndex",
            "repSurfaceRunoffMaps", "repRainMaps", "repSnowMaps", "repSnowCoverMaps", "repSnowMeltMaps", 
            "repLZMaps", "repUZMaps",
            "repGwPercUZLZMaps", "repRWS", "repPFMaps", "repPFForestMaps"
        )
        settings = setoptions(self.settings_files['base'],
                              opts_to_set=('repDischargeTs', 'repDischargeMaps', 
                                            "repThetaMaps", "repThetaForestMaps",
                                            "repThetaIrrigationMaps", "repE2O2") + self.modules_to_set,
                              opts_to_unset=opts_to_unset,
                              vars_to_set={'StepStart': step_start,
                                           'StepEnd': step_end,
                                           'DtSec': dt_sec,
                                           'PathOut': output_dir})
        lisfloodexe(settings)

    def test_output_daily(self):
        self.run('86400', '02/01/2016 06:00', '02/07/2016 06:00')
        self.compare_reference('dis', check='map', step_length='86400')
        self.compare_reference('dis', check='tss', step_length='86400')
        self.compare_reference('chanq', check='tss', step_length='86400')
        self.compare_reference('thia', check='map', step_length='86400')
        self.compare_reference('thic', check='map', step_length='86400')
        self.compare_reference('thfa', check='map', step_length='86400')
        self.compare_reference('thfc', check='map', step_length='86400')
        self.compare_reference('tha', check='map', step_length='86400')
        self.compare_reference('thc', check='map', step_length='86400')
        self.compare_reference('lz', check='map', step_length='86400')

    def test_output_6h(self):
        self.run('21600', '02/01/2016 06:00', '02/07/2016 06:00')
        self.compare_reference('dis', check='map', step_length='21600')
        self.compare_reference('dis', check='tss', step_length='21600')
        self.compare_reference('chanq', check='tss', step_length='21600')
        self.compare_reference('thia', check='map', step_length='21600')
        self.compare_reference('thic', check='map', step_length='21600')
        self.compare_reference('thfa', check='map', step_length='21600')
        self.compare_reference('thfc', check='map', step_length='21600')
        self.compare_reference('tha', check='map', step_length='21600')
        self.compare_reference('thc', check='map', step_length='21600')
        self.compare_reference('lz', check='map', step_length='21600')

    def test_initvars(self):
        output_dir = mk_path_out(os.path.join(self.case_dir, 'out/test_results_initvars'))
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
                              vars_to_set={'StepStart': '02/02/2016 06:00',
                                           'StepEnd': '05/02/2016 06:00',
                                           'PathOut': output_dir})
        lisfloodexe(settings)
        initcond_files = ('ch2cr.end.nc', 'chanq.end.nc', 'chcro.end.nc', 
                        'chside.end.nc', 'cseal.end.nc', 'cum.end.nc', 
                        'cumf.end.nc', 'cumi.end.nc', 'dslf.end.nc', 
                        'dsli.end.nc', 'dslr.end.nc', 'frost.end.nc',
                        'lakeh.end.nc', 'lakeprevinq.end.nc',  
                        'lakeprevoutq.end.nc', 'lz.end.nc', 'ofdir.end.nc',
                        'offor.end.nc', 'ofoth.end.nc', 'rsfil.end.nc', 
                        'scova.end.nc', 'scovb.end.nc', 'scovc.end.nc', 
                        'tha.end.nc', 'thb.end.nc', 'thc.end.nc', 
                        'thfa.end.nc', 'thfb.end.nc', 'thfc.end.nc', 
                        'thia.end.nc', 'thib.end.nc', 'thic.end.nc', 
                        'uz.end.nc', 'uzf.end.nc', 'uzi.end.nc')
        for f in initcond_files:
            assert os.path.exists(os.path.join(output_dir, f))

    def run_init(self, dt_sec, step_start, step_end):
        path_out_init = mk_path_out(os.path.join(self.case_dir, 'out/test_init_{}'.format(dt_sec)))
        settings = setoptions(self.settings_files['prerun'],
                              opts_to_set=self.modules_to_set,
                              vars_to_set={'DtSec': dt_sec,
                                           'PathOut': path_out_init,
                                           'StepStart': step_start,
                                           'StepEnd': step_end,
                                           })
        lisfloodexe(settings)

    def test_init_daily(self):
        self.run_init('86400', '31/12/2015 06:00', '06/01/2017 06:00')
        self.compare_reference('avgdis', check='map', step_length='86400')
        self.compare_reference('lzavin', check='map', step_length='86400')

    def test_init_6h(self):
        self.run_init('21600', '31/12/2015 06:00', '06/01/2017 06:00')
        self.compare_reference('avgdis', check='map', step_length='21600')
        self.compare_reference('lzavin', check='map', step_length='21600')

    def run_waterbalance(self, dt_sec, step_start, step_end):
        # init files from .../LF_ETRS89_UseCase/maps/safe_init
        # "AvgDis" value="$(PathRoot)/maps/safe_init/avgdis"
        # "LZAvInflowMap" value="$(PathRoot)/maps/safe_init/lzavin"
        output_dir = mk_path_out(os.path.join(self.case_dir, 'out/test_results{}'.format(dt_sec)))
        opts_to_unset = (
            'wateruse','riceIrrigation','groundwaterSmooth'
        )
        settings = setoptions(self.settings_files['base'],
                              opts_to_set=('SplitRouting','repMBTs','openwaterevapo','drainedIrrigation','simulateLakes','simulateReservoirs'),
                              opts_to_unset=opts_to_unset,
                              vars_to_set={'StepStart': step_start,
                                           'StepEnd': step_end,
                                           'DtSec': dt_sec,
                                           'PathOut': output_dir})
        lisfloodexe(settings)

    def test_waterbalance_daily(self):
        self.run_waterbalance('86400', '02/01/2016 06:00', '02/07/2016 06:00')
        self.compare_reference('mbError', check='tss', step_length='86400')
        self.compare_reference('mbErrorSplitRoutingM3', check='tss', step_length='86400')

    def test_waterbalance_6h(self):
        self.run_waterbalance('21600', '02/01/2016 06:00', '02/07/2016 06:00')
        self.compare_reference('mbError', check='tss', step_length='21600')
        self.compare_reference('mbErrorSplitRoutingM3', check='tss', step_length='21600')

