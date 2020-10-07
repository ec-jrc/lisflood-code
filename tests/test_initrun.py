from __future__ import absolute_import
import os

from tests import TestSettings


class TestInitRun(TestSettings):
    settings_files = {
        'initrun': os.path.join(os.path.dirname(__file__), 'data/settings/initrun.xml')
    }

    def test_initrun(self, mocker):
        self._reported_map(self.settings_files['initrun'], None, None, ['AvgDis', 'LZAvInflowMap'], mocker,
                           files_to_check=['avgdis.nc', 'lzavin.nc'])
