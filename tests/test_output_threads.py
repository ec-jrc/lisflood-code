"""Task 3 (output writing) tests: opt-in threaded output writer ('outputThreads').

Covers:
- threaded writer produces byte-identical outputs to the synchronous writer
  (array_equal comparison, so any float/NaN mismatch fails);
- the OutputMapsChunks > report-steps flush path (partial chunk written at the
  end of the run) is bit-identical between the two writer paths.
"""
import os
import shutil

from lisfloodutilities.compare.nc import NetCDFComparator

from lisflood.main import lisfloodexe

from .test_utils import setoptions, mk_path_out, ETRS89TestCase, worker_out


class TestOutputThreads(ETRS89TestCase):
    case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_ETRS89_UseCase')
    settings_file = os.path.join(case_dir, 'settings', 'full.xml')
    # Output dirs isolated per xdist worker (worker_out -> 'out/<gwN>/a') so
    # concurrent test files do not clobber each other's shared 'out/a'.
    out_dir_sync = os.path.join(case_dir, worker_out('a'))
    out_dir_threads = os.path.join(case_dir, worker_out('b'))
    out_dir_sync_flush = os.path.join(case_dir, worker_out('c'))
    out_dir_threads_flush = os.path.join(case_dir, worker_out('d'))
    pathout_sync = '$(PathRoot)/' + worker_out('a')
    pathout_threads = '$(PathRoot)/' + worker_out('b')
    pathout_sync_flush = '$(PathRoot)/' + worker_out('c')
    pathout_threads_flush = '$(PathRoot)/' + worker_out('d')

    def _run(self, pathout, opts_to_set=None, **extra_vars):
        """Run LISFLOOD on the full.xml usecase with the given PathOut and vars."""
        settings = setoptions(self.settings_file, opts_to_set=opts_to_set,
                              vars_to_set={'PathOut': pathout, **extra_vars})
        mk_path_out(os.path.join(self.case_dir, pathout.replace('$(PathRoot)/', '')))
        lisfloodexe(settings)
        return settings

    def teardown_method(self):
        for out_dir in (self.out_dir_sync, self.out_dir_threads,
                        self.out_dir_sync_flush, self.out_dir_threads_flush):
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_threaded_output_bit_identical(self):
        """Threaded writer must produce byte-identical outputs vs synchronous."""
        # repDischargeMaps etc. on: report options gate which map outputs exist,
        # so enable at least two map groups to genuinely exercise parallel writes.
        map_opts = ['repDischargeMaps', 'repStateMaps']
        settings_sync = self._run(self.pathout_sync, opts_to_set=map_opts,
                                  StepStart='30/07/2016 06:00',
                                  StepEnd='05/08/2016 06:00')
        out_sync = settings_sync.output_dir

        settings_thr = self._run(self.pathout_threads,
                                 opts_to_set=map_opts + ['outputThreads'],
                                 StepStart='30/07/2016 06:00',
                                 StepEnd='05/08/2016 06:00')
        out_thr = settings_thr.output_dir

        comparator = NetCDFComparator(settings_thr.maskpath, array_equal=True)
        comparator.compare_dirs(out_sync, out_thr)

    def test_chunk_flush_partial_chunk_bit_identical(self):
        """OutputMapsChunks > number of report steps: the end-of-run flush of the
        partial chunk must be bit-identical between threaded and sync writers."""
        map_opts = ['repDischargeMaps', 'repStateMaps']
        settings_sync = self._run(self.pathout_sync_flush, opts_to_set=map_opts,
                                  StepStart='30/07/2016 06:00',
                                  StepEnd='05/08/2016 06:00', OutputMapsChunks='100')
        out_sync = settings_sync.output_dir

        settings_thr = self._run(self.pathout_threads_flush,
                                 opts_to_set=map_opts + ['outputThreads'],
                                 StepStart='30/07/2016 06:00',
                                 StepEnd='05/08/2016 06:00', OutputMapsChunks='100')
        out_thr = settings_thr.output_dir

        comparator = NetCDFComparator(settings_thr.maskpath, array_equal=True)
        comparator.compare_dirs(out_sync, out_thr)
