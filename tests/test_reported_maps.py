import os
from unittest.mock import call

import numpy as np

import lisflood
from lisflood.main import lisfloodexe

from tests import TestSettings

settings_file = os.path.join(os.path.dirname(__file__), 'data/settings/full.xml')
settings_file_base = os.path.join(os.path.dirname(__file__), 'data/settings/base2.xml')


class TestReportedMaps(TestSettings):

    def test_rep_dischargemaps(self, mocker):
        settings = self.setoptions(settings_file, ['repDischargeMaps'])
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        args, kwargs = lisflood.global_modules.output.writenet.call_args_list[0]
        assert 'DischargeMaps' in args

    def test_rep_dischargemaps_not_called(self, mocker):
        settings = self.setoptions(settings_file)
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            assert 'DischargeMaps' not in args

    def test_rep_lakes(self, mocker):
        settings = self.setoptions(settings_file_base, ['simulateLakes', 'repsimulateLakes'])
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        args, kwargs = lisflood.global_modules.output.writenet.call_args_list[0]
        assert 'DischargeMaps' in args

    def test_rep_lakes_not_called(self, mocker):
        settings = self.setoptions(settings_file)
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        lisfloodexe(settings)
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            assert 'DischargeMaps' not in args
    #
    # def test_rep_dischargemaps(self, mocker):
    #     settings = self.setoptions(settings_file, ['repDischargeMaps'])
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     args, kwargs = lisflood.global_modules.output.writenet.call_args_list[0]
    #     assert 'DischargeMaps' in args
    #
    # def test_rep_dischargemaps_not_called(self, mocker):
    #     settings = self.setoptions(settings_file)
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     for c in lisflood.global_modules.output.writenet.call_args_list:
    #         args, kwargs = c
    #         assert 'DischargeMaps' not in args
    #
    # def test_rep_dischargemaps(self, mocker):
    #     settings = self.setoptions(settings_file, ['repDischargeMaps'])
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     args, kwargs = lisflood.global_modules.output.writenet.call_args_list[0]
    #     assert 'DischargeMaps' in args
    #
    # def test_rep_dischargemaps_not_called(self, mocker):
    #     settings = self.setoptions(settings_file)
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     for c in lisflood.global_modules.output.writenet.call_args_list:
    #         args, kwargs = c
    #         assert 'DischargeMaps' not in args
    #
    # def test_rep_dischargemaps(self, mocker):
    #     settings = self.setoptions(settings_file, ['repDischargeMaps'])
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     args, kwargs = lisflood.global_modules.output.writenet.call_args_list[0]
    #     assert 'DischargeMaps' in args
    #
    # def test_rep_dischargemaps_not_called(self, mocker):
    #     settings = self.setoptions(settings_file)
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     for c in lisflood.global_modules.output.writenet.call_args_list:
    #         args, kwargs = c
    #         assert 'DischargeMaps' not in args
    #
    # def test_rep_dischargemaps(self, mocker):
    #     settings = self.setoptions(settings_file, ['repDischargeMaps'])
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     args, kwargs = lisflood.global_modules.output.writenet.call_args_list[0]
    #     assert 'DischargeMaps' in args
    #
    # def test_rep_dischargemaps_not_called(self, mocker):
    #     settings = self.setoptions(settings_file)
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     for c in lisflood.global_modules.output.writenet.call_args_list:
    #         args, kwargs = c
    #         assert 'DischargeMaps' not in args
    #
    # def test_rep_dischargemaps(self, mocker):
    #     settings = self.setoptions(settings_file, ['repDischargeMaps'])
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     args, kwargs = lisflood.global_modules.output.writenet.call_args_list[0]
    #     assert 'DischargeMaps' in args
    #
    # def test_rep_dischargemaps_not_called(self, mocker):
    #     settings = self.setoptions(settings_file)
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     for c in lisflood.global_modules.output.writenet.call_args_list:
    #         args, kwargs = c
    #         assert 'DischargeMaps' not in args
    #
    # def test_rep_dischargemaps(self, mocker):
    #     settings = self.setoptions(settings_file, ['repDischargeMaps'])
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     args, kwargs = lisflood.global_modules.output.writenet.call_args_list[0]
    #     assert 'DischargeMaps' in args
    #
    # def test_rep_dischargemaps_not_called(self, mocker):
    #     settings = self.setoptions(settings_file)
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     for c in lisflood.global_modules.output.writenet.call_args_list:
    #         args, kwargs = c
    #         assert 'DischargeMaps' not in args
    #
    # def test_rep_dischargemaps(self, mocker):
    #     settings = self.setoptions(settings_file, ['repDischargeMaps'])
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     args, kwargs = lisflood.global_modules.output.writenet.call_args_list[0]
    #     assert 'DischargeMaps' in args
    #
    # def test_rep_dischargemaps_not_called(self, mocker):
    #     settings = self.setoptions(settings_file)
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     for c in lisflood.global_modules.output.writenet.call_args_list:
    #         args, kwargs = c
    #         assert 'DischargeMaps' not in args
    #
    # def test_rep_dischargemaps(self, mocker):
    #     settings = self.setoptions(settings_file, ['repDischargeMaps'])
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     args, kwargs = lisflood.global_modules.output.writenet.call_args_list[0]
    #     assert 'DischargeMaps' in args
    #
    # def test_rep_dischargemaps_not_called(self, mocker):
    #     settings = self.setoptions(settings_file)
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     for c in lisflood.global_modules.output.writenet.call_args_list:
    #         args, kwargs = c
    #         assert 'DischargeMaps' not in args
    #
    # def test_rep_dischargemaps(self, mocker):
    #     settings = self.setoptions(settings_file, ['repDischargeMaps'])
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     args, kwargs = lisflood.global_modules.output.writenet.call_args_list[0]
    #     assert 'DischargeMaps' in args
    #
    # def test_rep_dischargemaps_not_called(self, mocker):
    #     settings = self.setoptions(settings_file)
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     for c in lisflood.global_modules.output.writenet.call_args_list:
    #         args, kwargs = c
    #         assert 'DischargeMaps' not in args
    #
    # def test_rep_dischargemaps(self, mocker):
    #     settings = self.setoptions(settings_file, ['repDischargeMaps'])
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     args, kwargs = lisflood.global_modules.output.writenet.call_args_list[0]
    #     assert 'DischargeMaps' in args
    #
    # def test_rep_dischargemaps_not_called(self, mocker):
    #     settings = self.setoptions(settings_file)
    #     mock_api = mocker.MagicMock(name='writenet')
    #     mock_api.side_effect = self.dummywritenet
    #     mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
    #     lisfloodexe(settings)
    #     for c in lisflood.global_modules.output.writenet.call_args_list:
    #         args, kwargs = c
    #         assert 'DischargeMaps' not in args
