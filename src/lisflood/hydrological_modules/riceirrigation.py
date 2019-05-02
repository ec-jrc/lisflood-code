# -------------------------------------------------------------------------
# Name:        Rice irrigation loss module
# Purpose:
#
# Author:      burekpe
#
# Created:     03.02.2015
# Copyright:   (c) burekpe 2015
# Licence:     <your licence>
# -------------------------------------------------------------------------


from pcraster import*
from pcraster.framework import *
import sys
import os
import string
import math


from lisflood.global_modules.zusatz import *
from lisflood.global_modules.add1 import *
from lisflood.global_modules.globals import *


class riceirrigation(object):

    """
    # ************************************************************
    # ***** Rice irrigation   ************************************
    # ************************************************************
    """

    def __init__(self, riceirrigation_variable):
        self.var = riceirrigation_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the rice irrigation module
        """
        self.var.PaddyRiceWaterAbstractionFromSurfaceWaterM3 = globals.inZero.copy()

        if option['riceIrrigation']:

        # ************************************************************
        # ***** PADDY RICE IRRIGATION AND ABSTRACTION ******************
        # ************************************************************

        # Additional water for paddy rice cultivation is calculated seperately, as well as additional open water evaporation from rice fields
            # self.var.RiceFlooding = loadmap('RiceFlooding') #original
            self.var.RiceFlooding = loadmap('RiceFlooding')
            # 10 mm for 10 days (total 10cm water)
            # self.var.RicePercolation = loadmap('RicePercolation') #original
            self.var.RicePercolation = loadmap('RicePercolation')
            # FAO: percolation for heavy clay soils: PERC = 2 mm/day

            self.var.RicePlantingDay1 = loadmap('RicePlantingDay1')
            # starting day (of the year) of first rice planting
            self.var.RiceHarvestDay1 = loadmap('RiceHarvestDay1')
            # starting day (of the year) of first rice harvest

            self.var.RicePlantingDay2 = loadmap('RicePlantingDay2')
             # starting day (of the year) of second rice planting
            self.var.RiceHarvestDay2 = loadmap('RiceHarvestDay2')
             # starting day (of the year) of 2nd rice harvest



    def dynamic(self):
        """ dynamic part of the rice irrigation routine
           inside the water abstraction routine
        """


        if option['riceIrrigation']:

        # water needed for paddy rice is assumed to consist of:
            # phase 1: field preparation: soil saturation (assumed to happen in 10 days, 20 days before planting)
            # phase 2: flood fields (assumed to happen in 10 days, 10 days before planting)
            # phase 3: planting, while keep constant water level during growing season (open water evaporation)
            # phase 4: stop keeping constant water level 20 days before harvest date
            # phase 5: start draining 10 days before harvest date

	        #RiceSoilSaturationDemandM3=(WS1-W1Loop1+WS2-W2Loop1)*RiceFraction*MMtoM3;
            # RiceSoilSaturationDemandM3 = (self.var.WS1[0]-self.var.W1[0] +  self.var.WS2[0]-self.var.W2[0]) * self.var.RiceFraction * self.var.MMtoM3 #original
            RiceSoilSaturationDemandM3 = (self.var.WS1[0] - self.var.W1[0] + self.var.WS2[0] - self.var.W2[0]) * self.var.RiceFraction * self.var.MMtoM3 * self.var.DtDay
            # this part is using the whole other fraction to calculate the demand -> an rice only soil part is needed
            # RiceIrrigationDemandM3 unit is m3 per time interval [m3/dt]

            pl_20 = self.var.RicePlantingDay1-20
            pl_20 = np.where(pl_20 <0, 365+pl_20,pl_20)
            pl_10 = self.var.RicePlantingDay1-10
            pl_10 = np.where(pl_10 <0, 365+pl_10,pl_10)

            ha_20 = self.var.RiceHarvestDay1 - 20
            ha_20 = np.where(ha_20 < 0, 365+ha_20,ha_20)
            ha_10 = self.var.RiceHarvestDay1 - 10
            ha_10 = np.where(ha_10 < 0, 365+ha_10,ha_10)

             # for Europe ok, but for Global planting can be on the 330 and harvest on the 90, so harvest < planting
             # or riceplanting = 5 => riceplanting -20 =350 ==> riceplanting < riceplanting -20

            """ phase 1: field preparation: soil saturation (assumed to happen in 10 days, 20 days before planting)"""
            # RiceSoilSaturationM3=if((CalendarDay ge (RicePlantingDay1-20)) and (CalendarDay le (RicePlantingDay1-10)),0.1*RiceSoilSaturationDemandM3,0)
            RiceSoilSaturationM3 = np.where((self.var.CalendarDay >= pl_20) & (self.var.CalendarDay < pl_10), 0.1*RiceSoilSaturationDemandM3, globals.inZero)
            #RiceFloodingM3=if((CalendarDay ge (RicePlantingDay1-10)) and (CalendarDay le (RicePlantingDay1)),(RiceFlooding+EWRef)*RiceFraction*MMtoM3,0)

            RiceEva = self.var.EWRef - (self.var.ESAct[0]+self.var.Ta[0])
            RiceEva = np.maximum(RiceEva,0)
            RiceEvaporationDemandM3 = RiceEva * self.var.RiceFraction*self.var.MMtoM3   # m3 per time interval
               # should not happen, but just to be sure that this doesnt go <0
               # part of the evaporation is already taken out in soil module!
               # substracting the soil evaporation and transpiration which was already taken off in the soil module

            RiceFloodingDemandM3 = self.var.RiceFlooding * self.var.RiceFraction * self.var.MMtoM3 * self.var.DtDay     # m3 per time interval

            """ phase 2: flood fields (assumed to happen in 10 days, 10 days before planting)"""
            
            # RiceFloodingM3 = np.where((self.var.CalendarDay >= pl_10) & (self.var.CalendarDay < self.var.RicePlantingDay1), (self.var.RiceFlooding+RiceEva)*self.var.RiceFraction*self.var.MMtoM3, globals.inZero) #original
            RiceFloodingM3 = np.where((self.var.CalendarDay >= pl_10) & (self.var.CalendarDay < self.var.RicePlantingDay1),RiceFloodingDemandM3+RiceEvaporationDemandM3,globals.inZero) #m3 per time interval
            # part of the evaporation is already taken out in soil module!
               # assumption is that a fixed water layer is kept on the rice fields, totalling RiceFlooding*10 in mmm (typically 50 or 100 mm)
               # application is spread out over 10 days
               # open water evaporation at the same time


            """ phase 3: planting, while keep constant water level during growing season (open water evaporation) """
            #RiceEvaporationM3=if((CalendarDay ge RicePlantingDay1) and (CalendarDay le (RiceHarvestDay1-20)),EWRef*RiceFraction*MMtoM3,0)
            # RiceEvaporationM3 = np.where((self.var.CalendarDay >= self.var.RicePlantingDay1) & (self.var.CalendarDay < ha_20), RiceEva * self.var.RiceFraction*self.var.MMtoM3 , globals.inZero) #original
            RiceEvaporationM3 = np.where((self.var.CalendarDay >= self.var.RicePlantingDay1) & (self.var.CalendarDay < ha_20),RiceEvaporationDemandM3, globals.inZero)  #m3 per time interval

            # substracting the soil evaporation which was already taken off in the soil module (also transpitation should be tyaken off )

            #RicePercolationM3=if((CalendarDay ge RicePlantingDay1) and (CalendarDay le (RiceHarvestDay1-20)),RicePercolation*RiceFraction*MMtoM3,0)
            RicePercolationDemandM3 = self.var.RicePercolation * self.var.RiceFraction * self.var.MMtoM3 * self.var.DtDay   # m3 per time interval
            # RicePercolationM3 = np.where((self.var.CalendarDay >= self.var.RicePlantingDay1) & (self.var.CalendarDay < ha_20), self.var.RicePercolation*self.var.RiceFraction*self.var.MMtoM3, globals.inZero) #original
            RicePercolationM3 = np.where((self.var.CalendarDay >= self.var.RicePlantingDay1) & (self.var.CalendarDay < ha_20),RicePercolationDemandM3, globals.inZero)  # m3 per time interval
            # FAO: percolation for heavy clay soils: PERC = 2 mm/day
            self.var.PaddyRiceWaterAbstractionFromSurfaceWaterM3 = RiceSoilSaturationM3 + RiceFloodingM3 + RiceEvaporationM3 + RicePercolationM3    # m3 per time interval
               # m3 water needed for paddyrice

            #self.var.TotalAbstractionFromSurfaceWaterM3 = self.var.PaddyRiceWaterAbstractionFromSurfaceWaterM3
                
            """# phase 4: stop keeping constant water level 20 days before harvest date
                 phase 5: start draining 10 days before harvest date"""
            #RiceDrainageM3=if((CalendarDay ge (RiceHarvestDay1-10)) and (CalendarDay le RiceHarvestDay1),(WS1-WFC1+WS2-WFC2)*RiceFraction*MMtoM3,0)
            
            RiceDrainageDemandM3 = (self.var.WS1[0]-self.var.WFC1[0] + self.var.WS2[0]-self.var.WFC2[0]) * self.var.RiceFraction*self.var.MMtoM3 * self.var.DtDay   # m3 per time interval
            RiceDrainageM3 = np.where((self.var.CalendarDay >= ha_10) & (self.var.CalendarDay < self.var.RiceHarvestDay1),0.1 * RiceDrainageDemandM3,globals.inZero)
            # RiceDrainageM3 = np.where((self.var.CalendarDay >= ha_10) & (self.var.CalendarDay < self.var.RiceHarvestDay1),
            #                          0.1 * (self.var.WS1[0]-self.var.WFC1[0] + self.var.WS2[1]-self.var.WFC2[1]) * self.var.RiceFraction*self.var.MMtoM3,globals.inZero) #original

                # drainage until FC to soil/groundwater at end of season
                # assumption that the last weeks before harvest the 50mm water layer is completely evaporating
                # needs to be transported to channel system or being drained

            #UZLoop1 += cover((RiceDrainageM3+RicePercolationM3)*M3toMM/OtherFraction,0)
            self.var.UZ[0] += np.where(self.var.OtherFraction > 0.0,(RiceDrainageM3+RicePercolationM3)*self.var.M3toMM/self.var.OtherFraction,0.0)



 #           self.var.UZ[0] += (RicePercolationM3)*self.var.M3toMM/self.var.OtherFraction
              # drained water is added to Upper Zone





