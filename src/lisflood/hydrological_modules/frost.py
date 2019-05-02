# -------------------------------------------------------------------------
# Name:        FROST INDEX IN SOIL module
# Purpose:
#
# Author:      burekpe
#
# Created:     04/03/2014
# Copyright:   (c) burekpe 2014
# Licence:     <your licence>
# -------------------------------------------------------------------------


from pcraster import*
from pcraster.framework import *
import sys
import os
import string
import math
from time import *


from lisflood.global_modules.zusatz import *
from lisflood.global_modules.add1 import *
from lisflood.global_modules.globals import *


class frost(object):

    """
    # ************************************************************
    # ***** FROST INDEX IN SOIL **********************************
    # ************************************************************
    # Domain: whole pixel (permeable + direct runoff areas)
    """

    def __init__(self, frost_variable):
        self.var = frost_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------


    def initial(self):
        """ initial part of the frost index module
        """

        self.var.Kfrost = loadmap('Kfrost')
        self.var.Afrost = loadmap('Afrost')
        self.var.FrostIndexThreshold = loadmap('FrostIndexThreshold')
        self.var.SnowWaterEquivalent = loadmap('SnowWaterEquivalent')

        # FrostIndexInit=ifthen(defined(self.var.MaskMap),scalar(loadmap('FrostIndexInitValue')))
        # self.var.FrostIndex=FrostIndexInit
        self.var.FrostIndex = loadmap('FrostIndexInitValue')
        # self.var.AfrostIndex=-(1-self.var.Afrost)*self.var.FrostIndex
        # initial Frost Index value
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the frost index module
        """
        # FrostIndexChangeRate=-(1-Afrost)*FrostIndex - Tavg*exp(-0.04*Kfrost*SnowCover/SnowWaterEquivalent);

        FrostIndexChangeRate = -(1 - self.var.Afrost) * self.var.FrostIndex - self.var.Tavg * \
            np.exp(-0.04 * self.var.Kfrost * self.var.SnowCover / self.var.SnowWaterEquivalent)
        # FrostIndexChangeRate=self.var.AfrostIndex - self.var.Tavg*      pcraster.exp(self.var.Kfrost*self.var.SnowCover*self.var.InvSnowWaterEquivalent)
        # Rate of change of frost index (expressed as rate, [degree days/day])
        # CHANGED 9 September 2004:
        # - first term should be negative
        # - second term should be subtracted, not added!!

        self.var.FrostIndex = np.maximum(self.var.FrostIndex + FrostIndexChangeRate * self.var.DtDay, 0)
        # frost index in soil [degree days]
        # based on Molnau and Bissel (1983, A Continuous Frozen Ground Index for Flood
        # Forecasting. In: Maidment, Handbook of Hydrology, p. 7.28, 7.55)
        # if Tavg is above zero, FrostIndex will stay 0
        # if Tavg is negative, FrostIndex will increase with 1 per degree C per day
        # Exponent of 0.04 (instead of 0.4 in HoH): conversion [cm] to [mm]!
        # Division by SnowDensity because SnowDepth is expressed as equivalent water
        # depth(always less than depth of snow pack)
        # SnowWaterEquivalent taken as 0.100 (based on density of 100 kg/m3) (Handbook of Hydrology, p. 7.5)
        # Afrost, (daily decay coefficient) is taken as 0.97 (Handbook of Hydrology,
        # p. 7.28)
        # Kfrost, (snow depth reduction coefficient) is taken as 0.57 [1/cm],
        # (HH, p. 7.28)
