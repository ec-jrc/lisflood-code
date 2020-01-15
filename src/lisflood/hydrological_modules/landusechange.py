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
from ..global_modules.settings import LisSettings
from . import HydroModule


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
                        'TransientLandUseChange': ['ForestFractionMaps', 'DirectRunoffFractionMaps', 'WaterFractionMaps',
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

    def dynamic(self):
        """dynamic part of the landusechange module
        """
        settings = LisSettings.instance()
        option = settings.options
        binding = settings.binding

        if option['TransientLandUseChange'] and option['readNetcdfStack']:
            self.var.ForestFraction = readnetcdf(binding['ForestFractionMaps'], self.var.currentTimeStep(), timestampflag='closest')
            self.var.DirectRunoffFraction = readnetcdf(binding['DirectRunoffFractionMaps'], self.var.currentTimeStep(), timestampflag='closest')
            self.var.WaterFraction = readnetcdf(binding['WaterFractionMaps'], self.var.currentTimeStep(), timestampflag='closest')
            self.var.IrrigationFraction = readnetcdf(binding['IrrigationFractionMaps'], self.var.currentTimeStep(), timestampflag='closest')
            self.var.RiceFraction = readnetcdf(binding['RiceFractionMaps'], self.var.currentTimeStep(), timestampflag='closest')
            self.var.OtherFraction = readnetcdf(binding['OtherFractionMaps'], self.var.currentTimeStep(), timestampflag='closest')

            self.var.Test = self.var.RiceFraction*1.0
