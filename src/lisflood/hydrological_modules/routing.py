"""

Copyright 2019 European Union

Licensed under the EUPL, Version 1.2 or as soon they will be approved by the European Commission  subsequent versions of the EUPL (the "Licence");

You may not use this work except in compliance with the Licence.
You may obtain a copy of the Licence at:

https://joinup.ec.europa.eu/sites/default/files/inline-files/EUPL%20v1_2%20EN(1).txt

Unless required by applicable law or agreed to in writing, software distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and limitations under the Licence.

"""
from __future__ import print_function, absolute_import

from pcraster import lddmask, accuflux, boolean, downstream, pit, path, lddrepair, ifthenelse, cover, nominal, uniqueid, \
    catchment, upstream, pcr2numpy

import numpy as np

from .lakes import lakes
from .reservoir import reservoir
from .polder import polder
from .inflow import inflow
from .transmission import transmission
from .kinematic_wave_parallel import kinematicWave, kwpt
from .mct import MCTWave

from ..global_modules.settings import LisSettings, MaskInfo
from ..global_modules.add1 import loadmap, loadmap_base, compressArray, decompress
from . import HydroModule


class routing(HydroModule):

    """
    # ************************************************************
    # ***** ROUTING      *****************************************
    # ************************************************************
    """
    input_files_keys = {'all': ['beta', 'ChanLength', 'Ldd', 'Channels', 'ChanGrad', 'ChanGradMin',
                                'CalChanMan', 'ChanMan', 'ChanBottomWidth', 'ChanDepthThreshold',
                                'ChanSdXdY', 'TotalCrossSectionAreaInitValue', 'PrevDischarge'],
                        'SplitRouting': ['CrossSection2AreaInitValue', 'PrevSideflowInitValue', 'CalChanMan2'],
                        'dynamicWave': ['ChannelsDynamic'],
                        'MCTRouting': ['ChannelsMCT', 'ChanGradMaxMCT', 'PrevCmMCTInitValue', 'PrevDmMCTInitValue']}
    module_name = 'Routing'

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
        settings = LisSettings.instance()
        option = settings.options
        maskinfo = MaskInfo.instance()

        # ************************************************************
        # ***** NUMBER OF ROUTING STEPS          *********************
        # ************************************************************

        self.var.NoRoutSteps = int(np.maximum(1, round(self.var.DtSec / self.var.DtSecChannel,0)))
        # Number of routing sub-steps based on value of DtSecChannel or 1 if DtSec is smaller than DtSecChannel

        if option['InitLisflood']:
            self.var.NoRoutSteps = 1
            # InitLisflood is used! so channel routing step is the same as the general time step

        self.var.DtRouting = self.var.DtSec / self.var.NoRoutSteps
        # Corresponding routing sub-timestep (seconds)
        self.var.InvDtRouting = 1 / self.var.DtRouting
        self.var.InvNoRoutSteps = 1 / float(self.var.NoRoutSteps)
        # inverse for faster calculation inside the dynamic section

        # ************************************************************
        # ***** DRAINAGE NETWORK GEOMETRY - LDD  *********************
        # ************************************************************

        self.var.Ldd = lddmask(loadmap('Ldd', pcr=True, lddflag=True), self.var.MaskMap)    #pcr
        # Cut ldd to size of MaskMap (NEW, 29/9/2004)
        # Prevents 'unsound' ldd if MaskMap covers sub-area of ldd

        self.var.MaskMap = boolean(self.var.Ldd)    #pcr
        self.var.MaskMapNp=compressArray(self.var.MaskMap)  #np
        # Use boolean version of Ldd as calculation mask
        # (important for correct mass balance check any water generated outside of Ldd won't reach channel anyway)

        self.var.UpArea = accuflux(self.var.Ldd, self.var.PixelAreaPcr)     #pcr
        # Upstream contributing area for each pixel
        # Note that you might expect that values of UpArea would be identical to those of variable CatchArea (see below)
        # at the outflow points. This is NOT actually the case, because outflow points are shifted 1.
        # cell in upstream direction in the calculation of CatchArea!
        self.var.InvUpArea = 1 / self.var.UpArea    #pcr
        # Count (inverse of) upstream area for each pixel
        # Needed if we want to calculate average values of variables upstream of gauge locations
        # Calculate inverse, so we can multiply in dynamic (faster than divide)

        self.var.IsChannelPcr = boolean(loadmap('Channels', pcr=True))  #pcr
        self.var.IsChannel = np.bool8(compressArray(self.var.IsChannelPcr))   #bool
        self.var.IsChannelPcr = boolean(decompress(self.var.IsChannel))       #pcr
        # Identify grid cells containing a river channel

        self.var.IsChannelKinematic = self.var.IsChannel.copy()     #bool
        # Identify channel pixels using kinematic or split routing
        # (identical to IsChannel, unless MCT wave is used, see below)

        self.var.IsStructureChan = np.bool8(maskinfo.in_zero())        #bool
        # Initialise map that identifies special inflow/outflow structures (reservoirs, lakes) within the
        # channel routing. Set to (dummy) value of zero modified in reservoirs and lakes functions (if those are used)

        self.var.IsStructureKinematic = np.bool8(maskinfo.in_zero())        #bool
        # Initialise map that identifies special inflow/outflow structures (reservoirs, lakes) within the
        # kinematic wave channel routing. Set to (dummy) value of zero modified in reservoirs and lakes functions
        # (if those are used)

        self.var.LddChan = lddmask(self.var.Ldd, self.var.IsChannelPcr)  #pcr
        self.var.LddChanNp=compressArray(self.var.LddChan)    #np
        # LDD for channel network (excluding grid cells that do not have a channel)
        # It is the same as Ldd if there is a channel on every grid cell
        # We need a channel on each grid cell now but this could change in the future

        self.var.LddToChan = lddrepair(ifthenelse(self.var.IsChannelPcr, 5, self.var.Ldd)) #pcr
        self.var.LddToChanNp=compressArray(self.var.LddToChan)  #np
        # Routing of runoff (incl. groundwater) to the river channel

        if option['dynamicWave']:
            pass
            # # legacy code
            # AtOutflow = boolean(pit(self.var.Ldd))  # pcr
            # AtOutflowNp = compressArray(AtOutflow)  # np
            # # find outlet points...
            # # Function 'pit' assignes a unique number starting from 1 to pit cells (ldd=5) in the Ldd
            #
            # IsChannelDynamic = boolean(loadmap('ChannelsDynamic', pcr=True))
            # # Identify channel pixels where dynamic wave is used
            # self.var.IsChannelKinematic = (self.var.IsChannelPcr == 1) & (IsChannelDynamic == 0)
            # # Identify (update) channel pixels where kinematic wave is used
            # self.var.LddKinematic = lddmask(self.var.Ldd, self.var.IsChannelKinematic)
            # # Ldd for kinematic wave: ends (pit) just before dynamic stretch
            #
            # # Following statements produce an ldd network that connects the pits in
            # # LddKinematic to the nearest downstream dynamic wave pixel
            #
            # self.var.AtLastPoint = (downstream(self.var.Ldd, AtOutflow) == 1) & (AtOutflow != 1) & self.var.IsChannelPcr
            #
            # # NEW 23-6-2005
            # # Dynamic wave routine gives no outflow out of pits, so we calculate this
            # # one cell upstream (WvD)
            # # (implies that most downstream cell is not taken into account in mass balance
            # # calculations, even if dyn wave is not used)
            # # Only include points that are on a channel (otherwise some small 'micro-catchments'
            # # are included, for which the mass balance cannot be calculated
            # # properly)
        else:
            # For all routing options (kinematic, split and MCT)
            self.var.LddKinematic = self.var.LddChan
            self.var.LddKinematicNp = compressArray(self.var.LddKinematic)  # np

        self.var.AtLastPoint = boolean(pit(self.var.Ldd))    #pcr
        # Assign True to each of the grid cells where there are outlet points
        # Function 'pit' assigns a unique number starting from 1 to pit cells (ldd=5) in the Ldd
        self.var.AtLastPointC = np.bool8(compressArray(self.var.AtLastPoint)) #np

        lddC = compressArray(self.var.LddChan)     #np
        inAr = decompress(np.arange(maskinfo.info.mapC[0], dtype="int32"))  #pcr
        # Assign a number to each non-missing pixel as cell id, starting from 0

        self.var.downstruct = (compressArray(downstream(self.var.LddChan, inAr))).astype("int32")  #np
        # each upstream pixel gets the id of the downstream pixel
        self.var.downstruct[lddC == 5] = maskinfo.info.mapC[0]  #np
        # assigning to all pits an id number higher than any of the other cells

        OutflowPoints = nominal(uniqueid(self.var.AtLastPoint))     #pcr
        OutflowPointsNp = compressArray(OutflowPoints)      #np
        # assigning id to the outflow points starting from 1

        self.var.Catchments = (compressArray(catchment(self.var.Ldd, OutflowPoints))).astype(np.int32)  #np
        # assign outlet id to all pixel in its catchment
        # define catchment for each outflow point

        CatchArea = np.bincount(self.var.Catchments, weights=self.var.PixelArea)[self.var.Catchments]   #np
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
        # River bed slope
        # Avoid calculation of Alpha using ChanGrad=0: this creates MV!
        # Set minimum channel slope in rivers (ChanGradMin)

        self.var.CalChanMan = loadmap('CalChanMan')
        self.var.ChanMan = self.var.CalChanMan * loadmap('ChanMan')
        # Manning's roughtness coefficient n is multiplied by ChanManCal for calibration

        self.var.ChanBottomWidth = loadmap('ChanBottomWidth')
        # Riverbed width [m]
        ChanDepthThreshold = loadmap('ChanDepthThreshold')
        # Bankfull river depth [m]
        self.var.ChanSdXdY = loadmap('ChanSdXdY')
        # Riverbed sides slope

        # self.var.ChanSdXdY = maskinfo.in_zero()         # rectangular cross-section
        # self.var.ChanBottomWidth = maskinfo.in_zero()   # triangular cross-section

        self.var.ChanUpperWidth = self.var.ChanBottomWidth + 2 * self.var.ChanSdXdY * ChanDepthThreshold
        # Channel upper width [m]
        self.var.TotalCrossSectionAreaBankFull = 0.5 * \
            ChanDepthThreshold * (self.var.ChanUpperWidth + self.var.ChanBottomWidth)
        # Area (sq m) of bank full discharge cross-section [m2] (trapezoid area equation)

        # cmcheck - TotalCrossSectionAreaHalfBankFull is not 1/2 TotalCrossSectionAreaBankFull it's trapezoid
        # ChanUpperWidthHalfBankFull = self.var.ChanBottomWidth + 2 * self.var.ChanSdXdY * 0.5 * ChanDepthThreshold
        # TotalCrossSectionAreaHalfBankFull = 0.5 * \
        #     0.5 * ChanDepthThreshold * (ChanUpperWidthHalfBankFull + self.var.ChanBottomWidth)
        # Cross-sectional area at half bankfull [m2]
        # This can be used to initialise channel flow (see below)
        TotalCrossSectionAreaHalfBankFull = 0.5 * self.var.TotalCrossSectionAreaBankFull

        TotalCrossSectionAreaInitValue = loadmap('TotalCrossSectionAreaInitValue')
        self.var.TotalCrossSectionArea = np.where(TotalCrossSectionAreaInitValue == -9999, TotalCrossSectionAreaHalfBankFull, TotalCrossSectionAreaInitValue)
        # Total cross-sectional area [m2]: if initial value in binding equals -9999 the value at half bankfull is used,
        # otherwise TotalCrossSectionAreaInitValue (typically end map from previous simulation)

        if option['SplitRouting']:
            CrossSection2AreaInitValue = loadmap('CrossSection2AreaInitValue')
            self.var.CrossSection2Area = np.where(CrossSection2AreaInitValue == -9999, maskinfo.in_zero(), CrossSection2AreaInitValue)
            # cross-sectional area [m2] for 2nd line of routing (over bankfull only): if initial value in binding equals
            # -9999 the value is set to 0 otherwise CrossSection2AreaInitValue (typically end map from previous simulation)

            PrevSideflowInitValue = loadmap('PrevSideflowInitValue')
            self.var.Sideflow1Chan = np.where(PrevSideflowInitValue == -9999, maskinfo.in_zero(), PrevSideflowInitValue)
            # sideflow from previous run for 1st line of routing: if initial value in binding equals -9999 the value is set to 0
            # otherwise PrevSideflowInitValue (typically end map from previous simulation)

        # ************************************************************
        # ***** CHANNEL ALPHA (KIN. WAVE) ****************************
        # ************************************************************
        # Manning's steady state flow equations
        # from Ven The Chow - Applied Hydrology - page 283
        # https: // wecivilengineers.files.wordpress.com / 2017 / 10 / applied - hydrology - ven - te - chow.pdf
        # A = Alpha * Q ** Beta
        # Q = (A/Alpha) ** (1/Beta) = (invAlpha * A)**invBeta

        self.var.Beta = loadmap('beta')
        # This is 3/5. Exponent of Manning's equation A=alpha*Q^beta ->  Q= 1/alpha * A^(1/beta)
        self.var.InvBeta = 1 / self.var.Beta
        # Inverse of beta for kinematic wave
        self.var.ChanLength = loadmap('ChanLength').astype(float)
        # Channel length [m]
        self.var.InvChanLength = 1 / self.var.ChanLength
        # Inverse of channel length [1/m]

        # Following calculations are needed to calculate Alpha parameter in kinewave.
        # Alpha currently fixed at half of bankfull depth (this may change in future versions!)

        ChanWaterDepthAlpha = np.where(self.var.IsChannel, 0.5 * ChanDepthThreshold, 0.0)
        # Reference water depth for calculation of Alpha: half of bankfull
        self.var.ChanWettedPerimeterAlpha = self.var.ChanBottomWidth + 2 * \
            np.sqrt(np.square(ChanWaterDepthAlpha) + np.square(ChanWaterDepthAlpha * self.var.ChanSdXdY))
        # Channel wetted perimeter half bankfull [m](Pythagoras)

        AlpTermChan = (self.var.ChanMan / (np.sqrt(self.var.ChanGrad))) ** self.var.Beta
        self.var.AlpPow = 2.0 / 3.0 * self.var.Beta # this is 2/5
        self.var.ChannelAlpha = (AlpTermChan * (self.var.ChanWettedPerimeterAlpha ** self.var.AlpPow)).astype(float)

        self.var.InvChannelAlpha = 1 / self.var.ChannelAlpha
        # ChannelAlpha for kinematic wave

        # ************************************************************
        # ***** CHANNEL INITIAL DISCHARGE (KINEMATIC) ****************
        # ************************************************************

        self.var.ChanM3 = self.var.TotalCrossSectionArea * self.var.ChanLength  #np
        # Total water volume in river channel [m3]
        self.var.ChanIniM3 = self.var.ChanM3.copy() #np
        self.var.ChanM3Kin = self.var.ChanIniM3.copy().astype(float)    #np
        # Initialise water volume in kinematic wave channels [m3]

        self.var.ChanQKin = np.where(self.var.ChannelAlpha > 0, (self.var.TotalCrossSectionArea / self.var.ChannelAlpha) ** self.var.InvBeta, 0).astype(float)
        # Initialise discharge at kinematic wave pixels (note that InvBeta is simply 1/beta, computational efficiency!)

        self.var.CumQ = maskinfo.in_zero()
        # Initialise sum of discharge to calculate average

        # ************************************************************
        # ***** CHANNEL INITIAL DYNAMIC WAVE *************************
        # ************************************************************
        if option['dynamicWave']:
            pass
        # legacy code
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
            # For all routing options (kinematic, split and MCT)
            PrevDischarge = loadmap('PrevDischarge')
            # Outflow (x+dx) Q at the end of previous computation step for full cross-section (instant)
            # Used to calculated Inflow (x) from upstream pixels at the beginning of the computation step
            self.var.ChanQ = np.where(PrevDischarge == -9999, self.var.ChanQKin, PrevDischarge) #np
            # Initialise instantaneous channel discharge: cold start: equal to ChanQKin [m3/s]

            # cmcheck
            # initialising the variable
            # should initialisation be moved somewhere else?
            self.var.ChanQAvgDt = maskinfo.in_zero()
            self.var.ChanQKinAvgDt = maskinfo.in_zero()

            # cmcheck
            self.var.Chan2QKinAvgDt = maskinfo.in_zero()

            # I do not need a state file to initialise the average outflow discharge (ChanQAvgDt and ChanQKinAvgDt).
            # Initialisation would be necessary for pixels in order 0, but there is no upstream contribution for pixels in order 0.
            # For pixels in order 1 and beyond, upstream contribution is calculated during the calculation step.


        # ************************************************************
        # ***** CUMULATIVE OUTPUT VARIABLES  *************************
        # ************************************************************
        # Initialising cumulative output variables
        self.var.avgdis = maskinfo.in_zero()
        # average discharge over the simulation period

        # These are all needed to compute the cumulative mass balance error
        self.var.DischargeM3Out = maskinfo.in_zero()
        # Cumulative outflow volume at outlet [m3]
        self.var.TotalQInM3 = maskinfo.in_zero()
        # Cumulative inflow volume from inflow hydrographs [m3]
        self.var.sumDis = maskinfo.in_zero()
        self.var.sumIn = maskinfo.in_zero()
        # cmcheck - non so se sostituita da self.var.sumInWB
        self.var.sumInWB = maskinfo.in_zero()

    def initialSecond(self):
        """ initial part of the second line channel routing module for split routing
        """
        settings = LisSettings.instance()
        option = settings.options
        flags = settings.flags

        self.var.ChannelAlpha2 = None
        # Default value, if split-routing is not active and water is routed only in the main channel

        # ************************************************************
        # ***** CHANNEL INITIAL SPLIT UP IN SECOND CHANNEL************
        # ************************************************************
        if option['SplitRouting']:

            # calculate kin wave parameters for the (virtual) channel of the second line of routing

            ChanMan2 = (self.var.ChanMan / self.var.CalChanMan) * loadmap('CalChanMan2')
            # Manning's roughtness coefficient n for second line of routing
            AlpTermChan2 = (ChanMan2 / (np.sqrt(self.var.ChanGrad))) ** self.var.Beta
            self.var.ChannelAlpha2 = (AlpTermChan2 * (self.var.ChanWettedPerimeterAlpha ** self.var.AlpPow)).astype(float)
            #cmcheck -> using channel wetted perimeter of half bankfull ChanWettedPerimeterAlpha ?
            self.var.InvChannelAlpha2 = 1 / self.var.ChannelAlpha2
            # calculating second Alpha for second (virtual) channel

            if not(option['InitLisflood']):
                # ************************************************************
                # ***** INITIALISE SECOND LINE OF ROUTING (KINEMATIC) ********
                # ************************************************************
                # Over bankful discharge starts at QLimit
                # lower discharge limit for second line of routing
                # set to multiple of average discharge (map from prerun)
                # QSplitMult =2 is around 90 to 95% of Q

                self.var.QLimit = loadmap_base('AvgDis') * loadmap('QSplitMult')
                # Using loadmap_base function as we don't want to cache avgdis in the calibration
                self.var.M3Limit = self.var.ChannelAlpha * self.var.ChanLength * (self.var.QLimit ** self.var.Beta)
                # Water volume in bankful when over bankful discharge starts
                # Manning's equation

                self.var.Chan2M3Start = self.var.ChannelAlpha2 * self.var.ChanLength * (self.var.QLimit ** self.var.Beta)
                # Virtual (note we use ChannelAlpha2 now) amount of water in the main channel at the activation of second line of routing 'floodplains' (=> start using increased Manning coeff 2)
                self.var.Chan2QStart = self.var.QLimit - compressArray(upstream(self.var.LddKinematic, decompress(self.var.QLimit)))
                # Virtual outflow from main channel at the activation of second line of routing (=> start using increased Manning coeff 2)
                # Because kinematic routing with a low amount of discharge leads to long travel time:
                # Starting Q for second line is set to a higher value

                self.var.Chan2M3Kin = self.var.CrossSection2Area * self.var.ChanLength + self.var.Chan2M3Start
                # Total (virtual) volume of water in river channel when second routing line is active (= using increased Manning coeff 2)
                self.var.ChanM3Kin = self.var.ChanM3 - self.var.Chan2M3Kin + self.var.Chan2M3Start
                # (Real) Volume of water in main channel when second line of routing is active (= using riverbed Manning coeff)

                self.var.ChanM3Kin = np.where((self.var.ChanM3Kin < 0.0) & (self.var.ChanM3Kin > -0.0000001),0.0,self.var.ChanM3Kin)
                # this line prevents the warm start from failing in case of small numerical imprecisions when writing and reading the maps

                self.var.Chan2QKin = (self.var.Chan2M3Kin * self.var.InvChanLength * self.var.InvChannelAlpha2) ** (self.var.InvBeta)
                # Total (virtual) outflow from river channel when second routing line is active (= using increased Manning coeff 2)
                self.var.ChanQKin = (self.var.ChanM3Kin * self.var.InvChanLength * self.var.InvChannelAlpha) ** (self.var.InvBeta)
                # (Real) outflow from main channel when second line of routing is active (= using riverbed Manning coeff 2)


        # ************************************************************
        # ***** INITIALISE PARALLEL KINEMATIC WAVE ROUTER ************
        # ************************************************************

        # Initialise parallel kinematic wave router: main channel-only routing if self.var.ChannelAlpha2 is None; else split-routing(main channel + floodplains)
        # Initialization includes LDD for kinematic routing
        maskinfo = MaskInfo.instance()
        self.river_router = kinematicWave(compressArray(self.var.LddKinematic), ~maskinfo.info.mask, self.var.ChannelAlpha,
                                           self.var.Beta, self.var.ChanLength, self.var.DtRouting,
                                          alpha_floodplains=self.var.ChannelAlpha2, flagnancheck=flags['nancheck'])

        # ************************************************************
        # ***** WATER BALANCE                             ************
        # ************************************************************
        if option['InitLisflood'] and option['repMBTs']:
            # Calculate initial water storage in rivers (no lakes no reservoirs)
            # self.var.StorageStepINIT= self.var.ChanM3Kin
            self.var.StorageStepINIT = self.var.ChanM3
            # Initial water volume in river channels
            self.var.DischargeM3StructuresIni = maskinfo.in_zero()
            if option['simulateReservoirs']:
               self.var.StorageStepINIT += self.var.ReservoirStorageIniM3
            if option['simulateLakes']:
               self.var.StorageStepINIT += self.var.LakeStorageIniM3
            self.var.StorageStepINIT = np.take(np.bincount(self.var.Catchments, weights=self.var.StorageStepINIT), self.var.Catchments)

        if not option['InitLisflood'] and option['repMBTs']:
           self.var.StorageStepINIT = self.var.ChanM3
           # DisStructure = np.where(self.var.IsUpsOfStructureKinematicC, self.var.ChanQ * self.var.DtRouting, 0)
           DisStructure = np.where(self.var.IsUpsOfStructureChanC, self.var.ChanQ * self.var.DtRouting, 0)
           if not(option['SplitRouting']):
                # self.var.StorageStepINIT = self.var.ChanM3Kin
                # self.var.StorageStepINIT = self.var.ChanM3
                if option['simulateReservoirs']:
                   self.var.StorageStepINIT += self.var.ReservoirStorageIniM3
                   # DisStructure = np.where(self.var.IsUpsOfStructureKinematicC, self.var.ChanQ * self.var.DtRouting, 0)
                   DisStructure = np.where(self.var.IsUpsOfStructureChanC, self.var.ChanQ * self.var.DtRouting, 0)
                if option['simulateLakes']:
                   self.var.StorageStepINIT += self.var.LakeStorageIniM3
                   DisStructure += np.where(compressArray(self.var.IsUpsOfStructureLake), 0.5 * self.var.ChanQ * self.var.DtRouting, 0)
                self.var.DischargeM3StructuresIni = np.take(np.bincount(self.var.Catchments, weights=DisStructure), self.var.Catchments)
           else:
                # self.var.StorageStepINIT= self.var.ChanM3Kin+self.var.Chan2M3Kin-self.var.Chan2M3Start
                # self.var.StorageStepINIT = self.var.ChanM3
                if option['simulateReservoirs']:
                   self.var.StorageStepINIT += self.var.ReservoirStorageIniM3
                if option['simulateLakes']:
                   self.var.StorageStepINIT += self.var.LakeStorageIniM3
                self.var.StorageStepINIT = np.take(np.bincount(self.var.Catchments, weights=self.var.StorageStepINIT), self.var.Catchments)

    def initialMCT(self):
        """ initial part of the Muskingum-Cunge-Todini routing module
        """
        settings = LisSettings.instance()
        option = settings.options

        if not (option['SplitRouting']):
            self.var.ChannelAlpha2 = None
            # default value, if split-routing is not active and water is routed only in the riverbed channel

        # ************************************************************
        # ***** INITIALISATION FOR MCT ROUTING            ************
        # ************************************************************
        if option['MCTRouting']:
            maskinfo = MaskInfo.instance()

            self.var.IsChannelMCTPcr = boolean(loadmap('ChannelsMCT', pcr=True))   #pcr
            self.var.IsChannelMCT = np.bool8(compressArray(self.var.IsChannelMCTPcr))   #bool
            self.var.IsChannelMCTPcr = boolean(decompress(self.var.IsChannelMCT))       # pcr
            # Identify channel pixels where Muskingum-Cunge-Todini is used

            self.var.mctmask = np.bool8(pcr2numpy(self.var.IsChannelMCTPcr,0))
            # Create a mask with cells using MCT

            self.var.IsChannelKinematicPcr = (self.var.IsChannelPcr == 1) & (self.var.IsChannelMCTPcr == 0)  #pcr
            self.var.IsChannelKinematic = np.bool8(compressArray(self.var.IsChannelKinematicPcr))   #np
            # Identify channel pixels where Kinematic wave is used instead of MCT

            self.var.LddMCT = lddmask(self.var.LddChan, self.var.IsChannelMCTPcr)  #pcr
            # Ldd for MCT routing

            self.var.LddKinematic = lddmask(self.var.LddChan, self.var.IsChannelKinematicPcr)    #pcr
            # Ldd for kinematic routing

            ChanGradMaxMCT = loadmap('ChanGradMaxMCT')
            # Maximum riverbed slope for MCT rivers
            # Check where IsChannelMCT is True and values in ChanGrad > ChanGradMaxMCT
            MCT_slope_mask = np.logical_and(self.var.IsChannelMCT, self.var.ChanGrad > ChanGradMaxMCT)
            # Update values in ChanGrad where the condition is met
            self.var.ChanGrad[MCT_slope_mask] = ChanGradMaxMCT
            # set max channel slope for MCT pixels

            # cmcheck
            # This could become a calibration parameter if we want to use MCT+SplitRouting
            self.var.ChanManMCT = (self.var.ChanMan / self.var.CalChanMan) * loadmap('CalChanMan2')
            # Mannings coefficient for MCT pixels (same as second line of split routing)

            PrevCmMCT = loadmap('PrevCmMCTInitValue')
            self.var.PrevCm0 = np.where(PrevCmMCT == -9999, maskinfo.in_one(), PrevCmMCT) #np
            # Courant numnber (Cm) for MCT at previous time step t0
            PrevDmMCT = loadmap('PrevDmMCTInitValue')
            self.var.PrevDm0 = np.where(PrevDmMCT == -9999, maskinfo.in_zero(), PrevDmMCT) #np
            # Reynolds number (Dm) for MCT at previous time step t0


            # ************************************************************
            # ***** INITIALISE MUSKINGUM-CUNGE-TODINI WAVE ROUTER ********
            # ************************************************************
            mct_ldd = self.compress_mct(compressArray(self.var.LddMCT))
            # create mapping from global domain pixels index to MCT pixels index
            mapping_mct = self.compress_mct(range(len(self.var.ChanLength)))
            self.mct_river_router = MCTWave(
                mct_ldd,
                self.var.mctmask,
                self.var.ChanLength,
                self.var.ChanGrad,
                self.var.ChanBottomWidth,
                self.var.ChanManMCT,
                self.var.ChanSdXdY,
                self.var.DtRouting,
                self.river_router,
                mapping_mct
            )


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self, NoRoutingExecuted):
        """ dynamic part of the routing subtime module
        """
        settings = LisSettings.instance()
        option = settings.options

        if not(option['InitLisflood']):    # only with no InitLisflood
            self.lakes_module.dynamic_inloop(NoRoutingExecuted)
            self.reservoir_module.dynamic_inloop(NoRoutingExecuted)
            self.polder_module.dynamic_inloop()

        self.inflow_module.dynamic_inloop(NoRoutingExecuted)
        self.transmission_module.dynamic_inloop()

        if not(option['dynamicWave']):

            # ************************************************************
            # ***** SIDEFLOW                              ****************
            # ************************************************************
            # Calculating water contribution to channels

            SideflowChanM3 = self.var.ToChanM3RunoffDt.copy()
            # Runoff contribution from overland flow, upper and lower groundwater zones to the channel during routing sub step [m3]

            if option['openwaterevapo']:
                SideflowChanM3 -= self.var.EvaAddM3Dt
                # Evaporation from open water (rivers) - withdrawal [m3]
            if option['wateruse']:
                self.var.WUseAddM3Dt = (self.var.withdrawal_CH_actual_M3_routStep - self.var.returnflow_GwAbs2Channel_M3_routStep)  
                SideflowChanM3 -= self.var.WUseAddM3Dt
                # Water use abstraction from rivers - withdrawal    [m3]
            if option['inflow']:
                SideflowChanM3 += self.var.QInDt
                # Flow volume from inlets per sub step [m3]
            if option['TransLoss']:
                SideflowChanM3 -= self.var.TransLossM3Dt
                # Transmission flow volume - withdrawal [m3]

            if not(option['InitLisflood']):    # only with no InitLisflood
                if option['simulateLakes']:
                    SideflowChanM3 += self.var.QLakeOutM3Dt
                    # Lakes outflow volume per routing sub step [m3]
                if option['simulateReservoirs']:
                    SideflowChanM3 += self.var.QResOutM3Dt
                    # Reservoirs outflow volume per routing sub step [m3]
                if option['simulatePolders']:
                    SideflowChanM3 -= self.var.ChannelToPolderM3Dt
                    # Polders outflow volume per routing sub step [m3]

            # NOTE: polders currently don't work with kinematic wave, but nevertheless
            # ChannelToPolderM3 is already included in sideflow term (so it's there in case
            # the polder routine is ever modified to make it work with kin. wave)
            # Because of wateruse Sideflow might get even smaller than 0,
            # instead of inflow its outflow

            ### check mass balance within routing ###
            if option['repMBTs']:  
             if (NoRoutingExecuted<1):
                 self.var.AddedTRUN = np.take(np.bincount(self.var.Catchments, weights=self.var.ToChanM3RunoffDt.copy()),self.var.Catchments)
                 if option['inflow']:
                     self.var.AddedTRUN += np.take(np.bincount(self.var.Catchments, weights=self.var.QInDt),self.var.Catchments)
                 if option['openwaterevapo']:
                     self.var.AddedTRUN -= np.take(np.bincount(self.var.Catchments, weights=self.var.EvaAddM3Dt.copy()),self.var.Catchments)
                 if option['wateruse']:
                     self.var.AddedTRUN -= np.take(np.bincount(self.var.Catchments, weights=self.var.WUseAddM3Dt.copy()),self.var.Catchments)
             else:
                 self.var.AddedTRUN += np.take(np.bincount(self.var.Catchments, weights=self.var.ToChanM3RunoffDt.copy()),self.var.Catchments)
                 if option['inflow']:
                     self.var.AddedTRUN += np.take(np.bincount(self.var.Catchments, weights=self.var.QInDt),self.var.Catchments) 
                 if option['openwaterevapo']:
                     self.var.AddedTRUN -= np.take(np.bincount(self.var.Catchments, weights=self.var.EvaAddM3Dt.copy()),self.var.Catchments)
                 if option['wateruse']:
                     self.var.AddedTRUN -= np.take(np.bincount(self.var.Catchments, weights=self.var.WUseAddM3Dt.copy()),self.var.Catchments)      

            # Sideflow contribution to kinematic and split routing grid cells expressed in [cu m /s / m channel length]
            SideflowChan = np.where(self.var.IsChannelKinematic, SideflowChanM3 * self.var.InvChanLength * self.var.InvDtRouting,0)

            # ************************************************************
            # ***** RIVER ROUTING                         ****************
            # ************************************************************
            if option['InitLisflood']:
                self.var.IsChannelKinematic = self.var.IsChannel.copy()
            # Use kinematic routing in all grid cells

            # only run kinematic for InitLisflood option

            # KINEMATIC ROUTING ONLY
            if option['InitLisflood'] or not (option['SplitRouting']):
                # Kinematic routing uses the same variables for inputs and outputs. Values are updated during computation
                # from upstream to downstream.

                self.KinRouting(SideflowChan)

                # Store results to general variables for channels routing

                ChanQ = self.var.ChanQKin.copy()
                # Outflow (x+dx) Q at the end of computation step t+dt for full section (instant)

                ChanM3 = self.var.ChanM3Kin.copy()
                # Channel storage V at the end of computation step t+dt for full section (instant)

                ChanQAvgDt = self.var.ChanQKinAvgDt.copy()
                # Average Outflow (x+dx) Q during computation step dt for full section (instant)

            # SPLIT ROUTING ONLY
            else:
                # Split routing uses the same variables for inputs and outputs. Values are updated during computation
                # from upstream to downstream.

                self.SplitRouting(SideflowChan)

                # Combine the two lines of routing together
                # Store results to general variables for channels routing

                ChanQ = np.maximum(self.var.ChanQKin + self.var.Chan2QKin - self.var.QLimit, 0)
                # (real) total outflow (at x+dx) at time t+dt end of step for the full cross-section (instant)
                # Main channel routing and above bankfull routing from second line of routing

                ChanM3 = self.var.ChanM3Kin + self.var.Chan2M3Kin - self.var.Chan2M3Start
                # Total channel storage [m3] = Volume in main channel (ChanM3Kin) + volume above bankfull in second line (Chan2M3Kin - Chan2M3Start)
                # Total channel storage V at the end of computation step t+dt for full section (instant)

                # cmcheck
                ChanQAvgDt = np.maximum(self.var.ChanQKinAvgDt + self.var.Chan2QKinAvgDt - self.var.QLimit, 0)
                # (real) total outflow (at x+dx) at time t+dt end of step for the full cross-section (instant)
                # Main channel routing and above bankfull routing from second line of routing

            # KINEMATIC/SPLIT ROUTING AND MUSKINGUM-CUNGE-TODINI - no InitLisflood
            if option['MCTRouting']:
                # To parallelise the routing, pixels are grouped by orders. Pixels in the same order are independent and
                # routing can be solved in parallel.
                # The same order can have both Kin and MCT pixels.
                # First, Kinematic routing is solved on all pixels (including MCT pixels) to generate the inputs to the
                # MCT grid cells downstream (MCT needs input from upstream kinematic pixels).
                # (this needs to be changed in future versions)
                
                # Sideflow contribution to MCT grid cells expressed in [m3/s]
                SideflowChanMCT = np.where(self.var.IsChannelMCT, SideflowChanM3 * self.var.InvDtRouting, 0)  #Ql

                # MCT routing
                # This is calculated for MCT grid cell only but takes the output of kinematic or split routing

                # ChanQMCTOutStart = self.var.ChanQ.copy()
                # Outflow (x+dx) at time t (instant)  q10

                # cmcheck - debug
                # ChanQKinOutEnd[ChanQKinOutEnd != 0] = 0
                # Set inflow from kinematic pixels to 1

                # ChanM3MCTStart = self.var.ChanM3.copy()
                # Channel storage at time t V00

                # ChanQMCTInStart = self.var.PrevQMCTin.copy()   
                # Inflow (x) at time t instant (instant)  q00
                # This is coming from upstream pixels

                #### calling MCT routing
                # Using ChanQKinOutEnd and ChanQKinOutAvgDtEnd as inputs to receive inflow from upstream kinematic/split
                # routing pixels that are contributing to MCT pixels
                
                # Grab current state
                ChanQ_0 = self.var.ChanQ.copy()     # Outflow (x+dx) at time t (instant)  q10
                ChanM3_0 = self.var.ChanM3.copy()   # Channel storage at time t V00
                
                # put results of Kinematic/Split routing into MCT points
                self.var.ChanQ = ChanQ
                self.var.ChanM3 = ChanM3
                self.var.ChanQAvgDt = ChanQAvgDt

                # Update current state at MCT points
                self.mct_river_router.routing(
                    ChanQ_0,        # q10
                    ChanM3_0,       # V00
                    SideflowChanMCT,
                    # THESE ARE BOTH INPUTS AND OUTPUTS
                    self.var.ChanQ,
                    self.var.ChanQAvgDt,
                    self.var.PrevCm0,
                    self.var.PrevDm0,
                    self.var.ChanM3
                )

            else:
                # put results of Kinematic/Split routing into MCT points   
                self.var.ChanQ = ChanQ
                self.var.ChanM3 = ChanM3
                self.var.ChanQAvgDt = ChanQAvgDt
            
            # sum of average outflow Q on model sub-steps to give accumulated total outflow volume
            self.var.sumDisDay += self.var.ChanQAvgDt

            ### end of river routing calculation

            # ---- Uncomment lines 603-635 in order to compute the mass balance error within the routing module for the options (i) initial run or (ii) split routing off ----
            #'''
            # option['repMBTs']=True
            if option['repMBTs']:
                 if option['InitLisflood'] or (not(option['SplitRouting'])):
                    # Kinematic routing and MCT
                    if NoRoutingExecuted == (self.var.NoRoutSteps-1):
                      # StorageStep = self.var.ChanM3Kin.copy()
                      StorageStep = self.var.ChanM3.copy()
                      # Water storage at t+dt end of routing step: rivers channels
                      # Using ChanM3 so it's OK for both MCT and KIN

                      ChanQAvgR = self.var.sumDisDay/self.var.NoRoutSteps
                      # average (of instantaneous) outflow (x+dx) at t+dt end of routing step
                      sum1=ChanQAvgR.copy()
                      sum1[self.var.AtLastPointC == 0] = 0
                      OutStepM3 = np.take(np.bincount(self.var.Catchments,weights=sum1 * self.var.DtSec),self.var.Catchments)
                      # average outflow volume (x+dx) volume at t+dt

                      maskinfo = MaskInfo.instance()
                      DisStructureR = maskinfo.in_zero()
                      DischargeM3StructuresR = maskinfo.in_zero()

                      if not option['InitLisflood']:
                       if option['simulateReservoirs']:
                         sum1 =self.var.ChanQ.copy()
                         StorageStep =  StorageStep + self.var.ReservoirStorageM3.copy()
                         # DisStructureR = np.where(self.var.IsUpsOfStructureKinematicC, sum1 * self.var.DtRouting, 0)
                         DisStructureR = np.where(self.var.IsUpsOfStructureChanC, sum1 * self.var.DtRouting, 0)
                         DischargeM3StructuresR = np.take(np.bincount(self.var.Catchments, weights=DisStructureR), self.var.Catchments)
                         DischargeM3StructuresR -= self.var.DischargeM3StructuresIni

                      if not option['InitLisflood']:
                       if option['simulateLakes']:
                         sum1 =self.var.ChanQ.copy()
                         StorageStep =  StorageStep + self.var.LakeStorageM3Balance.copy()
                         # DisStructureR = np.where(self.var.IsUpsOfStructureKinematicC, sum1 * self.var.DtRouting, 0)
                         DisStructureR = np.where(self.var.IsUpsOfStructureChanC, sum1 * self.var.DtRouting, 0)
                         DischargeM3StructuresR = np.take(np.bincount(self.var.Catchments, weights=DisStructureR), self.var.Catchments)
                         maskinfo = MaskInfo.instance()
                         DisLake = maskinfo.in_zero()
                         np.put(DisLake, self.var.LakeIndex, 0.5 * self.var.LakeInflowCC * self.var.DtRouting)
                         DischargeM3Lake = np.take(np.bincount(self.var.Catchments, weights=DisLake),self.var.Catchments)
                         DischargeM3StructuresR += DischargeM3Lake
                         DischargeM3StructuresR -= self.var.DischargeM3StructuresIni

                      # Total Mass Balance Error in m3 per catchment for Initial Run OR Kinematic routing (Split Routing OFF)
                      # MB =-np.sum(StorageStep)+np.sum(self.var.StorageStepINIT) - OutStepM3[0]  -DischargeM3StructuresR[0] +self.var.AddedTRUN

                      # # cmcheck
                      # if MB.any() > 1.e-12:
                      #     print('Mass balance error MB > 1.e-12')


                      self.var.StorageStepINIT= np.sum(StorageStep) + DischargeM3StructuresR[0]
            #'''

            # ---- Uncomment lines in order to compute the mass balance error within the routing module for the options split routing  ----
            #'''
            if option['repMBTs']:
                 if (not(option['InitLisflood'])) and (option['SplitRouting']):
                    # SplitRouting
                    # compute the mass balance at the last of the sub-routing steps in order to account for the contributions of lakes and reservoirs
                    if NoRoutingExecuted == (self.var.NoRoutSteps-1):
                      ChanQAvgSR = self.var.sumDisDay/self.var.NoRoutSteps  #self.var.ChanQ
                      sum1=ChanQAvgSR.copy()
                      sum1[self.var.AtLastPointC == 0] = 0
                      OutStep = np.take(np.bincount(self.var.Catchments,weights=sum1 * self.var.DtSec),self.var.Catchments)

                      StorageStep=[]
                      # StorageStep= self.var.ChanM3Kin.copy()+self.var.Chan2M3Kin.copy()-self.var.Chan2M3Start.copy()
                      StorageStep = self.var.ChanM3


                      maskinfo = MaskInfo.instance()
                      DisStructureSR = maskinfo.in_zero()
                      DischargeM3StructuresR = maskinfo.in_zero()

                      if option['simulateReservoirs']:
                         sum1=[]
                         sum1 =self.var.ChanQ.copy()
                         StorageStep =  StorageStep + self.var.ReservoirStorageM3.copy()
                         # DisStructureSR = np.where(self.var.IsUpsOfStructureKinematicC, sum1 * self.var.DtRouting, 0)
                         DisStructureSR = np.where(self.var.IsUpsOfStructureChanC, sum1 * self.var.DtRouting, 0)
                         DischargeM3StructuresR = np.take(np.bincount(self.var.Catchments, weights=DisStructureSR), self.var.Catchments)
                         DischargeM3StructuresR -= self.var.DischargeM3StructuresIni

                      if option['simulateLakes']:
                         sum1 =self.var.ChanQ.copy()
                         StorageStep =  StorageStep + self.var.LakeStorageM3Balance.copy()
                         # DisStructureSR = np.where(self.var.IsUpsOfStructureKinematicC, sum1 * self.var.DtRouting, 0)
                         DisStructureSR = np.where(self.var.IsUpsOfStructureChanC, sum1 * self.var.DtRouting, 0)
                         DischargeM3StructuresR = np.take(np.bincount(self.var.Catchments, weights=DisStructureSR), self.var.Catchments)
                         DisLake = maskinfo.in_zero()
                         np.put(DisLake, self.var.LakeIndex, 0.5 * self.var.LakeInflowCC * self.var.DtRouting)
                         DischargeM3Lake = np.take(np.bincount(self.var.Catchments, weights=DisLake),self.var.Catchments)
                         DischargeM3StructuresR += DischargeM3Lake

                         DischargeM3StructuresR -= self.var.DischargeM3StructuresIni

                      # Mass Balance Error due to the Split Routing module
                      StorageStep1=np.take(np.bincount(self.var.Catchments, weights=StorageStep), self.var.Catchments)

                      self.var.MBErrorSplitRoutingM3  = - StorageStep1 + self.var.StorageStepINIT - OutStep  - DischargeM3StructuresR + self.var.AddedTRUN
                      # Discharge error at the outlet pointt [m3/s]
                      QoutCorrection=self.var.MBErrorSplitRoutingM3/self.var.DtRouting
                      QoutCorrection[self.var.AtLastPointC == 0] = 0
                      self.var.OutletDischargeErrorSplitRouting = np.take(np.bincount(self.var.Catchments,weights=QoutCorrection),self.var.Catchments)

                      self.var.StorageStepINIT= StorageStep1.copy()+DischargeM3StructuresR
             #'''

            # Legacy
            # TotalCrossSectionArea = np.maximum(self.var.ChanM3Kin * self.var.InvChanLength, 0.01)
            TotalCrossSectionArea = np.maximum(self.var.ChanM3 * self.var.InvChanLength, 0.01)
            self.var.FlowVelocity = np.minimum(self.var.ChanQKin/TotalCrossSectionArea, 0.36*self.var.ChanQKin**0.24)
            # Channel velocity (m/s); dividing Q (m3/s) by CrossSectionArea (m2)
            # avoid extreme velocities by using the Wollheim 2006 equation
            # assume 0.1 for upstream areas (outside ChanLdd)
            self.var.FlowVelocity *= np.minimum(np.sqrt(self.var.PixelArea)*self.var.InvChanLength,1)
            # reduction for sinuosity of channels
            self.var.TravelDistance=self.var.FlowVelocity*self.var.DtSec
            # if flow is fast, Traveltime=1, TravelDistance is high: Pixellength*DtSec
            # if flow is slow, Traveltime=DtSec then TravelDistance=PixelLength
            # maximum set to 30km/day for 5km cell, is at DtSec/Traveltime=6, is at Traveltime<DtSec/6


    def KinRouting(self,SideflowChan):
        """Kinematic routing based on a 4-point implicit finite-difference numerical solution of the kinematic wave equations.
        Given the instantaneous flow rate (discharge), the corresponding amount of water stored in the channel
        is calculated using Manning equation for steady state flow where Alpha is currently fixed
        at half of bankfull depth.
        See: Te Chow, V. and Maidment, D.R. and Mays, L.W. (1988). Applied Hydrology. McGraw-Hill. (Sec. 9.6)
        https://ponce.sdsu.edu/Applied_Hydrology_Chow_1988.pdf
        A = alpha * Q**beta
        V = chanlength * alpha * Q**beta
        Kinematic routing uses same variables for inputs and outputs. From upstream to downstream, input values are used
        to calculate inflow from upstream cells, then routing is solved and discharge values are updated.
        Takes:
        self.var.ChanQKin = inflow (at x) from upstream channels at time t+dt [m3/sec] (instant)
        self.var.ChanQKinAvgDt = average inflow (at x) from upstream channels at time t+dt [m3/sec] (average)
        SideflowChan = lateral inflow into the channel segment (cell) during dt [m3/channellength/sec]

        :param SideflowChan: side flow contribution from runoff (incl. groundwater), inflow from reservoirs (optional)
        and external inflow hydrographs (optional) [m3/s/m]
        :return
        self.var.ChanQKin = outflow (x+dx) at time t+dt (instant) [m3/s]
        self.var.ChanQKinAvgDt = average outflow (x+dx) at time t+dt (average) [m3/s]
        self.var.ChanM3Kin = amount of water stored in the channel at time t+dt (instant) [m3]
        """

        SideflowChan[np.isnan(SideflowChan)] = 0 # TEMPORARY FIX - SEE DEBUG ABOVE!
        # side flow contribution
        # side flow consists of runoff (incl. groundwater), inflow from reservoirs (optional) and external inflow hydrographs (optional)

        #####
        self.river_router.kinematicWaveRouting(self.var.ChanQKinAvgDt, self.var.ChanQKin, SideflowChan, "main_channel")
        # Calling function to solve kinematic routing
        #####

        self.var.ChanM3Kin = self.var.ChanLength * self.var.ChannelAlpha * self.var.ChanQKin**self.var.Beta
        # Water storage volume in the channel at end of computation step (at t+dt) (instant)

        self.var.ChanM3Kin = np.maximum(self.var.ChanM3Kin, 0.0)
        # Check for negative volumes at the end of computation step
        # Volume at time t+dt

        self.var.ChanQKin = (self.var.ChanM3Kin * self.var.InvChanLength * self.var.InvChannelAlpha) ** (self.var.InvBeta)
        # Correct for negative discharge at the end of computation step (instant)
        # Outflow (x+dx) at time t+dt

        return



    def SplitRouting(self, SideflowChan):
        """
        Split routing is based on a 4-point implicit finite-difference numerical solution of the kinematic wave equations.
        Split routing uses two lines of routing: a main channel and a virtual channel representing floodplains (second
        line of routing). Discharge is routed using the main channel up to QLimit. The second line uses the same channel
        geometry as the main channel but different riverbed roughness.
        Max discharge in the main channel (QLimit) is used to initialise the second line of routing then it's subtracted
        at the end of the computation.
        Total river outflow is given by (Q main channel + Q second line - QLimit)

        :param SideflowChan: side flow contribution from runoff (incl. groundwater), inflow from reservoirs (optional)
        and external inflow hydrographs (optional) [m3/s/m]
        :return:
        self.var.ChanQKin: outflow (x+dx) at time t+dt from the main channel (instant) [m3/s]
        self.var.ChanM3Kin: amount of water stored in the main channel at time t+dt (instant) [m3]
        self.var.Chan2QKin: outflow (x+dx) at time t+dt from the second line channel (including QLimit) (instant) [m3/s]
        self.var.Chan2M3Kin: amount of water stored in the second line channel at time t+dt (including self.var.Chan2M3Start) (instant) [m3]
        self.var.CrossSection2Area: cross-section area above bankfull for second line of routing at time t+dt (instant) [m2]
        """

        # --- Split sideflow between the two lines of routing ---
        # Ad
        SideflowRatio = np.where((self.var.ChanM3Kin + self.var.Chan2M3Kin) > 0,
                                 self.var.ChanM3Kin / (self.var.ChanM3Kin + self.var.Chan2M3Kin), 0.0)
        # Split sideflow between the two lines of routing

        # self.var.Sideflow1Chan = np.where(self.var.ChanM3Kin > self.var.M3Limit, SideflowRatio*SideflowChan, SideflowChan)
        # This is creating instability because ChanM3Kin can be < M3Limit between two routing sub-steps

        self.var.Sideflow1Chan = np.where(
            (self.var.ChanM3Kin + self.var.Chan2M3Kin - self.var.Chan2M3Start) > self.var.M3Limit,
            SideflowRatio * SideflowChan, SideflowChan)
        # sideflow to the main channel

        self.var.Sideflow1Chan = np.where(np.abs(SideflowChan) < 1e-7, SideflowChan, self.var.Sideflow1Chan)
        # too small values are avoided
        Sideflow2Chan = SideflowChan - self.var.Sideflow1Chan
        # sideflow to the 'second line' channel

        Sideflow2Chan = Sideflow2Chan + self.var.Chan2QStart * self.var.InvChanLength
        # as kinematic wave gets slower with less water a constant amount of water has to be added
        # -> add QLimit discharge

        # cmcheck
        # temporary workaround for average discharge in kinematic routing
        # creating dummy variables
        # ChanQKinOutStart_avg = self.var.ChanQKin.copy()
        # Chan2QKinOutStart_avg = self.var.Chan2QKin.copy()
        ######


        # --- Main channel routing ---

        # cmcheck
        self.river_router.kinematicWaveRouting(self.var.ChanQKinAvgDt, self.var.ChanQKin, self.var.Sideflow1Chan, "main_channel")
        # sef.var.ChanQKin is outflow (x+dx) from main channel at time t in input and at time t+dt in output (instant)
        # sef.var.ChanQKinAvgDt is average outflow (x+dx) from main channel during time dt (average)
        self.var.ChanM3Kin = self.var.ChanLength * self.var.ChannelAlpha * self.var.ChanQKin ** self.var.Beta
        # Volume in main channel at end of computation step (at t+dt) (instant)

        self.var.ChanM3Kin = np.maximum(self.var.ChanM3Kin, 0.0)
        # Check for negative volumes at the end of computation step in main channel
        # Volume in main channel at t+dt
        self.var.ChanQKin = (self.var.ChanM3Kin * self.var.InvChanLength * self.var.InvChannelAlpha) ** (self.var.InvBeta)
        # Correct negative discharge in main channel at the end of computation step
        # Outflow (x+dx) at t+dt (instant)


        # --- Second line channel routing (same channel geometry as main channel but increased Manning coeff) ---

        # cmcheck
        self.river_router.kinematicWaveRouting(self.var.Chan2QKinAvgDt, self.var.Chan2QKin, Sideflow2Chan, "floodplains")
        # sef.var.Chan2QKin is (virtual) total outflow (x+dx) at time t in input and at time t+dt in output (instant)
        # (same channel geometry but using increased Manninig coeff)
        # sef.var.Chan2QKinAvgDt is (virtual) average total outflow (x+dx) from second line channel during time dt (average)
        self.var.Chan2M3Kin = self.var.ChanLength * self.var.ChannelAlpha2 * self.var.Chan2QKin ** self.var.Beta
        # Total (virtual) volume of water in river channel when second routing line is active
        # (same channel geometry but using increased Manninig coeff)

        FldpM3 = self.var.Chan2M3Kin - self.var.Chan2M3Start
        # Water volume over bankfull
        self.var.Chan2M3Kin = np.where(FldpM3 < 0.0, self.var.Chan2M3Start, self.var.Chan2M3Kin)
        # Check for negative volume over bankfull at the end of routing step for second line of routing
        # Total (virtual) volume for second line of routing cannot be smaller than the bankfull volume for the second line
        # of routing aka the bankfull volume calculated with increased Manning coeff (Chan2M3Start)

        self.var.CrossSection2Area = (self.var.Chan2M3Kin - self.var.Chan2M3Start) * self.var.InvChanLength
        # Compute cross-section area above bankfull for second line of routing

        self.var.Chan2QKin = (self.var.Chan2M3Kin * self.var.InvChanLength * self.var.InvChannelAlpha2) ** (self.var.InvBeta)
        # (virtual) total outflow (at x + dx) at time t + dt (instant) for second line of routing (using increased Manninig coeff)
        # Correct negative discharge at the end of computation step in second line

        # FldpQKin = self.var.Chan2QKin - self.var.QLimit
        # Outflow at t+dt from above bankfull only

    def upstream(self, var):
        var_pcr = decompress(var)
        var_ups = compressArray(upstream(self.var.LddChan, var_pcr))
        return var_ups

    def compress_mct(self, var):
        """Compress to mct array.
        For any array (var) with all catchment pixels, it finds the MCT pixels (x) and
        reduces the dimension of the array (y).
        :param var: array (dimension is the number of cells in the basin)
        :return:
        y: same as input array (var) but with only MCT pixels
        """
        x = np.ma.masked_where(self.var.IsChannelKinematic, var)  # mask kinematic pixels
        y = x.compressed()

        return y
