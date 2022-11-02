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
import threading
from multiprocessing import pool

import os
import warnings
import numpy as np
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

    def stage(self, map_data):
        raise NotImplementedError

    def write(self, start_date, rep_steps):
        raise NotImplementedError

    def extract_map(self):
        what = 'self.var.' + self.map_value.output_var
        try:
            map_data = eval(what)
        except:
            map_data = None
            raise Exception(f'ERROR! {self.map_value.output_var} could not be found for outputs. \
            Variable needs to be initialised in the initial() function of the relevant hydrological module')

        return np.copy(map_data)


class NetcdfWriter(Writer):

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
        self.data = self.extract_map()
        flags = self.settings.flags
        if flags['nancheck']:
            nanCheckMap(self.data, self.map_name, self.map_key)

    def write(self, start_date, rep_steps):
        if self.data is not None:
            print(f'Writing {self.map_path} from thread {threading.get_ident()}')
            nf1 = write_netcdf_header(self.settings, self.map_name, self.map_path, self.var.DtDay,
                                    self.map_key, self.map_value.output_var, self.map_value.unit, 'd', 
                                    start_date, rep_steps, self.frequency)

            map_np = uncompress_array(self.data)
            
            nf1.variables[self.map_name][:, :] = map_np

            nf1.close()
            print(f'Done writing {self.map_path} from thread {threading.get_ident()}')
        else:
            raise Exception('You need to stage data before writing!')


class NetcdfStepsWriter(NetcdfWriter):

    def __init__(self, var, map_key, map_value, map_path, frequency, flag, end_step):

        self.settings = LisSettings.instance()
        binding = self.settings.binding

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

    def stage(self):

        map_np = self.extract_map()

        cdfflags = CDFFlags.instance()
        step = cdfflags[self.flag]

        flags = LisSettings.instance().flags
        if flags['nancheck']:
            nanCheckMap(map_np, self.map_name, self.map_key)

        self.step_range.append(step)
        self.data_steps.append(map_np)

    def write(self, start_date, rep_steps):
        if self.checkpoint():
            if self.data_steps:
                print(f'Writing {self.map_path} from thread {threading.get_ident()}')
                if self.step_range[0] == 0:
                    nf1 = write_netcdf_header(self.settings, self.map_name, self.map_path, self.var.DtDay,
                                            self.map_key, self.map_value.output_var, self.map_value.unit, 'd', 
                                            start_date, rep_steps, self.frequency)
                else:
                    nf1 = iterOpenNetcdf(self.map_path, "", 'a', format='NETCDF4')

                for step, data in zip(self.step_range, self.data_steps):
                    nf1.variables[self.map_name][step, :, :] = uncompress_array(data)

                nf1.close()

                # clear lists for next chunk
                self.step_range.clear()
                self.data_steps.clear()
                print(f'Done writing {self.map_path} from thread {threading.get_ident()}')
            else:
                raise Exception('You need to stage data before writing!')


class PCRasterWriter(Writer):

    def __init__(self, var, map_path):
        self.var = var
        self.map_path = map_path
        self.data = None

    def stage(self):
        self.data = self.extract_map()
        
    def write(self, start_date, rep_steps):
        if self.data is not None:
            self.var.report(decompress(self.data), str(self.map_path))
        else:
            raise Exception('You need to stage data before writing!')


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

        # staging data
        self.step = None

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

    def stage(self):
        self.step = self.var.currentTimeStep()
        if self.output_checkpoint():
            self.writer.stage()

    def write(self):
        if self.output_checkpoint():
            try:
                return self.writer.write(self.start_date, self.rep_steps)
            except:
                import traceback
                import sys
                print(traceback.format_exc())
                raise Exception('exception')
                return False
                


class MapOutputEnd(MapOutput):

    def __init__(self, var, map_key, map_value):

        settings = LisSettings.instance()
        self.binding = settings.binding
        out_type = 'end'
        frequency = None
        super().__init__(var, out_type, frequency, map_key, map_value)
    
    def output_checkpoint(self):
        check = self.step == self.var.nrTimeSteps()
        return check
    
    @property
    def start_date(self):
        start_date = inttodate(self.step - 1, self.var.CalendarDayStart, self.binding)
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
        check = (self.step in self.var.ReportSteps) and freq_check
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
# Output factory classes
# ------------------------------------------------------------------------

# class Worker(threading.Thread):
#     """Thread executing tasks from a given tasks queue"""
#     def __init__(self, tasks):
#         threading.Thread.__init__(self)
#         self.tasks = tasks
#         self.daemon = True
#         self.start()
    
#     def run(self):
#         while True:
#             func, args, kargs = self.tasks.get()
#             try: func(*args, **kargs)
#             except Exception: 
#                 raise Exception('Writing thread failed')
#             self.tasks.task_done()

# class ThreadPool:
#     """Pool of threads consuming tasks from a queue"""
#     def __init__(self, num_threads):
#         self.tasks = Queue(num_threads)
#         for _ in range(num_threads): Worker(self.tasks)

#     def add_task(self, func, *args, **kargs):
#         """Add a task to the queue"""
#         self.tasks.put((func, args, kargs))

#     def wait_completion(self):
#         """Wait for completion of all the tasks in the queue"""
#         if not self.tasks.empty():
#             self.tasks.join()

def write_output(output_map):
    output_map.write()

class OutputMapsFactory():
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

        check_duplicates = []
        outputs_clean = []
        for out in outputs:
            if out.map_path in check_duplicates:
                print(f'Warning! Output map {out.map_path} is duplicated, check list of outputs')
            else:
                check_duplicates.append(out.map_path)
                outputs_clean.append(out)

        self.output_maps = outputs_clean
        self.thread_pool = pool.ThreadPool(16)
        self.thread_out = None

    def write(self):
        # make sure that previous step finished writing, then stage data
        # if self.thread_out:
        #     self.thread_out.wait()
        for out in self.output_maps:
            out.stage()

        # # write outputs using thread pool
        # # for out in self.output_maps:
        # #     write_output(out)
        # self.thread_out = self.thread_pool.map_async(write_output, self.output_maps)

        # if self.var.currentTimeStep() == self.var.nrTimeSteps():
        #     self.thread_out.wait()

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
        # output for single column eg mapmaximum
        self.var.Tss = {}

        for tss in report_time_serie_act:
            where = report_time_serie_act[tss].where
            outpoints = binding[where]
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
        self.outputs = OutputMapsFactory(self.var)

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
                    print(" %10.2f" % self.var.Tss["DisTS"].firstout(decompress(self.var.ChanQAvg)))
                except:
                    pass

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
        self.outputs.write()

        # update local output steps
        cdfflags = CDFFlags.instance()
        cdfflags.update(self.var)
