from __future__ import absolute_import
import os
from copy import copy

from pathlib import Path

import lisflood
from lisflood.global_modules.add1 import loadmap
from lisflood.main import lisfloodexe
from lisflood.global_modules.default_options import default_options

from .test_utils import setoptions, mk_path_out

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

    def get_mocker(self, mocker):
        mocks = []
        mocks.append(mocker.patch('lisflood.global_modules.output.NetcdfWriter'))
        mocks.append(mocker.patch('lisflood.global_modules.output.NetcdfStepsWriter'))
        return mocks

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

        mocks = self.get_mocker(mocker)

        # ** execute lisflood
        lisfloodexe(settings)

        to_check = copy(map_to_check)
        # remove extensions (in Lisflood settings you can have names like lzavin.map but you check for lzavin.nc)
        f_to_check = [os.path.splitext(f)[0] for f in copy(files_to_check)]
        for mock in mocks:
            for c in mock.call_args_list:
                args, kwargs = c
                for m in map_to_check:
                    if m == args[1] and m in to_check:
                        to_check.remove(m)
                        if not to_check:
                            break
                path = os.path.splitext(Path(args[3]).name)[0]
                print(path)

                for f in files_to_check:
                    f = os.path.splitext(f)[0]
                    if f == path and f in f_to_check:
                        f_to_check.remove(f)
                        if not f_to_check:
                            break
        print(to_check)
        assert not to_check
        assert not f_to_check

    def _not_reported_map(self, settings_file, opts_to_set=None, opts_to_unset=None, map_to_check=None, mocker=None):
        if isinstance(map_to_check, str):
            # single map to check in writenet calls args
            map_to_check = [map_to_check]
        settings = setoptions(settings_file, opts_to_set, opts_to_unset)

        mocks = self.get_mocker(mocker)

        lisfloodexe(settings)

        res = True
        for mock in mocks:
            for c in mock.call_args_list:
                args, kwargs = c
                if any(m == args[2] for m in map_to_check):
                    res = False
                    break
        assert res

    # def test_all_maps(self, mocker):
    #     for rep_map in default_options['reportedmaps'].values():
    #         settings_file = self.settings_files['full']
    #         settings = setoptions(settings_file)
    #         options = settings.options.copy()
    #         options.pop('reportedmaps')
    #         options.pop('timeseries')
    #         print(options)
    #         check = True
    #         for opt in rep_map.restrictoption:
    #             print(opt, options[opt])
    #             if not options[opt]:
    #                 check = False

    #         if check:
    #             files_to_check = []
    #             files_to_check.extend(rep_map.end)
    #             files_to_check.extend(rep_map.all)
    #             files_to_check.extend(rep_map.steps)
    #             print(files_to_check)
    #             files_to_check = [ncfile + '.nc' for ncfile in files_to_check]

    #             self._reported_map(self.settings_files['full'], map_to_check=[rep_map.output_var], mocker=mocker,
    #                             files_to_check=files_to_check)

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

    def test_rep_wateruse(self, mocker):
        self._reported_map(self.settings_files['full'],
                           opts_to_set=['repWaterUse', 'repWIndex', 'repStateMaps'],
                           map_to_check=['FalkenmarkM3Capita1',
                                         'UpstreamInflowUsedM3',
                                         'abstraction_allSources_actual_irrigation_M3MonthRegion', 'WEI_Abs'], mocker=mocker)

    def test_rep_wateruse_not_called(self, mocker):
        self._not_reported_map(self.settings_files['full'],
                           map_to_check=['FalkenmarkM3Capita1',
                                         'UpstreamInflowUsedM3',
                                         'abstraction_allSources_actual_irrigation_M3MonthRegion', 'WEI_Abs'], mocker=mocker)
    '''
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
    '''