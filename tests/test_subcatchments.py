"""

Copyright 2019-2020 European Union

Licensed under the EUPL, Version 1.2 or as soon they will be approved by the European Commission  subsequent versions of the EUPL (the "Licence");

You may not use this work except in compliance with the Licence.
You may obtain a copy of the Licence at:

https://joinup.ec.europa.eu/sites/default/files/inline-files/EUPL%20v1_2%20EN(1).txt

Unless required by applicable law or agreed to in writing, software distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and limitations under the Licence.

"""

from __future__ import absolute_import
import os
import shutil
import glob

import pytest

from lisfloodutilities.compare.nc import NetCDFComparator

from lisflood.global_modules.settings import LisSettings
from lisflood.main import lisfloodexe

from .test_utils import setoptions, mk_path_out

@pytest.mark.slow
class TestSubcatchments():
    settings_files = {
        'cold': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/cold.xml'),
    }
    modules_to_unset = [
        'wateruse',
        'useWaterDemandAveYear',
        'wateruseRegion',
        'TransientWaterDemandChange',
        'riceIrrigation'
    ]
    modules_to_setGW= [
        'groundwaterSmooth',
    ]

    def test_subcacthment_daily(self):
        step_start = '02/01/2016 06:00'
        step_end = '30/03/2016 06:00'
        dt_sec = 86400
        report_steps = '3650..4100'
        self.run_subcathmenttest_by_dtsec(dt_sec, step_end, step_start, report_steps=report_steps)

    def test_subcacthment_daily_wateruse_groundwatersmooth_ON(self):
        step_start = '02/01/2016 06:00'
        step_end = '30/01/2016 06:00'
        dt_sec = 86400
        report_steps = '3650..4100'
        with pytest.raises(AssertionError) as excinfo:
            self.run_subcathmenttest_by_dtsec(dt_sec, step_end, step_start, report_steps=report_steps, wateruse_on=True, groundwatersmooth_on=True)
        assert 'Arrays are not equal' in str(excinfo.value)

    def test_subcacthment_daily_wateruse_groundwatersmooth_OFF(self):
        step_start = '02/01/2016 06:00'
        step_end = '30/01/2016 06:00'
        dt_sec = 86400
        report_steps = '3650..4100'
        self.run_subcathmenttest_by_dtsec(dt_sec, step_end, step_start, report_steps=report_steps, wateruse_on=True, groundwatersmooth_on=False)

    def test_subcacthment_6h(self):
        step_start = '01/03/2016 06:00'
        step_end = '30/03/2016 06:00'
        dt_sec = 21600
        report_steps = '14800..16000'
        self.run_subcathmenttest_by_dtsec(dt_sec, step_end, step_start, report_steps=report_steps)

    def run_subcathmenttest_by_dtsec(self, dt_sec, step_end, step_start, report_steps='1..9999', wateruse_on=False, groundwatersmooth_on=False):
        modules_to_unset = self.modules_to_unset if not wateruse_on else []
        modules_to_set = self.modules_to_setGW if groundwatersmooth_on else []
        #modules_to_set = self.modules_to_unset if wateruse_on else []

        # long run entire domain
        path_out_domain = mk_path_out('data/LF_ETRS89_UseCase/out/longrun_domain{}'.format(dt_sec))
        settings_longrun = setoptions(self.settings_files['cold'], opts_to_unset=modules_to_unset,
                                      opts_to_set=modules_to_set,
                                      vars_to_set={'StepStart': step_start,
                                                   'StepEnd': step_end,
                                                   'PathOut': path_out_domain,
                                                   'ReportSteps': report_steps,
                                                   'DtSec': dt_sec})
        # ** execute
        lisfloodexe(settings_longrun)

        # long run entire on subdomain
        path_out_subdomain = mk_path_out('data/LF_ETRS89_UseCase/out/longrun_subdomain{}'.format(dt_sec))
        settings_longrun_subdomain = setoptions(self.settings_files['cold'], opts_to_unset=modules_to_unset,
                                                opts_to_set=modules_to_set,
                                                vars_to_set={'StepStart': step_start,
                                                             'StepEnd': step_end,
                                                             'PathOut': path_out_subdomain,
                                                             'ReportSteps': report_steps,
                                                             'MaskMap': '$(PathRoot)/maps/subcatchment_mask.map',
                                                             'DtSec': dt_sec})
        # ** execute
        lisfloodexe(settings_longrun_subdomain)

        # ****** compare *******
        # compare using the last maskmap (subcatchment_mask.map)
        settings = LisSettings.instance()
        nc_comparator = NetCDFComparator(settings.maskpath, array_equal=True)
        nc_comparator.compare_dirs(path_out_subdomain, path_out_domain)

    def teardown_method(self):
        folders_list = glob.glob(os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/out/longrun_domain*')) + \
            glob.glob(os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/out/longrun_subdomain*'))
        for folder in folders_list:
            shutil.rmtree(folder)
