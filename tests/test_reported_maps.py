import os
from unittest.mock import call

import numpy as np

import lisflood
from lisflood.main import lisfloodexe

from tests import TestSettings

settings_file = os.path.join(os.path.dirname(__file__), 'data/settings/full.xml')
settings_file_lakes = os.path.join(os.path.dirname(__file__), 'data/settings/full_with_lakes.xml')


class TestReportedMaps(TestSettings):

    def test_rep_dischargemaps(self, mocker):
        settings = self.setoptions(settings_file, ['repDischargeMaps'])
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        args, kwargs = lisflood.global_modules.output.writenet.call_args_list[0]
        assert len(lisflood.global_modules.output.writenet.call_args_list) > 0
        assert 'DischargeMaps' in args

    def test_rep_dischargemaps_not_called(self, mocker):
        settings = self.setoptions(settings_file, ['repEndMaps'], opts_to_unset=['simulateLakes'])
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        assert len(lisflood.global_modules.output.writenet.call_args_list) > 0
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            assert 'DischargeMaps' not in args

    def test_rep_lakes(self, mocker):
        settings = self.setoptions(settings_file_lakes, ['simulateLakes', 'repsimulateLakes', 'repEndMaps', 'repStateMaps'])
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        res = False
        assert len(lisflood.global_modules.output.writenet.call_args_list) > 0
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            if 'LakeLevelState' == args[4]:
                res = True
                break
        assert res

    def test_rep_lakes_not_called(self, mocker):
        settings = self.setoptions(settings_file_lakes, ['repEndMaps', 'repStateMaps'])
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        res = True
        assert len(lisflood.global_modules.output.writenet.call_args_list) > 0
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            if 'LakeLevelState' == args[4]:
                res = False
                break
        assert res

    def test_rep_reservoirs(self, mocker):
        settings = self.setoptions(settings_file,
                                   opts_to_set=['simulateReservoirs', 'repsimulateReservoirs', 'repStateMaps'],
                                   opts_to_unset=['simulateLakes', 'repsimulateLakes'])
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        assert len(lisflood.global_modules.output.writenet.call_args_list) > 0
        res = False
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            if 'ReservoirFillState' == args[4]:
                res = True
                break
        assert res

    def test_rep_reservoirs_not_called(self, mocker):
        settings = self.setoptions(settings_file, opts_to_set=['repStateMaps'],
                                   opts_to_unset=['simulateLakes', 'repsimulateLakes', 'simulateReservoirs', 'repsimulateReservoirs'])
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        assert len(lisflood.global_modules.output.writenet.call_args_list) > 0
        res = True
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            if 'ReservoirFillState' == args[4]:
                res = False
                break
        assert res

    def test_rep_snowmaps(self, mocker):
        settings = self.setoptions(settings_file,
                                   opts_to_set=['repSnowMaps', 'repStateMaps'],
                                   opts_to_unset=['simulateLakes', 'repsimulateLakes'])
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        assert len(lisflood.global_modules.output.writenet.call_args_list) > 0
        res = False
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            if 'SnowMaps' == args[4]:
                res = True
                break
        assert res

    def test_rep_snowmaps_not_called(self, mocker):
        settings = self.setoptions(settings_file, opts_to_set=['repStateMaps'],
                                   opts_to_unset=['simulateLakes', 'repsimulateLakes'])
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        assert len(lisflood.global_modules.output.writenet.call_args_list) > 0
        res = True
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            if 'SnowMaps' == args[4]:
                res = False
                break
        assert res

    def test_rep_pfmaps(self, mocker):
        settings = self.setoptions(settings_file,
                                   opts_to_set=['repPFMaps', 'repStateMaps'],
                                   opts_to_unset=['simulateLakes', 'repsimulateLakes'])
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        assert len(lisflood.global_modules.output.writenet.call_args_list) > 0
        res = False
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            if 'PF1Maps' == args[4]:
                res = True
                break
        assert res

    def test_rep_pfmaps_not_called(self, mocker):
        settings = self.setoptions(settings_file, opts_to_set=['repStateMaps'],
                                   opts_to_unset=['simulateLakes', 'repsimulateLakes'])
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        assert len(lisflood.global_modules.output.writenet.call_args_list) > 0
        res = True
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            if 'PF1Maps' == args[4]:
                res = False
                break
        assert res

    def test_rep_lzmaps(self, mocker):
        settings = self.setoptions(settings_file,
                                   opts_to_set=['repLZMaps',],
                                   opts_to_unset=['simulateLakes', 'repsimulateLakes'])
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        assert len(lisflood.global_modules.output.writenet.call_args_list) > 0
        res = False
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            if 'LZMaps' == args[4]:
                res = True
                break
        assert res

    def test_rep_lzmaps_not_called(self, mocker):
        settings = self.setoptions(settings_file, opts_to_set=['repEndMaps',],
                                   opts_to_unset=['simulateLakes', 'repsimulateLakes'])
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        assert len(lisflood.global_modules.output.writenet.call_args_list) > 0
        res = True
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            if 'LZState' == args[4] or 'LZMaps' == args[4]:
                res = False
                break
        assert res

    def test_rep_uzmaps(self, mocker):
        settings = self.setoptions(settings_file,
                                   opts_to_set=['repUZMaps',],
                                   opts_to_unset=['simulateLakes', 'repsimulateLakes'])
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        assert len(lisflood.global_modules.output.writenet.call_args_list) > 0
        res = False
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            if 'UZMaps' == args[4]:
                res = True
                break
        assert res

    def test_rep_uzmaps_not_called(self, mocker):
        settings = self.setoptions(settings_file, opts_to_set=['repEndMaps',],
                                   opts_to_unset=['simulateLakes', 'repsimulateLakes'])
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        assert len(lisflood.global_modules.output.writenet.call_args_list) > 0
        res = True
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            if 'UZState' == args[4] or 'UZMaps' == args[4]:
                res = False
                break
        assert res
