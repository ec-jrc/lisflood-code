# -------------------------------------------------------------------------
# Name:        READ METEO input maps
# Purpose:
#
# Author:      burekpe
#
# Created:     12/08/2014
# Copyright:   (c) burekpe 2014
# Licence:     <your licence>
# -------------------------------------------------------------------------

from lisflood.global_modules.add1 import *

class readmeteo(object):

    """
     # ************************************************************
     # ***** READ METEOROLOGICAL DATA              ****************
     # ************************************************************
    """

    def __init__(self, readmeteo_variable):
        self.var = readmeteo_variable

        if option['readNetcdfStack']:
            # checking if time period in netCDF files (forcings) includes simulation period
            checknetcdf(binding['PrecipitationMaps'], binding['StepStart'], binding['StepEnd'] )
            checknetcdf(binding['TavgMaps'], binding['StepStart'], binding['StepEnd'] )
            checknetcdf(binding['ET0Maps'], binding['StepStart'], binding['StepEnd'] )
         #   checknetcdf(binding['ES0Maps'], binding['StepStart'], binding['StepEnd'] )
            checknetcdf(binding['E0Maps'], binding['StepStart'], binding['StepEnd'] )


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the readmeteo module
            read meteo input maps
        """


        # ************************************************************
        # ***** READ METEOROLOGICAL DATA *****************************
        # ************************************************************
        if option['readNetcdfStack']:
            # Read from NetCDF stack files
            self.var.Precipitation = readnetcdf(binding['PrecipitationMaps'], self.var.currentTimeStep()) * self.var.DtDay * self.var.PrScaling
            self.var.Tavg = readnetcdf(binding['TavgMaps'], self.var.currentTimeStep())
            self.var.ETRef = readnetcdf(binding['ET0Maps'], self.var.currentTimeStep()) * self.var.DtDay * self.var.CalEvaporation
            # self.var.ESRef = readnetcdf(binding['ES0Maps'], self.var.currentTimeStep()) * self.var.DtDay * self.var.CalEvaporation
            self.var.EWRef = readnetcdf(binding['E0Maps'], self.var.currentTimeStep()) * self.var.DtDay * self.var.CalEvaporation
        else:
            # Read from stack of maps in Pcraster format
            self.var.Precipitation = readmapsparse(binding['PrecipitationMaps'], self.var.currentTimeStep(), self.var.Precipitation) * self.var.DtDay * self.var.PrScaling
            # precipitation (conversion to [mm] per time step)
            self.var.Tavg = readmapsparse(binding['TavgMaps'], self.var.currentTimeStep(), self.var.Tavg)
            # average DAILY temperature (even if you are running the model on say an hourly time step) [degrees C]
            self.var.ETRef = readmapsparse(binding['ET0Maps'], self.var.currentTimeStep(), self.var.ETRef) * self.var.DtDay * self.var.CalEvaporation
            # daily reference evapotranspiration (conversion to [mm] per time step)
            # self.var.ESRef = readmapsparse(binding['ES0Maps'], self.var.currentTimeStep(), self.var.ESRef) * self.var.DtDay * self.var.CalEvaporation
            # potential evaporation rate from a bare soil surface (conversion to [mm] per time step)
            self.var.EWRef = readmapsparse(binding['E0Maps'], self.var.currentTimeStep(), self.var.EWRef) * self.var.DtDay * self.var.CalEvaporation
            # potential evaporation rate from water surface (conversion to [mm] per time step)

        self.var.ESRef = (self.var.EWRef + self.var.ETRef)/2

        if option['TemperatureInKelvin']:
            self.var.Tavg -= 273.15
