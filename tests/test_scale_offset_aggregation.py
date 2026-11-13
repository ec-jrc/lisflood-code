"""
Tests for the scale/offset packing and temporal aggregation features.

These tests verify that:
1. Output maps produced with int16 scale/offset packing are equivalent to
   float outputs within the expected quantization tolerance.
2. Aggregated (monthly mean/sum) outputs match the result of aggregating
   the daily time-step outputs after the fact.
"""
from __future__ import absolute_import

import os
import shutil
import datetime

import numpy as np
import pytest
from netCDF4 import Dataset

from lisflood.main import lisfloodexe
from lisflood.global_modules.default_options import default_options
from lisflood.global_modules.output import (
    PACK_MIN, PACK_MAX, PACK_FILL,
    LOG_PACK_QMIN, LOG_PACK_QMAX, LOG_PACK_MIN, LOG_PACK_SCALE, LOG_PACK_ATTRS,
    pack_discharge_log, unpack_discharge_log,
)
from lisflood.global_modules.settings import LisSettings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_data_var(ds):
    """Find the main data variable in a netCDF4 Dataset (the 3D variable)."""
    for name in ds.variables:
        var = ds.variables[name]
        if len(var.dimensions) == 3:
            return name
    # fallback: return first variable that is not a dimension or projection
    dims = set(ds.dimensions.keys())
    skip = dims | {'laea', 'lambert_azimuthal_equal_area'}
    for name in ds.variables:
        if name not in skip:
            return name
    raise ValueError(f"No data variable found in {ds.filepath()}")

def setoptions_with_new_vars(settings_file, opts_to_set=None, opts_to_unset=None,
                             vars_to_set=None, new_vars=None):
    """Extended version of setoptions that can inject NEW textvar entries.

    Parameters
    ----------
    settings_file : str
        Path to XML settings template.
    opts_to_set / opts_to_unset : list of str
        Options to enable/disable.
    vars_to_set : dict
        Existing textvars to modify (name -> value).
    new_vars : dict
        New textvars to inject (name -> value). They are added to the first
        <lfuser> section if not already present.
    """
    import uuid
    from bs4 import BeautifulSoup
    from lxml import etree
    from lisflood.global_modules.settings import LisSettings, Singleton
    from lisflood.global_modules.errors import LisfloodError

    if isinstance(opts_to_set, str):
        opts_to_set = [opts_to_set]
    if isinstance(opts_to_unset, str):
        opts_to_unset = [opts_to_unset]

    opts_to_set = [] if opts_to_set is None else opts_to_set
    opts_to_unset = [] if opts_to_unset is None else opts_to_unset
    vars_to_set = {} if vars_to_set is None else vars_to_set
    new_vars = {} if new_vars is None else new_vars

    with open(settings_file) as filetocheck:
        etree.parse(filetocheck)

    with open(settings_file) as tpl:
        soup = BeautifulSoup(tpl, 'lxml-xml')

        # Set/unset options
        lfoptions = soup.find('lfoptions')
        for opt in opts_to_set:
            tag = soup.find("setoption", {'name': opt})
            if tag:
                tag['choice'] = '1'
            elif lfoptions:
                # Option not in XML — inject it
                new_tag = soup.new_tag("setoption", attrs={'name': opt, 'choice': '1'})
                lfoptions.append(new_tag)
        for opt in opts_to_unset:
            tag = soup.find("setoption", {'name': opt})
            if tag:
                tag['choice'] = '0'
            elif lfoptions:
                new_tag = soup.new_tag("setoption", attrs={'name': opt, 'choice': '0'})
                lfoptions.append(new_tag)

        # Modify existing textvars
        for textvar, value in vars_to_set.items():
            for tag in soup.find_all("textvar", {'name': textvar}):
                tag['value'] = value
                break

        # Inject new textvars (add to both <lfuser> and <lfbinding> sections)
        if new_vars:
            lfuser = soup.find('lfuser')
            lfbinding = soup.find('lfbinding')
            for name, value in new_vars.items():
                # Add/update in lfuser
                if lfuser:
                    existing = lfuser.find("textvar", {'name': name})
                    if existing:
                        existing['value'] = value
                    else:
                        new_tag = soup.new_tag("textvar", attrs={'name': name, 'value': value})
                        lfuser.append(new_tag)
                # Add/update in lfbinding (this is where the model reads bindings from)
                if lfbinding:
                    existing = lfbinding.find("textvar", {'name': name})
                    if existing:
                        existing['value'] = value
                    else:
                        new_tag = soup.new_tag("textvar", attrs={'name': name, 'value': value})
                        lfbinding.append(new_tag)

    # Write temporary settings file
    uid = uuid.uuid4()
    filename = os.path.join(os.path.dirname(settings_file),
                            './{}_{}.xml'.format(os.path.basename(settings_file), uid))
    with open(filename, 'w') as dest:
        dest.write(soup.prettify())
    try:
        Singleton._instances = {}
        Singleton._current = {}
        settings = LisSettings(filename)
        options = settings.options
        for opt in opts_to_set:
            options[opt] = True
        for opt in opts_to_unset:
            options[opt] = False
    except LisfloodError as e:
        raise e
    finally:
        os.unlink(filename)
    return settings


def read_nc_variable(nc_path, var_name=None):
    """Read the data variable from a NetCDF file.

    Returns
    -------
    data : np.ndarray
        The data array (auto-unscaled by netCDF4 library). Masked/fill values become NaN.
    var_name : str
        Name of the variable read.
    """
    with Dataset(nc_path, 'r') as ds:
        if var_name is None:
            var_name = _find_data_var(ds)
        var = ds.variables[var_name]
        data = var[:]
    # Convert masked arrays to float with NaN for masked/fill values
    if hasattr(data, 'filled'):
        data = data.filled(np.nan).astype(np.float64)
    else:
        data = np.array(data, dtype=np.float64)
    # Also treat legacy -9999 fill values as NaN
    data[data == -9999.0] = np.nan
    return data, var_name


def get_nc_packing_info(nc_path, var_name=None):
    """Get packing metadata from a NetCDF file.

    Returns
    -------
    dict with keys: dtype, scale_factor, add_offset (or None if not packed)
    """
    with Dataset(nc_path, 'r') as ds:
        ds.set_auto_maskandscale(False)
        if var_name is None:
            var_name = _find_data_var(ds)
        var = ds.variables[var_name]
        ncattrs = var.ncattrs()
        info = {
            'dtype': var.dtype,
            'scale_factor': var.getncattr('scale_factor') if 'scale_factor' in ncattrs else None,
            'add_offset': var.getncattr('add_offset') if 'add_offset' in ncattrs else None,
        }
    return info


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestScaleOffsetPacking:
    """Test that int16 scale/offset packing produces outputs equivalent to float."""

    case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_ETRS89_UseCase')
    settings_file = os.path.join(case_dir, 'settings', 'full.xml')

    # Variables to test: these have scale_factor/add_offset defined
    # and use simple report options available in the test catchment.
    # Theta1Maps: scale_factor=1.526e-5, add_offset=0.5 (range 0-1)
    # Using repThetaMaps which produces Theta1Maps

    def _run_lisflood(self, output_dir, packing=False, dt_sec='86400',
                      step_start='30/07/2016 06:00', step_end='05/08/2016 06:00',
                      opts_to_set=None, opts_to_unset=None, new_vars=None):
        """Run lisflood with specified settings and return output path."""
        full_out_dir = os.path.join(self.case_dir, 'out', output_dir)
        if os.path.exists(full_out_dir):
            shutil.rmtree(full_out_dir, ignore_errors=True)
        os.makedirs(full_out_dir, exist_ok=True)

        base_opts_set = list(opts_to_set or [])
        base_opts_unset = list(opts_to_unset or [])
        base_new_vars = dict(new_vars or {})

        # Configure packing
        if packing:
            base_new_vars['OutputPacking'] = 'True'
        else:
            base_new_vars['OutputPacking'] = 'False'

        settings = setoptions_with_new_vars(
            self.settings_file,
            opts_to_set=base_opts_set,
            opts_to_unset=base_opts_unset,
            vars_to_set={
                'StepStart': step_start,
                'StepEnd': step_end,
                'DtSec': dt_sec,
                'PathOut': full_out_dir,
            },
            new_vars=base_new_vars,
        )
        lisfloodexe(settings)
        return full_out_dir

    def test_packing_all_variables(self):
        """All variables with scale_factor/add_offset should match float output within tolerance.

        Dynamically discovers all packed variables from default_options and checks
        every one that the model produces in this configuration.
        """
        # Enable as many report options as possible to produce packed variables
        opts = [
            'repThetaMaps', 'repThetaForestMaps', 'repThetaIrrigationMaps',
            'repE2O2', 'repUZMaps', 'repGwPercUZLZMaps',
            'repSnowMaps', 'repSnowCoverMaps', 'repSnowMeltMaps',
            'repDischargeMaps', 'repSurfaceRunoffMaps',
            'repFastRunoffMaps', 'repInfiltrationMaps', 'repInterceptionMaps',
            'repTotalRunoffMaps', 'repWaterDepthMaps',
            'repESActMaps', 'repETActMaps', 'repETRefMaps', 'repEWIntMaps',
            'repTaMaps', 'repRainMaps', 'repPrefFlowMaps',
            'repSeepSubToGWMaps', 'repUZOutflowMaps',
        ]

        # Run without packing (float64 output)
        out_float = self._run_lisflood(
            'test_packing_float',
            packing=False,
            opts_to_set=opts,
        )

        # Run with packing (int16 output)
        out_packed = self._run_lisflood(
            'test_packing_int16',
            packing=True,
            opts_to_set=opts,
        )

        # Build lookup: all variables that have scale_factor defined
        reportedmaps = default_options['reportedmaps']
        packed_vars = {
            name: rm for name, rm in reportedmaps.items()
            if getattr(rm, 'scale_factor', None) is not None
        }

        checked_count = 0

        for filename in sorted(os.listdir(out_packed)):
            if not filename.endswith('.nc'):
                continue

            nc_float = os.path.join(out_float, filename)
            nc_packed = os.path.join(out_packed, filename)

            if not os.path.exists(nc_float):
                continue

            info_packed = get_nc_packing_info(nc_packed)
            if info_packed['dtype'] != np.dtype('int16'):
                continue  # not packed, skip

            # Get tolerance from the file's own scale_factor/add_offset attributes
            scale_factor = info_packed['scale_factor']
            add_offset = info_packed['add_offset']

            data_float, _ = read_nc_variable(nc_float)
            data_packed, _ = read_nc_variable(nc_packed)

            valid = ~np.isnan(data_float) & ~np.isnan(data_packed)
            if not valid.any():
                continue

            # Assert no valid float values are outside the packing range
            pack_min = add_offset + scale_factor * PACK_MIN
            pack_max = add_offset + scale_factor * PACK_MAX
            out_of_range = valid & ((data_float < pack_min) | (data_float > pack_max))
            assert not out_of_range.any(), \
                f"{filename}: {out_of_range.sum()} values outside packing range " \
                f"[{pack_min:.4g}, {pack_max:.4g}]. Scale/offset parameters need adjustment."

            # Compare packed vs float within quantization tolerance
            tolerance = scale_factor  # full step tolerance
            max_diff = np.max(np.abs(data_float[valid] - data_packed[valid]))
            assert max_diff <= tolerance, \
                f"Max difference {max_diff} exceeds tolerance {tolerance} for {filename}"
            checked_count += 1

        assert checked_count > 0, "No packed variables were checked"

    @pytest.mark.parametrize('threaded', [False, True])
    def test_packing_unpacked_map_not_corrupted(self, threaded):
        """A reported map that carries no scale_factor/add_offset (e.g.
        DischargeMaps 'dis') must be written as real float data when
        OutputPacking=True, not replaced by the int16 fill value.

        The on-disk variable dtype is chosen by the NetCDF header and the
        per-step packing is chosen by the writer; both decisions must treat a
        missing scale_factor/add_offset as "not packed". If they disagree for a
        map without packing metadata, the writer packs into an int16 buffer that
        is then written into a plain float variable as all-fill. This asserts
        the written map holds real discharge instead.

        Checked under both the synchronous and threaded writers, which share the
        same packing decision in NetcdfStepsWriter.write().
        """
        # DischargeMaps ('dis') has scale_factor=None/add_offset=None.
        assert getattr(default_options['reportedmaps']['DischargeMaps'],
                       'scale_factor', None) is None, \
            "test premise broken: DischargeMaps now carries packing metadata"

        opts = ['repDischargeMaps']
        thr = ['outputThreads'] if threaded else None

        out_float = self._run_lisflood(
            'test_packing_unpacked_float', packing=False, opts_to_set=opts)
        out_packed = self._run_lisflood(
            'test_packing_unpacked_int16', packing=True,
            opts_to_set=(opts + (thr or [])))

        fdis = os.path.join(out_float, 'dis.nc')
        pdis = os.path.join(out_packed, 'dis.nc')
        assert os.path.exists(fdis) and os.path.exists(pdis), \
            f"dis.nc missing (float={os.path.exists(fdis)} packed={os.path.exists(pdis)})"

        # Raw read of the packed file (no auto-unscale) to catch an all-fill map.
        with Dataset(pdis, 'r') as ds:
            vname = _find_data_var(ds)
            raw = ds.variables[vname][:]
            raw = np.asarray(raw.filled(raw.fill_value) if hasattr(raw, 'filled') else raw)
        n_fill = int((raw == float(PACK_FILL)).sum())
        assert n_fill != raw.size, \
            f"dis.nc is entirely PACK_FILL ({PACK_FILL}): an unpacked map was " \
            f"written through the packing branch"

        # Physical values must match the non-packed float run (dis is unpacked,
        # so the two should agree closely; allow a tiny float32 margin).
        data_float, _ = read_nc_variable(fdis)
        data_packed, _ = read_nc_variable(pdis)
        valid = ~np.isnan(data_float) & ~np.isnan(data_packed)
        assert valid.any(), "no jointly-valid dis cells to compare"
        max_diff = np.max(np.abs(data_float[valid] - data_packed[valid]))
        rel = max_diff / max(np.max(np.abs(data_float[valid])), 1e-9)
        assert rel <= 1e-3, \
            f"packed dis differs from float dis (max abs {max_diff:.4g}, rel {rel:.4g})"

    def teardown_method(self):
        """Clean up output directories."""
        out_base = os.path.join(self.case_dir, 'out')
        if os.path.exists(out_base):
            for d in os.listdir(out_base):
                if d.startswith('test_packing_'):
                    shutil.rmtree(os.path.join(out_base, d), ignore_errors=True)


@pytest.mark.slow
class TestTemporalAggregation:
    """Test that temporal aggregation (monthly mean/sum) matches manual aggregation of daily outputs."""

    case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_ETRS89_UseCase')
    settings_file = os.path.join(case_dir, 'settings', 'full.xml')

    def _run_lisflood(self, output_dir, dt_sec='86400',
                      step_start='02/07/2016 06:00', step_end='01/09/2016 06:00',
                      opts_to_set=None, opts_to_unset=None, new_vars=None):
        """Run lisflood with specified settings."""
        full_out_dir = os.path.join(self.case_dir, 'out', output_dir)
        if os.path.exists(full_out_dir):
            shutil.rmtree(full_out_dir, ignore_errors=True)
        os.makedirs(full_out_dir, exist_ok=True)

        base_opts_set = list(opts_to_set or [])
        base_opts_unset = list(opts_to_unset or [])
        base_new_vars = dict(new_vars or {})

        settings = setoptions_with_new_vars(
            self.settings_file,
            opts_to_set=base_opts_set,
            opts_to_unset=base_opts_unset,
            vars_to_set={
                'StepStart': step_start,
                'StepEnd': step_end,
                'DtSec': dt_sec,
                'PathOut': full_out_dir,
            },
            new_vars=base_new_vars,
        )
        lisfloodexe(settings)
        return full_out_dir

    @pytest.mark.parametrize("frequency,operation", [
        ("monthly", "mean"),
        ("monthly", "sum"),
        ("yearly", "mean"),
        ("yearly", "sum"),
    ])
    def test_temporal_aggregation(self, frequency, operation):
        """Temporal aggregation should match manual aggregation of daily outputs.

        Dynamically discovers all variables with scale_factor from default_options,
        enables their report options, and verifies that the aggregated output
        matches the manually computed aggregation from daily outputs.

        The aggregation writes at period boundaries (month-end or year-end),
        so only complete periods produce output.
        """
        # Choose time range: monthly needs ~2 months, yearly needs >1 year
        if frequency == 'monthly':
            step_start = '02/07/2016 06:00'
            step_end = '01/09/2016 06:00'
        else:  # yearly
            step_start = '02/01/2016 06:00'
            step_end = '02/01/2017 06:00'
        # Build list of all report options that produce packed variables
        reportedmaps = default_options['reportedmaps']
        packed_vars = {
            name: rm for name, rm in reportedmaps.items()
            if getattr(rm, "scale_factor", None) is not None and rm.all and not rm.steps
        }
        # Collect all report options needed
        all_report_opts = set()
        for rm in packed_vars.values():
            all_report_opts.update(rm.all)
        all_report_opts.discard('')
        opts = list(all_report_opts)

        # Build semicolon-separated list of all packed variable names for aggregation
        agg_var_list = ';'.join(packed_vars.keys())

        # Select the aggregation setting key
        agg_setting = f'Output{frequency.capitalize()}{operation.capitalize()}'

        # Run with daily all-steps output (no aggregation)
        out_daily = self._run_lisflood(
            f'test_agg_{frequency}_{operation}_daily',
            step_start=step_start,
            step_end=step_end,
            opts_to_set=opts,
            new_vars={
                'OutputPacking': 'False',
                'OutputMonthlyMean': '',
                'OutputMonthlySum': '',
                'OutputYearlyMean': '',
                'OutputYearlySum': '',
            },
        )

        # Run with temporal aggregation for all packed variables
        out_agg = self._run_lisflood(
            f'test_agg_{frequency}_{operation}_agg',
            step_start=step_start,
            step_end=step_end,
            opts_to_set=opts,
            new_vars={
                'OutputPacking': 'False',
                'OutputMonthlyMean': agg_var_list if agg_setting == 'OutputMonthlyMean' else '',
                'OutputMonthlySum': agg_var_list if agg_setting == 'OutputMonthlySum' else '',
                'OutputYearlyMean': agg_var_list if agg_setting == 'OutputYearlyMean' else '',
                'OutputYearlySum': agg_var_list if agg_setting == 'OutputYearlySum' else '',
            },
        )

        # Aggregation function for manual computation
        agg_func = np.nanmean if operation == 'mean' else np.nansum

        checked_count = 0
        for filename in sorted(os.listdir(out_agg)):
            if not filename.endswith('.nc'):
                continue

            nc_daily_path = os.path.join(out_daily, filename)
            nc_agg_path = os.path.join(out_agg, filename)

            if not os.path.exists(nc_daily_path):
                continue

            # Load daily data
            with Dataset(nc_daily_path, 'r') as ds:
                time_var = ds.variables['time']
                times = time_var[:]
                time_units = time_var.units
                calendar = time_var.calendar

                from netCDF4 import num2date
                dates = num2date(times, time_units, calendar)

                var_name = _find_data_var(ds)
                daily_data = ds.variables[var_name][:]

            # Convert to float with NaN for masked values
            if hasattr(daily_data, 'filled'):
                daily_data = daily_data.filled(np.nan).astype(np.float64)
            daily_data[daily_data == -9999.0] = np.nan

            # Group daily data by period (month or year)
            dt_day = 1
            period_groups = {}
            for i, d in enumerate(dates):
                if frequency == 'monthly':
                    period_key = (d.year, d.month)
                else:
                    period_key = d.year
                if period_key not in period_groups:
                    period_groups[period_key] = []
                period_groups[period_key].append(daily_data[i])

            # Only keep completed periods (boundary reached)
            completed_periods = set()
            for i, d in enumerate(dates):
                next_d = d + datetime.timedelta(days=dt_day)
                if frequency == 'monthly':
                    if d.month != next_d.month:
                        completed_periods.add((d.year, d.month))
                else:
                    if d.year != next_d.year:
                        completed_periods.add(d.year)

            # Compute aggregation for each completed period
            manual_agg = []
            for key in sorted(completed_periods):
                stack = np.array(period_groups[key])
                manual_agg.append(agg_func(stack, axis=0))
            manual_agg = np.array(manual_agg)

            # Read aggregated output
            data_agg, _ = read_nc_variable(nc_agg_path)

            # Only compare if the aggregated output has fewer time steps than daily
            # (confirms aggregation actually happened for this variable)
            if data_agg.shape[0] >= daily_data.shape[0]:
                continue

            if data_agg.shape != manual_agg.shape:
                continue

            valid = ~np.isnan(manual_agg) & ~np.isnan(data_agg)
            if not valid.any():
                continue

            # Compare: absolute tolerance for mean, relative for sum
            if operation == 'mean':
                max_diff = np.max(np.abs(data_agg[valid] - manual_agg[valid]))
                assert max_diff < 1e-6, \
                    f"{filename}: {frequency} {operation} max difference {max_diff} exceeds tolerance 1e-6"
            else:
                max_rel_diff = np.max(np.abs(
                    (data_agg[valid] - manual_agg[valid]) /
                    np.where(manual_agg[valid] != 0, manual_agg[valid], 1.0)
                ))
                assert max_rel_diff < 1e-5, \
                    f"{filename}: {frequency} {operation} max relative difference {max_rel_diff} exceeds tolerance 1e-5"
            checked_count += 1

        assert checked_count > 0, f"No aggregated variables were checked for {frequency} {operation}"

    @pytest.mark.parametrize("operation", ["mean", "sum"])
    def test_daily_aggregation_subdaily(self, operation):
        """Daily aggregation of a SUB-DAILY run must equal the manual daily
        aggregation of the within-day steps.

        Runs at DtSec=21600 (6-hourly, 4 steps/day) and checks that
        OutputDaily{Mean,Sum} writes one slice per calendar day equal to the
        mean/sum of that day's 4 sub-daily steps. This is the behaviour that is
        impossible with the pre-existing monthly/yearly-only aggregation.
        """
        # ~3 days of 6-hourly steps; start at 00:00 so each day has its full 4 steps
        step_start = '02/07/2016 00:00'
        step_end = '05/07/2016 00:00'

        reportedmaps = default_options['reportedmaps']
        packed_vars = {
            name: rm for name, rm in reportedmaps.items()
            if getattr(rm, "scale_factor", None) is not None and rm.all and not rm.steps
        }
        all_report_opts = set()
        for rm in packed_vars.values():
            all_report_opts.update(rm.all)
        all_report_opts.discard('')
        opts = list(all_report_opts)

        agg_var_list = ';'.join(packed_vars.keys())
        agg_setting = 'OutputDailyMean' if operation == 'mean' else 'OutputDailySum'

        # Sub-daily all-steps output (no aggregation) -> 4 slices/day reference
        out_subdaily = self._run_lisflood(
            f'test_agg_daily_{operation}_subdaily',
            dt_sec='21600',
            step_start=step_start,
            step_end=step_end,
            opts_to_set=opts,
            new_vars={
                'OutputPacking': 'False',
                'OutputDailyMean': '',
                'OutputDailySum': '',
                'OutputMonthlyMean': '',
                'OutputMonthlySum': '',
                'OutputYearlyMean': '',
                'OutputYearlySum': '',
            },
        )

        # Same run with daily aggregation enabled
        out_agg = self._run_lisflood(
            f'test_agg_daily_{operation}_agg',
            dt_sec='21600',
            step_start=step_start,
            step_end=step_end,
            opts_to_set=opts,
            new_vars={
                'OutputPacking': 'False',
                'OutputDailyMean': agg_var_list if agg_setting == 'OutputDailyMean' else '',
                'OutputDailySum': agg_var_list if agg_setting == 'OutputDailySum' else '',
                'OutputMonthlyMean': '',
                'OutputMonthlySum': '',
                'OutputYearlyMean': '',
                'OutputYearlySum': '',
            },
        )

        agg_func = np.nanmean if operation == 'mean' else np.nansum

        checked_count = 0
        for filename in sorted(os.listdir(out_agg)):
            if not filename.endswith('.nc'):
                continue
            nc_sub_path = os.path.join(out_subdaily, filename)
            nc_agg_path = os.path.join(out_agg, filename)
            if not os.path.exists(nc_sub_path):
                continue

            with Dataset(nc_sub_path, 'r') as ds:
                time_var = ds.variables['time']
                times = time_var[:]
                from netCDF4 import num2date
                dates = num2date(times, time_var.units, time_var.calendar)
                var_name = _find_data_var(ds)
                sub_data = ds.variables[var_name][:]

            if hasattr(sub_data, 'filled'):
                sub_data = sub_data.filled(np.nan).astype(np.float64)
            sub_data[sub_data == -9999.0] = np.nan

            # Group sub-daily steps by calendar day
            period_groups = {}
            for i, d in enumerate(dates):
                key = (d.year, d.month, d.day)
                period_groups.setdefault(key, []).append(sub_data[i])

            # Only days whose boundary (day change) is crossed within the run
            dt_day = 0.25
            completed = set()
            for i, d in enumerate(dates):
                next_d = d + datetime.timedelta(days=dt_day)
                if d.day != next_d.day:
                    completed.add((d.year, d.month, d.day))

            manual_agg = np.array([agg_func(np.array(period_groups[k]), axis=0)
                                   for k in sorted(completed)])

            data_agg, _ = read_nc_variable(nc_agg_path)

            # Confirm aggregation actually reduced the step count
            if data_agg.shape[0] >= sub_data.shape[0]:
                continue
            if data_agg.shape != manual_agg.shape:
                continue

            valid = ~np.isnan(manual_agg) & ~np.isnan(data_agg)
            if not valid.any():
                continue

            if operation == 'mean':
                max_diff = np.max(np.abs(data_agg[valid] - manual_agg[valid]))
                assert max_diff < 1e-6, \
                    f"{filename}: daily {operation} max difference {max_diff} exceeds tolerance 1e-6"
            else:
                max_rel_diff = np.max(np.abs(
                    (data_agg[valid] - manual_agg[valid]) /
                    np.where(manual_agg[valid] != 0, manual_agg[valid], 1.0)
                ))
                assert max_rel_diff < 1e-5, \
                    f"{filename}: daily {operation} max relative difference {max_rel_diff} exceeds tolerance 1e-5"
            checked_count += 1

        assert checked_count > 0, f"No daily-aggregated variables were checked for {operation}"

    @pytest.mark.parametrize("operation", ["mean", "sum"])
    def test_daily_aggregation_subdaily_unpacked(self, operation):
        """Daily aggregation must also work for UNPACKED variables.

        The packed-variable tests select only reportedmaps entries that carry
        scale_factor/add_offset. Variables WITHOUT packing metadata (e.g.
        DischargeMaps, TavgMapsOut, FrostIndexMaps) go through a different
        branch of the writer (is_packed / has_packing predicates), and their
        aggregated output must (a) be produced, (b) stay unpacked float, and
        (c) equal the manual daily mean/sum of the sub-daily steps.
        """
        # ~3 days of 6-hourly steps; start at 00:00 so each day has its full 4 steps
        step_start = '02/07/2016 00:00'
        step_end = '05/07/2016 00:00'

        reportedmaps = default_options['reportedmaps']
        # Curated set of unpacked ('all'-type) variables: core quantities whose
        # report options are simple flags and whose output_var is always
        # computed in the EFAS use case.
        target_names = ('DischargeMaps', 'TavgMapsOut', 'FrostIndexMaps')
        unpacked_vars = {
            name: rm for name, rm in reportedmaps.items()
            if getattr(rm, "scale_factor", None) is None and rm.all and not rm.steps
            and name in target_names
        }
        assert set(unpacked_vars) == set(target_names), \
            f"Expected unpacked target variables missing from reportedmaps: " \
            f"{set(target_names) - set(unpacked_vars)}"

        all_report_opts = set()
        for rm in unpacked_vars.values():
            all_report_opts.update(rm.all)
        all_report_opts.discard('')
        opts = list(all_report_opts)

        agg_var_list = ';'.join(unpacked_vars.keys())
        agg_setting = 'OutputDailyMean' if operation == 'mean' else 'OutputDailySum'

        # Sub-daily all-steps output (no aggregation) -> 4 slices/day reference
        out_subdaily = self._run_lisflood(
            f'test_agg_daily_{operation}_unpacked_subdaily',
            dt_sec='21600',
            step_start=step_start,
            step_end=step_end,
            opts_to_set=opts,
            new_vars={
                'OutputPacking': 'False',
                'OutputDailyMean': '',
                'OutputDailySum': '',
                'OutputMonthlyMean': '',
                'OutputMonthlySum': '',
                'OutputYearlyMean': '',
                'OutputYearlySum': '',
            },
        )

        # Same run with daily aggregation enabled
        out_agg = self._run_lisflood(
            f'test_agg_daily_{operation}_unpacked_agg',
            dt_sec='21600',
            step_start=step_start,
            step_end=step_end,
            opts_to_set=opts,
            new_vars={
                'OutputPacking': 'False',
                'OutputDailyMean': agg_var_list if agg_setting == 'OutputDailyMean' else '',
                'OutputDailySum': agg_var_list if agg_setting == 'OutputDailySum' else '',
                'OutputMonthlyMean': '',
                'OutputMonthlySum': '',
                'OutputYearlyMean': '',
                'OutputYearlySum': '',
            },
        )

        checked_count = 0
        for var_name in unpacked_vars:
            checked_count += self._check_unpacked_daily_agg(
                operation, var_name, out_subdaily, out_agg)

        assert checked_count == len(unpacked_vars), \
            f"Only {checked_count}/{len(unpacked_vars)} unpacked variables were checked for {operation}"

    def _check_unpacked_daily_agg(self, operation, var_name, out_subdaily, out_agg):
        """Compare one unpacked variable's aggregated output against the manual
        daily aggregation of its sub-daily steps. Returns 1 when checked."""
        from netCDF4 import num2date

        filename = os.path.basename(LisSettings.instance().binding[var_name]) + '.nc'
        nc_sub_path = os.path.join(out_subdaily, filename)
        nc_agg_path = os.path.join(out_agg, filename)
        assert os.path.exists(nc_agg_path), \
            f"Aggregated output missing for unpacked variable {var_name}: {nc_agg_path}"
        if not os.path.exists(nc_sub_path):
            return 0

        with Dataset(nc_sub_path, 'r') as ds:
            time_var = ds.variables['time']
            times = time_var[:]
            dates = num2date(times, time_var.units, time_var.calendar)
            var_name_nc = _find_data_var(ds)
            sub_data = ds.variables[var_name_nc][:]

        if hasattr(sub_data, 'filled'):
            sub_data = sub_data.filled(np.nan).astype(np.float64)
        sub_data[sub_data == -9999.0] = np.nan

        # Group sub-daily steps by calendar day
        period_groups = {}
        for i, d in enumerate(dates):
            key = (d.year, d.month, d.day)
            period_groups.setdefault(key, []).append(sub_data[i])

        # Only days whose boundary (day change) is crossed within the run
        dt_day = 0.25
        completed = set()
        for i, d in enumerate(dates):
            next_d = d + datetime.timedelta(days=dt_day)
            if d.day != next_d.day:
                completed.add((d.year, d.month, d.day))

        agg_func = np.nanmean if operation == 'mean' else np.nansum
        manual_agg = np.array([agg_func(np.array(period_groups[k]), axis=0)
                               for k in sorted(completed)])

        data_agg, _ = read_nc_variable(nc_agg_path)

        # Unpacked output must stay float (no int16 packing)
        info = get_nc_packing_info(nc_agg_path)
        assert info['dtype'] != np.dtype('int16'), \
            f"{filename}: unpacked variable must NOT be int16-packed"

        # Confirm aggregation actually reduced the step count
        assert data_agg.shape[0] < sub_data.shape[0], \
            f"{filename}: aggregation did not reduce the step count " \
            f"({data_agg.shape[0]} >= {sub_data.shape[0]})"
        assert data_agg.shape == manual_agg.shape, \
            f"{filename}: aggregated shape {data_agg.shape} != manual {manual_agg.shape}"

        valid = ~np.isnan(manual_agg) & ~np.isnan(data_agg)
        assert valid.any(), f"{filename}: no valid values to compare"

        if operation == 'mean':
            max_diff = np.max(np.abs(data_agg[valid] - manual_agg[valid]))
            assert max_diff < 1e-6, \
                f"{filename}: daily {operation} (unpacked) max difference {max_diff} exceeds tolerance 1e-6"
        else:
            max_rel_diff = np.max(np.abs(
                (data_agg[valid] - manual_agg[valid]) /
                np.where(manual_agg[valid] != 0, manual_agg[valid], 1.0)
            ))
            assert max_rel_diff < 1e-5, \
                f"{filename}: daily {operation} (unpacked) max relative difference {max_rel_diff} exceeds tolerance 1e-5"
        return 1

    def test_daily_run_monthly_aggregation_ends_on_period_boundary(self):
        """Regression: a DAILY run ending exactly on a month+year boundary with
        monthly aggregation must not crash with 'NetCDF: Index exceeds dimension
        bound'.

        Previously the output time axis for aggregates was pre-sized by an
        independent month/year-end filter in write_netcdf_header, while
        MapOutputAggregated decided flushes from CalendarDate boundaries. When the
        two counts diverged (e.g. a run ending on Dec 31, crossing a year boundary
        during monthly aggregation) the writer wrote one slice past the fixed axis
        and crashed on the very last write. The axis is now unlimited and each
        flushed slice writes its own time coordinate, so #time-coords always
        equals #data-slices.

        The variable is reported BOTH per-step (repLZMaps) and as a monthly mean,
        mirroring the configuration that triggered the crash, and packing is on.
        """
        step_start = '02/01/2016 06:00'
        step_end = '31/12/2016 06:00'   # ends on month + year boundary

        out_dir = self._run_lisflood(
            'test_agg_daily_boundary',
            dt_sec='86400',
            step_start=step_start,
            step_end=step_end,
            opts_to_set=['repLZMaps', 'repE2O2'],
            new_vars={
                'OutputPacking': 'True',
                'OutputMonthlyMean': 'LZMaps',
                'OutputMonthlySum': '',
                'OutputYearlyMean': '',
                'OutputYearlySum': '',
            },
        )

        # The run must complete and produce lz.nc (crash would have aborted it).
        nc_path = os.path.join(out_dir, 'lz.nc')
        assert os.path.exists(nc_path), f"Output not found (run likely crashed): {nc_path}"

        # 2016 is a leap year; Jan 2 .. Dec 31 contains all 12 month-ends, so the
        # monthly-mean file must hold exactly 12 time slices, each with a finite
        # time coordinate (no leftover fill from a pre-sized axis).
        with Dataset(nc_path, 'r') as ds:
            tvar = ds.variables['time']
            n_time = tvar.shape[0]
            tvals = np.asarray(tvar[:], dtype=np.float64)
            vname = _find_data_var(ds)
            data_shape = ds.variables[vname].shape
        assert n_time == 12, f"expected 12 monthly slices, got {n_time}"
        assert data_shape[0] == n_time, \
            f"data slices ({data_shape[0]}) != time coords ({n_time})"
        assert np.all(np.isfinite(tvals)), "time axis has non-finite (unfilled) coordinates"

    def test_aggregation_sum_disables_packing(self):
        """Sum-aggregated outputs should NOT use int16 packing even when OutputPacking=True.

        Monthly/yearly sums can exceed the int16 range calibrated for daily values,
        so packing is disabled for sum aggregates.
        """
        out_dir = self._run_lisflood(
            'test_agg_no_packing',
            step_start='02/07/2016 06:00',
            step_end='01/09/2016 06:00',
            opts_to_set=['repThetaMaps', 'repE2O2'],
            new_vars={
                'OutputPacking': 'True',
                'OutputMonthlyMean': '',
                'OutputMonthlySum': 'Theta1Maps',
                'OutputYearlyMean': '',
                'OutputYearlySum': '',
            },
        )

        nc_path = os.path.join(out_dir, 'tha.nc')
        assert os.path.exists(nc_path), f"Output not found: {nc_path}"

        info = get_nc_packing_info(nc_path)
        # Sum-aggregated outputs should remain float (not packed)
        assert info['dtype'] != np.dtype('int16'), \
            "Sum-aggregated output should NOT be int16-packed"
        assert info['scale_factor'] is None, \
            "Sum-aggregated output should not have scale_factor attribute"

    def teardown_method(self):
        """Clean up output directories."""
        out_base = os.path.join(self.case_dir, 'out')
        if os.path.exists(out_base):
            for d in os.listdir(out_base):
                if d.startswith('test_agg_'):
                    shutil.rmtree(os.path.join(out_base, d), ignore_errors=True)


# ---------------------------------------------------------------------------
# Logarithmic discharge packing (OutputPackingDischarge)
# ---------------------------------------------------------------------------

class TestDischargeLogPackRoundtrip:
    """Unit tests for the pure log10 pack/unpack functions.

    These exercise pack_discharge_log / unpack_discharge_log directly (no model
    run), so they are fast and run anywhere. They verify the three defining
    properties of the encoding: (near) constant RELATIVE precision across the
    whole resolved range, clipping of out-of-range values, and that
    zero/negative/NaN/sub-minimum values map to the fill value (read back as
    NaN).
    """

    def test_roundtrip_relative_precision(self):
        """Values in [QMIN, QMAX] survive a pack/unpack round-trip within the
        quantization step, i.e. roughly constant relative precision."""
        # Sample the whole dynamic range geometrically (constant ratio spacing)
        q = np.logspace(np.log10(LOG_PACK_QMIN), np.log10(LOG_PACK_QMAX), 2000)

        packed = pack_discharge_log(q)
        assert packed.dtype == np.int16
        back = unpack_discharge_log(packed)

        assert np.all(np.isfinite(back)), "all in-range values must round-trip to finite"

        # One quantization step in log space is LOG_PACK_SCALE; the worst-case
        # relative error of a single rounding step is therefore bounded by
        # 10**(LOG_PACK_SCALE/2) - 1. Allow a hair of slack for float noise.
        step_rel = 10.0 ** (LOG_PACK_SCALE / 2.0) - 1.0
        rel_err = np.abs(back - q) / q
        assert rel_err.max() <= step_rel * 1.05, \
            f"max relative error {rel_err.max():.3e} exceeds one half-step {step_rel:.3e}"

    def test_fill_for_nonpositive_and_subminimum(self):
        """Zero, negatives, the -9999 sentinel, NaN, and values below QMIN all
        pack to PACK_FILL and unpack to NaN."""
        q = np.array([0.0, -1.0, -9999.0, np.nan, LOG_PACK_QMIN * 0.5], dtype=np.float64)
        packed = pack_discharge_log(q)
        assert np.all(packed == PACK_FILL), \
            "non-positive / sub-minimum / NaN discharge must map to PACK_FILL"
        back = unpack_discharge_log(packed)
        assert np.all(np.isnan(back)), "fill values must unpack to NaN"

    def test_clipping_above_qmax(self):
        """Values above QMAX are clipped to the maximum code (not wrapped) and
        decode to ~QMAX."""
        q = np.array([LOG_PACK_QMAX, LOG_PACK_QMAX * 10.0, 1e9], dtype=np.float64)
        packed = pack_discharge_log(q)
        assert np.all(packed == PACK_MAX), "values >= QMAX must clip to PACK_MAX"
        back = unpack_discharge_log(packed)
        # Decoded value of PACK_MAX is exactly QMAX (to float precision)
        assert np.allclose(back, LOG_PACK_QMAX, rtol=1e-6)

    def test_endpoints_map_to_code_range(self):
        """QMIN and QMAX map to the ends of the usable int16 range."""
        packed = pack_discharge_log(np.array([LOG_PACK_QMIN, LOG_PACK_QMAX]))
        assert packed[0] == PACK_MIN
        assert packed[1] == PACK_MAX


@pytest.mark.slow
class TestDischargeLogPacking:
    """Integration test: a model run with OutputPackingDischarge=True must write
    discharge as an int16 variable carrying the custom log10 packing attributes,
    which decode back to the float discharge within the expected relative
    tolerance. OutputPackingDischarge is completely independent of OutputPacking.
    """

    case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_ETRS89_UseCase')
    settings_file = os.path.join(case_dir, 'settings', 'full.xml')

    def _run_lisflood(self, output_dir, dt_sec='86400',
                      step_start='30/07/2016 06:00', step_end='05/08/2016 06:00',
                      opts_to_set=None, new_vars=None):
        """Run lisflood and return the output directory."""
        full_out_dir = os.path.join(self.case_dir, 'out', output_dir)
        if os.path.exists(full_out_dir):
            shutil.rmtree(full_out_dir, ignore_errors=True)
        os.makedirs(full_out_dir, exist_ok=True)

        settings = setoptions_with_new_vars(
            self.settings_file,
            opts_to_set=list(opts_to_set or []),
            vars_to_set={
                'StepStart': step_start,
                'StepEnd': step_end,
                'DtSec': dt_sec,
                'PathOut': full_out_dir,
            },
            new_vars=dict(new_vars or {}),
        )
        lisfloodexe(settings)
        return full_out_dir

    def test_discharge_log_packing_roundtrip(self):
        """dis.nc written with OutputPackingDischarge=True is int16 + log attrs,
        decodes (via unpack_discharge_log) to the float-run discharge within the
        encoding's relative precision, and leaves OTHER linearly-packable maps
        untouched (the two packing schemes are independent)."""
        opts = ['repDischargeMaps']

        # Reference run: no packing at all (float discharge).
        out_float = self._run_lisflood(
            'test_logpack_float',
            opts_to_set=opts,
            new_vars={'OutputPacking': 'False', 'OutputPackingDischarge': 'False'},
        )

        # Log-packed discharge, standard linear packing OFF (prove independence).
        out_logpacked = self._run_lisflood(
            'test_logpack_int16',
            opts_to_set=opts,
            new_vars={'OutputPacking': 'False', 'OutputPackingDischarge': 'True'},
        )

        fdis = os.path.join(out_float, 'dis.nc')
        pdis = os.path.join(out_logpacked, 'dis.nc')
        assert os.path.exists(fdis) and os.path.exists(pdis), \
            f"dis.nc missing (float={os.path.exists(fdis)} logpacked={os.path.exists(pdis)})"

        # On-disk variable must be int16 and carry the custom log attributes,
        # NOT the CF scale_factor/add_offset (which would trigger linear decode).
        with Dataset(pdis, 'r') as ds:
            ds.set_auto_maskandscale(False)
            vname = _find_data_var(ds)
            var = ds.variables[vname]
            ncattrs = var.ncattrs()
            assert var.dtype == np.dtype('int16'), \
                f"log-packed discharge must be int16, got {var.dtype}"
            assert var.getncattr('packing') == LOG_PACK_ATTRS['packing'], \
                "log-packed discharge must carry packing='log10'"
            for attr in ('packing_log_min', 'packing_log_scale', 'packing_int_offset',
                         'packing_valid_min', 'packing_valid_max'):
                assert attr in ncattrs, f"missing custom log-packing attribute '{attr}'"
            assert 'scale_factor' not in ncattrs and 'add_offset' not in ncattrs, \
                "log-packed discharge must NOT carry CF scale_factor/add_offset"
            raw = np.asarray(var[:])

        # The file must not be entirely fill: a real catchment has resolvable
        # discharge somewhere.
        assert int((raw == float(PACK_FILL)).sum()) != raw.size, \
            "dis.nc is entirely PACK_FILL - no discharge was packed"

        # Decode the raw int16 with the documented inverse transform and compare
        # to the float run. Only cells that are resolvable in BOTH (float >= QMIN
        # and not fill) are comparable; the log scheme intentionally drops
        # discharge below QMIN to fill.
        decoded = unpack_discharge_log(raw)
        data_float, _ = read_nc_variable(fdis)

        comparable = (~np.isnan(decoded) & ~np.isnan(data_float)
                      & (data_float >= LOG_PACK_QMIN) & (data_float <= LOG_PACK_QMAX))
        assert comparable.any(), "no jointly-resolvable discharge cells to compare"

        rel_err = np.abs(decoded[comparable] - data_float[comparable]) / data_float[comparable]
        # One half-step of relative quantization error, with a small margin.
        step_rel = 10.0 ** (LOG_PACK_SCALE / 2.0) - 1.0
        assert rel_err.max() <= step_rel * 1.05, \
            f"decoded discharge max relative error {rel_err.max():.3e} exceeds " \
            f"the log-packing half-step {step_rel:.3e}"

        # Sub-QMIN float discharge must have been stored as fill (dropped).
        dropped = (~np.isnan(data_float)) & (data_float < LOG_PACK_QMIN)
        if dropped.any():
            assert np.all(raw[dropped] == PACK_FILL), \
                "discharge below QMIN must be stored as PACK_FILL"

    def test_independent_of_linear_packing(self):
        """OutputPackingDischarge must not require OutputPacking: enabling only
        the discharge log packing still produces an int16 log-packed dis.nc."""
        out_dir = self._run_lisflood(
            'test_logpack_only',
            opts_to_set=['repDischargeMaps'],
            new_vars={'OutputPacking': 'False', 'OutputPackingDischarge': 'True'},
        )
        pdis = os.path.join(out_dir, 'dis.nc')
        assert os.path.exists(pdis), f"dis.nc missing: {pdis}"
        info = get_nc_packing_info(pdis)
        assert info['dtype'] == np.dtype('int16'), \
            "discharge log packing must apply even with OutputPacking=False"
        assert info['scale_factor'] is None, \
            "log-packed discharge must not use CF scale_factor"

    def teardown_method(self):
        """Clean up output directories."""
        out_base = os.path.join(self.case_dir, 'out')
        if os.path.exists(out_base):
            for d in os.listdir(out_base):
                if d.startswith('test_logpack_'):
                    shutil.rmtree(os.path.join(out_base, d), ignore_errors=True)
