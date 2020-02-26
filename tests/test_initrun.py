from __future__ import absolute_import
import os

from tests import TestSettings


class TestInitRun(TestSettings):
    settings_file = os.path.join(os.path.dirname(__file__), 'data/settings/initrun.xml')

    def test_initrun(self, mocker):
        self._reported_map(self.settings_file, None, None, ['AvgDis', 'LZAvInflowMap'], mocker,
                           files_to_check=['avgdis.nc', 'lzavin.nc'])
