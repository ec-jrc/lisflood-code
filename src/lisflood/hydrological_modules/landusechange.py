# -------------------------------------------------------------------------
# Name:        Land Use Change module
# Purpose:
#
# Author:      Ad de Roo
#
# Created:     28/07/2015
# Copyright:   (c) JRC 2015
# Licence:     <your licence>
# -------------------------------------------------------------------------

from global_modules.add1 import *
from collections import OrderedDict
import pandas as pd
import xarray as xr

class landusechange(object):

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

    def __init__(self, landusechange_variable):
        self.var = landusechange_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the landusechange module
        """
        self.var.DirectRunoffFraction = loadmap('DirectRunoffFraction')
        self.var.WaterFraction = loadmap('WaterFraction')
        self.var.RiceFraction = loadmap('RiceFraction') # TO BE INCLUDED IN IRRIGATED? OR KEEP SPECIAL TREATMENT?
        # Soil fraction split into: "Rainfed" (previously "Other"), "Forest", "Irrigated".
        soil = OrderedDict([(name, loadmap(LANDUSE_INPUTMAP[VEGETATION_LANDUSE[name]])) for name in self.var.prescribed_vegetation])
        self.var.SoilFraction = xr.DataArray(pd.DataFrame(soil).T, coords=self.var.coord_prescribed_vegetation, dims=self.var.coord_prescribed_vegetation.keys())
        # Interactive crop fractions (if EPIC is active)
        if option["cropsEPIC"]:
            self.var.crop_module.setSoilFractions()


    def dynamic(self):
        """ dynamic part of the landusechange module"""
        if option['TransientLandUseChange']:
            if option["cropsEPIC"]:
                raise Exception("Land use change for EPIC crops not implemented yet!")
            time_step = self.var.currentTimeStep()
            self.var.DirectRunoffFraction = readnetcdf(binding['DirectRunoffFractionMaps'], time_step)
            self.var.WaterFraction = readnetcdf(binding['WaterFractionMaps'], time_step)
            self.var.RiceFraction = readnetcdf(binding['RiceFractionMaps'], time_step)
            soil = OrderedDict([(name, readnetcdf(binding[LANDUSE_INPUTMAP[VEGETATION_LANDUSE[name]] + "Maps"], time_step)) for name in self.var.prescribed_vegetation])
            self.var.SoilFraction = xr.DataArray(pd.DataFrame(soil).T, coords=self.var.coord_prescribed_vegetation, dims=self.var.coord_prescribed_vegetation.keys())
