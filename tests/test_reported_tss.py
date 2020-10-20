from __future__ import absolute_import
import os

from tests import MixinTestSettings


class TestReportedTSS(MixinTestSettings):
    settings_files = {'full': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/full.xml')}

    def test_rep_dischargetss(self, mocker):
        self._reported_tss(self.settings_files['full'],
                           opts_to_set=['repStateUpsGauges', 'repDischargeTs'],
                           tss_to_check='disWin.tss', mocker=mocker)

    def test_rep_dischargetss_not_called(self, mocker):
        self._not_reported_tss(self.settings_files['full'], tss_to_check='disWin.tss', mocker=mocker)

    def test_rep_stateupgaugestss(self, mocker):
        self._reported_tss(self.settings_files['full'], opts_to_set=['repStateUpsGauges'],
                           tss_to_check=['dslrUps.tss', 'frostUps.tss', 'lzUps.tss',
                                         'scovUps.tss', 'wDepthUps.tss'],
                           mocker=mocker)

    def test_rep_stateupgaugestss_not_called(self, mocker):
        self._not_reported_tss(self.settings_files['full'],
                               tss_to_check=['dslrUps.tss', 'frostUps.tss', 'lzUps.tss',
                                             'scovUps.tss', 'wDepthUps.tss'], mocker=mocker)

    def test_rep_rateupgaugestss(self, mocker):
        self._reported_tss(self.settings_files['full'], opts_to_set=['repRateUpsGauges', ],
                           tss_to_check=['percUZLZUps.tss', 'infUps.tss', 'qLzUps.tss', 'qUzUps.tss',
                                         'dTopToSubUps.tss', 'prefFlowUps.tss', 'rainUps.tss',
                                         'snowUps.tss', 'snowMeltUps.tss', 'surfaceRunoffUps.tss'],
                           mocker=mocker)

    def test_rep_rateupgaugestss_not_called(self, mocker):
        self._not_reported_tss(self.settings_files['full'],
                               tss_to_check=['percUZLZUps.tss', 'infUps.tss', 'qLzUps.tss', 'qUzUps.tss',
                                             'dTopToSubUps.tss', 'prefFlowUps.tss', 'rainUps.tss',
                                             'snowUps.tss', 'snowMeltUps.tss', 'surfaceRunoffUps.tss'],
                               mocker=mocker)

    def test_rep_meteoupgaugestss(self, mocker):
        self._reported_tss(self.settings_files['full'], opts_to_set=['repMeteoUpsGauges', ],
                           tss_to_check=['etUps.tss', 'ewUps.tss', 'tAvgUps.tss'],
                           mocker=mocker)

    def test_rep_meteoupgaugestss_not_called(self, mocker):
        self._not_reported_tss(self.settings_files['full'],
                               tss_to_check=['etUps.tss', 'ewUps.tss', 'tAvgUps.tss'],
                               mocker=mocker)
