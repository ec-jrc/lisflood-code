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

from __future__ import absolute_import, print_function

from ..global_modules.add1 import loadmap, readnetcdf
from ..global_modules.settings import LisSettings, EPICSettings
from . import HydroModule

from ..global_modules.add1 import NumpyModified

from collections import OrderedDict
import pandas as pd
import xarray as xr
import numpy as np

class landusechange(HydroModule):

    """
    # ************************************************************
    # ***** LAND USE CHANGE : FRACTION MAPS **********************
    # ************************************************************

    # Each pixel is divided into several fractions, adding up to 1
    # open water
    # forest
    # sealed fraction
    # irrigated areas
    # rice irrigation areas
    # other
    """
    input_files_keys = {'all': ['ForestFraction', 'DirectRunoffFraction', 'WaterFraction',
                                'IrrigationFraction', 'RiceFraction', 'OtherFraction'],
                        'TransientLandUseChange': ['ForestFractionMaps', 'DirectRunoffFractionMaps',
                                                   'WaterFractionMaps',
                                                   'IrrigationFractionMaps', 'RiceFractionMaps', 'OtherFractionMaps']}
    module_name = 'LandUseChange'

    def __init__(self, landusechange_variable):
        self.var = landusechange_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
    
        settings = LisSettings.instance()
        option = settings.options
        binding = settings.binding
        
        """ initial part of the landusechange module
        """
        self.var.ForestFraction = loadmap('ForestFraction', timestampflag='closest').copy()
        self.var.DirectRunoffFraction = loadmap('DirectRunoffFraction', timestampflag='closest').copy()
        self.var.WaterFraction = loadmap('WaterFraction', timestampflag='closest').copy()
        self.var.IrrigationFraction = loadmap('IrrigationFraction', timestampflag='closest').copy()
        self.var.RiceFraction = loadmap('RiceFraction', timestampflag='closest').copy()
        self.var.OtherFraction = loadmap('OtherFraction', timestampflag='closest').copy()
        ##self.var.OtherFraction = 1 - (self.var.RiceFraction+self.var.IrrigationFraction+self.var.WaterFraction+self.var.DirectRunoffFraction+self.var.ForestFraction) 
        ## uncomment the line above to check the impact of pixels where the sum is not 1.0 (NB: this is an error in the fraction input maps as the fractions must always add up to 1.0)
        
        if option['TransientLandUseChange'] and option['readNetcdfStack']:
                model_steps = settings.model_steps                
                self.var.ForestFraction = readnetcdf(binding['ForestFractionMaps'], model_steps[0] , timestampflag='closest')        
                self.var.DirectRunoffFraction = readnetcdf(binding['DirectRunoffFractionMaps'],  model_steps[0] , timestampflag='closest')
                self.var.WaterFraction = readnetcdf(binding['WaterFractionMaps'],  model_steps[0], timestampflag='closest')
                self.var.IrrigationFraction = readnetcdf(binding['IrrigationFractionMaps'],  model_steps[0], timestampflag='closest')
                self.var.RiceFraction = readnetcdf(binding['RiceFractionMaps'],  model_steps[0] , timestampflag='closest')
                self.var.OtherFraction = readnetcdf(binding['OtherFractionMaps'],  model_steps[0] , timestampflag='closest')     
                
        epic_settings = EPICSettings.instance()    

        # Soil fraction split into: "Rainfed" (previously "Other"), "Forest", "Irrigated".           
        soil = OrderedDict([(name, loadmap(epic_settings.landuse_inputmap[epic_settings.vegetation_landuse[name]])) for name in self.var.prescribed_vegetation])
        if option.get('cropsEPIC'):
            self.var.SoilFraction = xr.DataArray(pd.DataFrame(soil).T, coords=self.var.coord_prescribed_vegetation, dims=self.var.coord_prescribed_vegetation.keys())
        else:
            self.var.SoilFraction = NumpyModified(pd.DataFrame(soil).T.values, dims=self.var.coord_prescribed_vegetation.keys())
        self.var.SoilFraction[0] =  self.var.OtherFraction
        self.var.SoilFraction[1] =  self.var.ForestFraction 
        self.var.SoilFraction[2] =  self.var.IrrigationFraction     
        # Interactive crop fractions (if EPIC is active)
        if option.get('cropsEPIC'):
            self.var.crop_module.setSoilFractions()       
        
    def dynamic(self):
        """ dynamic part of the landusechange module"""
        settings = LisSettings.instance()
        option = settings.options
        binding = settings.binding
        epic_settings = EPICSettings.instance()

        if option['TransientLandUseChange'] and option['readNetcdfStack']:
        
            if option["cropsEPIC"]:
                raise Exception("Land use change for EPIC crops not implemented yet!")
                                
            self.var.ForestFraction = readnetcdf(binding['ForestFractionMaps'], self.var.currentTimeStep(), timestampflag='closest')          #self.var.currentTimeStep()  
            self.var.DirectRunoffFraction = readnetcdf(binding['DirectRunoffFractionMaps'], self.var.currentTimeStep(), timestampflag='closest')          #self.var.currentTimeStep() 
            self.var.WaterFraction = readnetcdf(binding['WaterFractionMaps'], self.var.currentTimeStep(), timestampflag='closest')          #self.var.currentTimeStep() 
            self.var.IrrigationFraction = readnetcdf(binding['IrrigationFractionMaps'], self.var.currentTimeStep(), timestampflag='closest')          #self.var.currentTimeStep() 
            self.var.RiceFraction = readnetcdf(binding['RiceFractionMaps'], self.var.currentTimeStep(), timestampflag='closest')          #self.var.currentTimeStep() 
            self.var.OtherFraction = readnetcdf(binding['OtherFractionMaps'], self.var.currentTimeStep(), timestampflag='closest')          #self.var.currentTimeStep()  
            
            if option['repMBTs']:
                 self.var.ForestFraction_nextstep = []
                 self.var.DirectRunoffFraction_nextstep = []
                 self.var.WaterFraction_nextstep = []
                 self.var.IrrigationFraction_nextstep = []
                 self.var.RiceFraction_nextstep = []
                 self.var.OtherFraction_nextstep = []
                 self.var.DynamicLandCoverDelta = 0.0      
                 self.var.ForestFraction_nextstep = readnetcdf(binding['ForestFractionMaps'], self.var.currentTimeStep()+1, timestampflag='closest')            
                 self.var.DirectRunoffFraction_nextstep = readnetcdf(binding['DirectRunoffFractionMaps'], self.var.currentTimeStep()+1, timestampflag='closest')
                 self.var.WaterFraction_nextstep = readnetcdf(binding['WaterFractionMaps'], self.var.currentTimeStep()+1, timestampflag='closest')
                 self.var.IrrigationFraction_nextstep = readnetcdf(binding['IrrigationFractionMaps'], self.var.currentTimeStep()+1, timestampflag='closest')
                 self.var.RiceFraction_nextstep = readnetcdf(binding['RiceFractionMaps'], self.var.currentTimeStep()+1, timestampflag='closest')
                 self.var.OtherFraction_nextstep = readnetcdf(binding['OtherFractionMaps'], self.var.currentTimeStep()+1, timestampflag='closest')                     
                 self.var.DynamicLandCoverDelta = np.sum(np.abs(self.var.ForestFraction_nextstep-self.var.ForestFraction)+np.abs(self.var.DirectRunoffFraction_nextstep-self.var.DirectRunoffFraction)+np.abs(self.var.WaterFraction_nextstep-self.var.WaterFraction)+np.abs(self.var.IrrigationFraction_nextstep-self.var.IrrigationFraction)+np.abs(self.var.RiceFraction_nextstep-self.var.RiceFraction)+np.abs(self.var.OtherFraction_nextstep-self.var.OtherFraction))
 
            soil = OrderedDict([(name, loadmap(epic_settings.landuse_inputmap[epic_settings.vegetation_landuse[name]])) for name in self.var.prescribed_vegetation])
            if option.get('cropsEPIC'):
                self.var.SoilFraction = xr.DataArray(pd.DataFrame(soil).T, coords=self.var.coord_prescribed_vegetation, dims=self.var.coord_prescribed_vegetation.keys())
            else:
                self.var.SoilFraction = NumpyModified(pd.DataFrame(soil).T.values, dims=self.var.coord_prescribed_vegetation.keys())
            self.var.SoilFraction[0] =  self.var.OtherFraction
            self.var.SoilFraction[1] =  self.var.ForestFraction 
            self.var.SoilFraction[2] =  self.var.IrrigationFraction      
                          
            if not option["cropsEPIC"]: # If EPIC is active, the rice fraction initialisation is handled by EPIC (setSoilFractions in EPIC_main.py)
               self.var.SoilFraction.values[self.var.vegetation.index('Rainfed_prescribed')] += self.var.RiceFraction
                             
            # with EPIC off, rice is treated as other fraction
            # if the fraction of water varies then the other fraction are stored
            self.var.WaterFractionBase = self.var.WaterFraction.copy()
            self.var.OtherFractionBase = self.var.OtherFraction.copy()
            self.var.IrrigationFractionBase = self.var.IrrigationFraction.copy()
            self.var.ForestFractionBase = self.var.ForestFraction.copy()
            self.var.DirectRunoffFractionBase = self.var.DirectRunoffFraction.copy()
            self.var.PermeableFraction = 1 - self.var.DirectRunoffFraction - self.var.WaterFraction   
       
