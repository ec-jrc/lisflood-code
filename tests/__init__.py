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
import sys

from pyexpat import *
import numpy as np

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '../src/')
if os.path.exists(src_dir):
    sys.path.append(src_dir)

from lisflood.global_modules.add1 import readnetcdf
from lisflood.global_modules.globals import modelSteps, binding
from lisf1 import Lisfloodexe, get_optionxml_path


class TestLis(object):
    reference_files = {
        'dis': {'outpath': os.path.join(current_dir, 'data/Drina/reference/dis'),
                'report_map': 'DischargeMaps',
                'report_tss': 'DisTS'}
    }

    domain = None
    settings_path = None
    atol = 0.01
    max_perc_wrong_large_diff = 0.01
    max_perc_wrong = 0.05
    large_diff_th = atol * 10

    @classmethod
    def setup_class(cls):
        optionxml = get_optionxml_path()
        Lisfloodexe(cls.settings_path, optionxml)

    @classmethod
    def teardown_class(cls):
        for var, obj in cls.reference_files.items():
            output_nc = binding[cls.reference_files[var]['report_map']]
            output_nc = output_nc + '.nc'
            if os.path.exists(output_nc):
                os.remove(output_nc)
            output_tss = binding[cls.reference_files[var]['report_tss']]
            if os.path.exists(output_tss):
                os.remove(output_tss)

    @classmethod
    def check_var_step(cls, var, step):
        reference_path = cls.reference_files[var]['outpath']
        output_path = binding[cls.reference_files[var]['report_map']]
        reference = readnetcdf(reference_path, step)
        current_output = readnetcdf(output_path, step)

        same_size = reference.size == current_output.size
        diff_values = np.abs(reference - current_output)
        same_values = np.allclose(diff_values, np.zeros(diff_values.shape), atol=cls.atol)
        all_ok = same_size and same_values

        array_ok = np.isclose(diff_values, np.zeros(diff_values.shape), atol=cls.atol)
        wrong_values_size = array_ok[~array_ok].size

        if not all_ok and wrong_values_size > 0:
            max_diff = np.max(diff_values)
            large_diff = max_diff > cls.large_diff_th
            perc_wrong = float(wrong_values_size * 100) / float(diff_values.size)
            if perc_wrong >= cls.max_perc_wrong or perc_wrong >= cls.max_perc_wrong_large_diff and large_diff:
                print('[ERROR]')
                print('Var: {} - STEP {}: {:3.9f}% of values are different. max diff: {:3.4f}'.format(var, step, perc_wrong, max_diff))
                return False
            else:
                print('[OK] {} {}'.format(var, step))
                return True
        else:
            print('[OK] {} {}'.format(var, step))
            return True

    @classmethod
    def listest(cls, variable):
        reference_path = cls.reference_files[variable]['outpath']
        output_path = os.path.normpath(binding[cls.reference_files[variable]['report_map']])
        print '>>> Reference: {} - Current Output: {}'.format(reference_path, output_path)
        results = []
        start_step, end_step = modelSteps[0], modelSteps[1]
        for step in xrange(start_step, end_step + 1):
            results.append(cls.check_var_step(variable, step))
        assert all(results)
