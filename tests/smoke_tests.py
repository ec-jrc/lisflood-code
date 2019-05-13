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

import os

from lisflood.global_modules.globals import binding
from lisflood.lisf1 import Lisfloodexe, get_optionxml_path

from tests import listest, reference_files


current_dir = os.path.dirname(os.path.abspath(__file__))


class TestDrina(object):
    settings_path = os.path.join(current_dir, 'data/Drina/settings/lisfloodSettings_cold_day_base.xml')

    @classmethod
    def setup_class(cls):
        optionxml = get_optionxml_path()
        Lisfloodexe(cls.settings_path, optionxml)

    @classmethod
    def teardown_class(cls):
        for var, obj in reference_files.items():
            output_nc = binding[reference_files[var]['report_map']]
            output_nc = output_nc + '.nc'
            if os.path.exists(output_nc):
                os.remove(output_nc)
            output_tss = binding[reference_files[var]['report_tss']]
            if os.path.exists(output_tss):
                os.remove(output_tss)

    @listest('dis')
    def test_dis(self):
        pass
