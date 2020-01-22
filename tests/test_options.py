import os
from unittest.mock import call
import lisflood.global_modules.add1
from lisflood.main import lisfloodexe

from tests import TestSettings

settings_file = os.path.join(os.path.dirname(__file__), 'data/settings/base.xml')


class TestOptions(TestSettings):

    def test_basic(self, mocker):
        settings = self.setoption(settings_file)
        mock_api = mocker.MagicMock(name='loadmap')
        mock_api.side_effect = self.dummyloadmap
        mocker.patch('lisflood.hydrological_modules.reservoir.loadmap', new=mock_api)
        mocker.patch('lisflood.hydrological_modules.evapowater.loadmap', new=mock_api)
        mocker.patch('lisflood.hydrological_modules.waterabstraction.loadmap', new=mock_api)
        lisfloodexe(settings)
        assert not lisflood.hydrological_modules.reservoir.loadmap.called
        assert not lisflood.hydrological_modules.evapowater.loadmap.called
        assert not lisflood.hydrological_modules.waterabstraction.loadmap.called

    def test_split_routing(self, mocker):
        settings = self.setoption(settings_file, 'SplitRouting')
        mock_api = mocker.MagicMock(name='loadmap')
        mock_api2 = mocker.MagicMock(name='loadmap')
        mock_api.side_effect = self.dummyloadmap
        mock_api2.side_effect = self.dummyloadmap
        mocker.patch('lisflood.hydrological_modules.routing.loadmap', new=mock_api)
        mocker.patch('lisflood.hydrological_modules.reservoir.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.evapowater.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.waterabstraction.loadmap', new=mock_api2)
        lisfloodexe(settings)
        calls = [call('CrossSection2AreaInitValue'), call('PrevSideflowInitValue'),]
        lisflood.hydrological_modules.routing.loadmap.assert_has_calls(calls)
        assert not lisflood.hydrological_modules.waterabstraction.loadmap.called
        assert not lisflood.hydrological_modules.evapowater.loadmap.called
        assert not lisflood.hydrological_modules.reservoir.loadmap.called

    def test_reservoirs(self, mocker):
        settings = self.setoption(settings_file, 'simulateReservoirs')
        mock_api = mocker.MagicMock(name='loadmap')
        mock_api.side_effect = self.dummyloadmap
        mocker.patch('lisflood.hydrological_modules.reservoir.loadmap', new=mock_api)
        lisfloodexe(settings)
        calls = [call('ReservoirSites'), call('ReservoirSites', pcr=True), call('adjust_Normal_Flood'),
                 call('ReservoirRnormqMult'), call('ReservoirInitialFillValue')]
        lisflood.hydrological_modules.reservoir.loadmap.assert_has_calls(calls)

    def test_lakes(self, mocker):
        settings = self.setoption(settings_file, 'simulateLakes')
        mock_api = mocker.MagicMock(name='loadmap')
        mock_api.side_effect = self.dummyloadmap
        mocker.patch('lisflood.hydrological_modules.lakes.loadmap', new=mock_api)
        lisfloodexe(settings)
        calls = [call('LakeSites')]
        lisflood.hydrological_modules.lakes.loadmap.assert_has_calls(calls)

    def test_rice(self, mocker):
        settings = self.setoption(settings_file, 'riceIrrigation')
        mock_api = mocker.MagicMock(name='loadmap')
        mock_api2 = mocker.MagicMock(name='loadmap')
        mock_api.side_effect = self.dummyloadmap
        mock_api2.side_effect = self.dummyloadmap
        mocker.patch('lisflood.hydrological_modules.riceirrigation.loadmap', new=mock_api)
        mocker.patch('lisflood.hydrological_modules.reservoir.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.evapowater.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.waterabstraction.loadmap', new=mock_api2)
        lisfloodexe(settings)
        calls = [call('RiceFlooding'), call('RicePercolation'), call('RicePlantingDay1'),
                 call('RiceHarvestDay1'), call('RicePlantingDay2'), call('RiceHarvestDay2'), ]
        lisflood.hydrological_modules.riceirrigation.loadmap.assert_has_calls(calls)
        assert not lisflood.hydrological_modules.waterabstraction.loadmap.called
        assert not lisflood.hydrological_modules.evapowater.loadmap.called
        assert not lisflood.hydrological_modules.reservoir.loadmap.called
