"""

Copyright 2019 European Union

Licensed under the EUPL, Version 1.2 or as soon they will be approved by the European Commission
subsequent versions of the EUPL (the "Licence");

You may not use this work except in compliance with the Licence.
You may obtain a copy of the Licence at:

https://joinup.ec.europa.eu/sites/default/files/inline-files/EUPL%20v1_2%20EN(1).txt

Unless required by applicable law or agreed to in writing,
software distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and limitations under the Licence.

"""
from __future__ import absolute_import, print_function

import os
import warnings

from ..global_modules.errors import LisfloodWarning
from ..global_modules.settings import LisSettings


def is_number(v):
    if not v:
        return False
    try:
        float(v)
    except ValueError:
        return False
    else:
        return True


def is_path(v):
    if not v:
        return False
    path_no_ext, current_ext = os.path.splitext(v)
    v_alt = '{}.{}'.format(path_no_ext, 'nc' if current_ext in ('.map', '') else 'map')
    a = (os.path.exists(v) and os.path.isfile(v)) or os.access(v, os.W_OK)
    b = (os.path.exists(v_alt) and os.path.isfile(v_alt)) or os.access(v_alt, os.W_OK)
    return a or b


class HydroModule(object):
    input_files_keys = None
    module_name = None

    @classmethod
    def check_input_files(cls, option):
        settings = LisSettings.instance()
        binding = settings.binding
        ok = True
        keys = cls.input_files_keys[option]
        errors = []
        for k in keys:
            msg = None
            k_ok = True
            if not binding.get(k):
                msg = '[{}]: setting "{}" is missing in settings file {}'.format(cls.module_name, k, settings.settings_path)
                k_ok = False
            elif not (is_path(binding[k]) or is_number(binding[k])):
                k_ok = False
                msg = '[{}]: setting {} refers to a non existing path or a not well-formed float value: {}'.format(cls.module_name, k, binding[k])
            if not k_ok:
                ok = False
                warnings.warn(LisfloodWarning(msg))
                errors.append(msg)
        return ok, errors
