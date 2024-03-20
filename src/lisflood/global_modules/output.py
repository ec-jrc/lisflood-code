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
import numpy as np
from pcraster import ifthen, catchmenttotal, mapmaximum
import sys

from .zusatz import TimeoutputTimeseries
from .add1 import decompress, valuecell, loadmap, compressArray
from .netcdf import write_netcdf_header, iterOpenNetcdf, nanCheckMap, uncompress_array
from .errors import LisfloodFileError, LisfloodWarning
from .settings import inttodate, CDFFlags, LisSettings


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
            nf1 = write_netcdf_header(self.settings, self.map_name, self.map_path, self.var.DtDay,
                                    self.map_key, self.map_value.output_var, self.map_value.unit,
                                    start_date, rep_steps, self.frequency)

            map_np = uncompress_array(self.data)

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
                if self.step_range[0] == 0:
                    nf1 = write_netcdf_header(self.settings, self.map_name, self.map_path, self.var.DtDay,
                                            self.map_key, self.map_value.output_var, self.map_value.unit,
                                            start_date, rep_steps, self.frequency)
                else:
                    nf1 = iterOpenNetcdf(self.map_path, "", 'a', format='NETCDF4')

                for step, data in zip(self.step_range, self.data_steps):
                    nf1.variables[self.map_name][step, :, :] = uncompress_array(data)

                nf1.close()

                # clear lists for next chunk
                self.step_range.clear()
                self.data_steps.clear()
            else:
                raise Exception('You need to stage data before writing!')


class PCRasterWriter(Writer):
    """ Main PCRaster writer class
        Doesn't require another class to handle multiple steps as PCRaster doesn't support temporal metadata
        Writing outputs in temporal chunks not supported for PCRaster
    """

    def __init__(self, var, map_path):
        self.var = var
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
                self.writer = PCRasterWriter(self.var, self.map_path)
    
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

        check_duplicates = []
        outputs_clean = []
        for out in outputs:
            if out.map_path in check_duplicates:
                print(f'Warning! Output map {out.map_path} is duplicated, check list of outputs')
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
        Allows asynchronous writing on threads
        NOT FULLY TESTED, USE AS A PROOF OF CONTEXT
    """

    def __init__(self, var):
        super().__init__(var)

        from multiprocessing import pool
        self.thread_pool = pool.ThreadPool(16)
        self.thread_out = None

    def write(self):
        # make sure that previous step finished writing, then stage data
        if self.thread_out is not None:
            self.thread_out.wait()
    
        for out in self.output_maps:
            out.stage()

        # quickly wraps OutputMaps write function to allow the use of map_async
        def write_output(output_map):
            output_map.write()
        
        # write outputs using thread pool
        if self.output_maps:
            self.thread_out = self.thread_pool.map_async(write_output, self.output_maps)

        # for last step, wait until everything is finished
        if self.var.currentTimeStep() == self.var.nrTimeSteps() and self.thread_out is not None:
            self.thread_out.wait()

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

        self.output_maps.write()      

        # update local output steps
        cdfflags = CDFFlags.instance()
        cdfflags.update(self.var)
