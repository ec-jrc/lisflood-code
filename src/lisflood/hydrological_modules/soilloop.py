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
from __future__ import absolute_import, print_function
from nine import range

import numpy as np
import numexpr as nx
from numba import njit, prange, vectorize
from builtins import min, max
# from . import HydroModule
from ..global_modules.settings import LisSettings, MaskInfo

@njit(parallel=True, fastmath=False, cache=True)
def interception_water_balance(Interception, TaInterception, LeafDrainage, CumInterception, LAI, Rain, TaInterceptionMax, drainageK):
    num_vegs, num_pixs = Interception.shape
    for veg in range(num_vegs):
        for pix in prange(num_pixs):
            if LAI[veg,pix] <= .1:
                SMax = 0.
            elif LAI[veg,pix] <= 43.3:
                SMax = 0.935 + 0.498 * LAI[veg,pix] - 0.00575 * LAI[veg,pix]**2
            else:
                SMax = 11.718
            # maximum interception [mm]
            # Van Hoyningen-Huene (1981), p.46
            # small LAI: no interception
            # Note that for LAI = 43.3, SMax is at its maximum value of 11.718, and dropping
            # after that(but LAI should never be that high))
            if SMax > 0:
                Interception[veg,pix] = min(SMax - CumInterception[veg,pix], SMax * (1. - np.exp(-0.046 * LAI[veg,pix] * Rain[pix] / SMax)), Rain[pix])
                CumInterception[veg,pix] += Interception[veg,pix]
            else:
                Interception[veg,pix] = 0.
            # Interception (in [mm] per time step)
            # Smax is calculated from LAI as a constant self.var.PowerPrefFlow (above)
            # according to Aston (1970), based on Merriam (1960/1970)
            # 0.046*LAI = k = (1-p) p = 1-0.046*LAI  Aston (1970)
            # LAI must be a pixel average, not the average LAI for PER only!
            # ************************************************************
            # ***** EVAPORATION OF INTERCEPTED WATER *********************
            # ************************************************************
            if CumInterception[veg,pix] > 0.:
                TaInterception[veg,pix] = max(min(CumInterception[veg,pix], TaInterceptionMax[veg,pix]), 0.)
                # amount of interception water [mm] that can be evaporated
                # assumption: at first all interception water is evaporated rate is equal to
                # TaInterceptionMax
                CumInterception[veg,pix] = max(CumInterception[veg,pix] - TaInterception[veg,pix], 0.)
                # evaporated water is subtracted from Cumulative Interception
                LeafDrainage[veg,pix] = drainageK * CumInterception[veg,pix]
                # leaf drainage in [mm] per timestep, assuming linear reservoir
                # assumption: after 1 day all intercepted water is evaporated or has fallen
                # on the soil surface
                CumInterception[veg,pix] = max(CumInterception[veg,pix] - LeafDrainage[veg,pix], 0.)
            else:
                TaInterception[veg,pix] = 0.
                LeafDrainage[veg,pix] = 0.


@njit(parallel=True, fastmath=False, cache=True)
def potentialTranspiration(TranspirMax, TaInterception):
    return np.maximum(TranspirMax - TaInterception, 0)


@njit(parallel=True, fastmath=False, cache=True)
def soilColumnsWaterBalance(index_landuse_all, is_irrigated, is_paddy_irrig, paddy_inactive, DtDay,
                            AvailableWaterForInfiltration, Rain, SnowMelt,
                            LeafDrainage, Interception, DSLR,
                            AvWaterThreshold, ESAct, ESMax, isFrozenSoil,
                            b_Xinanjiang, StoreMaxPervious, PowerInfPot,
                            PrefFlow, PowerPrefFlow, Infiltration, CourantCrit,
                            PoreSpaceNotZero1a, PoreSpaceNotZero1b, PoreSpaceNotZero2,
                            KSat1a, KSat1b, KSat2,
                            GenuInvM1a, GenuInvM1b, GenuInvM2,
                            GenuM1a, GenuM1b, GenuM2,
                            W1a, W1b, W1, W2, 
                            Theta1a, Theta1b, Theta2,
                            Sat1a, Sat1b, Sat1, Sat2,
                            SeepTopToSubA, SeepTopToSubB, SeepSubToGW,
                            WRes1a, WRes1b, WRes1, WRes2,
                            WWP1a, WWP1b, WWP1, WWP2,
                            WFC1a, WFC1b, WFC1, WFC2,
                            SoilDepth1a, SoilDepth1b, SoilDepth2,
                            WS1a, WS1b, WS1, WS2,
                            UpperZoneK, DrainedFraction, GwPercStep,
                            UZOutflow, UZ, GwPercUZLZ):
    num_vegs, num_pixs = Interception.shape
    rain_plus_snowmelt = Rain + SnowMelt
    count_paddy_crop = 0
    

    for veg in range(num_vegs):   
    
        if is_paddy_irrig[veg]:
            _inactive_paddy = paddy_inactive[count_paddy_crop]
            if not _inactive_paddy.any(): # if no paddy is inactive, skip the vegetation fraction 
                continue
            is_drained_irrigation = False
            sim_pixels = np.arange(num_pixs)[_inactive_paddy]
            count_paddy_crop += 1
        else:
            is_drained_irrigation = is_irrigated[veg] and (DrainedFraction > 0)
            sim_pixels = np.arange(num_pixs)
        landuse = index_landuse_all[veg]
        NoSubS = np.empty(sim_pixels.size, dtype=np.int_)
        DtSub =  np.empty(sim_pixels.size)   ### merge 3 stef
        KUnSat1a, KUnSat1b, KUnSat2 = np.empty(sim_pixels.size), np.empty(sim_pixels.size), np.empty(sim_pixels.size)                         #| REMOVE BEFORE NEW
        AvailableWater1a, AvailableWater1b, AvailableWater2 = np.empty(sim_pixels.size), np.empty(sim_pixels.size), np.empty(sim_pixels.size) #| CALIBRATION
        CapacityLayer1, CapacityLayer2 = np.empty(sim_pixels.size), np.empty(sim_pixels.size)                                                 #| (SEE [*] BELOW)   Stef WHY??
        for q in prange(sim_pixels.size):
            pix = sim_pixels[q]

            # ************************************************************
            # ***** AVAILABLE WATER FOR INFILTRATION ****************************
            # ************************************************************
            # Domain: AvailableWaterForInfiltration only used for permeable fraction
            # DirectRunoff is total for whole pixel (permeable + direct runoff areas)
            AvailableWaterForInfiltration[veg,pix] = max(rain_plus_snowmelt[pix] + LeafDrainage[veg,pix] - Interception[veg,pix], 0.)
            # Water available for infiltration during this timestep [mm]
            # ************************************************************
            # ***** ACTUAL BARE SOIL EVAPORATION *************************
            # ************************************************************
            # ESActPixel valid for whole pixel
            if AvailableWaterForInfiltration[veg,pix] > AvWaterThreshold:
                DSLR[veg,pix] = 1
            else:
                DSLR[veg,pix] += DtDay
            # Days since last rain (minimum value=1)
            # AvWaterThreshold in mm (Stroosnijder, 1987 in Supit, p. 92)
            # Note that this equation was originally designed for DAILY time steps
            # to make it work with ANY time step AvWaterThreshold has to be provided
            # as an INTENSITY in the binding (AvWaterRateThreshold), which isn't quite
            # right (possible solution: keep track of total AvailableWaterForInfiltration
            # during last 24 hrs look at this later)
            if isFrozenSoil[pix]:
                ESAct[veg,pix] = 0. # soil evaporation is 0 when soil is frozen
            else:
                ESAct[veg,pix] = ESMax[veg,pix] * (np.sqrt(DSLR[veg,pix]) - np.sqrt(DSLR[veg,pix] - 1))
                # Reduction of actual soil evaporation is assumed to be proportional to the square root of time
                # ESAct in [mm] per timestep
                ESAct[veg,pix] = max(min(ESAct[veg,pix], W1[veg,pix] - WRes1[landuse,pix]), 0.)
                # either ESAct or availabe water from layer 1a and 1b
                # distributing ESAct over layer 1a and 1b, take the water from 1a first
                testSupply1a = W1a[veg,pix] - WRes1a[landuse,pix]
                EsAct1a = min(ESAct[veg,pix], testSupply1a)
                EsAct1b = max(ESAct[veg,pix] - testSupply1a, 0.)
                W1a[veg,pix] = max(W1a[veg,pix] - EsAct1a, WRes1a[landuse,pix])
                W1b[veg,pix] = max(W1b[veg,pix] - EsAct1b, WRes1b[landuse,pix])
            W1[veg,pix] = W1a[veg,pix] + W1b[veg,pix]
            # evaporation is subtracted from W1a (top layer) and W1b
            # ************************************************************
            # ***** INFILTRATION CAPACITY ********************************
            # ************************************************************
            # Domain: permeable fraction of pixel only            
            RelSat1 = min(W1[veg,pix] / WS1[landuse,pix], 1.0) if PoreSpaceNotZero1a[landuse,pix] else 0.0
            # Relative saturation term of the first two layers. This will allow to have more infiltration
            # than the storage capacity of layer 1
            # Setting this to  a maximum of 1
            # will prevent MV creation due to small rounding errors
            # 'if' statement prevents division by zero for zero-depth soils

            SatFraction = 1.0 - (1.0 - RelSat1) ** b_Xinanjiang[pix]
            # Fraction of pixel that is at saturation as a function of
            # the ratio Theta1/ThetaS1. Distribution function taken from
            # Zhao,1977, as cited in Todini, 1996 (JoH 175, 339-382)
            InfiltrationPot = 0.0 if isFrozenSoil[pix] else StoreMaxPervious[landuse,pix] * (1. - SatFraction) ** PowerInfPot[pix] * DtDay
            # Potential infiltration per time step [mm], which is the available pore space in the
            # pervious fraction of each pixel (1-SatFraction) times the depth of the upper soil layer.
            # For derivation see Appendix A in Todini, 1996
            # When the soil is frozen (frostindex larger than threshold), potential
            # infiltration is zero
            # ************************************************************
            # ***** PREFERENTIAL FLOW (Rapid bypass soil matrix) *********
            # ************************************************************
            # Domain: permeable fraction of pixel only
            # PrefFlowPixel valid for whole pixel
            PrefFlow[veg,pix] = (RelSat1 ** PowerPrefFlow[pix]) * AvailableWaterForInfiltration[veg,pix]
            # Assumption: fraction of available water that bypasses the soil matrix
            # (added directly to Upper Zone) is power function of the
            # relative saturation of the topsoil
            AvailableWaterForInfiltration[veg,pix] -= PrefFlow[veg,pix]
            # Update water availabe for infiltration
            # ************************************************************
            # ***** ACTUAL INFILTRATION AND SURFACE RUNOFF ***************
            # ************************************************************
            # Domain: permeable fraction of pixel only
            # SurfaceRunoff, InfiltrationPixel are valid for whole pixel
            Infiltration[veg,pix] = max(min(AvailableWaterForInfiltration[veg,pix], InfiltrationPot), 0.)
            # infiltration in [mm] per timestep
            # Maximum infiltration is equal to Rainfall-Interception-Snow+Snowmelt
            # if  +Inflitration is more than the maximum storage capacity of layer 1a, than the rest goes to 1b
            # could happen because InfiltrationPot is calculated based on layer 1a + 1b
            testW1a = W1a[veg,pix] + Infiltration[veg,pix]
               # sum up W1a and inflitration to test if it is > saturated WS1a
            #self.var.Infiltration[sLoop] = np.where(testW1a > self.var.WS1a[sLoop], self.var.WS1a[sLoop] - self.var.W1a[sLoop] ,self.var.Infiltration[sLoop])
               # in case we want to put it to runoff
            W1a[veg,pix] = min(WS1a[landuse,pix], testW1a)
            W1b[veg,pix] += max(testW1a - WS1a[landuse,pix], 0.)
            # soil moisture amount is adjusted
            # ************************************************************
            # ***** SOIL MOISTURE: FLUXES BETWEEN SOIL LAYERS   **********
            # ************************************************************
            # Domain: permeable fraction of pixel only
            # SeepTopToSubPixel,SeepSubToGWPixel valid for whole pixel
            # Flow between layer 1 and 2 and seepage out of layer 2: based on Darcy's
            # equation, assuming seepage is entirely gravity-driven,
            # so seepage rate equals unsaturated conductivity
            # The following calculations are performed to determine how many
            # sub-steps are needed to achieve sufficient numerical stability
            KUnSat1a[q] = unsaturatedConductivity(W1a[veg,pix], PoreSpaceNotZero1a[landuse,pix], WRes1a[landuse,pix], WS1a[landuse,pix],
                                                    KSat1a[landuse,pix], GenuInvM1a[landuse,pix], GenuM1a[landuse,pix])
            KUnSat1b[q] = unsaturatedConductivity(W1b[veg,pix], PoreSpaceNotZero1b[landuse,pix], WRes1b[landuse,pix], WS1b[landuse,pix],
                                                    KSat1b[landuse,pix], GenuInvM1b[landuse,pix], GenuM1b[landuse,pix])
            KUnSat2[q] = unsaturatedConductivity(W2[veg,pix], PoreSpaceNotZero2[landuse,pix], WRes2[landuse,pix], WS2[landuse,pix],
                                                   KSat2[landuse,pix], GenuInvM2[landuse,pix], GenuM2[landuse,pix])
            # Unsaturated conductivity at the beginning of this time step [mm/day]
            AvailableWater1a[q] = W1a[veg,pix] - WRes1a[landuse,pix]
            AvailableWater1b[q] = W1b[veg,pix] - WRes1b[landuse,pix]
            AvailableWater2[q] = W2[veg,pix] - WRes2[landuse,pix]
            # Available water in both soil layers [mm] # OPTIMIZE: COMPUTE IT BEFORE unsaturatedConductivity; ALSO COMPUTE SAT-RES AT INITIALISATION
            CapacityLayer1[q] = WS1b[landuse,pix] - W1b[veg,pix]
            CapacityLayer2[q] = WS2[landuse,pix] - W2[veg,pix]
            # Available storage capacity in subsoil
            CourantTopToSubA = 0. if AvailableWater1a[q] == 0 else KUnSat1a[q] * DtDay / AvailableWater1a[q]
            CourantTopToSubB = 0. if AvailableWater1b[q] == 0 else KUnSat1b[q] * DtDay / AvailableWater1b[q]
            CourantSubToGW = 0. if AvailableWater2[q] == 0 else KUnSat2[q] * DtDay / AvailableWater2[q]
            # Courant condition for computed soil moisture fluxes:
            # if Courant gt CourantCrit: sub-steps needed for required numerical accuracy
            # 'If'-statement prevents division by zero when available water equals zero:
            # in that case the unsaturated conductivity is zero as well, so
            # solution will be stable.
            CourantSoil = max(CourantTopToSubA, CourantTopToSubB, CourantSubToGW)
            # Both flow between soil layers and flow out of layer two
            # need to be numerically stable, so number of sub-steps is
            # based on process with largest Courant number
            NoSubS[q] = max(1, np.ceil(CourantSoil / CourantCrit))
            

            
            
        ### NoSubSteps = int(np.nanmax(NoSubS)) # merge3                      #| [*] UNINDENTED CODE BLOCK KEPT FOR CONSISTENCY: IT SHOULD BE REMOVED
        # Number of sub-steps needed for required numerical       #| WHEN A NEW CALIBRATION IS PERFORMED AS NOW THE NUMBER OF SUB-TIME-STEPS
        # accuracy. Always greater than or equal to 1             #| CAN BE SET INDEPENDENTLY FOR EACH PIXEL (BEFORE IT COULD NOT BE DONE
        # (otherwise division by zero!)                           #| BECAUSE OF VECTORIZATION)
        ### DtSub = DtDay / NoSubSteps    #merge3                             #|
        # DtSub=spatial(DtDay)/mapmaximum(NoSubSteps)             #|
        # Corresponding sub-timestep [days]                       #|
        # Soil loop is looping for the maximum of NoSubsteps      #|
        # therefore DtSub is calculated as part of the timestep   #|
        # according to the maximum of NoSubsteps                  #|              
        ### for q in prange(sim_pixels.size):   merge3                      #|
            pix = sim_pixels[q]
            WTemp1a = W1a[veg,pix]
            WTemp1b = W1b[veg,pix]
            WTemp2 = W2[veg,pix]
            # Copy current value of W1 and W2 to temporary variables,
            # because computed fluxes may need correction for storage
            # capacity of subsoil and in case soil is frozen (after loop)
            SeepTopToSubA[veg,pix] = 0.
            SeepTopToSubB[veg,pix] = 0.
            # Initialize top- to subsoil flux (accumulated value for all sub-steps)
            SeepSubToGW[veg,pix] = 0.
            # Initialize fluxes out of subsoil (accumulated value for all sub-steps)
            # Start iterating
            DtSub[q] = DtDay / NoSubS[q] ###  merge 3 (NoSubSteps)  
            for i in range(NoSubS[q]):  ### merge 3 (NoSubSteps)
                if i > 0:
                    KUnSat1a[q] = unsaturatedConductivity(WTemp1a, PoreSpaceNotZero1a[landuse,pix], WRes1a[landuse,pix], WS1a[landuse,pix],
                                                            KSat1a[landuse,pix], GenuInvM1a[landuse,pix], GenuM1a[landuse,pix])
                    KUnSat1b[q] = unsaturatedConductivity(WTemp1b, PoreSpaceNotZero1b[landuse,pix], WRes1b[landuse,pix], WS1b[landuse,pix],
                                                            KSat1b[landuse,pix], GenuInvM1b[landuse,pix], GenuM1b[landuse,pix])
                    KUnSat2[q] = unsaturatedConductivity(WTemp2, PoreSpaceNotZero2[landuse,pix], WRes2[landuse,pix], WS2[landuse,pix],
                                                           KSat2[landuse,pix], GenuInvM2[landuse,pix], GenuM2[landuse,pix])
                    # Unsaturated conductivity [mm/day]
                SeepTopToSubSubStepA = min(KUnSat1a[q] * DtSub[q], CapacityLayer1[q])
                SeepTopToSubSubStepB = min(KUnSat1b[q] * DtSub[q], CapacityLayer2[q])
                
                # Flux from top- to subsoil (cannot exceed storage capacity
                # of layer 2)
                SeepSubToGWSubStep = min(KUnSat2[q] * DtSub[q], AvailableWater2[q])
                # Flux out of soil [mm]
                # Minimise statement needed for exceptional cases
                # when Theta2 becomes lt 0 (possible due to small precision errors)
                AvailableWater1a[q] -= SeepTopToSubSubStepA
                AvailableWater1b[q] += SeepTopToSubSubStepA - SeepTopToSubSubStepB
                AvailableWater2[q] += SeepTopToSubSubStepB - SeepSubToGWSubStep
                # Update water balance for layers 1 and 2
                WTemp1a = AvailableWater1a[q] + WRes1a[landuse,pix]
                WTemp1b = AvailableWater1b[q] + WRes1b[landuse,pix]
                WTemp2 = AvailableWater2[q] + WRes2[landuse,pix]
                # Update WTemp1 and WTemp2
                CapacityLayer1[q] = WS1b[landuse,pix] - WTemp1b
                CapacityLayer2[q] = WS2[landuse,pix] - WTemp2
                # Update available storage capacity in layer 2
                SeepTopToSubA[veg,pix] += SeepTopToSubSubStepA
                SeepTopToSubB[veg,pix] += SeepTopToSubSubStepB
                # Update total top- to subsoil flux for this step
                SeepSubToGW[veg,pix] += SeepSubToGWSubStep
                # Update total flux out of subsoil for this step
            if isFrozenSoil[pix]:
                SeepTopToSubA[veg,pix] = 0.
                SeepTopToSubB[veg,pix] = 0.
                SeepSubToGW[veg,pix] = 0.
                # When the soil is frozen (frostindex larger than threshold), seepage is zero
                
            W1a[veg,pix] -= SeepTopToSubA[veg,pix]
            W1b[veg,pix] = W1b[veg,pix] + SeepTopToSubA[veg,pix] - SeepTopToSubB[veg,pix]
            W2[veg,pix] = W2[veg,pix] + SeepTopToSubB[veg,pix] - SeepSubToGW[veg,pix]
            W1[veg,pix] = W1a[veg,pix] + W1b[veg,pix] # SHOULD THIS BE MOVED AFTER W1a ADJUSTMENT BELOW?
            # Update soil moisture amounts in top- and sub soil
            Infiltration[veg,pix] -= max(W1a[veg,pix] - WS1a[landuse,pix], 0.)
            W1a[veg,pix] = min(W1a[veg,pix], WS1a[landuse,pix])
            # Compute the amount of water that could not infiltrate and add this water to the surface runoff
            # Remove the excess of water in the top layer
            # Calculate: volumetric soil moisture contents of top- and sub soil [V/V]; and saturation with respect to the WP and FC values
            # (it indicates potential stress)
            Theta1a[veg,pix] = thetaFun(W1a[veg,pix], SoilDepth1a[landuse,pix], PoreSpaceNotZero1a[landuse,pix])
            Theta1b[veg,pix] = thetaFun(W1b[veg,pix], SoilDepth1b[landuse,pix], PoreSpaceNotZero1b[landuse,pix])
            Theta2[veg,pix] = thetaFun(W2[veg,pix], SoilDepth2[landuse,pix], PoreSpaceNotZero2[landuse,pix])
            Sat1a[veg,pix] = satFun(W1a[veg,pix], WWP1a[landuse,pix], WFC1a[landuse,pix])
            Sat1b[veg,pix] = satFun(W1b[veg,pix], WWP1b[landuse,pix], WFC1b[landuse,pix])
            Sat1[veg,pix] = satFun(W1[veg,pix], WWP1[landuse,pix], WFC1[landuse,pix])
            Sat2[veg,pix] = satFun(W2[veg,pix], WWP2[landuse,pix], WFC2[landuse,pix])
            # *******************************************************************************************
            # ***** UPPER ZONE GROUNDWATER (UZ): TRANSFER TO CHANNEL NETWORK AND TO LOWER ZONE (LZ) *****
            # *******************************************************************************************
            UZOutflow[veg,pix] = min(UpperZoneK[pix] * UZ[veg,pix], UZ[veg,pix])
            # Outflow out of upper zone [mm]
            UZ[veg,pix] = max(UZ[veg,pix] - UZOutflow[veg,pix], 0.)
            if is_drained_irrigation:
                UZOutflow[veg,pix] += DrainedFraction * SeepSubToGW[veg,pix]
                UZ[veg,pix] += (1 - DrainedFraction) * SeepSubToGW[veg,pix] + PrefFlow[veg,pix]
                # use map of drainage systems, to determine return flow (if drained, all percolation to channel within day; if not, all normal soil processes)
            else:
                UZ[veg,pix] += SeepSubToGW[veg,pix] + PrefFlow[veg,pix]
                # water in upper response box [mm]
            GwPercUZLZ[veg,pix] = min(GwPercStep[pix], UZ[veg,pix])
            # percolation from upper to lower response box in [mm] per timestep
            # maximum value is controlled by GwPercStep (which is
            # GwPercValue*DtDay)
            UZ[veg,pix] = max(UZ[veg,pix] - GwPercUZLZ[veg,pix], 0.)
            # (ground)water in upper response box [mm]
          
        


@njit(nogil=True, fastmath=False, cache=True)
def unsaturatedConductivity(WTemp, PoreSpaceNotZero, WRes, WS, KSat, GenuInvM, GenuM):
    """Saturation term in Van Genuchten equation (always between 0 and 1)
       Due to small precision rounding errors, SatTerm can become slightly
       smaller than 0 or larger than 1, which results in errors in the Van
       Genuchten equation (root taken from negative number!)."""
    SatTerm = saturationDegree(WTemp, PoreSpaceNotZero, WRes, WS)
    return KSat * np.sqrt(SatTerm) * (1. - (1. - SatTerm ** GenuInvM) ** GenuM) ** 2


@njit(parallel=True, fastmath=False, cache=True)
def unsaturatedConductivityVectorized(WTemp, PoreSpaceNotZero, WRes, WS, KSat, GenuInvM, GenuM):
    out = np.empty(WTemp.size)
    for pix in prange(WTemp.size):
        out[pix] = unsaturatedConductivity(WTemp[pix], PoreSpaceNotZero[pix], WRes[pix], WS[pix], KSat[pix], GenuInvM[pix], GenuM[pix])
    return out


@njit(nogil=True, fastmath=False, cache=True)
def saturationDegree(w, PoreSpaceNotZero, WRes, WS):
    if PoreSpaceNotZero:
        return max(min((w - WRes) / (WS - WRes), 1.), 0.)
    else:
        return 0.


def __thetaFun(W, SoilDepth, PoreSpaceNotZero):
    return W / SoilDepth if PoreSpaceNotZero else 0.

thetaFun = njit(nogil=True, fastmath=False, cache=True)(__thetaFun)

thetaFunVectorized = vectorize("f8(f8,f8,b1)", nopython=True, target='parallel', fastmath=False, cache=True)(__thetaFun)

def __satFun(W, WWP, WFC):
    return (W - WWP) / (WFC - WWP)

satFun = njit(nogil=True, fastmath=False, cache=True)(__satFun)

satFunVectorized = vectorize("f8(f8,f8,f8)", nopython=True, target='parallel', fastmath=False, cache=True)(__satFun)


'''
@njit(parallel=True, fastmath=True)
def suctionUnsaturatedSoilPF(index_landuse_all, pF0, pF1, pF2, W1a, W1b, W2,
                             WRes1a, WRes1b, WRes2, WS1a, WS1b, WS2,
                             PoreSpaceNotZero1a, PoreSpaceNotZero1b, PoreSpaceNotZero2,
                             GenuInvAlpha1a, GenuInvAlpha1b, GenuInvAlpha2,
                             GenuInvM1a, GenuInvM1b, GenuInvM2,
                             GenuInvN1a, GenuInvN1b, GenuInvN2, HeadMax):
    """Compute PF values"""
    num_vegs, num_pixs = W1a.shape
    for veg in range(num_vegs):
        landuse = index_landuse_all[veg]
        for pix in prange(num_pixs):
            SatTerm1a = saturationDegree(W1a[veg,pix], PoreSpaceNotZero1a[landuse,pix], WRes1a[landuse,pix], WS1a[landuse,pix])
            SatTerm1b = saturationDegree(W1b[veg,pix], PoreSpaceNotZero1b[landuse,pix], WRes1b[landuse,pix], WS1b[landuse,pix])
            SatTerm2 = saturationDegree(W2[veg,pix], PoreSpaceNotZero2[landuse,pix], WRes2[landuse,pix], WS2[landuse,pix])
            # Saturation term in Van Genuchten equation
            Head1a = pressureHead(SatTerm1a, GenuInvAlpha1a[landuse,pix], GenuInvM1a[landuse,pix], GenuInvN1a[landuse,pix], HeadMax)
            Head1b = pressureHead(SatTerm1b, GenuInvAlpha1b[landuse,pix], GenuInvM1b[landuse,pix], GenuInvN1b[landuse,pix], HeadMax)
            Head2 = pressureHead(SatTerm2, GenuInvAlpha2[landuse,pix], GenuInvM2[landuse,pix], GenuInvN2[landuse,pix], HeadMax)
            # Compute capillary heads for both soil layers [cm]
            pF0[veg,pix] = np.log10(Head1a) if Head1a > 0 else -1.
            pF1[veg,pix] = np.log10(Head1b) if Head1b > 0 else -1.
            pF2[veg,pix] = np.log10(Head2) if Head2 > 0 else -1.
'''

@njit(nogil=True, fastmath=False, cache=True)
def pressureHead(SatTerm, GenuInvAlpha, GenuInvM, GenuInvN, HeadMax):
    if SatTerm == 0:
        return HeadMax
    else:
        return min(HeadMax, GenuInvAlpha * ((1. / SatTerm) ** GenuInvM - 1.) ** GenuInvN)

from ..global_modules.settings import LisSettings, MaskInfo, EPICSettings
from . import HydroModule


class soilloop(HydroModule):

    """
    # ************************************************************
    # ***** SOIL LOOP    *****************************************
    # ************************************************************
    """
    input_files_keys = {'wateruse': []}
    module_name = 'SoilLoop'
    

    def __init__(self, soilloop_variable):
        self.var = soilloop_variable

    def initial(self):
#        import ipdb; ipdb.set_trace()
        self.settings = LisSettings.instance()
        option = self.settings.options
        maskinfo = MaskInfo.instance()
        self.epic_settings = EPICSettings.instance()
        self.index_landuse_all = np.array([self.epic_settings.soil_uses.index(self.epic_settings.vegetation_landuse[v]) for v in self.var.vegetation])
        self.index_landuse_prescr = np.array([self.epic_settings.soil_uses.index(self.epic_settings.vegetation_landuse[v]) for v in self.var.prescribed_vegetation])
        self.is_irrigated = np.array([self.epic_settings.vegetation_landuse[v] == 'Irrigated' for v in self.var.vegetation])
        if option.get('cropsEPIC'):
            self.is_paddy_irrig = np.array([v in self.var.crop_module.paddy_crops for v in self.var.vegetation])
        else:
            self.is_paddy_irrig = np.zeros(len(self.var.vegetation), bool)

        self.index_landuse_all = np.array([self.var.SOIL_USES.index(self.var.VEGETATION_LANDUSE[v]) for v in self.var.vegetation]) #######################
        self.index_landuse_prescr = np.array([self.var.SOIL_USES.index(self.var.VEGETATION_LANDUSE[v]) for v in self.var.PRESCRIBED_VEGETATION]) #######################
        self.is_irrigated = np.array([self.var.VEGETATION_LANDUSE[v] == 'Irrigated' for v in self.var.vegetation]) #######################
        if option["cropsEPIC"]: #######################
            self.is_paddy_irrig = np.array([v in self.var.crop_module.paddy_crops for v in self.var.vegetation]) #######################
        else: #######################
            self.is_paddy_irrig = np.zeros(len(self.var.vegetation), bool) #######################



    def backup(self, variables):
        "TEST ONLY"
        return dict([(k, getattr(self.var, k).copy()) for k in variables])

    def reset(self, old_values):
        "TEST ONLY"
        for k, v in old_values.items():
            setattr(self.var, k, v)

    def compare(self, new_values):
        "TEST ONLY"
        for k, v in new_values.items():
            if (np.absolute(v.values - getattr(self.var, k).values).max() > 1e-6) or (np.isnan(v.values) | np.isnan(getattr(self.var, k).values)).any():
                import ipdb; ipdb.set_trace()

    def unsaturatedConductivity(self, fract, tmpW=None):
        """"""
        if tmpW == None:
            WTemp1a, WTemp1b, WTemp2 = self.var.W1a[fract].copy(), self.var.W1b[fract].copy(), self.var.W2[fract].copy()
        else:
            WTemp1a, WTemp1b, WTemp2 = tmpW
        SatTerm1a = (WTemp1a - self.var.WRes1a[fract]) / (self.var.WS1a[fract] - self.var.WRes1a[fract])
        SatTerm1a[~self.var.PoreSpaceNotZero1a[fract]] = 0
        SatTerm1b = (WTemp1b - self.var.WRes1b[fract]) / (self.var.WS1b[fract] - self.var.WRes1b[fract])
        SatTerm1b[~self.var.PoreSpaceNotZero1b[fract]] = 0
        SatTerm2 = (WTemp2 - self.var.WRes2[fract]) / (self.var.WS2[fract] - self.var.WRes2[fract])
        SatTerm2[~self.var.PoreSpaceNotZero2[fract]] = 0
        # Saturation term in Van Genuchten equation (always between 0 and 1)
        SatTerm1a = np.maximum(np.minimum(SatTerm1a, 1), 0)
        SatTerm1b = np.maximum(np.minimum(SatTerm1b, 1), 0)
        SatTerm2 = np.maximum(np.minimum(SatTerm2, 1), 0)
        # Due to small precision rounding errors, SatTerm can become slightly
        # smaller than 0 or larger than 1, which results in errors in the Van
        # Genuchten equation (root taken from negative number!).
        KUnSat1a = self.var.KSat1a[fract] * np.sqrt(SatTerm1a) * np.square(
            1 - (1 - SatTerm1a ** self.var.GenuInvM1a[fract]) ** self.var.GenuM1a[fract])
        KUnSat1b = self.var.KSat1b[fract] * np.sqrt(SatTerm1b) * np.square(
            1 - (1 - SatTerm1b ** self.var.GenuInvM1b[fract]) ** self.var.GenuM1b[fract])
        KUnSat2 = self.var.KSat2[fract] * np.sqrt(SatTerm2) * np.square(
            1 - (1 - SatTerm2 ** self.var.GenuInvM2[fract]) ** self.var.GenuM2[fract])
        return KUnSat1a, KUnSat1b, KUnSat2


    def dynamic_canopy(self):
        settings = LisSettings.instance()
        option = settings.options
        binding = settings.binding
        maskinfo = MaskInfo.instance()
        """ Dynamic part of the soil/vegetation loop describing processes that depend directly on the vegetation canopy:
            interception, evaporation of intercepted water, available water for infiltration,
            potential transpiration (with a correction applied only to prescribed fractions),
            actual transpiration and soil water stress (only prescribed fractions)"""
        # ***********************************************************************************************************************
        # ***** POTENTIAL INTERCEPTION EVAPORATION ******************************************************************************
        # ***********************************************************************************************************************
        one_minus_LAITerm = nx.evaluate('1. - LAITerm', local_dict={'LAITerm': self.var.LAITerm.sel(vegetation=self.var.prescribed_vegetation).values})
        TaInterceptionMax = nx.evaluate('EWRef * one_minus_LAITerm', global_dict={'EWRef': self.var.EWRef[None]})
        ## SG if self.settings.option.get('cropsEPIC'):
        if option['cropsEPIC']:
            TaInterceptionMax = np.vstack((TaInterceptionMax, self.var.crop_module.potential_interception_evaporation.values))
        # Maximum evaporation rate of intercepted water, [mm] per timestep
        # TaInterception at rate of open water surface only evaporation
        # of intercepted water in vegetated fraction,hence mutiplication  by(1-LAITerm)

        # ************************************************************
        # ***** INTERCEPTION *****************************************
        # ************************************************************
        interception_water_balance(self.var.Interception.values, self.var.TaInterception.values, self.var.LeafDrainage.values,
                                   self.var.CumInterception.values, self.var.LAI.values, self.var.Rain, TaInterceptionMax, self.var.LeafDrainageK)

        # ***********************************************************************************************************************
        # ***** POTENTIAL PLANT TRANSPIRATION ***********************************************************************************
        # ***********************************************************************************************************************
        gl_dict = {'CropCoef': self.var.CropCoef[self.index_landuse_prescr], 'ETRef': self.var.ETRef[None]}
        TranspirMax = nx.evaluate('CropCoef * ETRef * one_minus_LAITerm', global_dict=gl_dict)
        if option['cropsEPIC']:
            TranspirMax = np.vstack((TranspirMax, self.var.crop_module.potential_crop_ET.values))
        # maximum transpiration rate ([mm] per timestep)
        # crop coefficient is mostly 1, except for excessively transpirating crops,
        # such as sugarcane and some forests (coniferous forests)
        self.var.potential_transpiration[:] = potentialTranspiration(TranspirMax, self.var.TaInterception.values)
        # subtract TaInterception from TranspirMax to ensure energy balance is respected
        # (maximize statement because TranspirMax and TaInterception are calculated from
        # reference surfaces with slightly diferent properties)

        # *****************************************************************************************************************************
        # ***** SOIL WATER STRESS AND ACTUAL TRANSPIRATION FOR LISFLOOD PRESCRIBED FRACTIONS (EPIC IS USED FOR INTERACTIVE CROPS) *****
        # *****************************************************************************************************************************
        for veg in self.var.prescribed_vegetation:
            iveg, ilanduse, landuse = self.var.get_landuse_and_indexes_from_vegetation_epic(veg)

            swdf = 1 / (0.76 + 1.5 * np.minimum(0.1 * self.var.ETRef * self.var.InvDtDay, 1.0)) - 0.10 * (5 - self.var.CropGroupNumber.values[ilanduse])
            # soil water depletion fraction (easily available soil water)
            # Van Diepen et al., 1988: WOFOST 6.0, p.87
            # to avoid a strange behaviour of the p-formula's, ETRef is set to a maximum of
            # 10 mm/day. Thus, p will range from 0.15 to 0.45 at ETRef eq 10 and
            # CropGroupNumber 1-5
            swdf = np.where(self.var.CropGroupNumber.values[ilanduse] <= 2.5, swdf + (np.minimum(0.1 * self.var.ETRef * self.var.InvDtDay, 1.0) - 0.6) / (
                self.var.CropGroupNumber.values[ilanduse] * (self.var.CropGroupNumber.values[ilanduse] + 3)), swdf)
            # correction for crop groups 1 and 2 (Van Diepen et al, 1988)
            swdf = np.maximum(np.minimum(swdf, 1.0), 0)
            # p is between 0 and 1
            WCrit1 = ((1 - swdf) * (self.var.WFC1.values[ilanduse] - self.var.WWP1.values[ilanduse])) + self.var.WWP1.values[ilanduse]
            WCrit1a = ((1 - swdf) * (self.var.WFC1a.values[ilanduse] - self.var.WWP1a.values[ilanduse])) + self.var.WWP1a.values[ilanduse]
            WCrit1b = ((1 - swdf) * (self.var.WFC1b.values[ilanduse] - self.var.WWP1b.values[ilanduse])) + self.var.WWP1b.values[ilanduse]
            # critical moisture amount ([mm] water slice) for all layers
            if option['wateruse']:
                if landuse == "Irrigated":
                    #CR: using the original xarray variables WPF3a and WPF3a to keep WFilla and WFillb as xarrays
                    #N.B: WPF3a and WPF3b values are not changed in this function, so I can use the original
                    self.var.WFilla = np.minimum(WCrit1a, self.var.WPF3a.values[ilanduse])
                    self.var.WFillb = np.minimum(WCrit1b, self.var.WPF3b.values[ilanduse])
                    # if water use is calculated, get the filling of the soil layer for either pF3 or WCrit1
                    # that is the amount of water the soil gets filled by water from irrigation
               #  bc the divisor can have 0 -> this calculation is done first and raise a warning - zero encountered - even if it is catched afterwards
            self.var.RWS.values[iveg] = np.where((WCrit1 - self.var.WWP1.values[ilanduse]) > 0,\
                                             (self.var.W1.values[ilanduse] - self.var.WWP1.values[ilanduse]) / (WCrit1 - self.var.WWP1.values[ilanduse]), 1)
            # Transpiration reduction factor (in case of water stress)
            # if WCrit1 = WWP1, RWS is zero there is no water stress in that case
            self.var.RWS.values[iveg] = np.maximum(np.minimum(self.var.RWS.values[iveg], 1), 0)
            # Transpiration reduction factor (in case of water stress)
            if option['repStressDays']:
                self.var.SoilMoistureStressDays.values[iveg] = np.where(self.var.RWS.values[iveg] < 1, self.var.DtDay, 0)
                # Count number of days with soil water stress, RWS is between 0 and 1
                # no reduction of Transpiration at RWS=1, at RWS=0 there is no Transpiration at all

            transpirable_water = np.maximum(self.var.W1.values[ilanduse] - self.var.WWP1.values[ilanduse], 0)
            self.var.Ta.values[iveg] = np.minimum(self.var.RWS.values[iveg] * self.var.potential_transpiration[iveg], transpirable_water)
            # actual transpiration based on both layers 1a and 1b
            self.var.Ta.values[iveg] = np.where(self.var.isFrozenSoil, 0, self.var.Ta.values[iveg])
            # transpiration is 0 when soil is frozen
            # calculate distribution where to take Ta from:
            # 1st: above wCrit from layer 1a
            # 2nd: above Wcrit from layer 1b
            # 3rd:  distribute take off according to soil moisture availability below wcrit
            wc1a = np.maximum(self.var.W1a.values[ilanduse] - WCrit1a, 0) # unstressed water availability from layer 1a without stress (above critical soil moisture)
            wc1b = np.maximum(self.var.W1b.values[ilanduse] - WCrit1b, 0) # (same as above but for layer 1b)
            Ta1a = np.minimum(self.var.Ta.values[iveg], wc1a)         # temporary transpiration from layer 1a (<= unstressed layer 1a availability)
            restTa = np.maximum(self.var.Ta.values[iveg] - Ta1a, 0)   # transpiration left after layer 1a unstressed water has been abstracted
            Ta1b = np.minimum(restTa, wc1b)                       # temporary transpiration from layer 1b (<= unstressed layer 1b availability)
            restTa = np.maximum(restTa - Ta1b, 0)                 # transpiration left after layers 1a and 1b unstressed water have been abstracted
            stressed_availability_1a = np.maximum(self.var.W1a.values[ilanduse] - Ta1a - self.var.WWP1a.values[ilanduse], 0) #|
            stressed_availability_1b = np.maximum(self.var.W1b.values[ilanduse] - Ta1b - self.var.WWP1b.values[ilanduse], 0) #|
            stressed_availability_tot = stressed_availability_1a + stressed_availability_1b                      #|> distribution of abstractions of
            available = stressed_availability_tot > 0                                                            #|> soil moisture below the critical value
            fraction_rest_1a = np.where(available, stressed_availability_1a / stressed_availability_tot, 0)      #|> proportionally to each root-zone layer (1a and 1b)
            fraction_rest_1b = np.where(available, stressed_availability_1b / stressed_availability_tot, 0)      #|> "stressed" availability
            Ta1a += fraction_rest_1a * restTa                                                                    #|
            Ta1b += fraction_rest_1b * restTa                                                                    #|
            self.var.W1a.values[ilanduse] -= Ta1a
            self.var.W1b.values[ilanduse] -= Ta1b
            self.var.W1.values[iveg] = self.var.W1a.values[ilanduse] + self.var.W1b.values[ilanduse]


    def dynamic_soil(self):
        settings = LisSettings.instance()
        option = settings.options
        binding = settings.binding
        maskinfo = MaskInfo.instance()
        """ Dynamic part of the soil/vegetation loop describing soil processes (after canopy ones have been processed):
            """
        # Maximum evaporation from a shaded soil surface in [mm] per time step
        ESMax = nx.evaluate('ESRef * LAITerm', local_dict={'ESRef': self.var.ESRef[None], 'LAITerm': self.var.LAITerm.sel(vegetation=self.var.prescribed_vegetation).values})
        ### SG if self.settings.option.get('cropsEPIC'):
        if option['cropsEPIC']:
            ESMax = np.vstack((ESMax, self.var.crop_module.potential_undercanopy_evaporation.values))
            paddy_inactive = self.var.crop_module.irrigation_module.findInactivePaddy()
        else:
            paddy_inactive = np.zeros(self.var.num_pixel, bool)[None] # additional dimension needed for Numba to compile
        soilColumnsWaterBalance(self.index_landuse_all, self.is_irrigated, self.is_paddy_irrig, paddy_inactive, self.var.DtDay,
                                self.var.AvailableWaterForInfiltration.values, self.var.Rain, self.var.SnowMelt,
                                self.var.LeafDrainage.values, self.var.Interception.values, self.var.DSLR.values,
                                self.var.AvWaterThreshold, self.var.ESAct.values, ESMax, self.var.isFrozenSoil,
                                self.var.b_Xinanjiang, self.var.StoreMaxPervious.values, self.var.PowerInfPot,
                                self.var.PrefFlow.values, self.var.PowerPrefFlow, self.var.Infiltration.values, self.var.CourantCrit,
                                self.var.PoreSpaceNotZero1a.values, self.var.PoreSpaceNotZero1b.values, self.var.PoreSpaceNotZero2.values,
                                self.var.KSat1a.values, self.var.KSat1b.values, self.var.KSat2.values,
                                self.var.GenuInvM1a.values, self.var.GenuInvM1b.values, self.var.GenuInvM2.values,
                                self.var.GenuM1a.values, self.var.GenuM1b.values, self.var.GenuM2.values,
                                self.var.W1a.values, self.var.W1b.values, self.var.W1.values, self.var.W2.values, 
                                self.var.Theta1a.values, self.var.Theta1b.values, self.var.Theta2.values,
                                self.var.Sat1a.values, self.var.Sat1b.values, self.var.Sat1.values, self.var.Sat2.values,
                                self.var.SeepTopToSubA.values, self.var.SeepTopToSubB.values, self.var.SeepSubToGW.values,
                                self.var.WRes1a.values, self.var.WRes1b.values, self.var.WRes1.values, self.var.WRes2.values,
                                self.var.WWP1a.values, self.var.WWP1b.values, self.var.WWP1.values, self.var.WWP2.values,
                                self.var.WFC1a.values, self.var.WFC1b.values, self.var.WFC1.values, self.var.WFC2.values,
                                self.var.SoilDepth1a.values, self.var.SoilDepth1b.values, self.var.SoilDepth2.values,
                                self.var.WS1a.values, self.var.WS1b.values, self.var.WS1.values, self.var.WS2.values,
                                self.var.UpperZoneK, self.var.DrainedFraction, self.var.GwPercStep,
                                self.var.UZOutflow.values, self.var.UZ.values, self.var.GwPercUZLZ.values)
                   
                                
                                
                                
        # ************************************************************
        # ***** CALCULATION OF PF VALUES FROM SOIL MOISTURE (OPTIONAL)
        # ************************************************************
        @njit(parallel=True, fastmath=False, cache=True)
        def suctionUnsaturatedSoilPF(index_landuse_all, pF0, pF1, pF2, W1a, W1b, W2,
                                     WRes1a, WRes1b, WRes2, WS1a, WS1b, WS2,
                                     PoreSpaceNotZero1a, PoreSpaceNotZero1b, PoreSpaceNotZero2,
                                     GenuInvAlpha1a, GenuInvAlpha1b, GenuInvAlpha2,
                                     GenuInvM1a, GenuInvM1b, GenuInvM2,
                                     GenuInvN1a, GenuInvN1b, GenuInvN2, HeadMax):
            """Compute PF values"""
            num_vegs, num_pixs = W1a.shape
            for veg in range(num_vegs):
                landuse = index_landuse_all[veg]
                for pix in prange(num_pixs):
                    SatTerm1a = saturationDegree(W1a[veg,pix], PoreSpaceNotZero1a[landuse,pix], WRes1a[landuse,pix], WS1a[landuse,pix])
                    SatTerm1b = saturationDegree(W1b[veg,pix], PoreSpaceNotZero1b[landuse,pix], WRes1b[landuse,pix], WS1b[landuse,pix])
                    SatTerm2 = saturationDegree(W2[veg,pix], PoreSpaceNotZero2[landuse,pix], WRes2[landuse,pix], WS2[landuse,pix])
                    # Saturation term in Van Genuchten equation
                    Head1a = pressureHead(SatTerm1a, GenuInvAlpha1a[landuse,pix], GenuInvM1a[landuse,pix], GenuInvN1a[landuse,pix], HeadMax)
                    Head1b = pressureHead(SatTerm1b, GenuInvAlpha1b[landuse,pix], GenuInvM1b[landuse,pix], GenuInvN1b[landuse,pix], HeadMax)
                    Head2 = pressureHead(SatTerm2, GenuInvAlpha2[landuse,pix], GenuInvM2[landuse,pix], GenuInvN2[landuse,pix], HeadMax)
                    # Compute capillary heads for both soil layers [cm]
                    pF0[veg,pix] = np.log10(Head1a) if Head1a > 0 else -1.
                    pF1[veg,pix] = np.log10(Head1b) if Head1b > 0 else -1.
                    pF2[veg,pix] = np.log10(Head2) if Head2 > 0 else -1.
        if option['simulatePF']:
            suctionUnsaturatedSoilPF(self.index_landuse_all, self.var.pF0.values, self.var.pF1.values, self.var.pF2.values,
                                     self.var.W1a.values, self.var.W1b.values, self.var.W2.values,
                                     self.var.WRes1a.values, self.var.WRes1b.values, self.var.WRes2.values,
                                     self.var.WS1a.values, self.var.WS1b.values, self.var.WS2.values,
                                     self.var.PoreSpaceNotZero1a.values, self.var.PoreSpaceNotZero1b.values, self.var.PoreSpaceNotZero2.values,
                                     self.var.GenuInvAlpha1a.values, self.var.GenuInvAlpha1b.values, self.var.GenuInvAlpha2.values,
                                     self.var.GenuInvM1a.values, self.var.GenuInvM1b.values, self.var.GenuInvM2.values,
                                     self.var.GenuInvN1a.values, self.var.GenuInvN1b.values, self.var.GenuInvN2.values, self.var.HeadMax)

    def ThetaSatTerms(self, veg):
        iveg, ilanduse, _ = self.var.get_landuse_and_indexes_from_vegetation_epic(veg)

        self.var.Theta1a.values[iveg] = thetaFunVectorized(self.var.W1a.values[ilanduse], self.var.SoilDepth1a.values[ilanduse],
                                                       self.var.PoreSpaceNotZero1a.values[ilanduse])
        self.var.Theta1b.values[iveg] = thetaFunVectorized(self.var.W1b.values[ilanduse], self.var.SoilDepth1b.values[ilanduse],
                                                       self.var.PoreSpaceNotZero1b.values[ilanduse])
        self.var.Theta2.values[iveg] = thetaFunVectorized(self.var.W2.values[iveg], self.var.SoilDepth2.values[ilanduse],
                                                      self.var.PoreSpaceNotZero2.values[ilanduse])
        self.var.Sat1a.values[iveg] = satFunVectorized(self.var.W1a.values[ilanduse], self.var.WWP1a.values[ilanduse],
                                                   self.var.WFC1a.values[ilanduse])
        self.var.Sat1b.values[iveg] = satFunVectorized(self.var.W1b.values[ilanduse], self.var.WWP1b.values[ilanduse],
                                                   self.var.WFC1b.values[ilanduse])
        self.var.Sat1.values[iveg] = satFunVectorized(self.var.W1.values[iveg], self.var.WWP1.values[ilanduse],
                                                   self.var.WFC1.values[ilanduse])
        self.var.Sat2.values[iveg] = satFunVectorized(self.var.W2.values[iveg], self.var.WWP2.values[ilanduse],
                                                   self.var.WFC2.values[ilanduse])
