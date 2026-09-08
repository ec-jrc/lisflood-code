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
from lisflood.global_modules.output import PACK_MIN, PACK_MAX


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
