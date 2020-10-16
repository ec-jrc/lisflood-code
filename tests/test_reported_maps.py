from __future__ import absolute_import
import os

from tests import TestSettings


class TestReportedMaps(TestSettings):

    settings_files = {
        'full': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/full.xml'),
        'lakes': os.path.join(os.path.dirname(__file__), 'data/TestCatchmentWithLakes/settings/full.xml')
    }

    def test_rep_dischargemaps(self, mocker):
        self._reported_map(self.settings_files['full'], ['repDischargeMaps'], None, 'DischargeMaps', mocker)

    def test_rep_dischargemaps_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'], ['repEndMaps'], ['simulateLakes'], 'DischargeMaps', mocker)

    def test_rep_lakes(self, mocker):
        self._reported_map(self.settings_files['lakes'], ['simulateLakes', 'repsimulateLakes', 'repEndMaps', 'repStateMaps'],
                           None, 'LakeLevelState', mocker)

    def test_rep_lakes_not_called(self, mocker):
        self._not_reported_map(self.settings_files['lakes'], ['repEndMaps', 'repStateMaps'], None, 'LakeLevelState', mocker)

    def test_rep_reservoirs(self, mocker):
        self._reported_map(self.settings_files['full'], ['simulateReservoirs', 'repsimulateReservoirs', 'repStateMaps'],
                           ['simulateLakes', 'repsimulateLakes'], 'ReservoirFillState', mocker)

    def test_rep_reservoirs_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'], opts_to_set=['repStateMaps'],
                               opts_to_unset=['simulateLakes', 'repsimulateLakes',
                                              'simulateReservoirs', 'repsimulateReservoirs'],
                               map_to_check='ReservoirFillState', mocker=mocker)

    def test_rep_snowmaps(self, mocker):
        self._reported_map(self.settings_files['full'], opts_to_set=['repSnowMaps', 'repStateMaps'],
                           opts_to_unset=['simulateLakes', 'repsimulateLakes'],
                           map_to_check='SnowMaps', mocker=mocker)

    def test_rep_snowmaps_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'], opts_to_set=['repStateMaps'],
                               opts_to_unset=['simulateLakes', 'repsimulateLakes'], map_to_check='SnowMaps',
                               mocker=mocker)

    def test_rep_pfmaps(self, mocker):
        self._reported_map(self.settings_files['full'],
                           opts_to_set=['repPFMaps', 'repStateMaps'],
                           opts_to_unset=['simulateLakes', 'repsimulateLakes'], map_to_check='PF1Maps', mocker=mocker)

    def test_rep_pfmaps_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'], opts_to_set=['repStateMaps'],
                               opts_to_unset=['simulateLakes', 'repsimulateLakes'], map_to_check='PF1Maps',
                               mocker=mocker)

    def test_rep_lzmaps(self, mocker):
        self._reported_map(self.settings_files['full'], opts_to_set=['repLZMaps', 'repE2O2'],
                           opts_to_unset=['simulateLakes', 'repsimulateLakes'],
                           map_to_check='LZMaps', mocker=mocker)

    def test_rep_lzmaps_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'], opts_to_set=['repEndMaps', ],
                               opts_to_unset=['simulateLakes', 'repsimulateLakes'], map_to_check=['LZState', 'LZMaps'],
                               mocker=mocker)

    def test_rep_uzmaps(self, mocker):
        self._reported_map(self.settings_files['full'],
                           opts_to_set=['repUZMaps', ],
                           opts_to_unset=['simulateLakes', 'repsimulateLakes'], map_to_check='UZMaps', mocker=mocker)

    def test_rep_uzmaps_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'], opts_to_set=['repEndMaps', ],
                               opts_to_unset=['simulateLakes', 'repsimulateLakes'],
                               map_to_check=['UZState', 'UZMaps'], mocker=mocker)

    def test_rep_gwpercuzlzmaps(self, mocker):
        self._reported_map(self.settings_files['full'],
                           opts_to_set=['repE2O2', 'repGwPercUZLZMaps', 'repEndMaps', 'repStateMaps',],
                           opts_to_unset=['simulateLakes', 'repsimulateLakes'], map_to_check=['GwPercUZLZForestMaps', 'GwPercUZLZMaps'], mocker=mocker)

    def test_rep_gwpercuzlzmaps_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'], opts_to_set=['repEndMaps', 'repStateMaps',],
                           opts_to_unset=['simulateLakes', 'repsimulateLakes'],
                           map_to_check=['GwPercUZLZForestMaps', 'GwPercUZLZMaps'], mocker=mocker)

    def test_rep_totalabs(self, mocker):
        self._reported_map(self.settings_files['full'],
                           opts_to_set=['repTotalAbs', 'repStateMaps'],
                           opts_to_unset=['simulateLakes', 'repsimulateLakes'],
                           map_to_check=['AreaTotalAbstractionFromGroundwaterM3', 'AreaTotalAbstractionFromSurfaceWaterM3',
                                         'DomesticConsumptiveUse', 'EFlowIndicator'], mocker=mocker)

    def test_rep_totalabs_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'], opts_to_set=['repStateMaps'],
                           opts_to_unset=['simulateLakes', 'repsimulateLakes'],
                           map_to_check=['AreaTotalAbstractionFromGroundwaterM3', 'AreaTotalAbstractionFromSurfaceWaterM3',
                                         'DomesticConsumptiveUse', 'EFlowIndicator'], mocker=mocker)

    def test_rep_totalwuse(self, mocker):
        self._reported_map(self.settings_files['full'],
                           opts_to_set=['repTotalWUse', 'repStateMaps'],
                           opts_to_unset=['simulateLakes', 'repsimulateLakes'],
                           map_to_check=['TotalWUse', 'TotalWUseRegion'], mocker=mocker)

    def test_rep_totalwuse_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'], opts_to_set=['repStateMaps'],
                           opts_to_unset=['simulateLakes', 'repsimulateLakes'],
                           map_to_check=['TotalWUse', 'TotalWUseRegion'], mocker=mocker)

    def test_rep_windex(self, mocker):
        self._reported_map(self.settings_files['full'],
                           opts_to_set=['repWIndex', 'repStateMaps'],
                           opts_to_unset=['simulateLakes', 'repsimulateLakes'],
                           map_to_check=['WaterSecurityIndex', 'WaterSustainabilityIndex', 'WaterDependencyIndex', 'WEI_Dem',
                                         'WEI_Abs', 'MonthETactMM', 'MonthETdifMM',], mocker=mocker)

    def test_rep_windex_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'], opts_to_set=['repStateMaps'], opts_to_unset=['simulateLakes', 'repsimulateLakes'],
                               map_to_check=['WaterSecurityIndex', 'WaterSustainabilityIndex', 'WaterDependencyIndex',
                                             'WEI_Dem', 'FalkenmarkM3Capita1', 'FalkenmarkM3Capita2', 'FalkenmarkM3Capita3',
                                             'WEI_Abs', 'MonthETactMM', 'MonthETdifMM', 'MonthETpotMM'], mocker=mocker)
