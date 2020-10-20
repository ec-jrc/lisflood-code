from __future__ import absolute_import
import os

from tests import MixinTestSettings


class TestReportedMaps(MixinTestSettings):

    settings_files = {
        # full.xml of LF_ETRS89_UseCase has simulateLakes and repsimulateLakes off
        # because the catchment doesn't have lakes
        'full': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/full.xml'),
        # need a separate test catchment to test Lakes related options
        'lakes': os.path.join(os.path.dirname(__file__), 'data/TestCatchmentWithLakes/settings/full.xml')
    }

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
        self._reported_map(self.settings_files['lakes'],
                           opts_to_set=['simulateLakes', 'repsimulateLakes', 'repStateMaps'],
                           map_to_check='LakeLevelState', mocker=mocker)

    def test_rep_lakes_not_called(self, mocker):
        self._not_reported_map(self.settings_files['lakes'],
                               # opts_to_set=['repStateMaps'],
                               map_to_check='LakeLevelState', mocker=mocker)

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
