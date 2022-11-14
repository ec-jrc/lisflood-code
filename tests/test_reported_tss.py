from __future__ import absolute_import
import os
from copy import copy

import lisflood
from lisflood.main import lisfloodexe

from .test_utils import setoptions


class TestReportedTSS():
    settings_files = {'full': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/full.xml')}

    def _reported_tss(self, settings_file, opts_to_set=None, opts_to_unset=None, tss_to_check=None, mocker=None):
        if isinstance(tss_to_check, str):
            tss_to_check = [tss_to_check]
        settings = setoptions(settings_file, opts_to_set, opts_to_unset)
        mock_api = mocker.MagicMock(name='timeseries')
        mocker.patch('lisflood.global_modules.output.TimeoutputTimeseries', new=mock_api)
        lisfloodexe(settings)
        assert len(lisflood.global_modules.output.TimeoutputTimeseries.call_args_list) > 0
        to_check = copy(tss_to_check)
        for c in lisflood.global_modules.output.TimeoutputTimeseries.call_args_list:
            args, kwargs = c
            for tss in tss_to_check:
                if ('/' + tss) in args[0]:
                    to_check.remove(tss)
                    if not to_check:
                        break
        assert not to_check

    def _not_reported_tss(self, settings_file, opts_to_set=None, opts_to_unset=None, tss_to_check=None, mocker=None):
        if isinstance(tss_to_check, str):
            tss_to_check = [tss_to_check]
        settings = setoptions(settings_file, opts_to_set, opts_to_unset)
        mock_api = mocker.MagicMock(name='timeseries')
        mocker.patch('lisflood.global_modules.output.TimeoutputTimeseries', new=mock_api)
        lisfloodexe(settings)
        res = True
        for c in lisflood.global_modules.output.TimeoutputTimeseries.call_args_list:
            args, kwargs = c
            if any(tss == args[0] for tss in tss_to_check):
                res = False
                break
        assert res

    def test_rep_dischargetss(self, mocker):
        self._reported_tss(self.settings_files['full'],
                           opts_to_set=['repDischargeTs'],
                           tss_to_check='disWin.tss', mocker=mocker)

    def test_rep_dischargetss_not_called(self, mocker):
        self._not_reported_tss(self.settings_files['full'], tss_to_check='disWin.tss', mocker=mocker)

    def test_rep_stateupgaugestss(self, mocker):
        self._reported_tss(self.settings_files['full'], opts_to_set=['repStateUpsGauges'],
                           tss_to_check=['dslrUps.tss', 'frostUps.tss', 'lzUps.tss',
                                         'scovUps.tss', 'wDepthUps.tss',
                                         'th1aAvUps.tss', 'th1bAvUps.tss', 'th2AvUps.tss'], 
                           mocker=mocker)

    def test_rep_stateupgaugestss_not_called(self, mocker):
        self._not_reported_tss(self.settings_files['full'],
                               tss_to_check=['dslrUps.tss', 'frostUps.tss', 'lzUps.tss',
                                             'scovUps.tss', 'wDepthUps.tss',
                                             'th1aAvUps.tss', 'th1bAvUps.tss', 'th2AvUps.tss'], 
                               mocker=mocker)

    def test_rep_rateupgaugestss(self, mocker):
        self._reported_tss(self.settings_files['full'], opts_to_set=['repRateUpsGauges'],
                           tss_to_check=['percUZLZUps.tss', 'infUps.tss', 'qLzUps.tss', 'qUzUps.tss',
                                         'dTopToSubUps.tss', 'prefFlowUps.tss',
                                         'snowMeltUps.tss', 'surfaceRunoffUps.tss'],
                           mocker=mocker)

    def test_rep_rateupgaugestss_not_called(self, mocker):
        self._not_reported_tss(self.settings_files['full'],
                               tss_to_check=['percUZLZUps.tss', 'infUps.tss', 'qLzUps.tss', 'qUzUps.tss',
                                             'dTopToSubUps.tss', 'prefFlowUps.tss', 
                                             'snowMeltUps.tss', 'surfaceRunoffUps.tss'],
                               mocker=mocker)

    def test_rep_meteoupgaugestss(self, mocker):
        self._reported_tss(self.settings_files['full'], opts_to_set=['repMeteoUpsGauges'],
                           tss_to_check=['etUps.tss', 'ewUps.tss', 'tAvgUps.tss', 'snowUps.tss', 'rainUps.tss'],
                           mocker=mocker)

    def test_rep_meteoupgaugestss_not_called(self, mocker):
        self._not_reported_tss(self.settings_files['full'],
                               tss_to_check=['etUps.tss', 'ewUps.tss', 'tAvgUps.tss', 'snowUps.tss', 'rainUps.tss'],
                               mocker=mocker)

    def test_rep_statesitestss(self, mocker):
        self._reported_tss(self.settings_files['full'], opts_to_set=['repStateSites'],
                           tss_to_check=['dslr.tss', 'frost.tss', 'lz.tss','scov.tss','wDepth.tss',
                                         'th1a.tss', 'th1b.tss', 'th2.tss'],
                           mocker=mocker)

    def test_rep_statesitestss_not_called(self, mocker):
        self._not_reported_tss(self.settings_files['full'],
                               tss_to_check=['dslr.tss', 'frost.tss', 'lz.tss','scov.tss','wDepth.tss',
                                             'th1a.tss', 'th1b.tss', 'th2.tss'],
                               mocker=mocker)

    def test_rep_ratesitestss(self, mocker):
        self._reported_tss(self.settings_files['full'], opts_to_set=['repRateSites'],
                           tss_to_check=['esAct.tss', 'ewIntAct.tss', 'percUZLZ.tss','infiltration.tss',
                           'qLz.tss', 'dTopToSub.tss','prefFlow.tss',
                           'rain.tss','dSubToUz.tss','snow.tss','snowMelt.tss',
                           'surfaceRunoff.tss','tAct.tss','totalRunoff.tss','qUz.tss'],
                           mocker=mocker)

    def test_rep_ratesitestss_not_called(self, mocker):
        self._not_reported_tss(self.settings_files['full'],
                               tss_to_check=['esAct.tss', 'ewIntAct.tss', 'percUZLZ.tss','infiltration.tss',
                               'qLz.tss', 'dTopToSub.tss','prefFlow.tss',
                               'rain.tss','dSubToUz.tss','snow.tss','snowMelt.tss',
                               'surfaceRunoff.tss','tAct.tss','totalRunoff.tss','qUz.tss'],
                               mocker=mocker)
