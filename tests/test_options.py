import os
from unittest.mock import call
import lisflood.global_modules.add1
from lisflood.main import lisfloodexe

from tests import TestSettings

settings_file = os.path.join(os.path.dirname(__file__), 'data/settings/base.xml')


class TestOptions(TestSettings):

    def test_reservoirs(self, mocker):
        calls = [call('ReservoirSites'), call('ReservoirSites', pcr=True), call('adjust_Normal_Flood'),
                 call('ReservoirRnormqMult'), call('ReservoirInitialFillValue')]
        settings = self.setoption(settings_file, 'simulateReservoirs')
        # mask = loadsetclone('MaskMap')
        mock_api = mocker.MagicMock(name='loadmap')
        mocker.patch('lisflood.hydrological_modules.reservoir.loadmap', new=mock_api)
        mock_api.side_effect = self.dummyloadmap
        lisfloodexe(settings)
        lisflood.hydrological_modules.reservoir.loadmap.assert_has_calls(calls)
