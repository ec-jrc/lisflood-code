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
from __future__ import print_function, absolute_import
#from msilib.schema import Property

import os
import warnings
import sys

from pcraster import report, ifthen, catchmenttotal, mapmaximum

from .zusatz import TimeoutputTimeseries
from .add1 import decompress, valuecell, loadmap, compressArray
from .netcdf import write_netcdf_header, iterOpenNetcdf, nanCheckMap, uncompress_array
from .errors import LisfloodFileError, LisfloodWarning
from .settings import inttodate, CDFFlags, LisSettings


# ------------------------------------------------------------------------
# Writer classes
# ------------------------------------------------------------------------
class Writer():

    def write(self, map_data, start_date, rep_steps):
        raise NotImplementedError


class NetcdfWriter(Writer):

    def __init__(self, var, map_key, map_value, map_path, frequency=None):

        self.var = var

        self.map_key = map_key
        self.map_value = map_value
        self.map_path = map_path
        self.map_name = os.path.basename(self.map_path)
        self.map_path = map_path+'.nc'

        self.frequency = frequency

    def write(self, map_data, start_date, rep_steps):
        
        nf1 = write_netcdf_header(self.map_name, self.map_path, self.var.DtDay,
                                  self.map_key, self.map_value.output_var, self.map_value.unit, 'd', 
                                  start_date, rep_steps, self.frequency)

        flags = LisSettings.instance().flags
        if flags['nancheck']:
            nanCheckMap(map_data, self.map_name, self.map_key)
        
        map_np = uncompress_array(map_data)
        
        nf1.variables[self.map_name][:, :] = map_np

        nf1.close()


class NetcdfStepsWriter(NetcdfWriter):

    def __init__(self, var, map_key, map_value, map_path, frequency, flag, end_step):

        settings = LisSettings.instance()
        binding = settings.binding

        self.flag = flag
        self.chunks = int(binding['OutputMapsChunks'])
        self.end_step = end_step
        self.step_range = []
        self.data_steps = []

        super().__init__(var, map_key, map_value, map_path, frequency)

    def checkpoint(self):
        write = False
        end_run = self.var.currentTimeStep() == self.end_step
        if len(self.data_steps) == self.chunks or end_run:
            write = True
        return write

    def write(self, map_data, start_date, rep_steps):
        
        cdfflags = CDFFlags.instance()
        step = cdfflags[self.flag]

        flags = LisSettings.instance().flags
        if flags['nancheck']:
            nanCheckMap(map_data, self.map_name, self.map_key)

        map_np = uncompress_array(map_data)

        self.step_range.append(step)
        self.data_steps.append(map_np)

        if self.checkpoint():

            if self.step_range[0] == 0:
                nf1 = write_netcdf_header(self.map_name, self.map_path, self.var.DtDay,
                                        self.map_key, self.map_value.output_var, self.map_value.unit, 'd', 
                                        start_date, rep_steps, self.frequency)
            else:
                nf1 = iterOpenNetcdf(self.map_path, "", 'a', format='NETCDF4')

            for step, data in zip(self.step_range, self.data_steps):
                nf1.variables[self.map_name][step, :, :] = data

            nf1.close()

            # clear lists for next chunk
            self.step_range.clear()
            self.data_steps.clear()


class PCRasterWriter(Writer):

    def __init__(self, var, map_path):
        self.var = var
        self.map_path = map_path

    def write(self, map_data, start_date, rep_steps):
            self.var.report(decompress(map_data), str(self.map_path))


# ------------------------------------------------------------------------
# Map Output classes
# ------------------------------------------------------------------------
class MapOutput():

    def __init__(self, var, out_type, frequency, map_key, map_value):

        settings = LisSettings.instance()
        option = settings.options

        self.var = var

        cdfflags = CDFFlags.instance()
        self.flag = cdfflags.get_flag(out_type, frequency)
        self.frequency = frequency

        self.map_key = map_key
        self.map_value = map_value
        self.map_path = self.extract_path(settings)

        if self.is_valid():
            if option['writeNetcdf'] or option['writeNetcdfStack']:
                if self.flag == 0:
                    self.writer = NetcdfWriter(self.var, self.map_key, self.map_value, self.map_path)
                else:
                    self.writer = NetcdfStepsWriter(self.var, self.map_key, self.map_value, self.map_path, self.frequency, self.flag, self.rep_steps[-1])
            else:  # PCRaster
                self.writer = PCRasterWriter(self.var, self.map_path)

    def is_valid(self):
        valid = True
        # map_data = self.extract_map()
        # if map_data is None or self.map_path is None:
        #     valid = False
        if self.map_path is None:
            valid = False
        return valid

    def extract_map(self):
        what = 'self.var.' + self.map_value.output_var
        try:
            map_data = eval(what)
        except:
            map_data = None
            raise Exception(f'ERROR! {self.map_value.output_var} could not be found for outputs. \
            Variable needs to be initialised in the initial() function of the relevant hydrological module')
        return map_data

    def extract_path(self, settings):
        binding = settings.binding
        # report end map filename
        if settings.mc_set:
            # MonteCarlo model
            map_path = os.path.join(str(self.var.currentSampleNumber()), binding[self.map_key].split("/")[-1])
        else:
            map_path = binding.get(self.map_key)
        return map_path
    
    def output_checkpoint(self):
        raise NotImplementedError

    @property
    def start_date(self):
        raise NotImplementedError

    @property
    def rep_steps(self):
        raise NotImplementedError

    def write(self):
        if self.output_checkpoint():
            map_data = self.extract_map()
            self.writer.write(map_data, self.start_date, self.rep_steps)


class MapOutputEnd(MapOutput):

    def __init__(self, var, map_key, map_value):
        out_type = 'end'
        frequency = None
        super().__init__(var, out_type, frequency, map_key, map_value)
    
    def output_checkpoint(self):
        check = self.var.currentTimeStep() == self.var.nrTimeSteps()
        return check
    
    @property
    def start_date(self):
        start_date = inttodate(self.var.currentTimeStep() - 1, self.var.CalendarDayStart)
        return start_date

    @property
    def rep_steps(self):
        return None

class MapOutputSteps(MapOutput):

    def __init__(self, var, map_key, map_value, frequency):
        out_type = 'steps'
        if len(var.ReportSteps) > 0:
            self._start_date = var.CalendarDayStart
            self._rep_steps = var.ReportSteps
        super().__init__(var, out_type, frequency, map_key, map_value)
    
    def is_valid(self):
        valid = False
        if len(self.var.ReportSteps) > 0:
            valid = True
        return valid and super().is_valid()

    def output_checkpoint(self):
        cdfflags = CDFFlags.instance()
        freq_check = cdfflags.frequency_check(self.var, self.frequency)
        check = (self.var.currentTimeStep() in self.var.ReportSteps) and freq_check
        return check

    @property
    def start_date(self):
        return self._start_date

    @property
    def rep_steps(self):
        return self._rep_steps


class MapOutputAll(MapOutput):

    def __init__(self, var, map_key, map_value, frequency):
        out_type = 'all'
        settings = LisSettings.instance()
        binding = settings.binding
        self._start_date = var.CalendarDayStart
        self._rep_steps = range(binding['StepStartInt'],binding['StepEndInt']+1)
        super().__init__(var, out_type, frequency, map_key, map_value)
    
    def output_checkpoint(self):
        cdfflags = CDFFlags.instance()
        check = cdfflags.frequency_check(self.var, self.frequency)
        return check

    @property
    def start_date(self):
        return self._start_date

    @property
    def rep_steps(self):
        return self._rep_steps

# ------------------------------------------------------------------------
# Output factory
# ------------------------------------------------------------------------
def output_maps_factory(var):

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

    check_duplicates = []
    outputs_clean = []
    for out in outputs:
        if out.map_path in check_duplicates:
            print(f'Warning! Output map {out.map_path} is duplicated, check list of outputs')
        else:
            check_duplicates.append(out.map_path)
            outputs_clean.append(out)

    return outputs_clean


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

    def initial(self):
        """ initial part of the output module
        """
        settings = LisSettings.instance()
        option = settings.options
        flags = settings.flags
        binding = settings.binding
        report_time_serie_act = settings.report_timeseries
        binding['Catchments'] = self.var.Catchments
        # output for single column eg mapmaximum
        self.var.Tss = {}

        for tss in report_time_serie_act:
            where = report_time_serie_act[tss].where
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

        # initialise output objects
        self.output_maps = output_maps_factory(self.var)

    def dynamic(self):
        """ dynamic part of the output module
        """
        # ************************************************************
        # ***** WRITING RESULTS: TIME SERIES *************************
        # ************************************************************

        # if fast init than without time series
        settings = LisSettings.instance()
        option = settings.options
        binding = settings.binding
        flags = settings.flags
        report_time_serie_act = settings.report_timeseries

        if not(option['InitLisfloodwithoutSplit']):

            if flags['loud']:
                # print the discharge of the first output map loc
                try:
                    sys.stdout.write(" %10.2f" % self.var.Tss["DisTS"].firstout(decompress(self.var.ChanQAvg)))
                except:
                    pass
                sys.stdout.write("\n")

            for tss in report_time_serie_act:
                # report time series
                what = 'self.var.' + report_time_serie_act[tss].output_var
                how = report_time_serie_act[tss].operation[0] if len(report_time_serie_act[tss].operation) else ''
                if how == 'mapmaximum':
                    changed = compressArray(mapmaximum(decompress(eval(what))))
                    what = 'changed'
                if how == 'total':
                    changed = compressArray(catchmenttotal(decompress(eval(what)) * self.var.PixelAreaPcr, self.var.Ldd) * self.var.InvUpArea)
                    what = 'changed'
                self.var.Tss[tss].sample(decompress(eval(what)))

        # ************************************************************
        # ***** WRITING RESULTS: MAPS   ******************************
        # ************************************************************

        for out in self.output_maps:
            out.write()                   

        # update local output steps
        cdfflags = CDFFlags.instance()
        cdfflags.update(self.var)
