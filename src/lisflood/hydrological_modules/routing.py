# -------------------------------------------------------------------------
# Name:        routing module
# Purpose:
#
# Author:      burekpe
#
# Created:     29.03.2014
# Copyright:   (c) burekpe 2014
# Licence:     <your licence>
# -------------------------------------------------------------------------

from lisflood.global_modules.add1 import *

from lisflood.hydrological_modules.lakes import *
from lisflood.hydrological_modules.reservoir import *
from lisflood.hydrological_modules.polder import *
from lisflood.hydrological_modules.inflow import *
from lisflood.hydrological_modules.transmission import *
from lisflood.hydrological_modules.kinematic_wave_parallel import kinematicWave, kwpt



class routing(object):

    """
    # ************************************************************
    # ***** ROUTING      *****************************************
    # ************************************************************
    """

    def __init__(self, routing_variable):
        self.var = routing_variable

        self.lakes_module = lakes(self.var)
        self.reservoir_module = reservoir(self.var)
        self.polder_module = polder(self.var)
        self.inflow_module = inflow(self.var)
        self.transmission_module = transmission(self.var)

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
    def initial(self):
        """ initial part of the routing module
        """

        # ------------------------------------------------
        self.var.avgdis = globals.inZero.copy()
        self.var.Beta = loadmap('beta')
        self.var.InvBeta = 1 / self.var.Beta
        # Inverse of beta for kinematic wave
        self.var.ChanLength = loadmap('ChanLength').astype(float)
        self.var.InvChanLength = 1 / self.var.ChanLength
        # Inverse of channel length [1/m]

        self.var.NoRoutSteps = int(np.maximum(1, round(self.var.DtSec / self.var.DtSecChannel,0)))
        # Number of sub-steps based on value of DtSecChannel,
        # or 1 if DtSec is smaller than DtSecChannel

        if option['InitLisflood']:
            self.var.NoRoutSteps = 1
            # InitLisflood is used!
            # so channel routing step is the same as the general time step
        self.var.DtRouting = self.var.DtSec / self.var.NoRoutSteps
        # Corresponding sub-timestep (seconds)
        self.var.InvDtRouting = 1 / self.var.DtRouting
        self.var.InvNoRoutSteps = 1 / float(self.var.NoRoutSteps)
        # inverse for faster calculation inside the dynamic section

# -------------------------- LDD

        self.var.Ldd = lddmask(loadmap('Ldd',pcr=True,lddflag=True), self.var.MaskMap)
        # Cut ldd to size of MaskMap (NEW, 29/9/2004)
        # Prevents 'unsound' ldd if MaskMap covers sub-area of ldd

        # Count (inverse of) upstream area for each pixel
        # Needed if we want to calculate average values of variables
        # upstream of gauge locations

        self.var.UpArea = accuflux(self.var.Ldd, self.var.PixelAreaPcr)
        # Upstream contributing area for each pixel
        # Note that you might expext that values of UpArea would be identical to
        # those of variable CatchArea (see below) at the outflow points.
        # This is NOT actually the case, because outflow points are shifted 1
        # cell in upstream direction in the calculation of CatchArea!
        self.var.InvUpArea = 1 / self.var.UpArea
        # Calculate inverse, so we can multiply in dynamic (faster than divide)

        self.var.IsChannelPcr = pcraster.boolean(loadmap('Channels',pcr=True))
        self.var.IsChannel = np.bool8(compressArray(self.var.IsChannelPcr))

        # Identify channel pixels
        self.var.IsChannelKinematic = self.var.IsChannel.copy()
        # Identify kinematic wave channel pixels
        # (identical to IsChannel, unless dynamic wave is used, see below)
        #self.var.IsStructureKinematic = pcraster.boolean(0)
        self.var.IsStructureKinematic = np.bool8(globals.inZero.copy())

        # Map that identifies special inflow/outflow structures (reservoirs, lakes) within the
        # kinematic wave channel routing. Set to (dummy) value of zero modified in reservoir and lake
        # routines (if those are used)
        LddChan = lddmask(self.var.Ldd, self.var.IsChannelPcr)
        # ldd for Channel network
        self.var.MaskMap = pcraster.boolean(self.var.Ldd)
        # Use boolean version of Ldd as calculation mask
        # (important for correct mass balance check
        # any water generated outside of Ldd won't reach
        # channel anyway)
        self.var.LddToChan = lddrepair(ifthenelse(self.var.IsChannelPcr, 5, self.var.Ldd))
        # Routing of runoff (incl. ground water)en
        AtOutflow = pcraster.boolean(pit(self.var.Ldd))
        # find outlet points...

        if option['dynamicWave']:
            IsChannelDynamic = pcraster.boolean(loadmap('ChannelsDynamic',pcr=True))
            # Identify channel pixels where dynamic wave is used
            self.var.IsChannelKinematic = (self.var.IsChannelPcr == 1) & (IsChannelDynamic == 0)
            # Identify (update) channel pixels where kinematic wave is used
            self.var.LddKinematic = lddmask(self.var.Ldd, self.var.IsChannelKinematic)
            # Ldd for kinematic wave: ends (pit) just before dynamic stretch
            LddDynamic = lddmask(self.var.Ldd, IsChannelDynamic)
            # Ldd for dynamic wave

            # Following statements produce an ldd network that connects the pits in
            # LddKinematic to the nearest downstream dynamic wave pixel
            LddToDyn = lddrepair(ifthenelse(IsChannelDynamic, 5, self.var.Ldd))
            # Temporary ldd: flow paths end in dynamic pixels
            PitsKinematic = cover(pcraster.boolean(pit(self.var.LddKinematic)), 0)
            # Define start of each flow path at pit on LddKinematic
            PathKinToDyn = path(LddToDyn, PitsKinematic)
            # Identify paths that connect pits in LddKinematic to dynamic wave
            # pixels
            LddKinToDyn = lddmask(LddToDyn, PathKinToDyn)
            # Create ldd
            DynWaveBoundaryCondition = boolean(pit(LddDynamic))
            # NEW 12-7-2005 (experimental)
            # Location of boundary condition dynamic wave

            self.var.AtLastPoint = (downstream(self.var.Ldd, AtOutflow) == 1) & (
            AtOutflow != 1) & self.var.IsChannelPcr

            # NEW 23-6-2005
            # Dynamic wave routine gives no outflow out of pits, so we calculate this
            # one cell upstream (WvD)
            # (implies that most downstream cell is not taken into account in mass balance
            # calculations, even if dyn wave is not used)
            # Only include points that are on a channel (otherwise some small 'micro-catchments'
            # are included, for which the mass balance cannot be calculated
            # properly)



        else:
            self.var.LddKinematic = LddChan
            # No dynamic wave, so kinematic ldd equals channel ldd
            self.var.AtLastPoint = AtOutflow
            self.var.AtLastPointC = np.bool8(compressArray(self.var.AtLastPoint))
            # assign unique identifier to each of them


        lddC = compressArray(self.var.LddKinematic)
        inAr = decompress(np.arange(maskinfo['mapC'][0],dtype="int32"))
        # giving a number to each non missing pixel as id
        self.var.downstruct = (compressArray(downstream(self.var.LddKinematic,inAr))).astype("int32")
        # each upstream pixel gets the id of the downstream pixel
        self.var.downstruct[lddC==5] = maskinfo['mapC'][0]
        # all pits gets a high number
        #d3=np.bincount(self.var.down, weights=loadmap('AvgDis'))[:-1]
          # upstream function in numpy

        OutflowPoints = nominal(uniqueid(self.var.AtLastPoint))
            # and assign unique identifier to each of them
        self.var.Catchments = (compressArray(catchment(self.var.Ldd, OutflowPoints))).astype(np.int32)
        CatchArea = np.bincount(self.var.Catchments, weights=self.var.PixelArea)[self.var.Catchments]
        #CatchArea = CatchArea[self.var.Catchments]
        # define catchment for each outflow point
        #CatchArea = areatotal(self.var.PixelArea, self.var.Catchments)

        # Compute area of each catchment [m2]
        # Note: in earlier versions this was calculated using the "areaarea" function,
        # changed to "areatotal" in order to enable handling of grids with spatially
        # variable cell areas (e.g. lat/lon grids)
        self.var.InvCatchArea = 1 / CatchArea
        # inverse of catchment area [1/m2]

# ************************************************************
# ***** CHANNEL GEOMETRY  ************************************
# ************************************************************

        self.var.ChanGrad = np.maximum(loadmap('ChanGrad'), loadmap('ChanGradMin'))
        # avoid calculation of Alpha using ChanGrad=0: this creates MV!
        self.var.CalChanMan = loadmap('CalChanMan')
        self.var.ChanMan = self.var.CalChanMan * loadmap('ChanMan')
        # Manning's n is multiplied by ChanManCal
        # enables calibration for peak timing
        self.var.ChanBottomWidth = loadmap('ChanBottomWidth')
        ChanDepthThreshold = loadmap('ChanDepthThreshold')
        ChanSdXdY = loadmap('ChanSdXdY')
        self.var.ChanUpperWidth = self.var.ChanBottomWidth + 2 * ChanSdXdY * ChanDepthThreshold
        # Channel upper width [m]
        self.var.TotalCrossSectionAreaBankFull = 0.5 * \
            ChanDepthThreshold * (self.var.ChanUpperWidth + self.var.ChanBottomWidth)
        # Area (sq m) of bank full discharge cross section [m2]
        # (trapezoid area equation)
        TotalCrossSectionAreaHalfBankFull = 0.5 * self.var.TotalCrossSectionAreaBankFull
        # Cross-sectional area at half bankfull [m2]
        # This can be used to initialise channel flow (see below)


        TotalCrossSectionAreaInitValue = loadmap('TotalCrossSectionAreaInitValue')
        self.var.TotalCrossSectionArea = np.where(TotalCrossSectionAreaInitValue == -9999, TotalCrossSectionAreaHalfBankFull, TotalCrossSectionAreaInitValue)
        # Total cross-sectional area [m2]: if initial value in binding equals -9999 the value at half bankfull is used,
        # otherwise TotalCrossSectionAreaInitValue (typically end map from previous simulation)

        if option['SplitRouting']:
            CrossSection2AreaInitValue = loadmap('CrossSection2AreaInitValue')
            self.var.CrossSection2Area = np.where(CrossSection2AreaInitValue == -9999, globals.inZero, CrossSection2AreaInitValue)
            # cross-sectional area [m2] for 2nd line of routing: if initial value in binding equals -9999 the value is set to 0
            # otherwise CrossSection2AreaInitValue (typically end map from previous simulation)

            PrevSideflowInitValue = loadmap('PrevSideflowInitValue')


            self.var.Sideflow1Chan = np.where(PrevSideflowInitValue == -9999, globals.inZero, PrevSideflowInitValue)
            # sideflow from previous run for 1st line of routing: if initial value in binding equals -9999 the value is set to 0
            # otherwise PrevSideflowInitValue (typically end map from previous simulation)

# ************************************************************
# ***** CHANNEL ALPHA (KIN. WAVE)*****************************
# ************************************************************
# Following calculations are needed to calculate Alpha parameter in kinematic
# wave. Alpha currently fixed at half of bankful depth (this may change in
# future versions!)

        ChanWaterDepthAlpha = np.where(self.var.IsChannel, 0.5 * ChanDepthThreshold, 0.0)
        # Reference water depth for calculation of Alpha: half of bankfull
        self.var.ChanWettedPerimeterAlpha = self.var.ChanBottomWidth + 2 * \
            np.sqrt(np.square(ChanWaterDepthAlpha) + np.square(ChanWaterDepthAlpha * ChanSdXdY))
        # Channel wetted perimeter [m](Pythagoras)
        AlpTermChan = (self.var.ChanMan / (np.sqrt(self.var.ChanGrad))) ** self.var.Beta
        self.var.AlpPow = 2.0 / 3.0 * self.var.Beta

        self.var.ChannelAlpha = (AlpTermChan * (self.var.ChanWettedPerimeterAlpha ** self.var.AlpPow)).astype(float)
        self.var.InvChannelAlpha = 1 / self.var.ChannelAlpha
        # ChannelAlpha for kinematic wave

# ************************************************************
# ***** CHANNEL INITIAL DISCHARGE ****************************
# ************************************************************

        self.var.ChanM3 = self.var.TotalCrossSectionArea * self.var.ChanLength
        # channel water volume [m3]
        self.var.ChanIniM3 = self.var.ChanM3.copy()
        self.var.ChanM3Kin = self.var.ChanIniM3.copy().astype(float)
        # Initialise water volume in kinematic wave channels [m3]
        self.var.ChanQKin = np.where(self.var.ChannelAlpha > 0,
             (self.var.TotalCrossSectionArea / self.var.ChannelAlpha) ** self.var.InvBeta, 0).astype(float)


        # Initialise discharge at kinematic wave pixels (note that InvBeta is
        # simply 1/beta, computational efficiency!)

        self.var.CumQ = globals.inZero.copy()
        # ininialise sum of discharge to calculate average

# ************************************************************
# ***** CHANNEL INITIAL DYNAMIC WAVE *************************
# ************************************************************
        if option['dynamicWave']:
            dummy=0
            # TO DO !!!!!!!!!!!!!!!!!!!!

       #     lookchan = lookupstate(TabCrossSections, ChanCrossSections, ChanBottomLevel, self.var.ChanLength,
       #                            DynWaveConstantHeadBoundary + ChanBottomLevel)
       #     ChanIniM3 = ifthenelse(AtOutflow, lookchan, ChanIniM3)
            # Correct ChanIniM3 for constant head boundary in pit (only if
            # dynamic wave is used)
       #     ChanM3Dyn = ChanIniM3
            # Set volume of water in dynamic wave channel to initial value
            # (note that initial condition is expressed as a state in [m3] for the dynamic wave,
            # and as a rate [m3/s] for the kinematic wave (a bit confusing)

            # Estimate number of iterations needed in first time step (based on Courant criterium)
            # TO DO !!!!!!!!!!!!!!!!!!!!
        #    Potential = lookuppotential(
        #        TabCrossSections, ChanCrossSections, ChanBottomLevel, self.var.ChanLength, ChanM3Dyn)
            # Potential
        #    WaterLevelDyn = Potential - ChanBottomLevel
            # Water level [m above bottom level)
        #    WaveCelerityDyn = pcraster.sqrt(9.81 * WaterLevelDyn)
            # Dynamic wave celerity [m/s]
        #    CourantDynamic = self.var.DtSec * \
        #        (WaveCelerityDyn + 2) / self.var.ChanLength
            # Courant number for dynamic wave
            # We don't know the water velocity at this time so
            # we just guess it's 2 m/s (Odra tests show that flow velocity
            # is typically much lower than wave celerity, and 2 m/s is quite
            # high already so this gives a pretty conservative/safe estimate
            # for DynWaveIterations)
        #    DynWaveIterationsTemp = max(
        #        1, roundup(CourantDynamic / CourantDynamicCrit))
        #    DynWaveIterations = ordinal(mapmaximum(DynWaveIterationsTemp))
            # Number of sub-steps needed for required numerical
            # accuracy. Always greater than or equal to 1
            # (otherwise division by zero!)

            # TEST
            # If polder option is used, we need an estimate of the initial channel discharge, but we don't know this
            # for the dynamic wave pixels (since only initial state is known)! Try if this works (dyn wave flux based on zero inflow 1 iteration)
            # Note that resulting ChanQ is ONLY used in the polder routine!!!
            # Since we need instantaneous estimate at start of time step, a
            # ChanQM3Dyn is calculated for one single one-second time step!!!

        #    ChanQDyn = dynwaveflux(TabCrossSections,
        #                           ChanCrossSections,
        #                           LddDynamic,
        #                           ChanIniM3,
        #                           0.0,
        #                           ChanBottomLevel,
        #                           self.var.ChanMan,
        #                           self.var.ChanLength,
        #                           1,
        #                           1,
        #                           DynWaveBoundaryCondition)
            # Compute volume and discharge in channel after dynamic wave
            # ChanM3Dyn in [cu m]
            # ChanQDyn in [cu m / s]
        #    self.var.ChanQ = ifthenelse(
        #        IsChannelDynamic, ChanQDyn, self.var.ChanQKin)
            # Channel discharge: combine results of kinematic and dynamic wave
        else:


            # ***** NO DYNAMIC WAVE *************************
            # Dummy code if dynamic wave is not used, in which case ChanQ equals ChanQKin
            # (needed only for polder routine)

            PrevDischarge = loadmap('PrevDischarge')
            self.var.ChanQ = np.where(PrevDischarge == -9999, self.var.ChanQKin, PrevDischarge)
            # initialise channel discharge: cold start: equal to ChanQKin
            # [m3/s]

        # Initialising cumulative output variables
        # These are all needed to compute the cumulative mass balance error

        self.var.DischargeM3Out = globals.inZero.copy()
        # cumulative discharge at outlet [m3]
        self.var.TotalQInM3 = globals.inZero.copy()
        # cumulative inflow from inflow hydrographs [m3]

        #self.var.sumDis = globals.inZero.copy()
        self.var.sumDis = globals.inZero.copy()
        self.var.sumIn = globals.inZero.copy()


# --------------------------------------------------------------------------

    def initialSecond(self):
        """ initial part of the second channel routing module
        """
        self.var.ChannelAlpha2 = None # default value, if split-routing is not active and only water is routed only in the main channel
        # ************************************************************
        # ***** CHANNEL INITIAL SPLIT UP IN SECOND CHANNEL************
        # ************************************************************
        if option['SplitRouting']:

            ChanMan2 = (self.var.ChanMan / self.var.CalChanMan) * loadmap('CalChanMan2')
            AlpTermChan2 = (ChanMan2 / (np.sqrt(self.var.ChanGrad))) ** self.var.Beta
            self.var.ChannelAlpha2 = (AlpTermChan2 * (self.var.ChanWettedPerimeterAlpha ** self.var.AlpPow)).astype(float)
            self.var.InvChannelAlpha2 = 1 / self.var.ChannelAlpha2
            # calculating second Alpha for second (virtual) channel

            if not(option['InitLisflood']):

                self.var.QLimit = loadmap('AvgDis') * loadmap('QSplitMult')
                self.var.M3Limit = self.var.ChannelAlpha * self.var.ChanLength * (self.var.QLimit ** self.var.Beta)
                # Over bankful discharge starts at QLimit
                # lower discharge limit for second line of routing
                # set to mutiple of average discharge (map from prerun)
                # QSplitMult =2 is around 90 to 95% of Q

                ###############################################
                # CM mod
                # QLimit should NOT be dependent on the NoRoutSteps (number of routing steps)
                # self.var.QLimit = self.var.QLimit / self.var.NoRoutSteps #original

                # TEMPORARY WORKAROUND FOR EFAS XDOM!!!!!!!!!!
                # This must be removed
                self.var.QLimit = self.var.QLimit / 24.0
                ###############################################

                self.var.Chan2M3Start = self.var.ChannelAlpha2 * self.var.ChanLength * (self.var.QLimit ** self.var.Beta)
                # virtual amount of water in the channel through second line
                self.var.Chan2QStart = self.var.QLimit - compressArray(upstream(self.var.LddKinematic, decompress(self.var.QLimit)))
                # because kinematic routing with a low amount of discharge leads to long travel time:
                # Starting Q for second line is set to a higher value
                self.var.Chan2M3Kin = np.maximum(self.var.CrossSection2Area * self.var.ChanLength + self.var.Chan2M3Start, 0) # TEMPORARY SOLUTION TO VIRTUAL WATER PROBLEM
                self.var.ChanM3Kin = np.maximum(self.var.ChanM3 - self.var.Chan2M3Kin + self.var.Chan2M3Start, 0) # TEMPORARY SOLUTION TO VIRTUAL WATER PROBLEM
                self.var.Chan2QKin = (self.var.Chan2M3Kin*self.var.InvChanLength*self.var.InvChannelAlpha2)**(self.var.InvBeta)
                self.var.ChanQKin = (self.var.ChanM3Kin*self.var.InvChanLength*self.var.InvChannelAlpha)**(self.var.InvBeta)

        # Initialise parallel kinematic wave router: main channel-only routing if self.var.ChannelAlpha2 is None; else split-routing(main channel + floodplains)
        self.river_router = kinematicWave(compressArray(self.var.LddKinematic), ~maskinfo["mask"], self.var.ChannelAlpha,\
                                          self.var.Beta, self.var.ChanLength, self.var.DtRouting,\
                                          int(binding["numCPUs_parallelKinematicWave"]), alpha_floodplains=self.var.ChannelAlpha2)

               

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------



    def dynamic(self, NoRoutingExecuted):
        """ dynamic part of the routing subtime module
        """

        if not(option['InitLisflood']):    # only with no InitLisflood
            self.lakes_module.dynamic_inloop(NoRoutingExecuted)
            self.reservoir_module.dynamic_inloop(NoRoutingExecuted)
            self.polder_module.dynamic_inloop()

        # End only with no Lisflood (no reservoirs, lakes and polder with
        # initLisflood)

        self.inflow_module.dynamic_inloop(NoRoutingExecuted)
        self.transmission_module.dynamic_inloop()

        # ************************************************************
        # ***** CHANNEL FLOW ROUTING: KINEMATIC WAVE  ****************
        # ************************************************************



        if not(option['dynamicWave']):

            # ************************************************************
            # ***** SIDEFLOW
            # ************************************************************



            SideflowChanM3 = self.var.ToChanM3RunoffDt.copy()

            if option['openwaterevapo']:
                SideflowChanM3 -= self.var.EvaAddM3Dt
            if option['wateruse']:
                SideflowChanM3 -= self.var.WUseAddM3Dt
            if option['inflow']:
                SideflowChanM3 += self.var.QInDt
            if option['TransLoss']:
                SideflowChanM3 -= self.var.TransLossM3Dt
            if not(option['InitLisflood']):    # only with no InitLisflood
                if option['simulateLakes']:
                    SideflowChanM3 += self.var.QLakeOutM3Dt
                if option['simulateReservoirs']:
                    SideflowChanM3 += self.var.QResOutM3Dt
                if option['simulatePolders']:
                    SideflowChanM3 -= self.var.ChannelToPolderM3Dt

            # Runoff (surface runoff + flow out of Upper and Lower Zone), outflow from
            # reservoirs and lakes and inflow from external hydrographs are added to the channel
            # system (here in [cu m])
            #
            # NOTE: polders currently don't work with kinematic wave, but nevertheless
            # ChannelToPolderM3 is already included in sideflow term (so it's there in case
            # the polder routine is ever modified to make it work with kin. wave)
            # Because of wateruse Sideflow might get even smaller than 0,
            # instead of inflow its outflow

            SideflowChan = np.where(self.var.IsChannelKinematic, SideflowChanM3 * self.var.InvChanLength * self.var.InvDtRouting,0)
            # SideflowChan=if(IsChannelKinematic, SideflowChanM3*InvChanLength*InvDtRouting);
            # Sideflow expressed in [cu m /s / m channel length]



            # ************************************************************
            # ***** KINEMATIC WAVE                        ****************
            # ************************************************************

            if option['InitLisflood'] or (not(option['SplitRouting'])):
                # if InitLisflood no split routing is use
                #  ---- Single Routing ---------------
                # No split routing
                # side flow consists of runoff (incl. groundwater), inflow from reservoirs (optional) and external inflow hydrographs (optional)
                SideflowChan[np.isnan(SideflowChan)] = 0 # TEMPORARY FIX - SEE DEBUG ABOVE!

                # ChanQKin in [cu m / s]
                self.river_router.kinematicWaveRouting(self.var.ChanQKin, SideflowChan, "main_channel")
                self.var.ChanM3Kin = self.var.ChanLength * self.var.ChannelAlpha * self.var.ChanQKin**self.var.Beta
                # Volume in channel at end of computation step
                #self.var.ChanQKin=pcraster.max(self.var.ChanQKin,0)
                self.var.ChanQ=np.maximum(self.var.ChanQKin,0)
                # at single kin. ChanQ is the same
                self.var.sumDisDay+=self.var.ChanQ
                # Total channel storage [cu m], equal to ChanM3Kin
                #self.var.ChanQ = maxpcr(self.var.ChanQKin, null)

            else:
                #  ---- Double Routing ---------------
                # routing is split in two (virtual) channels)

                # Ad
                SideflowRatio=np.where((self.var.ChanM3Kin + self.var.Chan2M3Kin) > 0,self.var.ChanM3Kin/(self.var.ChanM3Kin+self.var.Chan2M3Kin),0.0)

                # CM ##################################
                self.var.Sideflow1Chan = np.where(self.var.ChanM3Kin > self.var.M3Limit, SideflowRatio*SideflowChan, SideflowChan)
                # This is creating instability because ChanM3Kin can be < M3Limit between two routing sub-steps
                #######################################
                # self.var.Sideflow1Chan = np.where((self.var.ChanM3Kin + self.var.Chan2M3Kin-self.var.Chan2M3Start) > self.var.M3Limit,
                #                                   SideflowRatio*SideflowChan, SideflowChan)

                self.var.Sideflow1Chan = np.where(np.abs(SideflowChan) < 1e-7, SideflowChan, self.var.Sideflow1Chan)
                # too small values are avoided
                Sideflow2Chan = SideflowChan - self.var.Sideflow1Chan
               
                Sideflow2Chan = Sideflow2Chan + self.var.Chan2QStart * self.var.InvChanLength   # originale
                # as kinematic wave gets slower with less water
                # a constant amount of water has to be added
                # -> add QLimit discharge

                # Main channel routing
                self.river_router.kinematicWaveRouting(self.var.ChanQKin, self.var.Sideflow1Chan, "main_channel")
                self.var.ChanM3Kin = self.var.ChanLength * self.var.ChannelAlpha * self.var.ChanQKin**self.var.Beta

                # Floodplains routing
                self.river_router.kinematicWaveRouting(self.var.Chan2QKin, Sideflow2Chan, "floodplains")
                self.var.Chan2M3Kin = self.var.ChanLength * self.var.ChannelAlpha2 * self.var.Chan2QKin**self.var.Beta
                self.var.CrossSection2Area = (self.var.Chan2M3Kin - self.var.Chan2M3Start) * self.var.InvChanLength # wet cross-section area of floodplain
                self.var.ChanQ = np.maximum(self.var.ChanQKin + self.var.Chan2QKin - self.var.QLimit, 0)
                # Main channel routing and floodplains routing

                # ChanQ=max(ChanQKin+Chan2QKin-QLimit,0.0);
                # Channel discharge: equal to ChanQKin [cu m / s]
                # End splitrouting
                self.var.sumDisDay+=self.var.ChanQ
                # ----------End splitrouting-------------------------------------------------


            
            TotalCrossSectionArea = np.maximum(self.var.ChanM3Kin*self.var.InvChanLength,0.01)

            self.var.FlowVelocity = np.minimum(self.var.ChanQKin/TotalCrossSectionArea, 0.36*self.var.ChanQKin**0.24)
              # Channel velocity (m/s); dividing Q (m3/s) by CrossSectionArea (m2)
              # avoid extreme velocities by using the Wollheim 2006 equation
              # assume 0.1 for upstream areas (outside ChanLdd)
            self.var.FlowVelocity *= np.minimum(np.sqrt(self.var.PixelArea)*self.var.InvChanLength,1);
	          # reduction for sinuosity of channels
            self.var.TravelDistance=self.var.FlowVelocity*self.var.DtSec;
	          # if flow is fast, Traveltime=1, TravelDistance is high: Pixellength*DtSec
	          # if flow is slow, Traveltime=DtSec then TravelDistance=PixelLength
	          # maximum set to 30km/day for 5km cell, is at DtSec/Traveltime=6, is at Traveltime<DtSec/6
