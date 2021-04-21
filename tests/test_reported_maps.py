from __future__ import absolute_import
import os
from copy import copy

from nine import IS_PYTHON2
if IS_PYTHON2:
    from pathlib2 import Path
else:
    from pathlib import Path

import lisflood
from lisflood.global_modules.add1 import loadmap
from lisflood.main import lisfloodexe

from .test_utils import setoptions


class TestReportedMaps():

    settings_files = {
        # full.xml of LF_ETRS89_UseCase has simulateLakes and repsimulateLakes off
        # because the catchment doesn't have lakes
        'full': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/full.xml'),
        # need a separate test catchment to test Lakes related options
        # 'lakes': os.path.join(os.path.dirname(__file__), 'data/TestCatchmentWithLakes/settings/full.xml'),
        'initrun': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/prerun.xml')
    }

    @classmethod
    def dummywritenet(cls, *args, **kwargs):
        return list(args), dict(**kwargs)

    def _reported_map(self, settings_file, opts_to_set=None, opts_to_unset=None,
                      map_to_check=None, mocker=None, files_to_check=None):
        """
        Check that writenet function was called for the list of maps to check and that files are correctly named
        :param settings_file:
        :param opts_to_set:
        :param opts_to_unset:
        :param map_to_check:
        :param mocker:
        :param files_to_check:
        :return:
        """
        if isinstance(map_to_check, str):
            # single map to check in writenet calls args
            map_to_check = [map_to_check]
        elif not map_to_check:
            map_to_check = []

        if not files_to_check:
            files_to_check = []

        settings = setoptions(settings_file, opts_to_set, opts_to_unset)
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        mock_api2 = mocker.MagicMock(name='timeseries')
        mocker.patch('lisflood.global_modules.output.TimeoutputTimeseries', new=mock_api2)

        mock_api3 = mocker.MagicMock(name='reportpcr')
        mocker.patch('lisflood.global_modules.output.report', new=mock_api3)

        # ** execute lisflood
        lisfloodexe(settings)
        assert len(lisflood.global_modules.output.writenet.call_args_list) > 0

        to_check = copy(map_to_check)
        # remove extensions (in Lisflood settings you can have names like lzavin.map but you check for lzavin.nc)
        f_to_check = [os.path.splitext(f)[0] for f in copy(files_to_check)]
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            for m in map_to_check:
                if m == args[4] and m in to_check:
                    to_check.remove(m)
                    if not to_check:
                        break
            path = os.path.splitext(Path(args[2]).name)[0]

            for f in files_to_check:
                f = os.path.splitext(f)[0]
                if f == path and f in f_to_check:
                    f_to_check.remove(f)
                    if not f_to_check:
                        break
        assert not to_check
        assert not f_to_check

    def _not_reported_map(self, settings_file, opts_to_set=None, opts_to_unset=None, map_to_check=None, mocker=None):
        if isinstance(map_to_check, str):
            # single map to check in writenet calls args
            map_to_check = [map_to_check]
        settings = setoptions(settings_file, opts_to_set, opts_to_unset)
        mock_api = mocker.MagicMock(name='writenet')
        mock_api.side_effect = self.dummywritenet
        mocker.patch('lisflood.global_modules.output.writenet', new=mock_api)
        mock_api2 = mocker.MagicMock(name='timeseries')
        mocker.patch('lisflood.global_modules.output.TimeoutputTimeseries', new=mock_api2)
        mock_api3 = mocker.MagicMock(name='reportpcr')
        mocker.patch('lisflood.global_modules.output.report', new=mock_api3)

        lisfloodexe(settings)
        res = True
        for c in lisflood.global_modules.output.writenet.call_args_list:
            args, kwargs = c
            if any(m == args[4] for m in map_to_check):
                res = False
                break
        assert res

    def test_prerun(self, mocker):
        self._reported_map(self.settings_files['initrun'], map_to_check=['AvgDis', 'LZAvInflowMap'], mocker=mocker,
                           files_to_check=['avgdis.nc', 'lzavin.nc'])

    def test_rep_dischargemaps(self, mocker):
        """
        Test that
        when repDischargeMaps is activated
        then the DischargeMaps is produced
        :param mocker: mocker injected by pytest-mock plugin
        """
        self._reported_map(self.settings_files['full'], opts_to_set=['repDischargeMaps'],
                           map_to_check='DischargeMaps', mocker=mocker)

    def test_rep_dischargemaps_not_called(self, mocker):
        """
        Test that
        when repDischargeMaps is not activated
        then the DischargeMaps is not produced
        :param mocker: mocker injected by pytest-mock plugin
        """
        self._not_reported_map(self.settings_files['full'],
                               opts_to_unset=['repDischargeMaps'],
                               map_to_check='DischargeMaps',
                               mocker=mocker)

    def test_rep_lakes(self, mocker):
        self._reported_map(self.settings_files['full'],
                           opts_to_set=['simulateLakes', 'repsimulateLakes', 'repStateMaps'],
                           map_to_check='LakeLevelState', mocker=mocker)

    def test_rep_lakes_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'], map_to_check='LakeLevelState', mocker=mocker)

    def test_rep_reservoirs(self, mocker):
        self._reported_map(self.settings_files['full'],
                           opts_to_set=['simulateReservoirs', 'repsimulateReservoirs', 'repStateMaps'],
                           map_to_check='ReservoirFillState', mocker=mocker)

    def test_rep_reservoirs_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'],
                               opts_to_unset=['simulateReservoirs', 'repsimulateReservoirs'],
                               map_to_check='ReservoirFillState', mocker=mocker)

    def test_rep_snowmaps(self, mocker):
        self._reported_map(self.settings_files['full'], opts_to_set=['repSnowMaps', 'repStateMaps'],
                           map_to_check='SnowMaps', mocker=mocker)

    def test_rep_snowmaps_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'],
                               opts_to_unset=['simulateLakes', 'repsimulateLakes'], map_to_check='SnowMaps',
                               mocker=mocker)

    def test_rep_pfmaps(self, mocker):
        self._reported_map(self.settings_files['full'],
                           opts_to_set=['repPFMaps', 'repStateMaps'], map_to_check='PF1Maps', mocker=mocker)

    def test_rep_pfmaps_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'],
                               map_to_check='PF1Maps',
                               mocker=mocker)

    def test_rep_lzmaps(self, mocker):
        self._reported_map(self.settings_files['full'], opts_to_set=['repLZMaps', 'repE2O2'],
                           map_to_check='LZMaps', mocker=mocker)

    def test_rep_lzmaps_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'],
                               opts_to_unset=['simulateLakes', 'repsimulateLakes'], map_to_check=['LZState', 'LZMaps'],
                               mocker=mocker)

    def test_rep_uzmaps(self, mocker):
        self._reported_map(self.settings_files['full'], opts_to_set=['repUZMaps', ],
                           map_to_check='UZMaps', mocker=mocker)

    def test_rep_uzmaps_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'],
                               opts_to_unset=['simulateLakes', 'repsimulateLakes'],
                               map_to_check=['UZState', 'UZMaps'], mocker=mocker)

    def test_rep_gwpercuzlzmaps(self, mocker):
        self._reported_map(self.settings_files['full'],
                           opts_to_set=['repE2O2', 'repGwPercUZLZMaps', 'repEndMaps', 'repStateMaps'],
                           map_to_check=['GwPercUZLZForestMaps', 'GwPercUZLZMaps'], mocker=mocker)

    def test_rep_gwpercuzlzmaps_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'],
                               map_to_check=['GwPercUZLZForestMaps', 'GwPercUZLZMaps'], mocker=mocker)

    def test_rep_totalabs(self, mocker):
        self._reported_map(self.settings_files['full'],
                           opts_to_set=['repTotalAbs', 'repStateMaps'],
                           map_to_check=['AreaTotalAbstractionFromGroundwaterM3',
                                         'AreaTotalAbstractionFromSurfaceWaterM3',
                                         'DomesticConsumptiveUse', 'EFlowIndicator'], mocker=mocker)

    def test_rep_totalabs_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'],
                               map_to_check=['AreaTotalAbstractionFromGroundwaterM3',
                                             'AreaTotalAbstractionFromSurfaceWaterM3',
                                             'DomesticConsumptiveUse', 'EFlowIndicator'], mocker=mocker)

    def test_rep_totalwuse(self, mocker):
        self._reported_map(self.settings_files['full'],
                           opts_to_set=['repTotalWUse', 'repStateMaps'],
                           map_to_check=['TotalWUse', 'TotalWUseRegion'], mocker=mocker)

    def test_rep_totalwuse_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'],
                               map_to_check=['TotalWUse', 'TotalWUseRegion'], mocker=mocker)

    def test_rep_windex(self, mocker):
        self._reported_map(self.settings_files['full'],
                           opts_to_set=['repWIndex', 'repStateMaps'],
                           map_to_check=['WaterSecurityIndex', 'WaterSustainabilityIndex',
                                         'WaterDependencyIndex', 'WEI_Dem',
                                         'WEI_Abs', 'MonthETactMM', 'MonthETdifMM'], mocker=mocker)

    def test_rep_windex_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'],
                               map_to_check=['WaterSecurityIndex', 'WaterSustainabilityIndex', 'WaterDependencyIndex',
                                             'WEI_Dem', 'FalkenmarkM3Capita1', 'FalkenmarkM3Capita2',
                                             'FalkenmarkM3Capita3',
                                             'WEI_Abs', 'MonthETactMM', 'MonthETdifMM', 'MonthETpotMM'], mocker=mocker)
