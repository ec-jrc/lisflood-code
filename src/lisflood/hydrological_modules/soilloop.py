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

from lisflood.global_modules.add1 import *


class soilloop(object):

    """
    # ************************************************************
    # ***** SOIL LOOP    *****************************************
    # ************************************************************
    """

    def __init__(self, soilloop_variable):
        self.var = soilloop_variable


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self, sLoop):
        """ dynamic part of the soil loop module
        """

        # to make things faster: global functions to local functions

        # ************************************************************
        # ***** INTERCEPTION *****************************************
        # ************************************************************
        # Domain: whole pixel (permeable + direct runoff areas)
        #
        np.seterr(invalid='ignore',divide='ignore')

        SMax = np.where(self.var.LAI[sLoop] > 0.1, 0.935 + 0.498 * self.var.LAI[sLoop] - 0.00575 * np.square(self.var.LAI[sLoop]), globals.inZero)
        SMax = np.where(self.var.LAI[sLoop] > 43.3, 11.718, SMax)
        # maximum interception [mm]
        # Van Hoyningen-Huene (1981), p.46
        # small LAI: no interception
        # Note that for LAI = 43.3, SMax is at its maximum value of 11.718, and dropping
        # after that(but LAI should never be that high))

        self.var.Interception[sLoop] = np.where(SMax > 0.0,
                                                np.minimum(SMax - self.var.CumInterception[sLoop],
                                                           SMax * (1 - np.exp(-0.046 * self.var.LAI[sLoop] * self.var.Rain / SMax))),
                                                globals.inZero)
        self.var.Interception[sLoop] = np.minimum(self.var.Interception[sLoop], self.var.Rain)
        # Interception (in [mm] per timestep)
        # Smax is calculated from LAI as a constant map (above)
        # according to Aston (1970), based on Merriam (1960/1970)
        # 0.046*LAI = k = (1-p) p = 1-0.046*LAI  Aston (1970)
        # LAI must be a pixel average, not the average LAI for PER only!

        self.var.CumInterception[sLoop] += self.var.Interception[sLoop]
        # total interception in [mm] per timestep



        # ************************************************************
        # ***** EVAPORATION OF INTERCEPTED WATER *********************
        # ************************************************************
        # Domain: whole pixel (permeable + direct runoff areas)

        TaInterceptionMax = self.var.EWRef * (1 - self.var.LAITerm[sLoop])
        # Maximum evaporation rate of intercepted water, [mm] per timestep
        # TaInterception at rate of open water surface only evaporation
        # of intercepted water in vegetated fraction,hence mutiplication
        # by(1-LAITerm)

        self.var.TaInterception[sLoop] = np.maximum(np.minimum(self.var.CumInterception[sLoop], TaInterceptionMax),
                                                    globals.inZero)
        # amount of interception water [mm] that can be evaporated
        # assumption: at first all interception water is evaporated rate is equal to TaInterceptionMax


        self.var.CumInterception[sLoop] = np.maximum(self.var.CumInterception[sLoop] - self.var.TaInterception[sLoop], globals.inZero)
        # evaporated water is subtracted from Cumulative Interception
        self.var.LeafDrainage[sLoop] = self.var.LeafDrainageK * self.var.CumInterception[sLoop]
        # leaf drainage in [mm] per timestep, assuming linear reservoir
        # assumption: after 1 day all intercepted water is evaporated or has fallen
        # on the soil surface
        self.var.CumInterception[sLoop] = np.maximum(self.var.CumInterception[sLoop] - self.var.LeafDrainage[sLoop], globals.inZero)

        # ************************************************************
        # ***** AVAILABLE WATER FOR INFILTRATION ****************************
        # ************************************************************
        # Domain: AvailableWaterForInfiltration only used for permeable fraction
        # DirectRunoff is total for whole pixel (permeable + direct runoff areas)

        self.var.AvailableWaterForInfiltration[sLoop] =\
            np.maximum(self.var.Rain + self.var.SnowMelt + self.var.LeafDrainage[sLoop] - self.var.Interception[sLoop], globals.inZero)
        # Water available for infiltration during this timestep [mm]


        # ************************************************************
        # ***** SOIL WATER STRESS ************************************
        # ************************************************************
        # Domain: permeable fraction of pixel only

        p = 1 / (0.76 + 1.5 * np.minimum(0.1 * self.var.ETRef * self.var.InvDtDay,
                                     1.0)) - 0.10 * (5 - self.var.CropGroupNumber[sLoop])
        # soil water depletion fraction (easily available soil water)
        # Van Diepen et al., 1988: WOFOST 6.0, p.87
        # to avoid a strange behaviour of the p-formula's, ETRef is set to a maximum of
        # 10 mm/day. Thus, p will range from 0.15 to 0.45 at ETRef eq 10 and
        # CropGroupNumber 1-5
        p = np.where(self.var.CropGroupNumber[sLoop] <= 2.5, p + (np.minimum(0.1 * self.var.ETRef * self.var.InvDtDay, 1.0) - 0.6) / (
            self.var.CropGroupNumber[sLoop] * (self.var.CropGroupNumber[sLoop] + 3)), p)
        # correction for crop groups 1 and 2 (Van Diepen et al, 1988)
        p = np.maximum(np.minimum(p, 1.0), globals.inZero)
        # p is between 0 and 1
        WCrit1 = ((1 - p) * (self.var.WFC1[sLoop] - self.var.WWP1[sLoop])) + self.var.WWP1[sLoop]
        WCrit1a = ((1 - p) * (self.var.WFC1a[sLoop] - self.var.WWP1a[sLoop])) + self.var.WWP1a[sLoop]
        WCrit1b= ((1 - p) * (self.var.WFC1b[sLoop] - self.var.WWP1b[sLoop])) + self.var.WWP1b[sLoop]
             # critical moisture amount ([mm] water slice) for all layers

        if option['wateruse']:
            if sLoop==2:
                self.var.WFilla = np.minimum(WCrit1a,self.var.WPF3a[2])
                self.var.WFillb = np.minimum(WCrit1b,self.var.WPF3b[2])
                # if water use is calculated, get the filling of the soil layer for either pF3 or WCrit1
                # that is the amount of water the soil gets filled by water from irrigation

      #  with np.errstate(invalid='ignore',divide='ignore'):
           #  bc the divisor can have 0 -> this calculation is done first and raise a warning - zero encountered - even if it is catched afterwards
        self.var.RWS[sLoop] = np.where((WCrit1 - self.var.WWP1[sLoop]) > 0, (self.var.W1[sLoop] - self.var.WWP1[sLoop]) / (WCrit1 - self.var.WWP1[sLoop]), 1.0)

        # Transpiration reduction factor (in case of water stress)
        # if WCrit1 = WWP1, RWS is zero there is no water stress in that case
        self.var.RWS[sLoop] = np.maximum(
            np.minimum(self.var.RWS[sLoop], 1.0), globals.inZero)
        # Transpiration reduction factor (in case of water stress)

        if option['repStressDays']:
            self.var.SoilMoistureStressDays[sLoop] = np.where(self.var.RWS[sLoop] < 1, self.var.DtDay, globals.inZero)
            # Count number of days with soil water stress, RWS is between 0 and 1
            # no reduction of Transpiration at RWS=1, at RWS=0 there is no Transpiration at all

        # ************************************************************
        # ***** MAXIMUM TRANSPIRATION RATE ***************************
        # ************************************************************
        # Domain: permeable fraction of pixel only

        TranspirMax = self.var.CropCoef[sLoop] * self.var.ETRef * (1 - self.var.LAITerm[sLoop])
        # maximum transpiration rate ([mm] per timestep)
        # crop coefficient is mostly 1, except for excessively transpirating crops,
        # such as sugarcane and some forests (coniferous forests)

        self.var.TranspirMaxCorrected = np.maximum(TranspirMax - self.var.TaInterception[sLoop], globals.inZero)
        # subtract TaInterception from TranspirMax to ensure energy balance is respected
        # (maximize statement because TranspirMax and TaInterception are calculated from
        # reference surfaces with slightly diferent properties)


        # ************************************************************
        # ***** ACTUAL TRANSPIRATION RATE ****************************
        # ************************************************************
        # Domain: permeable fraction of pixel only
        self.var.Ta[sLoop] = np.maximum(np.minimum(self.var.RWS[sLoop] * self.var.TranspirMaxCorrected, self.var.W1[sLoop] - self.var.WWP1[sLoop]), 0.0)
        # actual transpiration based on both layers 1a and 1b
        self.var.Ta[sLoop] = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, globals.inZero, self.var.Ta[sLoop])
        # transpiration is 0 when soil is frozen
        # calculate distribution where to take Ta from:
        # 1st: above wCrit from layer 1a
        # 2nd: above Wcrit from layer 1b
        # 3rd:  distribute take off according to soil moisture availability below wcrit
        wc1a = np.maximum(self.var.W1a[sLoop] - WCrit1a, 0) # unstressed water availability from layer 1a without stress (above critical soil moisture)
        wc1b = np.maximum(self.var.W1b[sLoop] - WCrit1b, 0) # (same as above but for layer 1b)
        Ta1a = np.minimum(self.var.Ta[sLoop], wc1a)         # temporary transpiration from layer 1a (<= unstressed layer 1a availability)
        restTa = np.maximum(self.var.Ta[sLoop] - Ta1a, 0)   # transpiration left after layer 1a unstressed water has been abstracted
        Ta1b = np.minimum(restTa, wc1b)                     # temporary transpiration from layer 1b (<= unstressed layer 1b availability)
        restTa = np.maximum(restTa - Ta1b, 0)               # transpiration left after layers 1a and 1b unstressed water have been abstracted
        stressed_availability_1a = np.maximum(self.var.W1a[sLoop] - Ta1a - self.var.WWP1a[sLoop], 0)    #|
        stressed_availability_1b = np.maximum(self.var.W1b[sLoop] - Ta1b - self.var.WWP1b[sLoop], 0)    #|
        stressed_availability_tot = stressed_availability_1a + stressed_availability_1b                 #|> distribution of abstractions of
        available = stressed_availability_tot > 0                                                       #|> soil moisture below the critical value
        fraction_rest_1a = np.where(available, stressed_availability_1a / stressed_availability_tot, 0) #|> proportionally to each root-zone layer (1a and 1b)
        fraction_rest_1b = np.where(available, stressed_availability_1b / stressed_availability_tot, 0) #|> "stressed" availability
        Ta1a += fraction_rest_1a * restTa                                                               #|
        Ta1b += fraction_rest_1b * restTa                                                               #|
        self.var.W1a[sLoop] -= Ta1a
        self.var.W1b[sLoop] -= Ta1b
        self.var.W1[sLoop] = np.add(self.var.W1a[sLoop], self.var.W1b[sLoop])

        # ************************************************************
        # ***** ACTUAL BARE SOIL EVAPORATION *************************
        # ************************************************************
        # Domain: permeable fraction of pixel only
        # ESActPixel valid for whole pixel

        self.var.DSLR[sLoop] = np.where(self.var.AvailableWaterForInfiltration[
                                     sLoop] > self.var.AvWaterThreshold, 1.0, self.var.DSLR[sLoop] + self.var.DtDay)
        # Days since last rain (minimum value=1)
        # AvWaterThreshold in mm (Stroosnijder, 1987 in Supit, p. 92)
        # Note that this equation was originally designed for DAILY time steps
        # to make it work with ANY time step AvWaterThreshold has to be provided
        # as an INTENSITY in the binding (AvWaterRateThreshold), which isn't quite
        # right (possible solution: keep track of total AvailableWaterForInfiltration
        # during last 24 hrs look at this later)

        ESMax = self.var.ESRef * self.var.LAITerm[sLoop]
        # Maximum evaporation from a shaded soil surface in [mm] per time step
        self.var.ESAct[sLoop] = ESMax * (np.sqrt(self.var.DSLR[sLoop]) - np.sqrt(self.var.DSLR[sLoop] - 1))
        # Reduction of actual soil evaporation is assumed to be proportional to the
        # square root of time
        # ESAct in [mm] per timestep

        self.var.ESAct[sLoop] = np.minimum(self.var.ESAct[sLoop], self.var.W1[sLoop] - self.var.WRes1[sLoop])
        # either ESAct or availabe water from layer 1a and 1b
        self.var.ESAct[sLoop] = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, globals.inZero, self.var.ESAct[sLoop])
        # soil evaporation is 0 when soil is frozen
        self.var.ESAct[sLoop] = np.maximum(self.var.ESAct[sLoop], globals.inZero)


        # distributing ESAct over layer 1a and 1b, take the water from 1a first
        testSupply1a = self.var.W1a[sLoop] - self.var.WRes1a[sLoop]
        EsAct1a = np.where(self.var.ESAct[sLoop] > testSupply1a, testSupply1a , self.var.ESAct[sLoop])
        EsAct1b = np.maximum(self.var.ESAct[sLoop] - testSupply1a, globals.inZero)

        self.var.W1a[sLoop] = self.var.W1a[sLoop] - EsAct1a
        self.var.W1b[sLoop] = self.var.W1b[sLoop] - EsAct1b
        self.var.W1[sLoop] = np.add(self.var.W1a[sLoop], self.var.W1b[sLoop])
        # evaporation is subtracted from W1a (top layer) and W1b


        # ************************************************************
        # ***** INFILTRATION CAPACITY ********************************
        # ************************************************************
        # Domain: permeable fraction of pixel only
        #print np.max(self.var.W1a)
        RelSat1 = np.where(self.var.PoreSpaceNotZero1a[sLoop], np.minimum(
            self.var.W1[sLoop] / self.var.WS1[sLoop], 1.0), globals.inZero)
        # Relative saturation term of the first two layers. This will allow to have more infiltration
        # than the storage capacity of layer 1
        # Setting this to  a maximum of 1
        # will prevent MV creation due to small rounding errors
        # 'if' statement prevents division by zero for zero-depth soils
        SatFraction = 1 - (1 - RelSat1) ** self.var.b_Xinanjiang
        # Fraction of pixel that is at saturation as a function of
        # the ratio Theta1/ThetaS1. Distribution function taken from
        # Zhao,1977, as cited in Todini, 1996 (JoH 175, 339-382)
        InfiltrationPot = self.var.StoreMaxPervious[sLoop] * (1 - SatFraction) ** self.var.PowerInfPot * self.var.DtDay
        # Potential infiltration per time step [mm], which is the available pore space in the
        # pervious fraction of each pixel (1-SatFraction) times the depth of the upper soil layer.
        # For derivation see Appendix A in Todini, 1996

        InfiltrationPot = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, globals.inZero, InfiltrationPot)
        # When the soil is frozen (frostindex larger than threshold), potential
        # infiltration is zero


        # ************************************************************
        # ***** PREFERENTIAL FLOW (Rapid bypass soil matrix) *********
        # ************************************************************
        # Domain: permeable fraction of pixel only
        # PrefFlowPixel valid for whole pixel

        self.var.PrefFlow[sLoop] = (RelSat1 ** self.var.PowerPrefFlow) * self.var.AvailableWaterForInfiltration[sLoop]
        # Assumption: fraction of available water that bypasses the soil matrix
        # (added directly to Upper Zone) is power function of the
        # relative saturation of the topsoil
        self.var.AvailableWaterForInfiltration[sLoop] -= self.var.PrefFlow[sLoop]
        # Update water availabe for infiltration

        # ************************************************************
        # ***** ACTUAL INFILTRATION AND SURFACE RUNOFF ***************
        # ************************************************************
        # Domain: permeable fraction of pixel only
        # SurfaceRunoff, InfiltrationPixel are valid for whole pixel

        self.var.Infiltration[sLoop] = np.maximum(np.minimum(self.var.AvailableWaterForInfiltration[sLoop], InfiltrationPot), globals.inZero)
        # infiltration in [mm] per timestep
        # Maximum infiltration is equal to Rainfall-Interception-Snow+Snowmelt


        # if  +Inflitration is more than the maximum storage capacity of layer 1a, than the rest goes to 1b
        # could happen because InfiltrationPot is calculated based on layer 1a + 1b
        testW1a = self.var.W1a[sLoop] + self.var.Infiltration[sLoop]
           # sum up W1a and inflitration to test if it is > saturated WS1a

        #self.var.Infiltration[sLoop] = np.where(testW1a > self.var.WS1a[sLoop], self.var.WS1a[sLoop] - self.var.W1a[sLoop] ,self.var.Infiltration[sLoop])
           # in case we want to put it to runoff
        self.var.W1a[sLoop] = np.minimum(self.var.WS1a[sLoop], testW1a)
        self.var.W1b[sLoop] = self.var.W1b[sLoop] + np.where(testW1a > self.var.WS1a[sLoop], testW1a - self.var.WS1a[sLoop], globals.inZero)


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
        KUnSat1a, KUnSat1b, KUnSat2 = self.unsaturatedConductivity(sLoop) # Unsaturated conductivity at the beginning of this time step [mm/day]

        AvailableWater1a = self.var.W1a[sLoop] - self.var.WRes1a[sLoop]
        AvailableWater1b = self.var.W1b[sLoop] - self.var.WRes1b[sLoop]
        AvailableWater2 = self.var.W2[sLoop] - self.var.WRes2[sLoop]
        # Available water in both soil layers [mm]

        CapacityLayer1 = self.var.WS1b[sLoop] - self.var.W1b[sLoop]
        CapacityLayer2 = self.var.WS2[sLoop] - self.var.W2[sLoop]
        # Available storage capacity in subsoil

        CourantTopToSubA = np.where(AvailableWater1a == 0, globals.inZero, KUnSat1a * self.var.DtDay / AvailableWater1a)
        CourantTopToSubB = np.where(AvailableWater1b == 0, globals.inZero, KUnSat1b * self.var.DtDay / AvailableWater1b)
        CourantSubToGW = np.where(AvailableWater2 == 0, globals.inZero, KUnSat2 * self.var.DtDay / AvailableWater2)
        # Courant condition for computed soil moisture fluxes:
        # if Courant gt CourantCrit: sub-steps needed for required numerical accuracy
        # 'If'-statement prevents division by zero when available water equals zero:
        # in that case the unsaturated conductivity is zero as well, so
        # solution will be stable.
        CourantSoil = np.maximum(CourantTopToSubA, CourantTopToSubB, CourantSubToGW)
        # Both flow between soil layers and flow out of layer two
        # need to be numerically stable, so number of sub-steps is
        # based on process with largest Courant number
        NoSubS = np.maximum(1, np.ceil(CourantSoil / self.var.CourantCrit))
        self.var.NoSubSteps = int(np.nanmax(NoSubS))
        # Number of sub-steps needed for required numerical
        # accuracy. Always greater than or equal to 1
        # (otherwise division by zero!)

        # DtSub=self.var.DtDay/NoSubSteps

# HUh whats this:
        #DtSub = scalar(self.var.DtDay / mapmaximum(self.var.NoSubSteps))
        DtSub = self.var.DtDay / self.var.NoSubSteps

        # DtSub=spatial(DtDay)/mapmaximum(NoSubSteps)
        # Corresponding sub-timestep [days]
        # Soil loop is looping for the maximum of NoSubsteps
        # therefore DtSub is calculated as part of the timestep according to
        # the maximum of NoSubsteps

        WTemp1a = self.var.W1a[sLoop]
        WTemp1b = self.var.W1b[sLoop]
        WTemp2 = self.var.W2[sLoop]
        # Copy current value of W1 and W2 to temporary variables,
        # because computed fluxes may need correction for storage
        # capacity of subsoil and in case soil is frozen (after loop)
        self.var.SeepTopToSubA[sLoop] = 0
        self.var.SeepTopToSubB[sLoop] = 0
        # Initialize top- to subsoil flux (accumulated value for all sub-steps)
        self.var.SeepSubToGW[sLoop] = 0
        # Initialize fluxes out of subsoil (accumulated value for all sub-steps)
        # Start iterating


        #NoSubS = int(mapmaximum(self.var.NoSubSteps))
        #NoSubS = self.var.NoSubSteps

        for i in xrange(self.var.NoSubSteps):
            if i > 0:
                KUnSat1a, KUnSat1b, KUnSat2 = self.unsaturatedConductivity(sLoop, (WTemp1a, WTemp1b, WTemp2)) # Unsaturated conductivity [mm/day]
            SeepTopToSubSubStepA = np.minimum(KUnSat1a * DtSub, CapacityLayer1)
            SeepTopToSubSubStepB = np.minimum(KUnSat1b * DtSub, CapacityLayer2)
            # Flux from top- to subsoil (cannot exceed storage capacity
            # of layer 2)
            SeepSubToGWSubStep = np.minimum(KUnSat2 * DtSub, AvailableWater2)
            # Flux out of soil [mm]
            # Minimise statement needed for exceptional cases
            # when Theta2 becomes lt 0 (possible due to small precision errors)
            AvailableWater1a = AvailableWater1a - SeepTopToSubSubStepA
            AvailableWater1b = AvailableWater1b + SeepTopToSubSubStepA - SeepTopToSubSubStepB
            AvailableWater2 = AvailableWater2 + SeepTopToSubSubStepB - SeepSubToGWSubStep
            # Update water balance for layers 1 and 2
            WTemp1a = AvailableWater1a + self.var.WRes1a[sLoop]
            WTemp1b = AvailableWater1b + self.var.WRes1b[sLoop]
            WTemp2 = AvailableWater2 + self.var.WRes2[sLoop]
            # Update WTemp1 and WTemp2
            CapacityLayer1 = self.var.WS1b[sLoop] - WTemp1b
            CapacityLayer2 = self.var.WS2[sLoop] - WTemp2
            # Update available storage capacity in layer 2
            self.var.SeepTopToSubA[sLoop] += SeepTopToSubSubStepA
            self.var.SeepTopToSubB[sLoop] += SeepTopToSubSubStepB
            # Update total top- to subsoil flux for this step
            self.var.SeepSubToGW[sLoop] += SeepSubToGWSubStep
            # Update total flux out of subsoil for this step

        self.var.SeepTopToSubA[sLoop] = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, globals.inZero, self.var.SeepTopToSubA[sLoop])
        self.var.SeepTopToSubB[sLoop] = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, globals.inZero, self.var.SeepTopToSubB[sLoop])
        # When the soil is frozen (frostindex larger than threshold), seepage
        # is zero
        self.var.SeepSubToGW[sLoop] = np.where(self.var.FrostIndex > self.var.FrostIndexThreshold, globals.inZero, self.var.SeepSubToGW[sLoop])
        # When the soil is frozen (frostindex larger than threshold), seepage
        # is zero
        self.var.W1a[sLoop] = self.var.W1a[sLoop] - self.var.SeepTopToSubA[sLoop]
        self.var.W1b[sLoop] = self.var.W1b[sLoop] + self.var.SeepTopToSubA[sLoop] - self.var.SeepTopToSubB[sLoop]
        self.var.W2[sLoop] = self.var.W2[sLoop] + self.var.SeepTopToSubB[sLoop] - self.var.SeepSubToGW[sLoop]
        self.var.W1[sLoop] = np.add(self.var.W1a[sLoop], self.var.W1b[sLoop])
        # Update soil moisture amounts in top- and sub soil

        self.var.Infiltration[sLoop] = self.var.Infiltration[sLoop] - np.maximum(self.var.W1a[sLoop] - self.var.WS1a[sLoop], 0.0)
        self.var.W1a[sLoop] = np.minimum(self.var.W1a[sLoop], self.var.WS1a[sLoop])
        # Compute the amount of water that could not infiltrate and add this water to the surface runoff
        # Remove the excess of water in the top layer

        self.var.Theta1a[sLoop] = np.where(self.var.PoreSpaceNotZero1a[sLoop], self.var.W1a[
                                       sLoop] / self.var.SoilDepth1a[sLoop], globals.inZero)
        self.var.Theta1b[sLoop] = np.where(self.var.PoreSpaceNotZero1b[sLoop], self.var.W1b[
                                       sLoop] / self.var.SoilDepth1b[sLoop], globals.inZero)
        self.var.Theta2[sLoop] = np.where(self.var.PoreSpaceNotZero2[sLoop], self.var.W2[
                                       sLoop] / self.var.SoilDepth2[sLoop], globals.inZero)
        # Calculate volumetric soil moisture contents of top- and sub soil
        # [V/V]

        self.var.Sat1a[sLoop] = (self.var.W1a[sLoop] - self.var.WWP1a[sLoop])/(self.var.WFC1a[sLoop] - self.var.WWP1a[sLoop])
        self.var.Sat1b[sLoop] = (self.var.W1b[sLoop] - self.var.WWP1b[sLoop])/(self.var.WFC1b[sLoop] - self.var.WWP1b[sLoop])
        self.var.Sat1[sLoop] = (self.var.W1[sLoop] - self.var.WWP1[sLoop])/(self.var.WFC1[sLoop] - self.var.WWP1[sLoop])
        self.var.Sat2[sLoop] = (self.var.W2[sLoop] - self.var.WWP2[sLoop])/(self.var.WFC2[sLoop] - self.var.WWP2[sLoop])
        ## Calculate the saturation term with respect to the WP and FC values. This will indicate potential stress

        # ************************************************************
        # ***** CALCULATION OF PF VALUES FROM SOIL MOISTURE (OPTIONAL)
        # ************************************************************

        if option['simulatePF']:
            SatTerm1a = np.where(self.var.PoreSpaceNotZero1a[sLoop], (self.var.W1a[
                             sLoop] - self.var.WRes1[sLoop]) / (self.var.WS1[sLoop] - self.var.WRes1[sLoop]), globals.inZero)
            SatTerm1b = np.where(self.var.PoreSpaceNotZero1b[sLoop], (self.var.W1b[
                             sLoop] - self.var.WRes1[sLoop]) / (self.var.WS1[sLoop] - self.var.WRes1[sLoop]), globals.inZero)
            SatTerm2 = np.where(self.var.PoreSpaceNotZero2[sLoop], (self.var.W2[
                             sLoop] - self.var.WRes2[sLoop]) / (self.var.WS2[sLoop] - self.var.WRes2[sLoop]), globals.inZero)
            SatTerm1a = np.maximum(np.minimum(SatTerm1a, 1), globals.inZero)
            SatTerm1b = np.maximum(np.minimum(SatTerm1b, 1), globals.inZero)
            SatTerm2  = np.maximum(np.minimum(SatTerm2 , 1), globals.inZero)
            # Saturation term in Van Genuchten equation

            Head1a = np.where(SatTerm1a == 0, self.var.HeadMax, np.minimum(self.var.HeadMax, self.var.GenuInvAlpha1a[
                          sLoop] * ((1 / SatTerm1a) ** self.var.GenuInvM1a[sLoop] - 1) ** self.var.GenuInvN1a[sLoop]))
            Head1b = np.where(SatTerm1b == 0, self.var.HeadMax, np.minimum(self.var.HeadMax, self.var.GenuInvAlpha1b[
                          sLoop] * ((1 / SatTerm1b) ** self.var.GenuInvM1b[sLoop] - 1) ** self.var.GenuInvN1b[sLoop]))
            Head2 = np.where(SatTerm2 == 0, self.var.HeadMax, np.minimum(self.var.HeadMax, self.var.GenuInvAlpha2[
                          sLoop] * ((1 / SatTerm2) ** self.var.GenuInvM2[sLoop] - 1) ** self.var.GenuInvN2[sLoop]))
            # Compute capillary heads for both soil layers [cm]

            self.var.pF0[sLoop] = np.where(Head1a > 0, np.log10(Head1a), -1)
            self.var.pF1[sLoop] = np.where(Head1b > 0, np.log10(Head1b), -1)
            self.var.pF2[sLoop] = np.where(Head2  > 0, np.log10(Head2) , -1)
            # Compute pF. Set to -1 should heads become equal to mor less than 0. No idea
            # if this can even actually happen (copied this from old LISFLOOD version) but it
            # shouldn't do any harm.

        # ************************************************************
        # ***** GROUNDWATER TRANSFER TO CHANNEL NETWORK ***
        # ************************************************************
        # Domain: permeable fraction of pixel only
        # UZOutflowPixel, LZOutflowToChannelPixel, GwLossPixel valid for whole
        # pixel

        self.var.UZOutflow[sLoop] = np.minimum(self.var.UpperZoneK * self.var.UZ[sLoop], self.var.UZ[sLoop])
        # Outflow out of upper zone [mm]

        self.var.UZ[sLoop] = np.maximum(self.var.UZ[sLoop] - self.var.UZOutflow[sLoop], globals.inZero)

        # Update upper-, lower zone storage

        # ************************************************************
        # ***** TOTAL RUNOFF *****************************************
        # ************************************************************
        # Domain: whole pixel

        # TotalRunoff=SurfaceRunoff+UZOutflowPixel+LZOutflowToChannelPixel
        # Total runoff for this time step [mm]
        # Only calculated for reporting purposes!

        # ************************************************************
        # ***** UPPER- AND LOWER ZONE STORAGE ************************
        # ************************************************************
        # Domain: permeable fraction of pixel only
        # GwPercUZLZPixel valid for whole pixel

        if option['drainedIrrigation'] and sLoop==2:
                self.var.UZOutflow[sLoop] += self.var.DrainedFraction * self.var.SeepSubToGW[sLoop]
                self.var.UZ[sLoop] +=  (1 - self.var.DrainedFraction) * self.var.SeepSubToGW[sLoop] + self.var.PrefFlow[sLoop]
                                # use map of drainage systems, to determine return flow (if drained, all percolation to channel within day;
   	            # if not, all normal soil processes)
        else:
                self.var.UZ[sLoop] += self.var.SeepSubToGW[sLoop] + self.var.PrefFlow[sLoop]
                # water in upper response box [mm]

        self.var.GwPercUZLZ[sLoop] = np.minimum(self.var.GwPercStep, self.var.UZ[sLoop])
        # percolation from upper to lower response box in [mm] per timestep
        # maximum value is controlled by GwPercStep (which is
        # GwPercValue*DtDay)
        self.var.UZ[sLoop] = np.maximum(self.var.UZ[sLoop] - self.var.GwPercUZLZ[sLoop], globals.inZero)
        # (ground)water in upper response box [mm]



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
        KUnSat1a = self.var.KSat1a[fract] * np.sqrt(SatTerm1a) * np.square(1 - (1 - SatTerm1a ** self.var.GenuInvM1a[fract]) ** self.var.GenuM1a[fract])
        KUnSat1b = self.var.KSat1b[fract] * np.sqrt(SatTerm1b) * np.square(1 - (1 - SatTerm1b ** self.var.GenuInvM1b[fract]) ** self.var.GenuM1b[fract])
        KUnSat2 = self.var.KSat2[fract] * np.sqrt(SatTerm2) * np.square(1 - (1 - SatTerm2 ** self.var.GenuInvM2[fract]) ** self.var.GenuM2[fract])
        return KUnSat1a, KUnSat1b, KUnSat2
