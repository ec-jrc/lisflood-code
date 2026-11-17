"""Task 3 (output writing) tests: opt-in threaded output writer ('outputThreads').

Covers:
- threaded writer produces byte-identical outputs to the synchronous writer
  (array_equal comparison, so any float/NaN mismatch fails);
- the OutputMapsChunks > report-steps flush path (partial chunk written at the
  end of the run) is bit-identical between the two writer paths.
"""
import os
import shutil
import pytest

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


class TestPCRasterOutputThreads(ETRS89TestCase):
    """PCRaster map output (netCDF off) must be identical with and without
    'outputThreads': same file names (step suffix taken from the staged step,
    not from the live model clock) and same values."""
    case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_ETRS89_UseCase')
    settings_file = os.path.join(case_dir, 'settings', 'full.xml')
    out_sync = worker_out('pcr_a')
    out_thr = worker_out('pcr_b')

    @classmethod
    def _short_names(cls):
        """PCRaster map names must be <= 8 chars without extension: override every
        map output name that is too long or carries an extension."""
        import re
        with open(cls.settings_file) as fh:
            xml = fh.read()
        names = {}
        pattern = r'<textvar name="(\w+)" value="\$\(PathOut\)/([^"]+)"'
        for i, (name, value) in enumerate(sorted(set(re.findall(pattern, xml)))):
            is_series = value.endswith('.tss') or name.endswith(('TS', 'TSS'))
            if not is_series and (len(value) > 8 or '.' in value):
                names[name] = '$(PathOut)/m%03d' % i
        return names

    def _run(self, out, threaded, step_end='03/08/2016 06:00'):
        vars_to_set = {'PathOut': '$(PathRoot)/' + out, 'DtSec': '86400',
                       'StepStart': '29/07/2016 06:00', 'StepEnd': step_end}
        vars_to_set.update(self._short_names())
        opts = ['repDischargeMaps', 'repStateMaps', 'repEndMaps', 'repWIndex', 'repWaterUse']
        if threaded:
            opts.append('outputThreads')
        settings = setoptions(self.settings_file, opts_to_set=opts,
                              opts_to_unset=['writeNetcdf', 'writeNetcdfStack'],
                              vars_to_set=vars_to_set)
        path = os.path.join(self.case_dir, out)
        shutil.rmtree(path, ignore_errors=True)
        mk_path_out(path)
        lisfloodexe(settings)
        return path

    @staticmethod
    def _map_files(directory):
        return sorted(f for f in os.listdir(directory)
                      if f[-4:].isdigit() or '.' in f and f.split('.')[-1].isdigit())

    @classmethod
    def _assert_dirs_equal(cls, sync_dir, thr_dir):
        import numpy as np
        from pcraster import readmap, pcr2numpy
        maps_sync, maps_thr = cls._map_files(sync_dir), cls._map_files(thr_dir)
        assert maps_sync, 'no PCRaster step maps produced'
        assert maps_sync == maps_thr, set(maps_sync) ^ set(maps_thr)
        for fname in maps_sync:
            a = pcr2numpy(readmap(os.path.join(sync_dir, fname)), -9999)
            b = pcr2numpy(readmap(os.path.join(thr_dir, fname)), -9999)
            assert np.array_equal(a, b), f'{fname} differs between sync and threaded'

    def teardown_method(self):
        for out in (self.out_sync, self.out_thr):
            shutil.rmtree(os.path.join(self.case_dir, out), ignore_errors=True)

    def test_pcraster_threaded_matches_sync(self):
        import numpy as np
        from pcraster import readmap, pcr2numpy
        sync_dir = self._run(self.out_sync, threaded=False)
        thr_dir = self._run(self.out_thr, threaded=True)
        maps_sync = sorted(f for f in os.listdir(sync_dir) if f[-4:].isdigit() or '.' in f and f.split('.')[-1].isdigit())
        maps_thr = sorted(f for f in os.listdir(thr_dir) if f[-4:].isdigit() or '.' in f and f.split('.')[-1].isdigit())
        assert maps_sync, 'no PCRaster step maps produced'
        assert maps_sync == maps_thr, set(maps_sync) ^ set(maps_thr)
        # Every reported step (first and last included) must be present for a per-step map.
        assert any(f.startswith('dis') and f.endswith('.056') for f in maps_sync)
        suffixes = {f[-3:] for f in maps_sync}
        assert {'056', '057', '058', '059', '060', '061'} <= suffixes
        # Monthly maps exist only at the month-end step (31/07/2016 = step 058),
        # end-of-run maps only at the last step (061).
        assert any(f.startswith('IrSh') and f.endswith('.058') for f in maps_sync)
        assert not any(f.startswith('IrSh') and not f.endswith('.058') for f in maps_sync)
        assert any(f.startswith('m006') and f.endswith('.061') for f in maps_sync)
        for fname in maps_sync:
            a = pcr2numpy(readmap(os.path.join(sync_dir, fname)), -9999)
            b = pcr2numpy(readmap(os.path.join(thr_dir, fname)), -9999)
            assert np.array_equal(a, b), f'{fname} differs between sync and threaded'

    @pytest.mark.slow
    def test_pcraster_threaded_stress_repeated(self):
        """Longer run, threaded 3 times: every repetition must equal the
        synchronous output (looks for nondeterministic races between workers
        reporting concurrently)."""
        step_end = '12/08/2016 06:00'
        sync_dir = self._run(self.out_sync, threaded=False, step_end=step_end)
        for _ in range(3):
            thr_dir = self._run(self.out_thr, threaded=True, step_end=step_end)
            self._assert_dirs_equal(sync_dir, thr_dir)
