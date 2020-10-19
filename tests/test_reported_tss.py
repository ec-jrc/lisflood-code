from __future__ import absolute_import
import os

from tests import MixinTestSettings


class TestReportedTSS(MixinTestSettings):
    settings_files = {'full': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/full.xml')}

    def test_rep_dischargetss(self, mocker):
        self._reported_tss(self.settings_files['full'], ['repStateUpsGauges', 'repDischargeTs'], None, 'disWin.tss', mocker)

    def test_rep_dischargetss_not_called(self, mocker):
        self._not_reported_tss(self.settings_files['full'], ['repStateUpsGauges', ], None, 'disWin.tss', mocker)

    def test_rep_stateupgaugestss(self, mocker):
        self._reported_tss(self.settings_files['full'], ['repStateUpsGauges', ], None,
                           ['dslrUps.tss', 'frostUps.tss', 'lzUps.tss', 'scovUps.tss', 'wDepthUps.tss'], mocker)

    def test_rep_stateupgaugestss_not_called(self, mocker):
        self._not_reported_tss(self.settings_files['full'], ['repRateUpsGauges', ], None,
                               ['dslrUps.tss', 'frostUps.tss', 'lzUps.tss', 'scovUps.tss', 'wDepthUps.tss'], mocker)

    def test_rep_rateupgaugestss(self, mocker):
        self._reported_tss(self.settings_files['full'], ['repRateUpsGauges', ], None,
                           ['percUZLZUps.tss', 'infUps.tss', 'qLzUps.tss', 'qUzUps.tss',
                            'dTopToSubUps.tss', 'prefFlowUps.tss', 'rainUps.tss',
                            'snowUps.tss', 'snowMeltUps.tss', 'surfaceRunoffUps.tss'], mocker)

    def test_rep_rateupgaugestss_not_called(self, mocker):
        self._not_reported_tss(self.settings_files['full'], ['repMeteoUpsGauges', ], None,
                               ['percUZLZUps.tss', 'infUps.tss', 'qLzUps.tss', 'qUzUps.tss',
                                'dTopToSubUps.tss', 'prefFlowUps.tss', 'rainUps.tss',
                                'snowUps.tss', 'snowMeltUps.tss', 'surfaceRunoffUps.tss'], mocker)

    def test_rep_meteoupgaugestss(self, mocker):
        self._reported_tss(self.settings_files['full'], ['repMeteoUpsGauges', ], None, ['etUps.tss', 'ewUps.tss', 'tAvgUps.tss'],
                           mocker)

    def test_rep_meteoupgaugestss_not_called(self, mocker):
        self._not_reported_tss(self.settings_files['full'], ['repStateUpsGauges', ], None, ['etUps.tss', 'ewUps.tss', 'tAvgUps.tss'],
                               mocker)
