# -------------------------------------------------------------------------
# Name:        lakes module
# Purpose:
#
# Author:      burekpe
#
# Created:     29.03.2014
# Copyright:   (c) burekpe 2014
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


class lakes(object):

    """
    # ************************************************************
    # ***** LAKES        *****************************************
    # ************************************************************
    """

    def __init__(self, lakes_variable):
        self.var = lakes_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the lakes module
        """

        # ************************************************************
        # ***** LAKES
        # ************************************************************


        if option['simulateLakes']:

            LakeSitesC = loadmap('LakeSites')


            LakeSitesC[LakeSitesC < 1] = 0
            LakeSitesC[self.var.IsChannel == 0] = 0
            #self.var.LakeSites = ifthen((defined(self.var.LakeSites) & boolean(decompress(self.var.IsChannel))), self.var.LakeSites)
            # Get rid of any lakes that are not part of the channel network

            
            # mask lakes sites when using sub-catchments mask
            self.var.LakeSitesCC = np.compress(LakeSitesC>0,LakeSitesC)
            self.var.LakeIndex = np.nonzero(LakeSitesC)[0]

            if self.var.LakeSitesCC.size==0:
                option['simulateLakes']=False
                option['repsimulateLakes']=False
                return
            # break if no lakes


            self.var.IsStructureKinematic = np.where(LakeSitesC > 0 , np.bool8(1),self.var.IsStructureKinematic)
            #self.var.IsStructureKinematic = ifthenelse(defined(self.var.LakeSites), pcraster.boolean(1), self.var.IsStructureKinematic)
            # Add lake locations to structures map (used to modify LddKinematic
            # and to calculate LddStructuresKinematic)

            #PCRaster part
            #-----------------------
            LakeSitePcr = loadmap('LakeSites',pcr=True)
            LakeSitePcr = ifthen((defined(LakeSitePcr) & boolean(decompress(self.var.IsChannel))), LakeSitePcr)
            IsStructureLake = pcraster.boolean(LakeSitePcr)
            # additional structure map only for lakes to calculate water balance
            self.var.IsUpsOfStructureLake = downstream(self.var.LddKinematic, cover(IsStructureLake, 0))
            # Get all pixels just upstream of lakes
            #-----------------------


            #self.var.LakeInflowOld = cover(ifthen(defined(self.var.LakeSites), upstream(self.var.LddKinematic, self.var.ChanQ)), scalar(0.0))
            self.var.LakeInflowOldCC = np.bincount(self.var.downstruct, weights=self.var.ChanQ)[self.var.LakeIndex]
            # for Modified Puls Method the Q(inflow)1 has to be used. It is assumed that this is the same as Q(inflow)2 for the first timestep
            # has to be checked if this works in forecasting mode!


            LakeArea = lookupscalar(binding['TabLakeArea'], LakeSitePcr)
            LakeAreaC = compressArray(LakeArea)
            self.var.LakeAreaCC = np.compress(LakeSitesC>0,LakeAreaC)

            # Surface area of each lake [m2]
            LakeA = lookupscalar(binding['TabLakeA'], LakeSitePcr)
            LakeAC = compressArray(LakeA) * loadmap('LakeMultiplier')
            self.var.LakeACC = np.compress(LakeSitesC>0,LakeAC)
            # Lake parameter A (suggested  value equal to outflow width in [m])
            # multiplied with the calibration parameter LakeMultiplier



            LakeInitialLevelValue  = loadmap('LakeInitialLevelValue')
            if np.max(LakeInitialLevelValue) == -9999:
                LakeAvNetInflowEstimate = lookupscalar(binding['TabLakeAvNetInflowEstimate'], LakeSitePcr)
                LakeAvNetC = compressArray(LakeAvNetInflowEstimate)
                self.var.LakeAvNetCC = np.compress(LakeSitesC>0,LakeAvNetC)

                LakeStorageIniM3CC = self.var.LakeAreaCC * np.sqrt(self.var.LakeAvNetCC / self.var.LakeACC)
                # Initial lake storage [m3]  based on: S = LakeArea * H = LakeArea
                # * sqrt(Q/a)
                self.var.LakeLevelCC = LakeStorageIniM3CC / self.var.LakeAreaCC
            else:
                self.var.LakeLevelCC = np.compress(LakeSitesC > 0, LakeInitialLevelValue)
                LakeStorageIniM3CC = self.var.LakeAreaCC * self.var.LakeLevelCC
                # Initial lake storage [m3]  based on: S = LakeArea * H

                self.var.LakeAvNetCC = np.compress(LakeSitesC > 0,loadmap('PrevDischarge'))

            # Repeatedly used expressions in lake routine

            # NEW Lake Routine using Modified Puls Method (see Maniak, p.331ff)
            # (Qin1 + Qin2)/2 - (Qout1 + Qout2)/2 = (S2 - S1)/dtime
            # changed into:
            # (S2/dtime + Qout2/2) = (S1/dtime + Qout1/2) - Qout1 + (Qin1 + Qin2)/2
            # outgoing discharge (Qout) are linked to storage (S) by elevation.
            # Now some assumption to make life easier:
            # 1.) storage volume is increase proportional to elevation: S = A * H
            #      H: elevation, A: area of lake
            # 2.) outgoing discharge = c * b * H **2.0 (c: weir constant, b: width)
            #      2.0 because it fits to a parabolic cross section see Aigner 2008
            #      (and it is much easier to calculate (that's the main reason)
            # c for a perfect weir with mu=0.577 and Poleni: 2/3 mu * sqrt(2*g) = 1.7
            # c for a parabolic weir: around 1.8
            # because it is a imperfect weir: C = c* 0.85 = 1.5
            # results in a formular : Q = 1.5 * b * H ** 2 = a*H**2 -> H =
            # sqrt(Q/a)
            self.var.LakeFactor = self.var.LakeAreaCC / (self.var.DtRouting * np.sqrt(self.var.LakeACC))

            #  solving the equation  (S2/dtime + Qout2/2) = (S1/dtime + Qout1/2) - Qout1 + (Qin1 + Qin2)/2
            #  SI = (S2/dtime + Qout2/2) =  (A*H)/DtRouting + Q/2 = A/(DtRouting*sqrt(a)  * sqrt(Q) + Q/2
            #  -> replacement: A/(DtRouting*sqrt(a)) = Lakefactor, Y = sqrt(Q)
            #  Y**2 + 2*Lakefactor*Y-2*SI=0
            # solution of this quadratic equation:
            # Q=sqr(-LakeFactor+sqrt(sqr(LakeFactor)+2*SI))

            self.var.LakeFactorSqr = np.square(self.var.LakeFactor)
            # for faster calculation inside dynamic section

            LakeStorageIndicator = LakeStorageIniM3CC / self.var.DtRouting + self.var.LakeAvNetCC / 2
            # SI = S/dt + Q/2
            self.var.LakeOutflow = np.square(-self.var.LakeFactor + np.sqrt(self.var.LakeFactorSqr + 2 * LakeStorageIndicator))
            # solution of quadratic equation
            # it is as easy as this because:
            # 1. storage volume is increase proportional to elevation
            # 2. Q= a *H **2.0  (if you choose Q= a *H **1.5 you have to solve
            # the formula of Cardano)

            self.var.LakeStorageM3CC = LakeStorageIniM3CC.copy()
            self.var.LakeStorageM3BalanceCC = LakeStorageIniM3CC.copy()

            self.var.LakeStorageIniM3 = globals.inZero.copy()
            self.var.LakeLevel = globals.inZero.copy()
            np.put(self.var.LakeStorageIniM3,self.var.LakeIndex,LakeStorageIniM3CC)
            self.var.LakeStorageM3 = self.var.LakeStorageIniM3.copy()
            np.put(self.var.LakeLevel,self.var.LakeIndex,self.var.LakeLevelCC)


            self.var.EWLakeCUMM3 = globals.inZero.copy()
            # Initialising cumulative output variables
            # These are all needed to compute the cumulative mass balance error



    def dynamic_inloop(self,NoRoutingExecuted):
        """ dynamic part of the lake routine
           inside the sub time step routing routine
        """

        # ************************************************************
        # ***** LAKE
        # ************************************************************
        if not(option['InitLisflood']):    # only with no InitLisflood
            if option['simulateLakes']:

                #self.var.LakeInflow = cover(ifthen(defined(self.var.LakeSites), upstream(self.var.LddStructuresKinematic, self.var.ChanQ)), scalar(0.0))
                self.var.LakeInflowCC = np.bincount(self.var.downstruct, weights=self.var.ChanQ)[self.var.LakeIndex]
                # Lake inflow in [m3/s]

                LakeIn = (self.var.LakeInflowCC + self.var.LakeInflowOldCC) * 0.5
                # for Modified Puls Method: (S2/dtime + Qout2/2) = (S1/dtime + Qout1/2) - Qout1 + (Qin1 + Qin2)/2
                #  here: (Qin1 + Qin2)/2
                self.var.LakeInflowOldCC = self.var.LakeInflowCC.copy()
                # Qin2 becomes Qin1 for the next time step

                LakeStorageIndicator = self.var.LakeStorageM3CC /self.var.DtRouting - 0.5 * self.var.LakeOutflow + LakeIn
                # here S1/dtime - Qout1/2 + LakeIn , so that is the right part
                # of the equation above

                self.var.LakeOutflow = np.square( -self.var.LakeFactor + np.sqrt(self.var.LakeFactorSqr + 2 * LakeStorageIndicator))
                # Flow out of lake:
                #  solving the equation  (S2/dtime + Qout2/2) = (S1/dtime + Qout1/2) - Qout1 + (Qin1 + Qin2)/2
                #  SI = (S2/dtime + Qout2/2) =  (A*H)/DtRouting + Q/2 = A/(DtRouting*sqrt(a)  * sqrt(Q) + Q/2
                #  -> replacement: A/(DtRouting*sqrt(a)) = Lakefactor, Y = sqrt(Q)
                #  Y**2 + 2*Lakefactor*Y-2*SI=0
                # solution of this quadratic equation:
                # Q=sqr(-LakeFactor+sqrt(sqr(LakeFactor)+2*SI));


                #self.var.QLakeOutM3Dt = cover(self.var.LakeOutflow * self.var.DtRouting, scalar(0.0))
                QLakeOutM3DtCC = self.var.LakeOutflow * self.var.DtRouting
                # Outflow in [m3] per timestep
                # Needed at every cell, hence cover statement

                self.var.LakeStorageM3CC = (LakeStorageIndicator - self.var.LakeOutflow * 0.5) * self.var.DtRouting
                # Lake storage

                # self.var.LakeStorageM3CC < 0 leads to NaN in state files
                # Check LakeStorageM3CC for negative values and set them to zero
                if any(np.isnan(self.var.LakeStorageM3CC)) or any(self.var.LakeStorageM3CC < 0):
                    msg = "Negative or NaN volume for lake storage set to 0. Increase computation time step for routing (DtSecChannel) \n"
                    print LisfloodWarning(msg)
                    self.var.LakeStorageM3CC[self.var.LakeStorageM3CC < 0] = 0
                    self.var.LakeStorageM3CC[np.isnan(self.var.LakeStorageM3CC)] = 0

                #self.var.LakeStorageM3CC = cover(self.var.LakeStorageM3CC - self.var.EWLakeM3Dt, scalar(0.0))
                # New lake storage [m3] (assuming lake surface area equals bottom area)

                #self.var.LakeStorageM3Balance += LakeIn * self.var.DtRouting - self.var.QLakeOutM3Dt - self.var.EWLakeM3Dt
                self.var.LakeStorageM3BalanceCC += LakeIn * self.var.DtRouting - QLakeOutM3DtCC
                # for mass balance, the lake storage is calculated every time step
                self.var.LakeLevelCC = self.var.LakeStorageM3CC / self.var.LakeAreaCC

                # expanding the size
                self.var.QLakeOutM3Dt = globals.inZero.copy()
                np.put(self.var.QLakeOutM3Dt,self.var.LakeIndex,QLakeOutM3DtCC)



                if option['repsimulateLakes']:
                    if NoRoutingExecuted==0:
                       self.var.LakeInflowM3S = globals.inZero.copy()
                       self.var.LakeOutflowM3S = globals.inZero.copy()
                       self.var.sumLakeInCC =  self.var.LakeInflowCC * self.var.DtRouting
                       self.var.sumLakeOutCC = QLakeOutM3DtCC
                       # for timeseries output - in and outflow to the reservoir is sumed up over the sub timesteps and stored in m/s
                       # set to zero at first timestep
                    else:
                       self.var.sumLakeInCC  += self.var.LakeInflowCC * self.var.DtRouting
                       self.var.sumLakeOutCC += QLakeOutM3DtCC
                       # summing up over all sub timesteps

                if NoRoutingExecuted == (self.var.NoRoutSteps-1):

                    # expanding the size after last sub timestep
                    self.var.LakeStorageM3Balance = globals.inZero.copy()
                    self.var.LakeStorageM3 = globals.inZero.copy()
                    self.var.LakeLevel = globals.inZero.copy()
                    np.put(self.var.LakeStorageM3Balance,self.var.LakeIndex,self.var.LakeStorageM3BalanceCC)
                    np.put(self.var.LakeStorageM3,self.var.LakeIndex,self.var.LakeStorageM3CC)
                    np.put(self.var.LakeLevel,self.var.LakeIndex,self.var.LakeLevelCC)

                    if option['repsimulateLakes']:
                       np.put(self.var.LakeInflowM3S ,self.var.LakeIndex,self.var.sumLakeInCC / self.var.DtSec)
                       np.put(self.var.LakeOutflowM3S,self.var.LakeIndex,self.var.sumLakeOutCC / self.var.DtSec)

