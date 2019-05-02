# -------------------------------------------------------------------------
# Name:        Reservoir module
# Purpose:
#
# Author:      burekpe
#
# Created:     29.03.2014
# Copyright:   (c) burekpe 2014
# Licence:     <your licence>
# -------------------------------------------------------------------------

from lisflood.global_modules.add1 import *

class reservoir(object):

    """
    # ************************************************************
    # ***** RESERVOIR    *****************************************
    # ************************************************************
    """

    def __init__(self, reservoir_variable):
        self.var = reservoir_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the reservoir module
        """
        # ************************************************************
        # ***** RESERVOIRS
        # ************************************************************

        if option['simulateReservoirs']:

            # NoSubStepsRes=max(1,roundup(self.var.DtSec/loadmap('DtSecReservoirs')))
            # Number of sub-steps based on value of DtSecReservoirs,
            # or 1 if DtSec is smaller than DtSecReservoirs
            # DtSubRes=self.var.DtSec/loadmap('NoSubStepsRes')
            # Corresponding sub-timestep (seconds)

            self.var.ReservoirSitesC = loadmap('ReservoirSites')
            self.var.ReservoirSitesC[self.var.ReservoirSitesC < 1] = 0
            self.var.ReservoirSitesC[self.var.IsChannel == 0] = 0
            # Get rid of any reservoirs that are not part of the channel network

            
            # mask reserovoirs sites when using sub-catchments mask
            # ReservoirSitesC_masked = ifthen(self.var.MaskMap,self.var.ReservoirSitesC)
            self.var.ReservoirSitesCC = np.compress(self.var.ReservoirSitesC>0,self.var.ReservoirSitesC)
            self.var.ReservoirIndex = np.nonzero(self.var.ReservoirSitesC)[0]
            
            if self.var.ReservoirSitesC.size==0:
                option['simulateReservoirs']=False
                option['repsimulateReservoirs']=False
                return
            # break if no reservoirs


            self.var.IsStructureKinematic = np.where(self.var.ReservoirSitesC > 0 , np.bool8(1),self.var.IsStructureKinematic)
            #self.var.IsStructureKinematic = ifthenelse(defined(self.var.ReservoirSites), pcraster.boolean(1), self.var.IsStructureKinematic)
            # Add reservoir locations to structures map (used to modify LddKinematic
            # and to calculate LddStructuresKinematic)


            ReservoirSitePcr = loadmap('ReservoirSites',pcr=True)
            self.var.ReservoirSites = ReservoirSitePcr
            ReservoirSitePcr = ifthen((defined(ReservoirSitePcr) & boolean(decompress(self.var.IsChannel))), ReservoirSitePcr)
            # Get rid of any reservoirs that are not part of the channel network
            # (following logic of 'old' code the inflow into these reservoirs is
            # always zero, so either change this or leave them out!)


            TotalReservoirStorageM3 = lookupscalar(binding['TabTotStorage'], ReservoirSitePcr)
            self.var.TotalReservoirStorageM3C = compressArray(TotalReservoirStorageM3)
            self.var.TotalReservoirStorageM3C = np.where(np.isnan(self.var.TotalReservoirStorageM3C),0,self.var.TotalReservoirStorageM3C)
            self.var.TotalReservoirStorageM3CC = np.compress(self.var.ReservoirSitesC > 0, self.var.TotalReservoirStorageM3C)
            # Total storage of each reservoir [m3]

            ConservativeStorageLimit = lookupscalar(binding['TabConservativeStorageLimit'], ReservoirSitePcr)
            ConservativeStorageLimitC = compressArray(ConservativeStorageLimit)
            self.var.ConservativeStorageLimitCC = np.compress(self.var.ReservoirSitesC > 0,ConservativeStorageLimitC)
            # Conservative storage limit (fraction of total storage, [-])

            NormalStorageLimit = lookupscalar(binding['TabNormalStorageLimit'], ReservoirSitePcr)
            NormalStorageLimitC = compressArray(NormalStorageLimit)
            self.var.NormalStorageLimitCC = np.compress(self.var.ReservoirSitesC > 0,NormalStorageLimitC)
            # Normal storage limit (fraction of total storage, [-])

            FloodStorageLimit = lookupscalar( binding['TabFloodStorageLimit'], ReservoirSitePcr)
            FloodStorageLimitC = compressArray(FloodStorageLimit)
            self.var.FloodStorageLimitCC = np.compress(self.var.ReservoirSitesC > 0,FloodStorageLimitC)
            # Flood storage limit (fraction of total storage, [-])

            NonDamagingReservoirOutflow = lookupscalar(binding['TabNonDamagingOutflowQ'], ReservoirSitePcr)
            NonDamagingReservoirOutflowC = compressArray(NonDamagingReservoirOutflow)
            self.var.NonDamagingReservoirOutflowCC = np.compress(self.var.ReservoirSitesC > 0,NonDamagingReservoirOutflowC)
            # Non-damaging reservoir outflow [m3/s]

            NormalReservoirOutflow = lookupscalar( binding['TabNormalOutflowQ'], ReservoirSitePcr)
            NormalReservoirOutflowC = compressArray(NormalReservoirOutflow)
            self.var.NormalReservoirOutflowCC = np.compress(self.var.ReservoirSitesC > 0,NormalReservoirOutflowC)
            # Normal reservoir outflow [m3/s]

            MinReservoirOutflow = lookupscalar(binding['TabMinOutflowQ'], ReservoirSitePcr)
            MinReservoirOutflowC = compressArray(MinReservoirOutflow)
            self.var.MinReservoirOutflowCC = np.compress(self.var.ReservoirSitesC > 0,MinReservoirOutflowC)
            # minimum reservoir outflow [m3/s]


            # Calibration

            adjust_Normal_Flood = loadmap('adjust_Normal_Flood')
            adjust_Normal_FloodC = makenumpy(adjust_Normal_Flood)
            adjust_Normal_FloodCC = np.compress(self.var.ReservoirSitesC > 0, adjust_Normal_FloodC)
              # adjusting the balance between normal and flood storage
              # big value (= closer to flood) results in keeping the normal qoutflow longer constant
            self.var.Normal_FloodStorageLimitCC = self.var.NormalStorageLimitCC + adjust_Normal_FloodCC * ( self.var.FloodStorageLimitCC - self.var.NormalStorageLimitCC)

            ReservoirRnormqMult = loadmap('ReservoirRnormqMult')
            ReservoirRnormqMultC = makenumpy(ReservoirRnormqMult)
            ReservoirRnormqMultCC = np.compress(self.var.ReservoirSitesC > 0, ReservoirRnormqMultC)
            self.var.NormalReservoirOutflowCC = self.var.NormalReservoirOutflowCC * ReservoirRnormqMultCC
               # calibration: all reservoirs normal outflow are multiplied with a factor
            self.var.NormalReservoirOutflowCC = np.where(self.var.NormalReservoirOutflowCC > self.var.MinReservoirOutflowCC,self.var.NormalReservoirOutflowCC,self.var.MinReservoirOutflowCC+0.01)
            self.var.NormalReservoirOutflowCC = np.where(self.var.NormalReservoirOutflowCC < self.var.NonDamagingReservoirOutflowCC,self.var.NormalReservoirOutflowCC,self.var.NonDamagingReservoirOutflowCC-0.01)



            # Repeatedly used expressions in reservoirs routine
            self.var.DeltaO = self.var.NormalReservoirOutflowCC - self.var.MinReservoirOutflowCC
            self.var.DeltaLN = self.var.NormalStorageLimitCC - 2 * self.var.ConservativeStorageLimitCC
            self.var.DeltaLF = self.var.FloodStorageLimitCC -  self.var.NormalStorageLimitCC
            self.var.DeltaNFL = self.var.FloodStorageLimitCC -  self.var.Normal_FloodStorageLimitCC

            #ReservoirInitialFillValue = loadmap('ReservoirInitialFillValue')
            #ReservoirInitialFill = ifthenelse(ReservoirInitialFillValue == -9999, self.var.NormalStorageLimit, ReservoirInitialFillValue)
            ReservoirInitialFillValue = loadmap('ReservoirInitialFillValue')
            if np.max(ReservoirInitialFillValue)==-9999:
               ReservoirInitialFill = self.var.NormalStorageLimitCC,
            else:
                ReservoirInitialFill =  np.compress(self.var.ReservoirSitesC > 0, ReservoirInitialFillValue)

            self.var.ReservoirFillCC = ReservoirInitialFill
            # Initial reservoir fill (fraction of total storage, [-])
            # -9999: assume reservoirs are filled to normal storage limit
            ReservoirStorageIniM3CC = ReservoirInitialFill * self.var.TotalReservoirStorageM3CC
            # Initial reservoir storage [m3] from state or initvalue
            self.var.ReservoirStorageM3CC = ReservoirStorageIniM3CC.copy()
            #self.var.ReservoirFill = ReservoirInitialFill.copy()
            #  Initial fill of reservoirs (fraction of total storage, [-])


            self.var.ReservoirStorageIniM3 = globals.inZero.copy()
            np.put(self.var.ReservoirStorageIniM3,self.var.ReservoirIndex,ReservoirStorageIniM3CC)

            self.var.ReservoirStorageM3 = self.var.ReservoirStorageIniM3


    def dynamic_inloop(self,NoRoutingExecuted):
        """ dynamic part of the lake routine
           inside the sub time step routing routine
        """

        # ************************************************************
        # ***** RESERVOIR
        # ************************************************************

        if option['simulateReservoirs']:

            #
            InvDtSecDay = 1/86400
            # InvDtSecDay=self.var.InvDtSec
            #ReservoirInflow = cover(ifthen(defined(self.var.ReservoirSites), upstream(
            #    self.var.LddStructuresKinematic, self.var.ChanQ)), scalar(0.0))

            ReservoirInflowCC = np.bincount(self.var.downstruct, weights=self.var.ChanQ)[self.var.ReservoirIndex]
            # ReservoirInflow=cover(ifpcr(defined(self.var.ReservoirSites),upstream(self.var.LddStructuresKinematic,self.var.ChanQ)),null)
            # Reservoir inflow in [m3/s]
            # 20-2-2006: Replaced ChanQKin by ChanQ (if this results in problems change back to ChanQKin!)
            # 21-2-2006: Inflow now taken from 1st upstream cell(s), using LddStructuresKinematic
            # (LddStructuresKinematic equals LddKinematic, but without the pits/sinks upstream of the structure
            # locations; note that using Ldd here instead would introduce MV!)

            QResInM3Dt = ReservoirInflowCC * self.var.DtRouting
            # Reservoir inflow in [m3] per timestep (routing step)


            self.var.ReservoirStorageM3CC += QResInM3Dt
            # New reservoir storage [m3] = plus inflow for this sub step
            self.var.ReservoirFillCC = self.var.ReservoirStorageM3CC / self.var.TotalReservoirStorageM3CC
            # New reservoir fill (fraction)


            ReservoirOutflow1 = np.minimum( self.var.MinReservoirOutflowCC, self.var.ReservoirStorageM3CC * InvDtSecDay)
            # Reservoir outflow [m3/s] if ReservoirFill le
            # 2*ConservativeStorageLimit

            ReservoirOutflow2 = self.var.MinReservoirOutflowCC + self.var.DeltaO * (self.var.ReservoirFillCC - 2 * self.var.ConservativeStorageLimitCC) / self.var.DeltaLN
            # Reservoir outflow [m3/s] if NormalStorageLimit le ReservoirFill
            # gt 2*ConservativeStorageLimit

            ReservoirOutflow3a = self.var.NormalReservoirOutflowCC
            ReservoirOutflow3b = self.var.NormalReservoirOutflowCC + ((self.var.ReservoirFillCC - self.var.Normal_FloodStorageLimitCC)
                                / self.var.DeltaNFL) * (self.var.NonDamagingReservoirOutflowCC - self.var.NormalReservoirOutflowCC)
            # Reservoir outflow [m3/s] if FloodStorageLimit le ReservoirFill gt NormalStorageLimit
            # NEW 24-9-2004: linear transition between normal and non-damaging
            # outflow.
            #ReservoirOutflow4 = np.maximum((self.var.ReservoirFillCC - self.var.FloodStorageLimitCC) *
            #    self.var.TotalReservoirStorageM3CC * self.var.InvDtSec, self.var.NonDamagingReservoirOutflowCC)
            temp = np.minimum(self.var.NonDamagingReservoirOutflowCC,np.maximum(ReservoirInflowCC * 1.2,self.var.NormalReservoirOutflowCC))
            ReservoirOutflow4 = np.maximum((self.var.ReservoirFillCC - self.var.FloodStorageLimitCC-0.01) *
                                           self.var.TotalReservoirStorageM3CC * InvDtSecDay, temp)



            # Reservoir outflow [m3/s] if ReservoirFill gt FloodStorageLimit
            # Depending on ReservoirFill the reservoir outflow equals ReservoirOutflow1, ReservoirOutflow2,
            # ReservoirOutflow3 or ReservoirOutflow4




            ReservoirOutflow = ReservoirOutflow1.copy()
            ReservoirOutflow = np.where(self.var.ReservoirFillCC > 2 * self.var.ConservativeStorageLimitCC,
                                ReservoirOutflow2, ReservoirOutflow)
           # ReservoirOutflow = np.where(self.var.ReservoirFillCC > self.var.NormalStorageLimitCC,
           #                     ReservoirOutflow3, ReservoirOutflow)

            ReservoirOutflow = np.where(self.var.ReservoirFillCC > self.var.NormalStorageLimitCC,
                                ReservoirOutflow3a, ReservoirOutflow)
            ReservoirOutflow = np.where(self.var.ReservoirFillCC > self.var.Normal_FloodStorageLimitCC,
                                ReservoirOutflow3b, ReservoirOutflow)

            ReservoirOutflow = np.where(self.var.ReservoirFillCC > self.var.FloodStorageLimitCC,
                                ReservoirOutflow4, ReservoirOutflow)


            temp = np.minimum(ReservoirOutflow,np.maximum(ReservoirInflowCC,self.var.NormalReservoirOutflowCC))

            ReservoirOutflow = np.where((ReservoirOutflow > 1.2 * ReservoirInflowCC) &
                                        (ReservoirOutflow > self.var.NormalReservoirOutflowCC) &
                                        (self.var.ReservoirFillCC < self.var.FloodStorageLimitCC), temp, ReservoirOutflow)
#           ReservoirOutflow = np.minimum(ReservoirOutflow,np.maximum(ReservoirInflowCC,self.var.NormalReservoirOutflowCC))


            QResOutM3DtCC = ReservoirOutflow * self.var.DtRouting
            # Reservoir outflow in [m3] per sub step
            QResOutM3DtCC = np.minimum(QResOutM3DtCC, self.var.ReservoirStorageM3CC)
            # Check to prevent outflow from becoming larger than storage +
            # inflow
            QResOutM3DtCC = np.maximum(QResOutM3DtCC, self.var.ReservoirStorageM3CC - self.var.TotalReservoirStorageM3CC)

            # NEW 24-9-2004: Check to prevent reservoir storage from exceeding total capacity
            # expression to the right of comma always negative unless capacity is exceeded

            #self.var.ReservoirStorageM3CC += QResInM3Dt - QResOutM3DtCC
            self.var.ReservoirStorageM3CC -= QResOutM3DtCC
            # New reservoir storage [m3]
            self.var.ReservoirFillCC = self.var.ReservoirStorageM3CC / self.var.TotalReservoirStorageM3CC
            # New reservoir fill


            # CM: Check ReservoirStorageM3CC for negative values and set them to zero
            nel = len(self.var.ReservoirFillCC[:])
            for i in range(0,nel-1):
                if np.isnan(self.var.ReservoirFillCC[i]) or self.var.ReservoirFillCC[i] < 0:
                    msg = "Negative or NaN volume for reservoir fill set to 0. Increase computation time step for routing (DtSecChannel) \n"
                    print LisfloodError(msg)
                    self.var.ReservoirFillCC[self.var.ReservoirFillCC < 0] = 0
                    self.var.ReservoirFillCC[np.isnan(self.var.ReservoirFillCC)] = 0


            # expanding the size as input for routing routine
            self.var.QResOutM3Dt = globals.inZero.copy()
            np.put(self.var.QResOutM3Dt,self.var.ReservoirIndex,QResOutM3DtCC)
                # this is put to the channel again at each sub timestep



            if option['repsimulateReservoirs']:
                if NoRoutingExecuted==0:
                    self.var.ReservoirInflowM3S = globals.inZero.copy()
                    self.var.ReservoirOutflowM3S = globals.inZero.copy()
                    self.var.sumResInCC = QResInM3Dt
                    self.var.sumResOutCC = QResOutM3DtCC
                    # for timeseries output - in and outflow to the reservoir is sumed up over the sub timesteps and stored in m/s
                    # set to zero at first timestep
                else:
                    self.var.sumResInCC  += QResInM3Dt
                    self.var.sumResOutCC += QResOutM3DtCC
                    # summing up over all sub timesteps

            if NoRoutingExecuted == (self.var.NoRoutSteps-1):

                # expanding the size after last sub timestep
                self.var.ReservoirStorageM3 = globals.inZero.copy()
                self.var.ReservoirFill = globals.inZero.copy()
                np.put(self.var.ReservoirStorageM3,self.var.ReservoirIndex,self.var.ReservoirStorageM3CC)
                np.put(self.var.ReservoirFill,self.var.ReservoirIndex,self.var.ReservoirFillCC)

                if option['repsimulateReservoirs']:
                    np.put(self.var.ReservoirInflowM3S ,self.var.ReservoirIndex,self.var.sumResInCC / self.var.DtSec)
                    np.put(self.var.ReservoirOutflowM3S,self.var.ReservoirIndex,self.var.sumResOutCC / self.var.DtSec)



