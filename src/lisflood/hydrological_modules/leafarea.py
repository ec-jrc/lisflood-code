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

        self.var.kgb = 0.75 * loadmap('kdf')
        # extinction coefficient for global solar radiation [-]
        # kdf= extinction coefficient for diffuse visible light [-], varies between
        # 0.4 and 1.1

        # LAINr=[1,32,60,91,121,152,182,213,244,274,305,335,370]
        LAINr = [1, 11, 21, 32, 42, 52, 60, 70, 80, 91, 101, 111, 121, 131, 141, 152, 162, 172, 182,
                 192, 202, 213, 223, 233, 244, 254, 264, 274, 284, 294, 305, 315, 325, 335, 345, 355, 370]

        self.var.LAIX = [[0 for x in range(36)] for x in range(3)]
        self.var.LAI = [0, 0]
        self.var.L1 = []

        # self.var.L1.append(36)
        j = 0
        for i in range(367):
            if i >= LAINr[j + 1]:
                j += 1
            self.var.L1.append(j)
            # print i,self.L1[i],LAINr1[self.L1[i]]
        settings = LisSettings.instance()
        binding = settings.binding
        for i in range(36):
            LAIName = generateName(binding['LAIOtherMaps'], LAINr[i])
            self.var.LAIX[0][i] = loadLAI(binding['LAIOtherMaps'], LAIName, i)

            LAIName = generateName(binding['LAIForestMaps'], LAINr[i])
            self.var.LAIX[1][i] = loadLAI(binding['LAIForestMaps'], LAIName, i)

            LAIName = generateName(binding['LAIIrrigationMaps'], LAINr[i])
            self.var.LAIX[2][i] = loadLAI(binding['LAIIrrigationMaps'], LAIName, i)

# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the leaf area index module
        """

        i = self.var.L1[self.var.CalendarDay]
        self.var.LAI = [self.var.LAIX[0][i], self.var.LAIX[1][i], self.var.LAIX[2][i]]

        # Leaf Area Index, average over whole pixel [m2/m2]
        self.var.LAITerm = [np.exp(-self.var.kgb * self.var.LAI[0]), np.exp(-self.var.kgb * self.var.LAI[1]), np.exp(-self.var.kgb * self.var.LAI[2])]
