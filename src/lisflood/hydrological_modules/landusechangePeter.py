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

        self.var.ForestFractionInit = loadmap('ForestFraction')
        self.var.DirectRunoffFractionInit = loadmap('DirectRunoffFraction')
        self.var.WaterFractionInit = loadmap('WaterFraction')
        self.var.IrrigationFractionInit = loadmap('IrrigationFraction')
        self.var.RiceFractionInit = loadmap('RiceFraction')
        self.var.OtherFractionInit = loadmap('OtherFraction')

        self.var.ForestFraction = self.var.ForestFractionInit.copy()
        self.var.DirectRunoffFraction = self.var.DirectRunoffFractionInit.copy()
        self.var.WaterFraction =self.var.WaterFractionInit.copy()
        self.var.IrrigationFraction = self.var.IrrigationFractionInit.copy()
        self.var.RiceFraction = self.var.RiceFractionInit.copy()
        self.var.OtherFraction = self.var.OtherFractionInit.copy()

        self.var.FiveYearDayNo = np.array([1, 1462, 3288, 5115, 6941, 8767, 10593, 12420, 14246, 99999])

#        FiveYearDayNo = [1, 1462, 3288, 5115, 6941, 8767, 10593, 12420, 14246, 99999]
#        FiveYearDayNo = [1, 3, 5, 7, 9, 11, 13, 28, 30, 99999]
#        self.var.ForestFractionChange = []   # forest fraction change since start
#        self.var.DirectRunoffFractionChange = []   # direct runoff fraction change since start
#        self.var.WaterFractionChange = []   # water fraction change since start
#        self.var.IrrigationFractionChange = []   # irrigation fraction change since start
#        self.var.RiceFractionChange = []   # rice fraction change since start
#        self.var.OtherFractionChange = []   # other fraction change since start

#        self.var.FiveYearTrick = []

#        self.var.FiveYearTrick.append(9)
#        j = 0
#        for i in xrange(1, 99998):
#                if i >= FiveYearDayNo[j + 1]:
#                    j += 1
#                self.var.FiveYearTrick.append(j)
#        j = 0
#        for i in xrange(9):
#                FractionName = generateName(binding['ForestFractionChangeMaps'], FiveYearDayNo[i])
#                self.var.ForestFractionChange.append(loadLAI(binding['ForestFractionChangeMaps'], FractionName, i))

#                FractionName = generateName(binding['DirectRunoffFractionChangeMaps'], FiveYearDayNo[i])
#                self.var.DirectRunoffFractionChange.append(loadLAI(binding['DirectRunoffFractionChangeMaps'], FractionName, i))

#                FractionName = generateName(binding['WaterFractionChangeMaps'], FiveYearDayNo[i])
#                self.var.WaterFractionChange.append(loadLAI(binding['WaterFractionChangeMaps'], FractionName, i))

#                FractionName = generateName(binding['IrrigationFractionChangeMaps'], FiveYearDayNo[i])
#                self.var.IrrigationFractionChange.append(loadLAI(binding['IrrigationFractionChangeMaps'], FractionName, i))

#                FractionName = generateName(binding['RiceFractionChangeMaps'], FiveYearDayNo[i])
#                self.var.RiceFractionChange.append(loadLAI(binding['RiceFractionChangeMaps'], FractionName, i))

#                FractionName = generateName(binding['OtherFractionChangeMaps'], FiveYearDayNo[i])
#                self.var.OtherFractionChange.append(loadLAI(binding['OtherFractionChangeMaps'], FractionName, i))

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):

     if option['LandUseChange']:

        """ dynamic part of the landusechange module
        """

        FiveYearIndex = np.where(self.var.FiveYearDayNo <= self.var.currentTimeStep()) [0][-1]
            # this creates an index 0 for time 1-1461, index 1 for 1462-3287 etc

        self.var.ForestFraction = self.var.ForestFractionInit + self.var.ForestFractionChange[FiveYearIndex]
        self.var.DirectRunoffFraction = self.var.DirectRunoffFractionInit + self.var.DirectRunoffFractionChange[FiveYearIndex]
        self.var.WaterFraction = self.var.WaterFractionInit + self.var.WaterFractionChange[FiveYearIndex]
        self.var.IrrigationFraction = self.var.IrrigationFractionInit + self.var.IrrigationFractionChange[FiveYearIndex]
        self.var.RiceFraction = self.var.RiceFractionInit + self.var.RiceFractionChange[FiveYearIndex]
        self.var.OtherFraction = self.var.OtherFractionInit + self.var.OtherFractionChange[FiveYearIndex]

#        self.var.ForestFraction = self.var.ForestFractionInit+ self.var.ForestFractionChange[self.var.FiveYearTrick[self.var.currentTimeStep()]]
#        self.var.DirectRunoffFraction = self.var.DirectRunoffFractionInit + self.var.DirectRunoffFractionChange[self.var.FiveYearTrick[self.var.currentTimeStep()]]
#        self.var.WaterFraction = self.var.WaterFractionInit+ self.var.WaterFractionChange[self.var.FiveYearTrick[self.var.currentTimeStep()]]
#        self.var.IrrigationFraction = self.var.IrrigationFractionInit+ self.var.IrrigationFractionChange[self.var.FiveYearTrick[self.var.currentTimeStep()]]
#        self.var.RiceFraction = self.var.RiceFractionInit+ self.var.RiceFractionChange[self.var.FiveYearTrick[self.var.currentTimeStep()]]
#        self.var.OtherFraction = self.var.OtherFractionInit+ self.var.OtherFractionChange[self.var.FiveYearTrick[self.var.currentTimeStep()]]
