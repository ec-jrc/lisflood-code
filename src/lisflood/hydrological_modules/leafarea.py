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
from nine import range

import numpy as np

from ..global_modules.add1 import loadmap, generateName, loadLAI
from ..global_modules.settings import LisSettings
from . import HydroModule
from collections import OrderedDict
import xarray as xr

class leafarea(HydroModule):

    """
   # ************************************************************
   # ***** LEAF AREA INDEX DATA ****************************
   # ************************************************************
    """
    input_files_keys = {'all': ['kdf', 'LAIOtherMaps', 'LAIForestMaps', 'LAIIrrigationMaps']}
    module_name = 'LeafArea'

    def __init__(self, leafarea_variable):
        self.var = leafarea_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the leaf area index module
        """
        # extinction coefficient for global solar radiation [-]
        self.var.kgb = 0.75 * loadmap('kdf') # kdf = extinction coefficient for diffuse visible light [-], varies between 0.4 and 1.1
        # Days delimiting time intervals over which prescribed LAI is constant
        LAINr = [1, 11, 21, 32, 42, 52, 60, 70, 80, 91, 101, 111, 121, 131, 141, 152, 162, 172, 182,
                 192, 202, 213, 223, 233, 244, 254, 264, 274, 284, 294, 305, 315, 325, 335, 345, 355, 370]
        # Prescribed LAI values: for each fraction, the sets of LAI values that are constant over each time interval
        settings = LisSettings.instance()
        binding = settings.binding
        num_lai_steps = len(LAINr) - 1
        coord_prescribed = OrderedDict([("interval", range(num_lai_steps))])
        coord_prescribed.update(self.var.coord_prescribed_vegetation)
        self.var.LAIX = xr.DataArray(np.zeros([len(v) for v in coord_prescribed.values()]),
                                     coords=coord_prescribed, dims=coord_prescribed.keys())
        for i in self.var.LAIX.interval.values:
            for veg, map_name in self.var.PRESCRIBED_LAI.items():
                LAIName = generateName(binding[map_name], LAINr[i])
                self.var.LAIX.loc[i,veg] = loadLAI(binding[map_name], LAIName, i)
        # Calendar day to interval lookup list
        self.var.L1 = []
        j = 0
        for i in range(367):
            if i >= LAINr[j + 1]:
                j += 1
            self.var.L1.append(j)
        # Allocate LAI data structure
        self.var.LAI = self.var.allocateVariableAllVegetation()



    def dynamic(self):
        """ Dynamic part of the leaf area index module.
            Only prescribed vegetation fractions.
            If EPIC is active, "Rainfed_prescribed" and "Irrigated_prescribed" represent the residuals not modelled by EPIC crops.
        """
        # Set prescribed LAI values ()
        lai = self.var.LAIX.sel(interval=self.var.L1[self.var.CalendarDay]).copy()
        ivegvalues = []
        ivegvaluesx = []
        for veg in self.var.prescribed_vegetation:
            ivegvalues.append(self.var.vegetation.index(veg))
            ivegvaluesx.append(self.var.coord_prescribed_vegetation['vegetation'].index(veg))
        self.var.LAI.values[ivegvalues] = lai.values[ivegvaluesx]
        # LAI term used for evapotranspiration calculations
        self.var.LAITerm = np.exp(-self.var.kgb * lai)