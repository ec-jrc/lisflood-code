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

from __future__ import absolute_import
import os
import shutil

from netCDF4 import Dataset

from lisfloodutilities.compare.nc import NetCDFComparator
from lisflood.global_modules.settings import datetoint

from lisflood.main import lisfloodexe

from .test_utils import ETRS89TestCase, setoptions, mk_path_out


class TestRepStepMaps(ETRS89TestCase):
    case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_ETRS89_UseCase')
    settings_file = os.path.join(case_dir, 'settings', 'cold.xml')
    out_dir_a = os.path.join(case_dir, 'out', 'a')
    out_dir_b = os.path.join(case_dir, 'out', 'b')

    def test_reported_steps(self):

        strReportStepA = 'starttime+10..endtime'
        settings_a = setoptions(self.settings_file,
                                vars_to_set={'StepStart': '01/07/2016 00:00', 'StepEnd': '01/08/2016 00:00',
                                             'PathOut': '$(PathRoot)/out/a',
                                             'ReportSteps': strReportStepA, 
                                             })
        mk_path_out(self.out_dir_a)
        lisfloodexe(settings_a)

        int_start, _ = datetoint(settings_a.binding['StepStart'], settings_a.binding)
        int_end, _ = datetoint(settings_a.binding['StepEnd'], settings_a.binding)

        strReportStepB = ''
        for i in range(int_start,int_end,10):
            if strReportStepB != '':
                strReportStepB = strReportStepB + ',' 
            strReportStepB = strReportStepB + str(i)

        settings_b = setoptions(self.settings_file,
                                vars_to_set={'StepStart': '01/07/2016 00:00', 'StepEnd': '01/08/2016 00:00',
                                             'PathOut': '$(PathRoot)/out/b',
                                             'ReportSteps': strReportStepB,
                                             })
        mk_path_out(self.out_dir_b)
        lisfloodexe(settings_b)

        comparator = NetCDFComparator(settings_a.maskpath, array_equal=True)
        comparator.compare_dirs(self.out_dir_b, self.out_dir_a)
        assert not comparator.errors
