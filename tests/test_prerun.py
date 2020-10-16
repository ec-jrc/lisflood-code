from __future__ import absolute_import
import os

from tests import TestSettings


class TestPreRun(TestSettings):
    settings_files = {
        'initrun': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/prerun.xml')
    }

    def test_prerun(self, mocker):
        self._reported_map(self.settings_files['initrun'], None, None, ['AvgDis', 'LZAvInflowMap'], mocker,
                           files_to_check=['avgdis.nc', 'lzavin.nc'])
