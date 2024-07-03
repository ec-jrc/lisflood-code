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

from .test_utils import setoptions, mk_path_out, MCTTestCase


@pytest.mark.slow
class TestCatch(MCTTestCase):
    case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_MCT_UseCase')
    modules_to_set = (
        'MCTRouting',
    )
    settings_files = {
        'cold': os.path.join(case_dir, 'settings/mct_cold.xml')
    }

    def run(self, dt_sec, dt_sec_chan, step_start, step_end):
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
        settings = setoptions(self.settings_files['cold'],
                              opts_to_set=('repDischargeTs', 'repDischargeMaps',
                                            'repMBTs') + self.modules_to_set,
                              opts_to_unset=opts_to_unset,
                              vars_to_set={'StepStart': step_start,
                                           'StepEnd': step_end,
                                           'DtSec': dt_sec,
                                           'DtSecChannel': dt_sec_chan,
                                           'PathOut': output_dir})
        lisfloodexe(settings)

    def test_output_daily(self):
        self.run('86400', '3600', '02/01/2016 06:00', '02/07/2016 06:00')
        self.compare_reference('dis', check='map', step_length='86400')
        self.compare_reference('dis', check='tss', step_length='86400')
        self.compare_reference('chanq', check='tss', step_length='86400')
        self.compare_reference('mbError', check='tss', step_length='86400')

    # def test_output_6h_6h(self):
    #     self.run('21600', '21600','02/01/2016 06:00', '02/07/2016 06:00')
    #     self.compare_reference('dis', check='map', step_length='21600')
    #     self.compare_reference('dis', check='tss', step_length='21600')
    #     self.compare_reference('chanq', check='tss', step_length='21600')
    #     self.compare_reference('mbError', check='tss', step_length='21600')
    #
    # def test_output_6h_1h(self):
    #     self.run('21600', '3600','02/01/2016 06:00', '02/07/2016 06:00')
    #     self.compare_reference('dis', check='map', step_length='21600')
    #     self.compare_reference('dis', check='tss', step_length='21600')
    #     self.compare_reference('chanq', check='tss', step_length='21600')
    #     self.compare_reference('mbError', check='tss', step_length='21600')
