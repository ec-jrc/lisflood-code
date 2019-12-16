#! /usr/bin/python2
from lisf1 import LisfloodModel
import os
import re
import numpy as np
import pandas as pd
import xarray as xr
from sys import argv
from global_modules.zusatz import optionBinding
from basic_modeling_interface.bmi import Bmi
from global_modules.zusatz import checkifDate, pcraster
from global_modules.globals import modelSteps, maskinfo
from pcraster.framework.dynamicFramework import DynamicFramework
#from ipdb import set_trace as bp

OUT_VARS = [('Discharge', 'ChanQAvg', 'm^3/s'), ('Topsoil moisture', 'W1a', '1e-3 m')]
OUT_VARS = pd.DataFrame(OUT_VARS, columns=['external_name','internal_name','units']).set_index('external_name')
RE_XML_ENTRY = '\"[A-Za-z]+\"[\sA-Za-z=]+\"([A-Za-z0-9_\/]+)\"'

def checkGridID(grid_id):
    if grid_id != 0:
        raise Exception("Invalid grid id")

def checkIndices(indices):
    assert isinstance(indices, tuple) or isinstance(indices, list) or isinstance(indices, np.ndarray)

def isValidDataArray(da):
    return isinstance(da, xr.DataArray) and ('vegetation' in da.dims) and (len(da.dims) == 2)


class LisfloodBmi(Bmi):

    def initialize(self, settings_xml):
        self._path_settings = settings_xml
        link_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OptionTserieMaps.xml")
        optionBinding(self._path_settings, link_file)
        checkifDate('StepStart','StepEnd')
        self.model = LisfloodModel()
        self.framework = DynamicFramework(self.model, firstTimestep=modelSteps[0], lastTimeStep=modelSteps[1])
        self.framework._atStartOfScript()
        self.framework._runInitial()
        self.framework._userModel()._setInDynamic(True)
        # Read 1st and last time steps
        self.calendar_start = self.framework._userModel().CalendarDayStart
        self.start_step = self.framework._userModel().firstTimeStep()
        self.end_step = self.framework._userModel().nrTimeSteps()
        self.current_step = self.start_step
        # Get the domain mask (True = simulated)
        self.mask = ~maskinfo['mask']
        # Grid information
        self.num_rows, self.num_cols = self.mask.shape
        self.cell_size = round(pcraster.clone().cellSize(),5)
        self.left_x = round((pcraster.clone().west() + self.cell_size / 2),5)
        self.right_x = round((self.left_x + self.num_cols * self.cell_size),5)
        self.top_y = round((pcraster.clone().north() - self.cell_size / 2),5)
        self.bottom_y = round((self.top_y - self.num_rows * self.cell_size),5)

    def update(self):
        """
        Derived from _runDynamic method of PCRaster FrameworkBase class.
        """
        self.framework._incrementIndentLevel()
        self.framework._atStartOfTimeStep(self.current_step)
        self.framework._userModel()._setCurrentTimeStep(self.current_step)
        self.framework._incrementIndentLevel()
        self.framework._traceIn("dynamic")
        self.framework._userModel().dynamic()
        self.framework._traceOut("dynamic")
        self.framework._decrementIndentLevel()
        self.framework._timeStepFinished()
        self.framework._decrementIndentLevel()
        self.current_step += 1

    def update_until(self, until_step):
        if until_step > self.current_step:
            raise Exception("Input time step ({}) < current time step ({})".format(until_step, self.current_step))
        else:
            while self.current_step <= until_step:
                self.update()

    def update_frac(self, time_frac):
        raise NotImplementedError

    def finalize(self):
        self._userModel()._setInDynamic(False)

    def get_start_time(self):
        return float(self.start_step)

    def get_current_time(self):
        return float(self.current_step)

    def get_end_time(self):
        return float(self.end_step)

    def get_time_step(self):
        return 1.

    def get_time_units(self):
        return "days since " + self.model.CalendarDayStart.strftime('%Y-%m-%d')

    def get_component_name(self):
        return "LISFLOOD hydrologic and water resources model"

    def get_input_var_names(self): # TO DO
        super(LisfloodBmi, self).get_input_var_names()

    def get_output_var_names(self): # TO BE LINKED WITH SETTINGS/OPTION XML?
        return OUT_VARS.index.tolist()

    def get_var_type(self, var_name):
        return str(self._getVar(var_name).dtype)

    def get_var_units(self, var_name):
        return OUT_VARS.loc[var_name,'units']

    def get_var_itemsize(self, var_name):
        return self._reGrid(self._getVar(var_name).nbytes)

    def get_var_nbytes(self, var_name): # OK
        return self.get_var_itemsize(var_name)

    def get_var_grid(self, var_name):
        return 0

    def get_value(self, var_name):
        return self._reGrid(self._getVar(var_name))

    def get_value_ref(self, var_name): # OK? getters return values on 2d maps - calculations use 1d arrays (not exposed)
        return self.get_value(var_name)

    def get_value_at_indices(self, var_name, rows_cols):
        return self.get_value(var_name)[rows_cols[:,0],rows_cols[:,1]]

    def set_value(self, var_name, src):
        vector = self._refDomainVar(var_name)
        if isinstance(vector, np.ndarray):
            vector[:] = src[self.mask] # the model attribute is changed as raw is a reference to it
        elif isValidDataArray(vector):
            domain_src = src[:,self.mask]
            if vector.shape == domain_src.shape:
                vector.values[:] = domain_src
            else:
                raise Exception('Shape mismatch between input values and model variable')
        else:
            raise NotImplementedError

    def set_value_at_indices(self, var_name, indices, src):
        checkIndices(indices)
        vector = self._refDomainVar(var_name)
        if isinstance(vector, np.ndarray):
            vector[indices] = src # the model attribute is changed as vector is a reference
        elif isValidDataArray(vector):
            vector.values[indices] = src
        else:
            raise NotImplementedError

    def get_grid_shape(self, grid_id): # get_var_location? relevant for uniform rectilinear grid?
        return self.mask.shape

    def get_grid_x(self, grid_id): # not relevant for uniform rectilinear grid - NotImplementedError?
        checkGridID(grid_id)
        super(LisfloodBmi, self).get_grid_x(grid_id)

    def get_grid_y(self, grid_id): # not relevant for uniform rectilinear grid - NotImplementedError?
        checkGridID(grid_id)
        super(LisfloodBmi, self).get_grid_y(grid_id)

    def get_grid_z(self, grid_id): # not relevant for uniform rectilinear grid - NotImplementedError?
        checkGridID(grid_id)
        super(LisfloodBmi, self).get_grid_z(grid_id)

    def get_grid_spacing(self, grid_id):
        checkGridID(grid_id)
        return self.cell_size

    def get_grid_origin(self, grid_id):
        return np.array([self.left_x, self.bottom_y])

    def get_grid_connectivity(self, grid_id): # not relevant for uniform rectilinear grid - NotImplementedError?
        checkGridID(grid_id)
        super(LisfloodBmi, self).get_grid_connectivity(grid_id)

    def get_grid_offset(self, grid_id): # not relevant for uniform rectilinear grid - NotImplementedError?
        checkGridID(grid_id)
        super(LisfloodBmi, self).get_grid_offset(grid_id)

    def get_grid_rank(self, grid_id):
        return 2

    def get_grid_size(self, grid_id):
        checkGridID(grid_id)
        return self.mask.size

    def get_grid_type(self, grid_id):
        checkGridID(grid_id)
        return 'uniform_rectilinear'
    
    def readSetting(self, name):
        line = [l for l in open(self._path_settings).readlines() if '\"{}\"'.format(name) in l][0]
        return re.search(RE_XML_ENTRY, line).group(1)

    def _refDomainVar(self, var_name):
        return getattr(self.model, OUT_VARS.loc[var_name,'internal_name'])
    
    def _getVar(self, var_name):
        """1d array on simulated land pixels"""
        vector = self._refDomainVar(var_name)
        if isinstance(vector, np.ndarray):
            return vector
        elif isValidDataArray(vector):
            return (vector * self.model.SoilFraction).sum('vegetation').values
        else:
            raise NotImplementedError

    def _reGrid(self, vector):
        """2d array on the rectangle containing the simulated land pixels (missing values reported as nan)"""
        matrix = np.full(self.mask.shape, np.nan)
        matrix[self.mask] = vector
        return matrix

    # Undefined methods
    def get_grid_face_edges(self):
        return None
    
    def get_input_item_count(self):
        return None
    
    def get_output_item_count(self):
        return None
#
#
#if __name__ == '__main__':
#    # Shell argument: settings file path
#    path_settings, dir_out = argv[1:]
#    if os.path.exists(dir_out):
#        raise Exception(dir_out + ' already exists - specify a new output folder name')
#    os.makedirs(dir_out)
#    # Initialise BMI interface and LISFLOOD model
#    model = LisfloodBmi()
#    model.initialize(path_settings)
#    # Load station-pixel matching information (to compare simulated and reported river discharge)
#    path_info = os.path.join(model.readSetting('PathRoot'), 'station-pixel_matches.json')
#    station_pixel = pd.read_json(path_info)
#    # Allocate comparison dataframe and load GRDC-reported values
#    days = pd.period_range(model.calendar_start, periods=model.end_step)[model.start_step-1:]
#    discharge_comparison = pd.DataFrame(index=days, columns=pd.MultiIndex.from_product((station_pixel.index, ['Observed', 'Simulated'])))
#    for riv, path_obs in station_pixel['Observation_file'].iteritems():
#        obs = pd.read_table(path_obs, skiprows=35, sep=';\s*', index_col='YYYY-MM-DD', parse_dates=True).Value
#        obs.loc[obs < 0] = np.nan # filter missing observations out
#        obs.index = obs.index.to_period()
#        discharge_comparison.loc[:,(riv, 'Observed')] = obs.loc[days]
#    # Run the model and store simulated discharge at each time step
#    for d in days:
#        model.update() # Run the model for a daily time step
#        for riv, row, col in station_pixel[['Row_model','Col_model']].itertuples():
#            discharge_comparison.loc[d,(riv, 'Simulated')] = model.get_value_at_indices('Discharge', (row, col))
#    # Write comparison data to file
#    path_out = os.path.join(dir_out, 'discharge_comparison.pickle')
#    discharge_comparison.to_pickle(path_out)
#    print('Comparison data written to {}\nStations info is in {}'.format(path_out, path_info))
