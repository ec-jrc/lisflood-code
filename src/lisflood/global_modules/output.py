"""

Copyright 2019 European Union

Licensed under the EUPL, Version 1.2 or as soon they will be approved by the European Commission  subsequent versions of the EUPL (the "Licence");

You may not use this work except in compliance with the Licence.
You may obtain a copy of the Licence at:

https://joinup.ec.europa.eu/sites/default/files/inline-files/EUPL%20v1_2%20EN(1).txt

Unless required by applicable law or agreed to in writing, software distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and limitations under the Licence.

"""
import os
import datetime
import numpy as np
from pcraster import ifthen, catchmenttotal, mapmaximum, pcr2numpy
import sys
import warnings

from .zusatz import TimeoutputTimeseries
from .add1 import decompress, valuecell, loadmap, compressArray
from .netcdf import write_netcdf_header, iterOpenNetcdf, nanCheckMap, uncompress_array
from .netcdf import hdf5_lock as _hdf5_lock
from .errors import LisfloodFileError, LisfloodWarning
from .settings import inttodate, CDFFlags, LisSettings, MaskInfo
from netCDF4 import default_fillvals, date2num

# ------------------------------------------------------------------------
# Optional earthkit-hydro acceleration of the PCRaster reductions
# (opt-in via the `useEarthkitHydro` setoption; default False keeps the
# historical PCRaster path bit-identical). See earthkit_network.py.
# ------------------------------------------------------------------------
try:
    from .earthkit_network import (
        earthkit_available,
        get_earthkit_network,
        ek_upstream_sum,
        ek_upstream_sum_batch,
        ek_upstream_mean,
        model_precision,
    )
except ImportError:  # pragma: no cover - earthkit-hydro not installed
    earthkit_available = staticmethod(lambda: False)
    get_earthkit_network = None
    ek_upstream_sum = None
    ek_upstream_sum_batch = None
    ek_upstream_mean = None

    def model_precision():
        from .parallelization import get_model_dtype
        return get_model_dtype()


# ------------------------------------------------------------------------
# Packing constants for int16 CF scale/offset encoding
# ------------------------------------------------------------------------
PACK_FILL = np.int16(default_fillvals['i2'])      # -32767
# Keep PACK_MIN / PACK_MAX as plain Python ints: arithmetic between np.int16
# scalars silently overflows under numpy 2.x NEP 50 semantics (e.g.
# PACK_MAX - PACK_MIN wraps to -3), which would corrupt derived quantities such
# as LOG_PACK_SCALE below. Python ints are unbounded, so the span is exact, and
# they still broadcast/clip correctly against int16 arrays.
PACK_MIN = int(PACK_FILL) + 1                     # -32766
PACK_MAX = int(np.iinfo(np.int16).max)            #  32767

# ------------------------------------------------------------------------
# Logarithmic int16 packing for discharge (OutputPackingDischarge)
# ------------------------------------------------------------------------
# Discharge spans several orders of magnitude on a global domain, so the
# linear CF scale/offset packing used for the other variables would lose too
# much precision. Instead we pack log10(discharge) linearly into int16, which
# gives (near) constant RELATIVE precision across the whole range.
#
# This is a NON-CF encoding: readers cannot auto-decode it via the standard
# scale_factor/add_offset attributes. Instead, the writer tags the variable
# with explicit custom attributes (see LOG_PACK_ATTRS below) describing the
# transform so a decoder can invert it:
#
#     stored = round((log10(q) - LOG_PACK_MIN) / LOG_PACK_SCALE) + PACK_MIN
#     q      = 10 ** (LOG_PACK_MIN + LOG_PACK_SCALE * (stored - PACK_MIN))
#
# Discharge values below LOG_PACK_QMIN (0.01 m3/s) -- including zero and
# negatives -- carry no useful information at this precision and are stored as
# _FillValue (read back as masked). Values above LOG_PACK_QMAX are clipped.
LOG_PACK_QMIN = 0.01        # m3/s, smallest resolved discharge
LOG_PACK_QMAX = 500000.0    # m3/s, largest resolved discharge
LOG_PACK_MIN = np.log10(LOG_PACK_QMIN)   # -2.0
LOG_PACK_MAX = np.log10(LOG_PACK_QMAX)   # ~5.69897
# Map [LOG_PACK_MIN, LOG_PACK_MAX] onto the usable int16 range
# [PACK_MIN, PACK_MAX] (PACK_FILL is reserved as _FillValue).
LOG_PACK_SCALE = (LOG_PACK_MAX - LOG_PACK_MIN) / float(PACK_MAX - PACK_MIN)

# Custom attributes written on a log-packed discharge variable so downstream
# tooling can invert the transform. These are NOT CF scale_factor/add_offset.
LOG_PACK_ATTRS = {
    'packing': 'log10',
    'packing_log_min': np.float64(LOG_PACK_MIN),
    'packing_log_scale': np.float64(LOG_PACK_SCALE),
    'packing_int_offset': np.float64(PACK_MIN),
    'packing_valid_min': np.float64(LOG_PACK_QMIN),
    'packing_valid_max': np.float64(LOG_PACK_QMAX),
}


def pack_discharge_log(values):
    """Pack a discharge array (float, physical m3/s) into int16 log space.

    Parameters
    ----------
    values : numpy.ndarray
        Discharge values in m3/s. May contain NaN / fill (-9999) / non-positive
        entries; all of those are stored as PACK_FILL.

    Returns
    -------
    numpy.ndarray (int16)
        Log-packed discharge, same shape as `values`.
    """
    q = np.asarray(values, dtype=np.float64)
    # Resolvable cells: finite and >= the minimum resolved discharge. Zero,
    # negative, NaN, and the -9999 sentinel all fall out here and become fill.
    resolved = np.isfinite(q) & (q >= LOG_PACK_QMIN)

    packed = np.full(q.shape, PACK_FILL, dtype=np.int16)
    if resolved.any():
        qr = np.clip(q[resolved], LOG_PACK_QMIN, LOG_PACK_QMAX)
        idx = np.round((np.log10(qr) - LOG_PACK_MIN) / LOG_PACK_SCALE) + PACK_MIN
        idx = np.clip(idx, PACK_MIN, PACK_MAX)
        packed[resolved] = idx.astype(np.int16)
    return packed


def unpack_discharge_log(packed):
    """Invert :func:`pack_discharge_log`.

    Parameters
    ----------
    packed : numpy.ndarray (int16)
        Log-packed discharge as produced by `pack_discharge_log`.

    Returns
    -------
    numpy.ndarray (float64)
        Discharge in m3/s. Fill cells are returned as NaN.
    """
    stored = np.asarray(packed)
    out = np.full(stored.shape, np.nan, dtype=np.float64)
    valid = stored != PACK_FILL
    if valid.any():
        exponent = LOG_PACK_MIN + LOG_PACK_SCALE * (stored[valid].astype(np.float64) - PACK_MIN)
        out[valid] = np.power(10.0, exponent)
    return out

# ------------------------------------------------------------------------
# Writer classes
# ------------------------------------------------------------------------
class Writer():
    """ Abstract writer class
    """

    def stage(self, map_data):
        """ Registers the output data and store it in the object for future write
            Implemented here as the staging depends on the type of outputs
        """
        raise NotImplementedError

    def write(self, start_date, rep_steps):
        """ Write the staged data

        Parameters
        ----------
        start_date : datetime.datetime object
            Start date to write in the output file
        rep_steps : list
            List of steps to write
        """
        raise NotImplementedError

    def _extract_map(self):
        """ Private, extracts the output map from the variable (self.var) object
        """
        what = 'self.var.' + self.map_value.output_var
        try:
            map_data = eval(what)
        except:
            map_data = None
            raise Exception(f'ERROR! {self.map_value.output_var} could not be found for outputs. \
            Variable needs to be initialised in the initial() function of the relevant hydrological module')

        return np.copy(map_data)


class NetcdfWriter(Writer):
    """ Main NetCDF writer class, handles single step outputs
    """

    def __init__(self, var, map_key, map_value, map_path, frequency=None):

        self.settings = LisSettings.instance()

        self.var = var

        self.map_key = map_key
        self.map_value = map_value
        self.map_path = map_path
        self.map_name = os.path.basename(self.map_path)
        self.map_path = map_path+'.nc'

        self.frequency = frequency

        self.data = None

    def stage(self):
        self.data = self._extract_map()
        flags = self.settings.flags
        if flags['nancheck']:
            nanCheckMap(self.data, self.map_name, self.map_key)
    
    def write(self, start_date, rep_steps):
        if self.data is not None:
            # HDF5 lock only around the actual netCDF4 calls (open/header,
            # slice write, close); everything else is pure numpy and runs
            # outside the lock so writer threads can overlap on it.
            with _hdf5_lock:
                nf1 = write_netcdf_header(self.settings, self.map_name, self.map_path, self.var.DtDay,
                                        self.map_key, self.map_value.output_var, self.map_value.unit,
                                        start_date, rep_steps, self.frequency, map_value=self.map_value)

            map_np = uncompress_array(self.data)

            with _hdf5_lock:
                nf1.variables[self.map_name][:, :] = map_np

                nf1.close()
        else:
            raise Exception('You need to stage the variable data before writing!')


class NetcdfStepsWriter(NetcdfWriter):
    """ Extension of the NetcdfWriter class to handle multiple steps outputs
    """

    def __init__(self, var, map_key, map_value, map_path, frequency, flag, end_step):

        self.settings = LisSettings.instance()
        binding = self.settings.binding

        self.flag = flag
        self.chunks = int(binding['OutputMapsChunks'])
        self.end_step = end_step
        self.step_range = []
        self.data_steps = []
        # Per-slice time coordinates for temporal AGGREGATES only. Left empty for
        # every-step ('all') outputs, whose time axis is fixed and pre-written by
        # write_netcdf_header. MapOutputAggregated appends one stamp per flushed
        # period here so the writer can grow the (unlimited) time axis in lock-
        # step with the data slices - guaranteeing #time-coords == #data-slices.
        self.time_stamps = []
        # Set True by MapOutputAggregated for monthly/yearly SUM aggregates to
        # suppress the logarithmic discharge packing (those sums can exceed the
        # calibrated range). Daily sums and mean aggregates leave it False.
        self.log_pack_disabled = False

        super().__init__(var, map_key, map_value, map_path, frequency)

    def _checkpoint(self):
        """ Private, makes sure this is the right time to write
        """
        write = False
        end_run = self.var.currentTimeStep() == self.end_step
        if len(self.data_steps) == self.chunks or end_run:
            write = True
        return write

    def stage(self):
        map_np = self._extract_map()

        cdfflags = CDFFlags.instance()
        step = cdfflags[self.flag]

        flags = LisSettings.instance().flags
        if flags['nancheck']:
            nanCheckMap(map_np, self.map_name, self.map_key)
    
        self.step_range.append(step)
        self.data_steps.append(map_np)

    def write(self, start_date, rep_steps):
        if self._checkpoint():
            if self.data_steps:
                # Pre-compute all packed arrays OUTSIDE the HDF5 lock: the int16
                # packing arithmetic (round/divide/clip/fill) is pure numpy and
                # is the expensive part of compressed output. Only the actual
                # netCDF4 calls (open/header, slice writes, close) are serialised.
                # `prepared_steps` is thread-local to this writer instance, and
                # the flush handshake guarantees one flush generation at a time
                # per file, so no cross-thread data race is possible here.
                # The packing parameters come from the staged step metadata and
                # are identical for every step of one flush, so they can be read
                # once before the loop. This mirrors exactly how
                # write_netcdf_header decides the variable dtype: packing is
                # int16 with CF scale/offset only when OutputPacking is enabled
                # AND the map_value carries scale_factor/add_offset (as float64,
                # matching the values stored in the header).
                packing_enabled = self.settings.binding.get('OutputPacking', 'False') == 'True'
                # Decide packing from the RAW scale_factor/add_offset, testing
                # for None BEFORE any coercion: np.float64(None) is nan, which
                # `is not None`, so coercing first would enable packing for maps
                # that carry no packing metadata. This predicate must stay
                # identical to write_netcdf_header's `has_packing` (netcdf.py) so
                # the on-disk variable dtype and the per-step packing decision
                # agree for every map.
                raw_scale = getattr(self.map_value, 'scale_factor', None) if self.map_value is not None else None
                raw_offset = getattr(self.map_value, 'add_offset', None) if self.map_value is not None else None
                is_packed = packing_enabled and raw_scale is not None and raw_offset is not None
                packed_scale = np.float64(raw_scale) if is_packed else None
                packed_offset = np.float64(raw_offset) if is_packed else None
                # Logarithmic discharge packing is a COMPLETELY separate opt-in
                # (OutputPackingDischarge), independent of OutputPacking above.
                # It only applies to the DischargeMaps output and uses the
                # custom log10 int16 encoding (pack_discharge_log), never the
                # linear CF scale/offset path. This predicate MUST stay in sync
                # with write_netcdf_header's `is_log_packed`.
                is_log_packed = (self.settings.binding.get('OutputPackingDischarge', 'False') == 'True'
                                 and self.map_key == 'DischargeMaps'
                                 and not self.log_pack_disabled)
                maskinfo = MaskInfo.instance()

                prepared_steps = []
                for step, data in zip(self.step_range, self.data_steps):
                    if is_log_packed:
                        # Pack BEFORE uncompressing (same rationale as the
                        # linear path): operate on the staged compressed
                        # in-domain vector so masking can never hide NaN.
                        map_in = np.ma.getdata(data).astype(np.float64)
                        packed_in = pack_discharge_log(map_in)
                        packed = np.full(maskinfo.info.shape, PACK_FILL, dtype=np.int16)
                        packed.reshape(-1)[~maskinfo.info.maskflat] = packed_in
                    elif is_packed:
                        # Pack BEFORE uncompressing: operate on the staged
                        # compressed in-domain vector (np.ma.getdata = the
                        # positional raw buffer, as a plain ndarray) so np.ma
                        # auto-masking can never hide NaN from the guard below
                        # (isnan ignores masked entries, while astype(int16)
                        # still casts the raw NaN buffer -> RuntimeWarning +
                        # silent 0). The int16 result is then scattered into a
                        # full-domain array pre-filled with PACK_FILL.
                        map_in = np.ma.getdata(data).astype(np.float64)
                        packed_in = np.round((map_in - packed_offset) / packed_scale)
                        clipped = ((packed_in < PACK_MIN) | (packed_in > PACK_MAX)) & (map_in != -9999)
                        if clipped.any():
                            vmin = packed_offset + packed_scale * PACK_MIN
                            vmax = packed_offset + packed_scale * PACK_MAX
                            warnings.warn(LisfloodWarning(
                                f"OutputPacking: {clipped.sum()} values in '{self.map_name}' outside "
                                f"packing range [{vmin:.4g}, {vmax:.4g}] and will be clipped."
                            ))
                        packed_in = np.clip(packed_in, PACK_MIN, PACK_MAX)
                        # NaN cannot be represented in int16: after the clip it
                        # would silently cast to 0 (i.e. read back as add_offset,
                        # a plausible but wrong value). Store the fill value
                        # instead, so those cells read back as masked, and warn
                        # so the run reports which maps contain non-finite data.
                        nonfinite = np.isnan(packed_in)
                        if nonfinite.any():
                            warnings.warn(LisfloodWarning(
                                f"OutputPacking: {nonfinite.sum()} non-finite (NaN) values in '{self.map_name}' "
                                f"cannot be packed and are stored as _FillValue."
                            ))
                            packed_in[nonfinite] = PACK_FILL
                        packed_in = packed_in.astype(np.int16)
                        # Scatter into the full domain, pre-filled with the
                        # packing fill value (outside-mask cells were written
                        # as PACK_FILL before, and their uninitialised buffer
                        # content never enters the arithmetic now).
                        packed = np.full(maskinfo.info.shape, PACK_FILL, dtype=np.int16)
                        packed.reshape(-1)[~maskinfo.info.maskflat] = packed_in
                    else:
                        map_np = uncompress_array(data)
                        # For non-packed: convert masked array to plain array with fill value
                        if hasattr(map_np, 'filled'):
                            map_np = map_np.filled(-9999)
                        packed = map_np
                    prepared_steps.append((step, packed))

                # HDF5 lock around the actual netCDF4 calls only
                with _hdf5_lock:
                    if self.step_range[0] == 0:
                        nf1 = write_netcdf_header(self.settings, self.map_name, self.map_path, self.var.DtDay,
                                                self.map_key, self.map_value.output_var, self.map_value.unit,
                                                start_date, rep_steps, self.frequency, map_value=self.map_value,
                                                log_packed=is_log_packed)
                    else:
                        nf1 = iterOpenNetcdf(self.map_path, "", 'a', format='NETCDF4')

                    nc_var = nf1.variables[self.map_name]
                    nc_var.set_auto_maskandscale(False)

                    for step, packed in prepared_steps:
                        nc_var[step, :, :] = packed

                    # Temporal aggregates grow an UNLIMITED time axis: write each
                    # flushed slice's own time coordinate so the number of time
                    # coords always equals the number of data slices (no fixed
                    # pre-sized axis to overflow). Non-aggregated writers leave
                    # time_stamps empty and skip this - their axis is pre-written
                    # by write_netcdf_header. Kept INSIDE the HDF5 lock because
                    # assigning past the current extent grows the unlimited
                    # dimension, an HDF5 state change that must not race with the
                    # threaded writers / forcing readers.
                    if self.time_stamps:
                        nc_time = nf1.variables['time']
                        for step, stamp in zip(self.step_range, self.time_stamps):
                            nc_time[step] = date2num(stamp, nc_time.units, nc_time.calendar)

                    nf1.close()

                self.step_range.clear()
                self.data_steps.clear()
                self.time_stamps.clear()
            else:
                raise Exception('You need to stage data before writing!')


class PCRasterWriter(Writer):
    """ Main PCRaster writer class
        Doesn't require another class to handle multiple steps as PCRaster doesn't support temporal metadata
        Writing outputs in temporal chunks not supported for PCRaster
    """

    def __init__(self, var, map_value, map_path):
        self.var = var
        self.map_value = map_value
        self.map_path = map_path
        self.data = None

    def stage(self):
        self.data = self._extract_map()

    def write(self, start_date, rep_steps):
        if self.data is not None:
            self.var.report(decompress(self.data), str(self.map_path))
        else:
            raise Exception('You need to stage data before writing!')


# ------------------------------------------------------------------------
# Map Output classes
# ------------------------------------------------------------------------
class MapOutput():
    """ Base output class, can't be used directly
        Stores the output parameters:
            - variable name and path
            - frequency of output
            - output path
            - writer object
    """

    def __init__(self, var, out_type, frequency, map_key, map_value):
        """ MapOutput Constructor
        
        Parameters
        ----------
        var : object
            Lisflood variable object
        out_type : str
            Output type (end, steps or all)
        frequency : str
            Output frequency (all, monthly or yearly) 
        map_key : str
            Output convention (typically CF) name 
        map_value : str
            Lisflood variable name  
        
        Returns
        -------
        object
            MapOutput object
        """

        self.settings = LisSettings.instance()
        option = self.settings.options

        self.var = var

        cdfflags = CDFFlags.instance()
        self.flag = cdfflags.get_flag(out_type, frequency)
        self.frequency = frequency

        self.map_key = map_key
        self.map_value = map_value
        self.map_path = self._extract_path()

        # staging data
        self.step = None

        if self.is_valid():
            if option['writeNetcdf'] or option['writeNetcdfStack']:
                if self.flag == 0:
                    self.writer = NetcdfWriter(self.var, self.map_key, self.map_value, self.map_path)
                else:
                    self.writer = NetcdfStepsWriter(self.var, self.map_key, self.map_value, self.map_path, self.frequency, self.flag, self._rep_steps[-1])
            else:  # PCRaster
                self.writer = PCRasterWriter(self.var, self.map_value, self.map_path)
    
    def _extract_path(self):
        """ Extracts output path from settings
        """
        binding = self.settings.binding
        # report end map filename
        if self.settings.mc_set:
            # MonteCarlo model
            map_path = os.path.join(str(self.var.currentSampleNumber()), binding[self.map_key].split("/")[-1])
        else:
            map_path = binding.get(self.map_key)
        return map_path
    
    def _output_checkpoint(self):
        """ Check if it's the right time to output
        """
        raise NotImplementedError

    @property
    def _start_date(self):
        """ Start data of the dataset
        """
        raise NotImplementedError

    @property
    def _rep_steps(self):
        """ Reporting steps
        """
        raise NotImplementedError

    def is_valid(self):
        """ Checks if output is valid (if path is not None)
        """
        valid = True
        if self.map_path is None:
            valid = False
        return valid
    
    def stage(self):
        """ Registers map for output at current step
        """
        self.step = self.var.currentTimeStep()
        if self._output_checkpoint():
            self.writer.stage()
    
    def write(self):
        """ Writes staged maps
        """
        if self._output_checkpoint():
            return self.writer.write(self._start_date, self._rep_steps)
    

class MapOutputEnd(MapOutput):
    """ Extension of the base MapOutput class for end files
    """

    def __init__(self, var, map_key, map_value):
        settings = LisSettings.instance()
        self.binding = settings.binding
        out_type = 'end'
        frequency = None
        super().__init__(var, out_type, frequency, map_key, map_value)
    
    def _output_checkpoint(self):
        check = self.step == self.var.nrTimeSteps()
        return check
    
    @property
    def _start_date(self):
        start_date = inttodate(self.step - 1, self.var.CalendarDayStart, self.binding)
        return start_date

    @property
    def _rep_steps(self):
        return None


class MapOutputSteps(MapOutput):
    """ Extension of the base MapOutput class for outputs at specific steps
    """

    def __init__(self, var, map_key, map_value, frequency):
        out_type = 'steps'
        if len(var.ReportSteps) > 0:
            self._start_date_val = var.CalendarDayStart
            self._rep_steps_val = var.ReportSteps
        super().__init__(var, out_type, frequency, map_key, map_value)
    
    def is_valid(self):
        valid = False
        if len(self.var.ReportSteps) > 0:
            valid = True
        return valid and super().is_valid()

    def _output_checkpoint(self):
        cdfflags = CDFFlags.instance()
        freq_check = cdfflags.frequency_check(self.var, self.frequency)
        check = (self.step in self.var.ReportSteps) and freq_check
        return check

    @property
    def _start_date(self):
        return self._start_date_val

    @property
    def _rep_steps(self):
        return self._rep_steps_val


class MapOutputAll(MapOutput):
    """ Extension of the base MapOutput class for outputs at all steps
    """

    def __init__(self, var, map_key, map_value, frequency):
        out_type = 'all'
        settings = LisSettings.instance()
        binding = settings.binding
        self._start_date_val = var.CalendarDayStart
        self._rep_steps_val = range(binding['StepStartInt'],binding['StepEndInt']+1)
        super().__init__(var, out_type, frequency, map_key, map_value)
    
    def _output_checkpoint(self):
        cdfflags = CDFFlags.instance()
        check = cdfflags.frequency_check(self.var, self.frequency)
        return check

    @property
    def _start_date(self):
        return self._start_date_val

    @property
    def _rep_steps(self):
        return self._rep_steps_val


class MapOutputAggregated(MapOutput):
    """Handles temporal aggregation (monthly/yearly mean/sum) for a variable."""

    def __init__(self, var, map_key, map_value, frequency, operation):
        out_type = 'all'  # accumulates every timestep
        settings = LisSettings.instance()
        binding = settings.binding
        self._start_date_val = var.CalendarDayStart
        self._rep_steps_val = range(binding['StepStartInt'], binding['StepEndInt'] + 1)
        
        self._operation = operation  # 'mean' or 'sum'
        self._accum_buffer = None
        self._accum_count = 0
        self._write_step = 0  # own step counter for NetCDF time dimension

        # Packing of SUM aggregates depends on the aggregation period:
        #  - MONTHLY / YEARLY sums accumulate many timesteps and overflow the
        #    int16 range that scale_factor/add_offset were calibrated for, so
        #    they are written UNPACKED (float), as originally.
        #  - DAILY sums stay close to the per-step value range (at most a few
        #    timesteps per day), so they keep int16 packing.
        # MEAN aggregates always keep packing (they stay in the per-step range).
        pack_disabled = (operation == 'sum' and frequency in ('monthly', 'yearly'))
        if pack_disabled:
            map_value_no_pack = map_value._replace(scale_factor=None, add_offset=None)
        else:
            map_value_no_pack = map_value

        super().__init__(var, out_type, frequency, map_key, map_value_no_pack)

        # Same reasoning for the independent logarithmic DISCHARGE packing: a
        # monthly/yearly SUM of discharge can exceed the calibrated log range
        # (max 500000 m3/s), so disable log packing for those. Daily sums and
        # mean aggregates keep it. The linear _replace() above cannot express
        # this (log packing does not use scale_factor/add_offset), so flag it
        # on the writer directly.
        if pack_disabled and hasattr(self, 'writer'):
            self.writer.log_pack_disabled = True

        # Force immediate write for aggregated outputs (one slice per period)
        if hasattr(self, 'writer') and hasattr(self.writer, 'chunks'):
            self.writer.chunks = 1
            
    def _output_checkpoint(self):
        """Always True — we accumulate every timestep."""
        return True

    @property
    def _start_date(self):
        return self._start_date_val

    @property
    def _rep_steps(self):
        return self._rep_steps_val

    def stage(self):
        """Accumulate instead of storing instantaneous values."""
        self.step = self.var.currentTimeStep()
        map_np = self.writer._extract_map()

        if self._accum_buffer is None:
            self._accum_buffer = np.zeros_like(map_np)

        self._accum_buffer += map_np
        self._accum_count += 1

    def write(self):
        """Write at each period boundary (day/month/year-end) and at end-of-run.

        A period is flushed when the next step crosses into a new day/month/year.
        The final step of the run is ALSO treated as a flush point so a run that
        stops mid-period still writes its last (partial) aggregate instead of
        silently dropping the accumulator. This is safe because the output time
        axis for aggregates is unlimited (see write_netcdf_header): the writer
        appends one time coordinate per flushed slice, so the count can never
        overflow regardless of how many periods there are.
        """
        current_date = self.var.CalendarDate
        next_date = current_date + datetime.timedelta(days=self.var.DtDay)
        if self.frequency == 'daily':
            is_boundary = current_date.day != next_date.day
        elif self.frequency == 'monthly':
            is_boundary = current_date.month != next_date.month
        elif self.frequency == 'yearly':
            is_boundary = current_date.year != next_date.year
        else:
            is_boundary = True

        # End-of-run also flushes the current (possibly partial) period. When the
        # last step happens to be a real boundary this stays a SINGLE flush (one
        # combined condition, no double write).
        is_last_step = self.var.currentTimeStep() == self.var.nrTimeSteps()

        if (is_boundary or is_last_step) and self._accum_buffer is not None:
            # Finalize
            if self._operation == 'mean':
                result = self._accum_buffer / self._accum_count
            else:  # sum
                result = self._accum_buffer

            # Stage the aggregated result into the writer, together with this
            # period's representative date (the boundary step's CalendarDate,
            # matching the historical *_end timestamp convention).
            self.writer.data_steps.append(result)
            self.writer.step_range.append(self._write_step)
            self.writer.time_stamps.append(current_date)
            self.writer.write(self._start_date, self._rep_steps)

            # Increment own step counter and reset accumulator
            self._write_step += 1
            self._accum_buffer = None
            self._accum_count = 0

# ------------------------------------------------------------------------
# Output factory
# ------------------------------------------------------------------------

class OutputMapsFactory():
    """ Handles all the maps outputs
        Registers them in dedicated lists at construction
        Loops the outputs and write them when write() called
    """

    def __init__(self, var):

        self.var = var

        settings = LisSettings.instance()

        report_maps_end = settings.report_maps_end
        report_maps_steps = settings.report_maps_steps
        report_maps_all = settings.report_maps_all

        outputs = []
        
        for map_key, map_value in report_maps_end.items():
            out = MapOutputEnd(var, map_key, map_value)
            if out.is_valid():
                outputs.append(out)

        for map_key, map_value in report_maps_steps.items():
            if map_value.monthly:
                out = MapOutputSteps(var, map_key, map_value, frequency='monthly')
            elif map_value.yearly:
                out = MapOutputSteps(var, map_key, map_value, frequency='yearly')
            else:
                out = MapOutputSteps(var, map_key, map_value, frequency='all')
            if out.is_valid():
                outputs.append(out)
            
        for map_key, map_value in report_maps_all.items():
            if map_value.monthly:
                out = MapOutputAll(var, map_key, map_value, frequency='monthly')
            elif map_value.yearly:
                out = MapOutputAll(var, map_key, map_value, frequency='yearly')
            else:
                out = MapOutputAll(var, map_key, map_value, frequency='all')
            if out.is_valid():
                outputs.append(out)

        # --- Temporal aggregation outputs ---
        binding = settings.binding
        aggregation_configs = {
            'OutputDailyMean': ('daily', 'mean'),
            'OutputDailySum': ('daily', 'sum'),
            'OutputMonthlyMean': ('monthly', 'mean'),
            'OutputMonthlySum': ('monthly', 'sum'),
            'OutputYearlyMean': ('yearly', 'mean'),
            'OutputYearlySum': ('yearly', 'sum'),
        }
        aggregated_vars = set()  # track which vars are aggregated

        # Match aggregation-list entries against ReportedMap.name, which is the
        # identifier used everywhere else in the output system: the per-step/all
        # outputs are keyed and path-resolved by rm.name (see
        # settings._reported_maps), and the output settings textvars are named
        # after rm.name too. The reportedmaps DICT KEY is only an internal dict
        # handle and for a few entries differs from rm.name (e.g. key
        # 'SeepSubToGWforestMaps' vs name 'SeepSubToGWForestMaps'). Matching the
        # user's list against the dict key (as before) meant that for those
        # entries no spelling worked: the dict-key spelling passed the lookup but
        # then failed path resolution (aggregate dropped, per-step file kept at
        # full resolution), while the rm.name spelling failed the lookup outright.
        # Keying by rm.name makes the aggregate resolve to the right file AND
        # match the surviving per-step output in the cleanup below.
        reportedmaps = settings.options['reportedmaps']
        maps_by_name = {rm.name: rm for rm in reportedmaps.values()}
        for setting_key, (frequency, operation) in aggregation_configs.items():
            var_list = binding.get(setting_key, '').split(';')
            for var_name in var_list:
                var_name = var_name.strip()
                if var_name and var_name in maps_by_name:
                    map_value = maps_by_name[var_name]
                    out = MapOutputAggregated(var, var_name, map_value, frequency, operation)
                    if out.is_valid():
                        outputs.append(out)
                        aggregated_vars.add(var_name)

        # Remove normal outputs for variables that are now aggregated
        outputs_clean = []
        check_duplicates = []
        for out in outputs:
            # Skip normal Maps/All output if variable is aggregated
            if hasattr(out, 'map_key') and out.map_key in aggregated_vars:
                if not isinstance(out, (MapOutputEnd, MapOutputAggregated)):
                    continue
            if out.map_path in check_duplicates:
                print(f'Warning! Output map {out.map_path} is duplicated')
            else:
                check_duplicates.append(out.map_path)
                outputs_clean.append(out)

        self.output_maps = outputs_clean

    def write(self):
        # synchronous approach, no real need to stage and then write
        # so done directly here
        for out in self.output_maps:
            out.stage()
            out.write()


class OutputMapsFactoryThreads(OutputMapsFactory):
    """ Extension of the OutputMapsFactory class
        Allows asynchronous writing on threads, overlapping NetCDF disk I/O
        with the model computation of the next time step. Opt-in via the
        'outputThreads' option (default off = synchronous writing).

        Thread-safety contract (HDF5 is not thread-safe, single writer per
        file):
        - stage() runs on the MAIN thread: map extraction, decompression and
          nancheck never race with writers.
        - Every actual netCDF4/HDF5 library call (file open, variable slice
          write, close) is serialised through netcdf.py's process-wide
          hdf5_lock (imported below as _hdf5_lock), not a writer-local lock:
          the dynamic loop's forcing readers (netcdf.py load_next_chunk under
          dask's threaded scheduler) also touch HDF5, and concurrent access on
          a non-threadsafe HDF5 build corrupts global state and aborts the
          process. The lock is held ONLY around the HDF5 calls themselves --
          metadata handling, uncompress_array and int16 packing arithmetic are
          pure numpy and run OUTSIDE the lock, so compression/encoding cost is
          not serialised. Holding several file handles open at once across
          threads is fine: only non-overlapping *calls* matter.
        - At most one flush generation is in flight: write() waits for the
          previous map_async batch before staging the next step, so each
          NetCDF file is touched by one worker thread at a time. The write
          path per file is open -> write -> close within one worker call,
          and iterOpenNetcdf/write_netcdf_header are stateless per call.
    """

    # Upper bound on writer threads; the pool is anyway sized to the number
    # of map outputs, so this only matters for very map-heavy configurations.
    max_threads = 16

    # Serialises the actual netCDF4/HDF5 library calls among worker threads and
    # with the reader side (netcdf.py load_next_chunk). The HDF5 library used
    # in this build is not compiled --enable-threadsafe, so concurrent Dataset
    # calls segfault even when they target *distinct* files. The lock is held
    # only around the HDF5 operations themselves (see NetcdfWriter.write /
    # NetcdfStepsWriter.write), not around the whole per-map write, so numpy
    # packing/encoding work overlaps across threads. This keeps the feature's
    # actual goal: background writing overlapping with main-thread computation
    # of the next time step (the handshake already ensures only one flush
    # generation is in flight).
    hdf5_write_lock = _hdf5_lock

    def __init__(self, var):
        super().__init__(var)

        from multiprocessing import pool
        # One thread per output map writer at most, capped at max_threads;
        # avoids idle threads on small configurations (the prototype
        # hardcoded 16 regardless of the actual map count).
        self.thread_pool = pool.ThreadPool(min(len(self.output_maps), self.max_threads) or 1)
        self.thread_out = None

    def write(self):
        # make sure that previous step finished writing, then stage data
        if self.thread_out is not None:
            self.thread_out.wait()

        for out in self.output_maps:
            out.stage()

        # quickly wraps OutputMaps write function to allow the use of map_async.
        # NOTE: the HDF5 lock is NOT taken here -- the writers acquire it
        # themselves around the individual netCDF4 operations (open, slice
        # write, close), leaving packing/encoding work outside the lock.
        def write_output(output_map):
            output_map.write()

        # write outputs using thread pool
        if self.output_maps:
            self.thread_out = self.thread_pool.map_async(write_output, self.output_maps)

        # for last step, re-raise any exception the workers hit (get() propagates
        # worker exceptions, wait() would silently swallow them and truncate the
        # output files without failing the run)
        if self.var.currentTimeStep() == self.var.nrTimeSteps() and self.thread_out is not None:
            self.thread_out.get()


# ------------------------------------------------------------------------
# Output Module
# ------------------------------------------------------------------------
class outputTssMap(object):

    """
    # ************************************************************
    # ***** Output of time series (.tss) and maps*****************
    # ************************************************************
    """

    def __init__(self, out_variable):
        self.var = out_variable
        # earthkit-hydro RiverNetwork (lazily built in initial(), see below)
        self._ek_net = None

    def _ek_network(self):
        """ Build (once) the earthkit RiverNetwork from the model Ldd for the
        opt-in useEarthkitHydro reporting path. The network node order equals
        LISFLOOD's compressed 1D order, so compressed arrays can be passed
        directly. Raises if earthkit-hydro is unavailable (caller only calls
        this when option['useEarthkitHydro'] and earthkit_available()).
        """
        if self._ek_net is None:
            ldd_np = pcr2numpy(self.var.Ldd, 0)
            self._ek_net = get_earthkit_network(ldd_np)
        return self._ek_net

    def initial(self):
        """ initial part of the output module
        """
        settings = LisSettings.instance()
        option = settings.options
        flags = settings.flags
        binding = settings.binding
        report_time_serie_act = settings.report_timeseries
        maskinfo = MaskInfo.instance()
        binding['Catchments'] = self.var.Catchments
        # output for single column eg mapmaximum
        self.var.Tss = {}

        # --- opt-in earthkit-hydro acceleration of the reporting path --------
        # Precompute the 1D arrays the earthkit path needs (upstream area and
        # pixel area in compressed order), and the per-series zone-code arrays
        # for multi-cell gauge zones. Nothing here touches the PCRaster path.
        if option['useEarthkitHydro'] and earthkit_available():
            net = self._ek_network()
            pixelarea_1d = np.asarray(self.var.PixelArea, dtype=np.float64)
            self.var.EkPixelArea = pixelarea_1d
            # UpArea recomputed on the network (fast, parallel) instead of
            # reusing the PCRaster map: same accumulation, compressed order.
            uparea_1d = ek_upstream_sum(net, pixelarea_1d, node_weights=None)
            self.var.EkInvUpArea = 1.0 / uparea_1d

        # Resolve each distinct output-point location ("where": Gauges, Sites,
        # LakeSites, Catchments, ...) only ONCE. The resolved map is used read-only by
        # TimeoutputTimeseries.__init__, so sharing one object per `where` is safe.
        outpoints_by_where = {}

        for tss in report_time_serie_act:
            where = report_time_serie_act[tss].where
            if where in outpoints_by_where:
                outpoints = outpoints_by_where[where]
            else:
                outpoints = binding[where]
                if where == "Catchments":
                    outpoints = decompress(outpoints)
                else:
                    coord = binding[where].split()  # could be gauges, sites, lakeSites etc.
                    if len(coord) % 2 == 0:
                        outpoints = valuecell(self.var.MaskMap, coord, outpoints)
                    else:
                        try:
                            outpoints = loadmap(where, pcr=True)
                            outpoints = ifthen(outpoints != 0, outpoints)
                            # this is necessary if netcdf maps are loaded !! otherwise strange dis.tss
                        except Exception as e:
                            msg = "Setting output points\n {}".format(str(e))
                            raise LisfloodFileError(outpoints, msg)
                outpoints_by_where[where] = outpoints

            if option['MonteCarlo']:
                if os.path.exists(os.path.split(binding[tss])[0]):
                    self.var.Tss[tss] = TimeoutputTimeseries(str(binding[tss].split("/")[-1]), self.var, outpoints, noHeader=flags['noheader'])
                else:
                    msg = "Checking output timeseries \n"
                    raise LisfloodFileError(binding[tss],msg)
            else:
                if os.path.exists(os.path.split(binding[tss])[0]):
                    self.var.Tss[tss] = TimeoutputTimeseries(str(binding[tss]), self.var, outpoints, noHeader=flags['noheader'])
                else:
                    msg = "Checking output timeseries \n"
                    raise LisfloodFileError(str(binding[tss]), msg)

        # initialise output objects. Threaded writer is opt-in via the
        # 'outputThreads' option. With a single map output there is nothing to
        # parallelise, so the (cheap) threaded factory is discarded and the
        # synchronous one kept. OutputMapsChunks-driven mid-run flushes are
        # handled by whichever factory is selected here.
        if option['outputThreads']:
            factory = OutputMapsFactoryThreads(self.var)
            if len(factory.output_maps) > 1:
                self.output_maps = factory
            else:
                # dispose of the idle pool and keep the synchronous factory
                factory.thread_pool.close()
                factory.thread_pool.join()
                self.output_maps = OutputMapsFactory(self.var)
        else:
            self.output_maps = OutputMapsFactory(self.var)

    def dynamic(self):
        """ dynamic part of the output module
        """
        # ************************************************************
        # ***** WRITING RESULTS: TIME SERIES *************************
        # ************************************************************

        # if fast init than without time series
        settings = LisSettings.instance()
        option = settings.options
        flags = settings.flags
        maskinfo = MaskInfo.instance()
        report_time_serie_act = settings.report_timeseries

        # Opt-in reporting-path wall timers (LISFLOOD_EK_PROFILE=1).
        # cProfile mis-attributes the PCRaster engine reductions here
        # (recursion accounting), so these wall timers are the only
        # trustworthy measurement of the reporting path.
        import os as _os
        _ek_prof = _os.environ.get('LISFLOOD_EK_PROFILE') == '1'
        _ek_times = {'mapmaximum': 0.0, 'total': 0.0, 'sample': 0.0,
                     'sample_compressed': 0.0, 'sample_zone_means': 0.0}
        import time as _time

        if not(option['InitLisfloodwithoutSplit']):

            if flags['loud']:
                # print the discharge of the first output map loc
                try:
                    sys.stdout.write(" %10.2f" % self.var.Tss["DisTS"].firstout(decompress(self.var.ChanQAvg)))
                except:
                    pass
                sys.stdout.write("\n")

            # earthkit/numpy fast path (opt-in useEarthkitHydro): the
            # how=='total' series (the upstream-accumulation family) all share
            # the same network and node_weights and differ only by field, so
            # collect their fields in one pass and issue a SINGLE batched
            # upstream accumulation for the whole step instead of one traversal
            # per series. The batch axis is a pure outer vectorization, so each
            # per-series result is bit-identical to the scalar path. The batched
            # accumulation is timed under the 'total' bucket to keep the
            # LISFLOOD_EK_PROFILE before/after comparison meaningful.
            _fused_changed = {}
            if option['useEarthkitHydro'] and earthkit_available():
                _t0 = _time.perf_counter() if _ek_prof else None
                _fused_fields = []
                _fused_keys = []
                for tss in report_time_serie_act:
                    _how = report_time_serie_act[tss].operation[0] if len(report_time_serie_act[tss].operation) else ''
                    if _how == 'total':
                        _what = 'self.var.' + report_time_serie_act[tss].output_var
                        _x_1d = eval(_what)
                        _fused_fields.append(np.asarray(_x_1d, dtype=np.float64))
                        _fused_keys.append(tss)
                if _fused_fields:
                    _net = self._ek_network()
                    _stacked = np.stack(_fused_fields)
                    _tot = ek_upstream_sum_batch(_net, _stacked,
                                                 node_weights=self.var.EkPixelArea)
                    _mp = model_precision()
                    for _k, _key in enumerate(_fused_keys):
                        _fused_changed[_key] = (_tot[_k] * self.var.EkInvUpArea).astype(
                            _mp, copy=False)
                if _ek_prof:
                    _ek_times['total'] += _time.perf_counter() - _t0

            for tss in report_time_serie_act:
                # report time series
                what = 'self.var.' + report_time_serie_act[tss].output_var
                how = report_time_serie_act[tss].operation[0] if len(report_time_serie_act[tss].operation) else ''
                # earthkit/numpy fast path (opt-in useEarthkitHydro): operate on
                # the 1D compressed arrays directly, never building 2D PCRaster
                # maps (kills the decompress/numpy2pcr/pcr2numpy round-trips and
                # the single-threaded PCRaster engine reductions). The historical
                # PCRaster statements are kept verbatim in the else branches.
                _t0 = _time.perf_counter() if _ek_prof else None
                if option['useEarthkitHydro'] and earthkit_available():
                    if how == 'mapmaximum':
                        x_1d = eval(what)
                        with np.errstate(invalid='ignore'):
                            changed = np.full(maskinfo.info.mapC, np.nanmax(x_1d),
                                              dtype=np.float64)
                        what = 'changed'
                    elif how == 'total':
                        # distribute the pre-batched upstream sum for this series
                        changed = _fused_changed[tss]
                        what = 'changed'
                else:
                    if how == 'mapmaximum':
                        changed = compressArray(mapmaximum(decompress(eval(what))))
                        what = 'changed'
                    if how == 'total':
                        changed = compressArray(catchmenttotal(decompress(eval(what)) * self.var.PixelAreaPcr, self.var.Ldd) * self.var.InvUpArea)
                        what = 'changed'
                if _ek_prof and how in _ek_times:
                    _ek_times[how] += _time.perf_counter() - _t0
                tss_obj = self.var.Tss[tss]
                value_1d = eval(what)
                # Fast path: when every gauge is a single cell, the inherited
                # .sample()'s per-zone areaaverage equals the gauge-cell value,
                # so read it straight from the 1D array and skip the
                # decompress -> numpy2pcr full-map conversion (~50-136 ms/call on
                # a global grid). Only for Scalar series (the areaaverage branch);
                # a 1D numpy array implies Scalar/Directional here. Falls back to
                # the exact PCRaster path otherwise (e.g. multi-cell gauge zones,
                # non-spatial gauges, or non-ndarray values).
                _t0 = _time.perf_counter() if _ek_prof else None
                _sample_kind = 'sample'
                if getattr(tss_obj, '_compressed_sampling_ok', False) and isinstance(value_1d, np.ndarray):
                    tss_obj.sample_compressed(value_1d)
                    _sample_kind = 'sample_compressed'
                elif option['useEarthkitHydro'] and earthkit_available() and \
                        getattr(tss_obj, '_ek_zone_codes', None) is not None and \
                        isinstance(value_1d, np.ndarray):
                    # multi-cell gauge zones: numpy zone-mean (equivalent of the
                    # .sample() -> pcraster.areaaverage fallback), still without
                    # any 2D map round-trip
                    from .earthkit_network import ek_sample_zone_means
                    ek_sample_zone_means(tss_obj, value_1d)
                    _sample_kind = 'sample_zone_means'
                else:
                    tss_obj.sample(decompress(value_1d))
                if _ek_prof:
                    _ek_times[_sample_kind] += _time.perf_counter() - _t0

        # ************************************************************
        # ***** WRITING RESULTS: MAPS   ******************************
        # ************************************************************

        self.output_maps.write()

        # update local output steps
        cdfflags = CDFFlags.instance()
        cdfflags.update(self.var)

        if _ek_prof and self.var.currentTimeStep() == self.var.nrTimeSteps():
            sys.stdout.write(
                '[ek-profile] reporting-path wall seconds '
                'mapmaximum=%.2f total=%.2f sample=%.2f '
                'sample_compressed=%.2f sample_zone_means=%.2f\n'
                % (_ek_times['mapmaximum'], _ek_times['total'],
                   _ek_times['sample'], _ek_times['sample_compressed'],
                   _ek_times['sample_zone_means']))
            sys.stdout.flush()
