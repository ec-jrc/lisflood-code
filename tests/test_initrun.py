from __future__ import absolute_import
import os

from tests import TestSettings

settings_file = os.path.join(os.path.dirname(__file__), 'data/settings/initrun.xml')


class TestInitRun(TestSettings):

    def test_initrun(self, mocker):
        self._reported_map(settings_file, None, None, ['AvgDis', 'LZAvInflowMap'], mocker,
                           files_to_check=['avgdis.nc', 'lzavin.nc'])
