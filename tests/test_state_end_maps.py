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

from lisflood.main import lisfloodexe

from .test_utils import setoptions, mk_path_out


class TestRepMaps():
    settings_files = {'base': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/base.xml')}

    def teardown_method(self):
        shutil.rmtree(os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/out/testrep'), ignore_errors=True)

    def test_no_reported(self):
        path_out = mk_path_out('data/LF_ETRS89_UseCase/out/testrep')
        settings = setoptions(self.settings_files['base'], vars_to_set={'PathOut': path_out})
        lisfloodexe(settings)
        files = [os.path.join(settings.output_dir, f) for f in os.listdir(settings.output_dir) if f.endswith('.nc') or f.endswith('.tss')]
        assert not files

    def test_end_reported(self):
        path_out = mk_path_out('data/LF_ETRS89_UseCase/out/testrep')
        settings = setoptions(self.settings_files['base'], ['repEndMaps'], vars_to_set={'PathOut': path_out})
        lisfloodexe(settings)
        files = [os.path.join(settings.output_dir, f) for f in os.listdir(settings.output_dir) if f.endswith('.end.nc')]
        no_files = [os.path.join(settings.output_dir, f) for f in os.listdir(settings.output_dir) if f.endswith('.nc') and '.end.' not in f]
        assert files
        assert not no_files

    def test_state_reported(self):
        path_out = mk_path_out('data/LF_ETRS89_UseCase/out/testrep')
        settings = setoptions(self.settings_files['base'], ['repStateMaps'], vars_to_set={'PathOut': path_out})
        lisfloodexe(settings)
        no_files = [os.path.join(settings.output_dir, f) for f in os.listdir(settings.output_dir) if f.endswith('.end.nc')]
        files = [os.path.join(settings.output_dir, f) for f in os.listdir(settings.output_dir) if f.endswith('.nc') and '.end.' not in f]
        assert files
        assert not no_files

    def test_end_state_reported(self):
        path_out = mk_path_out('data/LF_ETRS89_UseCase/out/testrep')
        settings = setoptions(self.settings_files['base'], ['repEndMaps', 'repStateMaps', 'repDischargeMaps'], vars_to_set={'PathOut': path_out})
        lisfloodexe(settings)
        comparator = NetCDFComparator(settings.maskpath, array_equal=True)
        end_files = [os.path.join(settings.output_dir, f) for f in os.listdir(settings.output_dir) if f.endswith('.end.nc')]
        state_files = [os.path.join(settings.output_dir, f) for f in os.listdir(settings.output_dir) if f.endswith('.nc') and '.end.' not in f]
        assert end_files
        assert state_files
        # assert that unique timestep in end maps is equal to last timestep in state maps
        for end_file in end_files:
            basename = end_file.replace('.end.nc', '')
            state_file = '{}.nc'.format(basename)
            if not os.path.exists(state_file):
                continue
            state_nc = Dataset(state_file)
            end_nc = Dataset(end_file)
            var_name = [k for k in state_nc.variables if len(state_nc.variables[k].dimensions) == 3][0]
            vara = state_nc.variables[var_name]
            varb = end_nc.variables['{}.end'.format(var_name)]
            assert 'time' not in end_nc.variables

            # compare latest timestep in state map with unique timestep in end map
            comparator.compare_arrays(vara[-1][:, :], varb[:, :], varname=basename)
        assert not comparator.errors
