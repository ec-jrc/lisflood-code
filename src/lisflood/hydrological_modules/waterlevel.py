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

import numpy as np

from ..global_modules.add1 import loadmap
from ..global_modules.settings import LisSettings
from . import HydroModule


class waterlevel(HydroModule):
    """
    # ************************************************************
    # ***** WATER LEVEL    *****************************************
    # ************************************************************
    """
    input_files_keys = {'simulateWaterLevels': ['FloodPlainWidth']}
    module_name = 'WaterLevel'

    def __init__(self, waterlevel_variable):
        self.var = waterlevel_variable

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the water level module
        """
        settings = LisSettings.instance()
        option = settings.options
        if option['simulateWaterLevels']:
            self.var.FloodPlainWidth = loadmap('FloodPlainWidth')

    def dynamic(self):
        """ dynamic part of the water level module
        """

        # Additional computations for channel and floodplain geometry
        # Activating this option doesn't affect LISFLOOD's behaviour in any way, option only
        # included to allow reporting of water level maps / time series
        # Actual reporting activated using separate options!
        settings = LisSettings.instance()
        option = settings.options
        if option['simulateWaterLevels']:
            ChanCrossSectionArea = np.where(
                self.var.IsChannelKinematic,
                np.minimum(self.var.TotalCrossSectionArea, self.var.TotalCrossSectionAreaBankFull),
                0
            )
            # Cross-sectional area for channel only (excluding floodplain) [sq m]
            FloodPlainCrossSectionArea = self.var.TotalCrossSectionArea - ChanCrossSectionArea
            # Floodplain area [sq m]
            ChanWaterDepth = 2 * ChanCrossSectionArea / (self.var.ChanUpperWidth + self.var.ChanBottomWidth)
            # Water level in channel [m]
            FloodPlainWaterDepth = FloodPlainCrossSectionArea / self.var.FloodPlainWidth
            # Water level on floodplain [m]
            WaterLevelKin = ChanWaterDepth + FloodPlainWaterDepth
            # Total water level [m]
            self.var.WaterLevel = np.where(self.var.IsChannelKinematic, WaterLevelKin, 0)
            # Use WaterLevelKin if kinematic wave routing is used ...
            if option['dynamicWave']:
                self.var.WaterLevel = self.var.WaterLevelDyn
