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

from lisflood.global_modules.add1 import *

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

        self.var.ForestFraction = loadmap('ForestFraction',timestampflag='closest')
        self.var.DirectRunoffFraction = loadmap('DirectRunoffFraction',timestampflag='closest')
        self.var.WaterFraction = loadmap('WaterFraction',timestampflag='closest')
        self.var.IrrigationFraction = loadmap('IrrigationFraction',timestampflag='closest')
        self.var.RiceFraction = loadmap('RiceFraction',timestampflag='closest')
        self.var.OtherFraction = loadmap('OtherFraction',timestampflag='closest')


    def dynamic(self):
        """dynamic part of the landusechange module
        """

        if option['TransientLandUseChange']:
            if option['readNetcdfStack']:
                self.var.ForestFraction = readnetcdf(binding['ForestFractionMaps'], self.var.currentTimeStep(),timestampflag='closest')
                self.var.DirectRunoffFraction = readnetcdf(binding['DirectRunoffFractionMaps'], self.var.currentTimeStep(),timestampflag='closest')
                self.var.WaterFraction = readnetcdf(binding['WaterFractionMaps'], self.var.currentTimeStep(),timestampflag='closest')
                self.var.IrrigationFraction = readnetcdf(binding['IrrigationFractionMaps'], self.var.currentTimeStep(),timestampflag='closest')
                self.var.RiceFraction = readnetcdf(binding['RiceFractionMaps'], self.var.currentTimeStep(),timestampflag='closest')
                self.var.OtherFraction = readnetcdf(binding['OtherFractionMaps'], self.var.currentTimeStep(),timestampflag='closest')

                self.var.Test = self.var.RiceFraction*1.0
