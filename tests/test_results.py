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
import warnings

import pytest

from lisflood.global_modules.errors import LisfloodWarning, LisfloodError
from lisflood.main import lisfloodexe
from tests import TestLis, setoptions

current_dir = os.path.dirname(os.path.abspath(__file__))

warnings.simplefilter('ignore', LisfloodWarning)


class TestCatch(TestLis):
    output_dir = os.path.join(current_dir, 'data/LF_ETRS89_UseCase/out')
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

    def test_dis(self):
        opts_to_unset = (
            "repStateSites", "repRateSites", "repStateUpsGauges", "repRateUpsGauges", "repMeteoUpsGauges",
            "repsimulateLakes", "repStateMaps",
            "repsimulateReservoirs", "repSnowMaps", "repPFMaps", "repLZMaps", "repUZMaps",
            "repGwPercUZLZMaps", "repRWS", "repTotalWUse", "repWIndex",
            "repSurfaceRunoffMaps", "repRainMaps", "repSnowMaps", "repSnowCoverMaps", "repSnowMeltMaps", "repThetaMaps",
            "repThetaForestMaps", "repLZMaps", "repUZMaps",
            "repGwPercUZLZMaps", "repRWS", "repPFMaps", "repPFForestMaps"
        )
        settings = setoptions(os.path.join(current_dir, 'data/LF_ETRS89_UseCase/settings/base.xml'),
                              opts_to_set=('repDischargeTs', 'repDischargeMaps', ) + self.modules_to_set,
                              opts_to_unset=opts_to_unset,
                              vars_to_set={'StepStart': '02/01/2000 06:00',
                                           'StepEnd': '02/07/2000 06:00',
                                           'PathOut': self.output_dir})
        lisfloodexe(settings)
        assert self.listest('dis', check='map')
        assert self.listest('dis', check='tss')
        assert self.listest('chanq', check='tss')

        # TODO add a 6hourly test

    def test_initvars(self):
        opts_to_unset = (
            "repStateSites", "repRateSites", "repStateUpsGauges", "repRateUpsGauges", "repMeteoUpsGauges",
            "repsimulateLakes", "repStateMaps",
            "repsimulateReservoirs", "repSnowMaps", "repPFMaps", "repLZMaps", "repUZMaps",
            "repGwPercUZLZMaps", "repRWS", "repTotalWUse", "repWIndex",
            "repSurfaceRunoffMaps", "repRainMaps", "repSnowMaps", "repSnowCoverMaps", "repSnowMeltMaps", "repThetaMaps",
            "repThetaForestMaps", "repLZMaps", "repUZMaps", "repDischargeTs", "repDischargeMaps",
            "repGwPercUZLZMaps", "repRWS", "repPFMaps", "repPFForestMaps"
        )
        settings = setoptions(os.path.join(current_dir, 'data/LF_ETRS89_UseCase/settings/base.xml'),
                              opts_to_set=('repEndMaps',) + self.modules_to_set,
                              opts_to_unset=opts_to_unset,
                              vars_to_set={'StepStart': '02/02/2000 06:00',
                                           'StepEnd': '05/02/2000 06:00',
                                           'PathOut': self.output_dir})
        lisfloodexe(settings)
        out_dir = self.output_dir
        initcond_files = ('ch2cr.end.nc', 'chcro.end.nc', 'chside.end.nc', 'cseal.end.nc', 'cum.end.nc', 'cumf.end.nc',
                          'cumi.end.nc', 'dis.end.nc', 'dslf.end.nc', 'dsli.end.nc', 'dslr.end.nc', 'frost.end.nc',
                          'lz.end.nc',
                          'rsfil.end.nc', 'scova.end.nc', 'scovb.end.nc', 'scovc.end.nc', 'tha.end.nc', 'thb.end.nc',
                          'thc.end.nc', 'thfa.end.nc', 'thfb.end.nc', 'thfc.end.nc', 'thia.end.nc', 'thib.end.nc',
                          'thic.end.nc', 'uz.end.nc', 'uzf.end.nc', 'uzi.end.nc', 'wdept.end.nc')
        for f in initcond_files:
            assert os.path.exists(os.path.join(out_dir, f))


class TestWrongTimestepInit:

    def test_raisexc(self):
        settings_path = os.path.join(current_dir, 'data/LF_ETRS89_UseCase/settings/warm.xml')
        with pytest.raises(LisfloodError) as e:
            setoptions(settings_path, vars_to_set={'timestepInit': 'PDAY'})
        assert 'Option timestepInit was not parsable.' in str(e.value)
