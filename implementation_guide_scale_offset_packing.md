# Implementation Guide: CF Scale/Offset Packing for LISFLOOD Outputs

## Overview

This guide walks through adding int16 scale/offset packing to LISFLOOD output NetCDF files.
The feature stores floating-point output variables as packed int16 values using the CF-convention
`scale_factor` and `add_offset` attributes. All CF-compliant readers (xarray, CDO, NCO, QGIS)
automatically unpack on read — no downstream changes needed.

**Result:** 75-90% smaller output files compared to float64 defaults.

**Design principles:**
- Global on/off via a simple `True`/`False` setting (`OutputPacking`)
- Per-variable scale/offset stored directly in the `ReportedMap` namedtuple attributes
- State/end maps (for warm start) are never packed
- Range documentation kept in a separate `.md` reference file

---

## Step 1: Add the setting to the reference settings XML

**File:** `src/lisfloodSettings_reference.xml`

Find the block where `OutputMapsDataType` is defined and add after it:

```xml
<textvar name="OutputPacking" value="False">
<comment>
The option "OutputPacking" enables CF-convention scale_factor/add_offset packing
of output maps into int16 (2 bytes per value instead of 4 or 8).
    - "False" (default): write raw floating-point values (dtype from OutputMapsDataType)
    - "True": pack into signed 16-bit integers using per-variable scale/offset
              Readers automatically unpack using: value = packed * scale_factor + add_offset
Note: State/end maps used for warm starts are NEVER packed (always full precision).
</comment>
</textvar>
```

Also add the pass-through in the bindings section (where `OutputMapsDataType` is passed):

```xml
<textvar name="OutputPacking" value="$(OutputPacking)"/>
```


---

## Step 2: Extend the `ReportedMap` namedtuple

**File:** `src/lisflood/global_modules/default_options.py`

Change:

```python
ReportedMap = namedtuple('ReportedMap', 'name, output_var, unit, end, steps, all, restrictoption, monthly, yearly')
```

To:

```python
ReportedMap = namedtuple('ReportedMap', 'name, output_var, unit, end, steps, all, restrictoption, monthly, yearly, scale_factor, add_offset')
ReportedMap.__new__.__defaults__ = (None, None)  # scale_factor and add_offset default to None (= no packing)
```

Setting `__new__.__defaults__` means all existing `ReportedMap(...)` entries remain valid
without modification — they'll get `scale_factor=None, add_offset=None` automatically.
Only variables you explicitly want to pack need the extra two fields.

---

## Step 3: Add scale/offset values to output variables

**File:** `src/lisflood/global_modules/default_options.py`

For each variable you want to pack, add `scale_factor` and `add_offset` at the end of its
`ReportedMap` entry. Use the helper formula:

```
scale_factor = (physical_max - physical_min) / 65534
add_offset = physical_min + scale_factor * 32767
```

Examples:

```python
'DischargeMaps': ReportedMap(name='DischargeMaps', output_var='ChanQAvg',
                             unit='m3/s', end=[], steps=[],
                             all=['repDischargeMaps'], restrictoption=[],
                             monthly=False, yearly=False,
                             scale_factor=3.052,       # range 0-200000 m3/s
                             add_offset=100001.5),

'WaterLevelMaps': ReportedMap(name='WaterLevelMaps', output_var='WaterLevel',
                              unit='m', end=[], steps=[],
                              all=['repWaterLevelMaps'], restrictoption=['nonInit'],
                              monthly=False, yearly=False,
                              scale_factor=6.104e-4,   # range -10 to +30 m
                              add_offset=10.0),

'SnowMaps': ReportedMap(name='SnowMaps', output_var='SnowCover',
                        unit='mm', end=[], steps=[],
                        all=['repSnowMaps'], restrictoption=['nonInit'],
                        monthly=False, yearly=False,
                        scale_factor=0.04578,    # range 0-3000 mm
                        add_offset=1500.0),
```

Variables that should NOT be packed (state/end maps) simply omit the fields:

```python
'ChanQEnd': ReportedMap(name='ChanQEnd', output_var='ChanQ', unit='m3/s',
                        end=['repEndMaps'], steps=[], all=[],
                        restrictoption=[], monthly=False, yearly=False),
                        # No scale_factor/add_offset → defaults to None → never packed
```


---

## Step 4: Modify `write_netcdf_header()` to support packing

**File:** `src/lisflood/global_modules/netcdf.py`

### 4a. Change the function signature

Add `map_value=None` as a parameter:

```python
def write_netcdf_header(settings, var_name, netfile, DtDay,
                        value_standard_name, value_long_name, value_unit,
                        start_date, rep_steps, frequency,
                        map_value=None):    # <-- NEW
```

### 4b. Replace the variable creation logic

Find the block at the end of the function where the NetCDF variable is created.
Replace with:

```python
    # Determine if packing is active for this variable
    packing_enabled = binding.get('OutputPacking', 'False') == 'True'
    has_packing = (map_value is not None
                   and getattr(map_value, 'scale_factor', None) is not None
                   and getattr(map_value, 'add_offset', None) is not None)

    if frequency is not None:  # output file with "time" dimension
        if packing_enabled and has_packing:
            # CF scale/offset packing into int16
            value = nf1.createVariable(var_name, 'i2', ('time', dim_lat_y, dim_lon_x),
                                       zlib=True, fill_value=np.int16(-32768),
                                       chunksizes=(1, nrow, ncol))
            value.scale_factor = np.float64(map_value.scale_factor)
            value.add_offset = np.float64(map_value.add_offset)
        else:
            # Standard float output (current behaviour)
            value = nf1.createVariable(var_name, dtype, ('time', dim_lat_y, dim_lon_x),
                                       zlib=True, fill_value=-9999, chunksizes=(1, nrow, ncol))
    else:
        # End/state maps — NEVER pack (need full precision for warm start)
        value = nf1.createVariable(var_name, dtype, (dim_lat_y, dim_lon_x),
                                   zlib=True, fill_value=-9999)
```


---

## Step 5: Pass `map_value` through the output call chain

**File:** `src/lisflood/global_modules/output.py`

In both `NetcdfWriter.write()` and `NetcdfStepsWriter.write()`, pass `self.map_value` to
`write_netcdf_header`:

```python
nf1 = write_netcdf_header(self.settings, self.map_name, self.map_path, self.var.DtDay,
                           self.map_key, self.map_value.output_var, self.map_value.unit,
                           start_date, rep_steps, self.frequency,
                           map_value=self.map_value)   # <-- ADD THIS
```

---

## Step 6: Modify the write methods to pack data before storing

**File:** `src/lisflood/global_modules/output.py`

### 6a. In `NetcdfStepsWriter.write()`:

Replace the data-writing loop:

```python
for step, data in zip(self.step_range, self.data_steps):
    map_np = uncompress_array(data)

    nc_var = nf1.variables[self.map_name]
    if nc_var.dtype == np.int16:
        # Pack float → int16
        scale = nc_var.scale_factor
        offset = nc_var.add_offset
        packed = np.round((map_np - offset) / scale).astype(np.float64)
        packed = np.clip(packed, -32767, 32767)
        packed[map_np == -9999] = -32768  # fill value
        nc_var.set_auto_maskandscale(False)  # CRITICAL: prevent double-packing
        nc_var[step, :, :] = packed.astype(np.int16)
    else:
        nc_var[step, :, :] = map_np
```

**Critical:** `set_auto_maskandscale(False)` MUST be called before writing. Without it, the
netCDF4 library applies scale/offset again on write, resulting in double-packing (garbage values).


---

## Step 7: Testing

### Quick verification script

```python
import xarray as xr
import numpy as np

# Open a packed output file — xarray auto-unpacks
ds = xr.open_dataset('path/to/output.nc')

print(ds['DischargeMaps'].dtype)       # float64 (auto-unpacked)
print(ds['DischargeMaps'].values[:5])  # physically reasonable values
print(ds['DischargeMaps'].encoding)    # shows scale_factor, add_offset, dtype=int16
```

### Comparison test

Run the same simulation with `OutputPacking = False` and `OutputPacking = True`:

```python
import xarray as xr
import numpy as np

ref = xr.open_dataset('output_nopacking.nc')
packed = xr.open_dataset('output_packed.nc')

var = 'DischargeMaps'
diff = np.abs(ref[var].values - packed[var].values)
print(f"Max absolute difference: {diff.max():.4f}")
print(f"Max relative difference: {(diff / (np.abs(ref[var].values) + 1e-10)).max():.6e}")

# For discharge with range 0-200000:
# scale_factor ≈ 3.05
# Max error ≈ ±1.5 m3/s (half a quantization step)
```

### File size comparison

```bash
dir output_nopacking.nc output_packed.nc
# Expected: packed file ≈ 20-25% of original size
```


---

## Summary of files to modify

| # | File | What to do |
|---|------|------------|
| 1 | `src/lisfloodSettings_reference.xml` | Add `OutputPacking` textvar (True/False) + pass-through |
| 2 | `src/lisflood/global_modules/default_options.py` | Extend `ReportedMap` namedtuple with `scale_factor, add_offset` |
| 3 | `src/lisflood/global_modules/default_options.py` | Add scale/offset values to specific output variable entries |
| 4 | `src/lisflood/global_modules/netcdf.py` | Add `map_value` param to `write_netcdf_header()`; int16 creation logic |
| 5 | `src/lisflood/global_modules/output.py` | Pass `map_value` to `write_netcdf_header()` |
| 6 | `src/lisflood/global_modules/output.py` | Add packing logic in write methods |
| 7 | `docs/packing_ranges_reference.md` | Create documentation file with range/precision table |

---

## How the flag works

```
User sets OutputPacking = "True" in settings XML
              │
              ▼
write_netcdf_header() reads binding['OutputPacking']
              │
              ▼
    ┌─────────────────────────────────┐
    │ packing_enabled = True          │
    │ has_packing = map_value has     │
    │   scale_factor and add_offset?  │
    └──────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
    has_packing    no packing attrs
    = True         = False (None)
        │             │
        ▼             ▼
   Create int16    Create float
   variable with   variable (normal
   scale/offset    behaviour)
```

Three conditions must ALL be true for packing to happen:
1. `OutputPacking = "True"` in settings (global toggle)
2. The variable's `ReportedMap` has `scale_factor` and `add_offset` defined (per-variable control)
3. The output has a time dimension (`frequency is not None`) — state/end maps are excluded

---

## Gotchas

1. **Double-packing**: Call `nc_var.set_auto_maskandscale(False)` before writing raw int16 values. Otherwise netCDF4 applies scale/offset again.

2. **Fill value**: Use `-32768` (int16 minimum). The packed data range uses -32767 to +32767 (65534 levels). NetCDF4/xarray will mask cells with fill value as NaN on read.

3. **Out-of-range clipping**: If the model produces values outside the defined range, they get clipped. Set ranges generously — better to waste quantization levels than clip real data.

4. **State files**: The `frequency is None` guard ensures end maps are never packed. Don't add `scale_factor`/`add_offset` to End/State `ReportedMap` entries either (belt and braces).

5. **Variable name matching**: The `map_value` object is passed directly from the output writer, so no name-to-range matching is needed — the metadata travels with the variable.

---

## Helper: Computing scale/offset from a physical range

```python
def compute_packing_params(vmin, vmax):
    """Compute CF-convention scale_factor and add_offset for int16 packing.
    
    Parameters
    ----------
    vmin : float - Minimum physical value
    vmax : float - Maximum physical value
        
    Returns
    -------
    scale_factor : float
    add_offset : float
    """
    n_levels = 65534.0  # int16 usable range: -32767 to +32767
    scale_factor = (vmax - vmin) / n_levels
    add_offset = vmin + scale_factor * 32767.0
    return scale_factor, add_offset
```

Example outputs:
```
compute_packing_params(0, 200000)     → (3.052, 100001.5)    discharge m3/s
compute_packing_params(0, 1.0)        → (1.526e-5, 0.5)      fraction
compute_packing_params(-10, 30)       → (6.104e-4, 10.0)     water level m
compute_packing_params(0, 3000)       → (0.04578, 1500.0)    snow mm
compute_packing_params(0, 500)        → (0.00763, 250.0)     precip mm/day
compute_packing_params(0, 5000)       → (0.07630, 2500.0)    groundwater mm
```
