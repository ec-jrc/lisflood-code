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

from collections import OrderedDict
import pandas as pd
import xarray as xr


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
        """ initial part of the landusechange module
        """
        self.var.ForestFraction = loadmap('ForestFraction', timestampflag='closest')
        self.var.DirectRunoffFraction = loadmap('DirectRunoffFraction', timestampflag='closest')
        self.var.WaterFraction = loadmap('WaterFraction', timestampflag='closest')
        self.var.IrrigationFraction = loadmap('IrrigationFraction', timestampflag='closest')
        self.var.RiceFraction = loadmap('RiceFraction', timestampflag='closest')
        self.var.OtherFraction = loadmap('OtherFraction', timestampflag='closest')
        settings = LisSettings.instance()
        option = settings.options
        epic_settings = EPICSettings.instance()
        # Soil fraction split into: "Rainfed" (previously "Other"), "Forest", "Irrigated".
        soil = OrderedDict([(name, loadmap(epic_settings.landuse_inputmap[epic_settings.vegetation_landuse[name]])) for name in self.var.prescribed_vegetation])
        self.var.SoilFraction = xr.DataArray(pd.DataFrame(soil).T, coords=self.var.coord_prescribed_vegetation, dims=self.var.coord_prescribed_vegetation.keys())
        # Interactive crop fractions (if EPIC is active)
        if option.get('cropsEPIC'):
            self.var.crop_module.setSoilFractions()


    def dynamic(self):
        """ dynamic part of the landusechange module"""
        settings = LisSettings.instance()
        option = settings.options
        binding = settings.binding
        epic_settings = EPICSettings.instance()
        if option['TransientLandUseChange']:
            if option["cropsEPIC"]:
                raise Exception("Land use change for EPIC crops not implemented yet!")
            time_step = self.var.currentTimeStep()
            self.var.DirectRunoffFraction = readnetcdf(binding['DirectRunoffFractionMaps'], time_step)
            self.var.WaterFraction = readnetcdf(binding['WaterFractionMaps'], time_step)
            self.var.RiceFraction = readnetcdf(binding['RiceFractionMaps'], time_step)
            soil = OrderedDict([(name, readnetcdf(binding[epic_settings.landuse_inputmap[epic_settings.vegetation_landuse[name]] + "Maps"], time_step)) for name in self.var.prescribed_vegetation])
            self.var.SoilFraction = xr.DataArray(pd.DataFrame(soil).T, coords=self.var.coord_prescribed_vegetation, dims=self.var.coord_prescribed_vegetation.keys())
