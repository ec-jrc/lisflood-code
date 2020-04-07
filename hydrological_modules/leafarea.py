# -------------------------------------------------------------------------
# Name:        LEAF AREA INDEX (LAI) module
# Purpose:
#
# Author:      burekpe
#
# Created:     04/03/2014
# Copyright:   (c) burekpe 2014
# Licence:     <your licence>
# -------------------------------------------------------------------------

from global_modules.add1 import *
from collections import OrderedDict
import xarray as xr

class leafarea(object):

    """
   # ************************************************************
   # ***** LEAF AREA INDEX DATA ****************************
   # ************************************************************
    """

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
        num_lai_steps = len(LAINr) - 1
        coord_prescribed = OrderedDict([("interval", range(num_lai_steps))])
        coord_prescribed.update(self.var.coord_prescribed_vegetation)
        self.var.LAIX = xr.DataArray(np.zeros([len(v) for v in coord_prescribed.values()]),
                                     coords=coord_prescribed, dims=coord_prescribed.keys())
        for i in self.var.LAIX.interval.values:
            for veg, map_name in PRESCRIBED_LAI.items():
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
        lai = self.var.LAIX.loc[self.var.L1[self.var.CalendarDay]].copy()
        self.var.LAI.loc[self.var.prescribed_vegetation] = lai
        # LAI term used for evapotranspiration calculations
        self.var.LAITerm = np.exp(-self.var.kgb * lai)
