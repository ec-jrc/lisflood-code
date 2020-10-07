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

from netCDF4 import Dataset

from lisfloodutilities.compare import NetCDFComparator

from lisflood.global_modules.settings import MaskInfo
from lisflood.main import lisfloodexe

from tests import TestSettings


class TestWarmStartDays(TestSettings):
    settings_file = os.path.join(os.path.dirname(__file__), 'data/settings/init.xml')
    settings_file_cold = os.path.join(os.path.dirname(__file__), 'data/settings/cold.xml')
    settings_file_warm = os.path.join(os.path.dirname(__file__), 'data/settings/warm.xml')

    def test_warmstart(self):
        settings_init = self.setoptions(self.settings_file,
                                        vars_to_set={'DtSec': '86400'})

        lisfloodexe(settings_init)
        settings_cold = self.setoptions(self.settings_file_cold,
                                        vars_to_set={'PathInit': settings_init.output_dir, 'DtSec': '86400'})
        lisfloodexe(settings_cold)

        # TODO
        assert False
