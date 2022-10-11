"""

Copyright 2019-2020 European Union

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

import pytest
from nine import IS_PYTHON2

from lisflood.global_modules.errors import LisfloodError

if IS_PYTHON2:
    from mock import call
else:
    from unittest.mock import call

import lisflood
from lisflood.global_modules.add1 import loadmap
from lisflood.main import lisfloodexe

from .test_utils import setoptions, mk_path_out


class TestOptions():
    settings_files = {'base': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/base.xml')}

    @classmethod
    def dummyloadmap(cls, *args, **kwargs):
        return loadmap(*args, **kwargs)

    def test_basic(self, mocker):
        settings = setoptions(self.settings_files['base'])
        mock_api = mocker.MagicMock(name='loadmap_notcalled')
        mock_api2 = mocker.MagicMock(name='loadmap')
        mock_api.side_effect = self.dummyloadmap
        mock_api2.side_effect = self.dummyloadmap
        mocker.patch('lisflood.hydrological_modules.reservoir.loadmap', new=mock_api)
        mocker.patch('lisflood.hydrological_modules.evapowater.loadmap', new=mock_api)
        mocker.patch('lisflood.hydrological_modules.waterabstraction.loadmap', new=mock_api)
        mocker.patch('lisflood.hydrological_modules.inflow.loadmap', new=mock_api)
        mocker.patch('lisflood.hydrological_modules.lakes.loadmap', new=mock_api)
        mocker.patch('lisflood.hydrological_modules.riceirrigation.loadmap', new=mock_api)
        mocker.patch('lisflood.hydrological_modules.transmission.loadmap', new=mock_api)
        mocker.patch('lisflood.hydrological_modules.waterabstraction.loadmap', new=mock_api)
        mocker.patch('lisflood.hydrological_modules.routing.loadmap', new=mock_api2)
        lisfloodexe(settings)
        calls = [call('CrossSection2AreaInitValue'), call('PrevSideflowInitValue'), ]
        for c in calls:
            assert c not in lisflood.hydrological_modules.routing.loadmap.mock_calls
        assert not lisflood.hydrological_modules.reservoir.loadmap.called
        assert not lisflood.hydrological_modules.evapowater.loadmap.called
        assert not lisflood.hydrological_modules.waterabstraction.loadmap.called
        assert not lisflood.hydrological_modules.inflow.loadmap.called
        assert not lisflood.hydrological_modules.lakes.loadmap.called
        assert not lisflood.hydrological_modules.riceirrigation.loadmap.called
        assert not lisflood.hydrological_modules.transmission.loadmap.called
        assert not lisflood.hydrological_modules.waterabstraction.loadmap.called

    def test_split_routing_only(self, mocker):
        settings = setoptions(self.settings_files['base'], 'SplitRouting')
        mock_api = mocker.MagicMock(name='loadmap')
        mock_api2 = mocker.MagicMock(name='loadmap_notcalled')
        mock_api.side_effect = self.dummyloadmap
        mock_api2.side_effect = self.dummyloadmap
        mocker.patch('lisflood.hydrological_modules.routing.loadmap', new=mock_api)
        mocker.patch('lisflood.hydrological_modules.reservoir.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.evapowater.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.waterabstraction.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.inflow.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.lakes.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.riceirrigation.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.transmission.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.waterabstraction.loadmap', new=mock_api2)
        lisfloodexe(settings)
        calls = [call('CrossSection2AreaInitValue'), call('PrevSideflowInitValue'), ]
        lisflood.hydrological_modules.routing.loadmap.assert_has_calls(calls)
        assert not lisflood.hydrological_modules.reservoir.loadmap.called
        assert not lisflood.hydrological_modules.evapowater.loadmap.called
        assert not lisflood.hydrological_modules.waterabstraction.loadmap.called
        assert not lisflood.hydrological_modules.inflow.loadmap.called
        assert not lisflood.hydrological_modules.lakes.loadmap.called
        assert not lisflood.hydrological_modules.riceirrigation.loadmap.called
        assert not lisflood.hydrological_modules.transmission.loadmap.called
        assert not lisflood.hydrological_modules.waterabstraction.loadmap.called

    def test_reservoirs_only(self, mocker):
        settings = setoptions(self.settings_files['base'],
                              'simulateReservoirs',
                              )
        mock_api = mocker.MagicMock(name='loadmap')
        mock_api.side_effect = self.dummyloadmap
        mocker.patch('lisflood.hydrological_modules.reservoir.loadmap', new=mock_api)
        lisfloodexe(settings)
        calls = [call('ReservoirSites'), call('ReservoirSites', pcr=True), call('adjust_Normal_Flood'),
                 call('ReservoirRnormqMult'), call('ReservoirInitialFillValue')]
        lisflood.hydrological_modules.reservoir.loadmap.assert_has_calls(calls)

    def test_lakes_only(self, mocker):
        settings = setoptions(self.settings_files['base'], 'simulateLakes')
        mock_api = mocker.MagicMock(name='loadmap')
        mock_api.side_effect = self.dummyloadmap
        mocker.patch('lisflood.hydrological_modules.lakes.loadmap', new=mock_api)
        lisfloodexe(settings)
        calls = [call('LakeSites')]
        lisflood.hydrological_modules.lakes.loadmap.assert_has_calls(calls)

    def test_rice_only(self, mocker):
        settings = setoptions(self.settings_files['base'], 
            ('riceIrrigation', 'wateruse',
            'TransientWaterDemandChange', 'useWaterDemandAveYear', 'wateruseRegion'))
        mock_api = mocker.MagicMock(name='loadmap')
        mock_api2 = mocker.MagicMock(name='loadmap_notcalled')
        mock_api.side_effect = self.dummyloadmap
        mock_api2.side_effect = self.dummyloadmap
        mocker.patch('lisflood.hydrological_modules.riceirrigation.loadmap', new=mock_api)
        mocker.patch('lisflood.hydrological_modules.reservoir.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.evapowater.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.waterabstraction.loadmap', new=mock_api)
        mocker.patch('lisflood.hydrological_modules.inflow.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.lakes.loadmap', new=mock_api2)
        lisfloodexe(settings)
        calls = [call('RiceFlooding'), call('RicePercolation'), call('RicePlantingDay1'),
                 call('RiceHarvestDay1'), call('RicePlantingDay2'), call('RiceHarvestDay2'), ]
        lisflood.hydrological_modules.riceirrigation.loadmap.assert_has_calls(calls)
        assert not lisflood.hydrological_modules.evapowater.loadmap.called
        assert not lisflood.hydrological_modules.reservoir.loadmap.called
        assert not lisflood.hydrological_modules.inflow.loadmap.called
        assert not lisflood.hydrological_modules.lakes.loadmap.called

    def test_pf_only(self, mocker):
        settings = setoptions(self.settings_files['base'], 'simulatePF')
        mock_api = mocker.MagicMock(name='loadmap')
        mock_api2 = mocker.MagicMock(name='loadmap_notcalled')
        mock_api.side_effect = self.dummyloadmap
        mock_api2.side_effect = self.dummyloadmap
        mocker.patch('lisflood.hydrological_modules.soil.loadmap', new=mock_api)
        mocker.patch('lisflood.hydrological_modules.riceirrigation.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.reservoir.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.evapowater.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.waterabstraction.loadmap', new=mock_api2)
        lisfloodexe(settings)
        calls = [call('HeadMax'), ]
        lisflood.hydrological_modules.soil.loadmap.assert_has_calls(calls)
        assert not lisflood.hydrological_modules.riceirrigation.loadmap.called
        assert not lisflood.hydrological_modules.waterabstraction.loadmap.called
        assert not lisflood.hydrological_modules.evapowater.loadmap.called
        assert not lisflood.hydrological_modules.reservoir.loadmap.called

    def test_waterabstraction_only(self, mocker):
        settings = setoptions(self.settings_files['base'], ['groundwaterSmooth', 'wateruse',
                                                                 'TransientWaterDemandChange', 'useWaterDemandAveYear', 'wateruseRegion'])
        mock_api = mocker.MagicMock(name='loadmap')
        mock_api2 = mocker.MagicMock(name='loadmap_notcalled')
        mock_api.side_effect = self.dummyloadmap
        mock_api2.side_effect = self.dummyloadmap
        mocker.patch('lisflood.hydrological_modules.transmission.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.inflow.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.lakes.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.riceirrigation.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.reservoir.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.evapowater.loadmap', new=mock_api2)
        mocker.patch('lisflood.hydrological_modules.waterabstraction.loadmap', new=mock_api)
        lisfloodexe(settings)
        assert not lisflood.hydrological_modules.riceirrigation.loadmap.called
        assert not lisflood.hydrological_modules.transmission.loadmap.called
        assert not lisflood.hydrological_modules.inflow.loadmap.called
        assert not lisflood.hydrological_modules.lakes.loadmap.called
        assert not lisflood.hydrological_modules.evapowater.loadmap.called
        assert not lisflood.hydrological_modules.reservoir.loadmap.called
        calls = [call('WUsePercRemain'), call('maxNoWateruse'), call('GroundwaterBodies'), call('WUseRegion'), ]
        for c in calls:
            assert c in lisflood.hydrological_modules.waterabstraction.loadmap.mock_calls


class TestWrongTimestepInit:

    def test_raisexc(self):
        settings_path = os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/warm.xml')
        with pytest.raises(LisfloodError) as e:
            setoptions(settings_path, vars_to_set={'timestepInit': 'PDAY'})
        assert 'Option timestepInit was not parsable.' in str(e.value)
