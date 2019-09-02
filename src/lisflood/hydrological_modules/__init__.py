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
from __future__ import absolute_import, print_function, division
from nine import range

import os

from lisflood.global_modules.errors import LisfloodWarning
from ..global_modules.settings import LisSettings


class HydroModule(object):
    input_files_keys = None
    module_name = None

    def check_input_files(self):
        settings = LisSettings.instance()
        binding = settings.binding
        ok = True
        for key in self.input_files_keys:
            if not binding.get(key) or not os.path.exists(binding[key]) or not os.path.isfile(binding[key]):
                ok = False
                print(LisfloodWarning('Settings {} or File {}: missing settings or file for {} module.'.format(
                    key, binding.get(key, ''), self.module_name))
                )
        return ok

