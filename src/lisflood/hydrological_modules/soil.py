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


class soil(object):

    """
    # ************************************************************
    # ***** SOIL         *****************************************
    # ************************************************************
    """

    def __init__(self, soil_variable):
        self.var = soil_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the soil module
        """
        def splitlanduse(array1, array2=None, array3=None):
            """ splits maps into the 3 different land use types - other , forest, irrigation
            """
            if array2 is None:
                array2 = array1
            if array3 is None:
                array3 = array1
            return [array1, array2, array3]

        # ------------------------------------------------
        # Fraction of Landuse
        # using maps instead of table to be more sensitive to landuse change
        # Soil properties for percentage of pixel area without forest, water ,
        # impervious soil

        #np.seterr(invalid='ignore',divide='ignore')

#        self.var.RiceFraction = loadmap('RiceFraction')
#        self.var.ForestFraction = loadmap('ForestFraction')
#        self.var.OtherFraction = loadmap('OtherFraction')
#        self.var.IrrigationFraction = loadmap('IrrigationFraction')
#        self.var.DirectRunoffFraction = loadmap('DirectRunoffFraction')
#        self.var.WaterFraction = loadmap('WaterFraction')

        self.var.OtherFraction += self.var.RiceFraction
           # for the moment rice is treated as other fraction	        if option['varfractionwater']:
            # if the fraction of water varies then the other fraction are stored
        self.var.WaterFractionBase = self.var.WaterFraction.copy()
        self.var.OtherFractionBase = self.var.OtherFraction.copy()
        self.var.IrrigationFractionBase = self.var.IrrigationFraction.copy()
        self.var.ForestFractionBase = self.var.ForestFraction.copy()
        self.var.DirectRunoffFractionBase = self.var.DirectRunoffFraction.copy()

        self.var.SoilFraction = self.var.ForestFraction +  self.var.OtherFraction + self.var.IrrigationFraction
        self.var.PermeableFraction = 1 - self.var.DirectRunoffFraction - self.var.WaterFraction
        # Permeable fraction of pixel

        # Soil Depth 1st layer [mm]
        # soil depth top layer for every landuse but forest, impervious soil
        # and water

        self.var.SoilDepth1a = defsoil('SoilDepth1','SoilDepth1Forest')
        self.var.SoilDepth1b = defsoil('SoilDepth2','SoilDepth2Forest')
        self.var.SoilDepth2  = defsoil('SoilDepth3','SoilDepth3Forest')

# ----------------- miscParameters ---------------------------

        self.var.CourantCrit = loadmap('CourantCrit')
        self.var.LeafDrainageK = np.minimum(self.var.DtDay * (1 / loadmap('LeafDrainageTimeConstant')), 1)
        # Reservoir constant for interception store
        # Minimize statement ONLY needed if LeafDrainageTimeConstant
        # becomes greater than DtDay (unlikely, but possible for time steps
        # greater than daily)

        self.var.AvWaterThreshold = loadmap('AvWaterRateThreshold') * self.var.DtDay
        # Converts AvWaterRateThreshold from  [mm/day]
        # to [mm] per time step


# ************************************************************
# ***** LAND USE RELATED MAPS ********************************
# ************************************************************

        # using maps instead of table to be more sensitive to landuse change
        # Soil properties for percentage of pixel area without forest, water ,
        # impervious soil
        #self.var.CropCoef = [loadmap('MapCropCoef'), loadmap('MapForestCropCoef')]
        self.var.CropCoef = defsoil('MapCropCoef','MapForestCropCoef','MapIrrigationCropCoef')

        # crop coefficients for each land use class

        self.var.CropGroupNumber = defsoil('MapCropGroupNumber','MapForestCropGroupNumber','MapIrrigationCropGroupNumber')

        # crop group numbers for soil water depletion factor
        # self.var.NManning = [loadmap('MapN'), loadmap('MapForestN'), 0.02]
        self.var.NManning = defsoil('MapN','MapForestN', 0.02)
        # Manning's roughness coefficient for each land use class
        # third manning is from direct runoff
        # self.var.NManningDirect=scalar(0.02)


# ************************************************************
# ***** MAPS DERIVED FROM SOIL TEXTURE AND SOIL DEPTH ********
# ************************************************************

        # HYPRES Parameters for TopSoil:

        self.var.KSat1a = defsoil('MapKSat1', 'MapKSat1Forest')
        self.var.KSat1b = defsoil('MapKSat2', 'MapKSat2Forest')
        self.var.KSat2 = defsoil('MapKSat3')
        # Saturated conductivity for other land use and forest
        Lambda1a = defsoil('MapLambda1','MapLambda1Forest')
        Lambda1b = defsoil('MapLambda2','MapLambda2Forest')
        Lambda2 = defsoil('MapLambda3')
        # Pore-size index (for Van Genuchten parameters)
        GenuAlpha1a = defsoil('MapGenuAlpha1','MapGenuAlpha1Forest')
        GenuAlpha1b = defsoil('MapGenuAlpha2','MapGenuAlpha2Forest')
        GenuAlpha2 = defsoil('MapGenuAlpha3')
        # Van Genuchten Alpha coefficient
        ThetaS1a = defsoil('MapThetaSat1','MapThetaSat1Forest')
        ThetaS1b = defsoil('MapThetaSat2','MapThetaSat2Forest')
        ThetaS2 = defsoil('MapThetaSat3')
        # Soil moisture content at saturation [V/V]
        ThetaRes1a = defsoil('MapThetaRes1', 'MapThetaRes1Forest')
        ThetaRes1b = defsoil('MapThetaRes2', 'MapThetaRes2Forest')
        ThetaRes2 = defsoil('MapThetaRes3')
        # Soil moisture content at saturation [V/V]

        # GenuN1=Lambda+1
        GenuN1a = [x + 1 for x in Lambda1a]
        GenuN1b = [x + 1 for x in Lambda1b]
        GenuN2 = [x + 1 for x in Lambda2]
        # self.var.GenuM1=Lambda1/GenuN1
        self.var.GenuM1a = [x / y for x, y in zip(Lambda1a, GenuN1a)]
        self.var.GenuM1b = [x / y for x, y in zip(Lambda1b, GenuN1b)]
        self.var.GenuM2 = [x / y for x, y in zip(Lambda2, GenuN2)]
        # self.var.GenuInvM1=1/self.var.GenuM1
        self.var.GenuInvM1a = [1 / x for x in self.var.GenuM1a]
        self.var.GenuInvM1b = [1 / x for x in self.var.GenuM1b]
        self.var.GenuInvM2 = [1 / x for x in self.var.GenuM2]
        # self.var.GenuInvN1=1/GenuN1
        self.var.GenuInvN1a = [1 / x for x in GenuN1a]
        self.var.GenuInvN1b = [1 / x for x in GenuN1b]
        self.var.GenuInvN2 = [1 / x for x in GenuN2]
        # GenuInvAlpha1=1/GenuAlpha1
        self.var.GenuInvAlpha1a = [1 / x for x in GenuAlpha1a]
        self.var.GenuInvAlpha1b = [1 / x for x in GenuAlpha1b]
        self.var.GenuInvAlpha2 = [1 / x for x in GenuAlpha2]
        # Van Genuchten n and m coefficients
        # In previous versions both n and m were read from separate tables.
        # Since both are calculated from same pore-size index (Lambda=n-1),
        # only table of Lambda is used here (Lambda is also more commonly
        # reported in the literature, which makes any comparison easier)
        # Inverse values computed once here for improved performance
        # (inverse of N and Alpha only needed if option simulatePF is used)

        # self.var.WS1=ThetaS1*self.var.SoilDepth1
        self.var.WS1a = [x * y for x, y in zip(ThetaS1a, self.var.SoilDepth1a)]
        self.var.WS1b = [x * y for x, y in zip(ThetaS1b, self.var.SoilDepth1b)]
        self.var.WS2 = [x * y for x, y in zip(ThetaS2, self.var.SoilDepth2)]
        self.var.WS1 = np.add(self.var.WS1a, self.var.WS1b)

        # self.var.WRes1=ThetaRes1*self.var.SoilDepth1
        self.var.WRes1a = [x * y for x, y in zip(ThetaRes1a, self.var.SoilDepth1a)]
        self.var.WRes1b = [x * y for x, y in zip(ThetaRes1b, self.var.SoilDepth1b)]
        self.var.WRes1 = np.add(self.var.WRes1a, self.var.WRes1b)
        self.var.WRes2 = [x * y for x, y in zip(ThetaRes2, self.var.SoilDepth2)]

        # self.var.WS1WRes=self.var.WS1-self.var.WRes1
        self.var.WS1WResa = [x - y for x, y in zip(self.var.WS1a, self.var.WRes1a)]
        self.var.WS1WResb = [x - y for x, y in zip(self.var.WS1b, self.var.WRes1b)]
        self.var.WS2WRes = [x - y for x, y in zip(self.var.WS2, self.var.WRes2)]

        # Express volume fractions in [mm] water slice

        # self.var.WFC1=self.var.WRes1+(self.var.WS1-self.var.WRes1)/((1+(GenuAlpha1*100)**GenuN1)**self.var.GenuM1)
        self.var.WFC1a = map(lambda res, s, ga, gn, gm: res + (s - res) / ((1 + (ga * 100)
                       ** gn) ** gm), self.var.WRes1a, self.var.WS1a, GenuAlpha1a, GenuN1a, self.var.GenuM1a)
        self.var.WFC1b = map(lambda res, s, ga, gn, gm: res + (s - res) / ((1 + (ga * 100)
                       ** gn) ** gm), self.var.WRes1b, self.var.WS1b, GenuAlpha1b, GenuN1b, self.var.GenuM1b)
        self.var.WFC1 = np.add(self.var.WFC1a, self.var.WFC1b)
        self.var.WFC2 = map(lambda res, s, ga, gn, gm: res + (s - res) / ((1 + (ga * 100)
                       ** gn) ** gm), self.var.WRes2, self.var.WS2, GenuAlpha2, GenuN2, self.var.GenuM2)
        # Soil moisture at field capacity (pF2, 100 cm) [mm water slice]
        # Mualem equation (van Genuchten, 1980)

        self.var.WPF3a = map(lambda res, s, ga, gn, gm: res + (s - res) / ((1 + (ga * 1000)
                        ** gn) ** gm), self.var.WRes1a, self.var.WS1a, GenuAlpha1a, GenuN1a, self.var.GenuM1a)
        self.var.WPF3b = map(lambda res, s, ga, gn, gm: res + (s - res) / ((1 + (ga * 1000)
                        ** gn) ** gm), self.var.WRes1b, self.var.WS1b, GenuAlpha1b, GenuN1b, self.var.GenuM1b)
        self.var.WPF3 = np.add(self.var.WPF3a, self.var.WPF3b)

        # Soil moisture at field capacity (pF3, 1000 cm) [mm water slice]
        # Mualem equation (van Genuchten, 1980)        # self.var.WWP1=self.var.WRes1+(self.var.WS1-self.var.WRes1)/  ((1+(GenuAlpha1*(10**4.2))**GenuN1)**self.var.GenuM1)
        self.var.WWP1a = map(lambda res, s, ga, gn, gm: res + (s - res) / ((1 + (ga * 15000)
                       ** gn) ** gm), self.var.WRes1a, self.var.WS1a, GenuAlpha1a, GenuN1a, self.var.GenuM1a)
        self.var.WWP1b = map(lambda res, s, ga, gn, gm: res + (s - res) / ((1 + (ga * 15000)
                       ** gn) ** gm), self.var.WRes1b, self.var.WS1b, GenuAlpha1b, GenuN1b, self.var.GenuM1b)
        self.var.WWP1 = np.add(self.var.WWP1a, self.var.WWP1b)
        self.var.WWP2 = map(lambda res, s, ga, gn, gm: res + (s - res) / ((1 + (ga * 15000)
                       ** gn) ** gm), self.var.WRes2, self.var.WS2, GenuAlpha2, GenuN2, self.var.GenuM2)
        # Soil moisture at wilting point (pF4.2, 10**4.2 cm) in [mm] water slice
        # Mualem equation (van Genuchten, 1980)

        self.var.PoreSpaceNotZero1a = splitlanduse(np.bool8((self.var.SoilDepth1a[0] != 0) & (self.var.WS1a[0] != 0)),
             np.bool8((self.var.SoilDepth1a[1] != 0) & (self.var.WS1a[1] != 0)),
             np.bool8((self.var.SoilDepth1a[2] != 0) & (self.var.WS1a[2] != 0)))
        self.var.PoreSpaceNotZero1b = splitlanduse(np.bool8((self.var.SoilDepth1b[0] != 0) & (self.var.WS1b[0] != 0)),
             np.bool8((self.var.SoilDepth1b[1] != 0) & (self.var.WS1b[1] != 0)),
             np.bool8((self.var.SoilDepth1b[2] != 0) & (self.var.WS1b[2] != 0)))
        self.var.PoreSpaceNotZero2 = splitlanduse(np.bool8((self.var.SoilDepth2[0] != 0) & (self.var.WS2[0] != 0)),
             np.bool8((self.var.SoilDepth2[1] != 0) & (self.var.WS2[1] != 0)),
             np.bool8((self.var.SoilDepth2[2] != 0) & (self.var.WS2[2] != 0)))

#        self.var.PoreSpaceNotZero1 = [np.bool8((self.var.SoilDepth1[0] != 0) & (self.var.WS1[0] != 0)),
#            np.bool8((self.var.SoilDepth1[1] != 0) & (self.var.WS1[1] != 0))]
#        self.var.PoreSpaceNotZero2 = [np.bool8((self.var.SoilDepth2[0] != 0) & (self.var.WS2[0] != 0)),
#            np.bool8((self.var.SoilDepth2[1] != 0) & (self.var.WS2[1] != 0))]
        # Flag that is Boolean 1 if pixel has (any) soil moisture storage space.
        # Needed to avoid divisions by zero in soil moisture calculations

        # ***** INITIAL VALUES for soil

        ThetaInit1aValue = defsoil('ThetaInit1Value','ThetaForestInit1Value','ThetaIrrigationInit1Value')
        ThetaInit1bValue = defsoil('ThetaInit2Value','ThetaForestInit2Value','ThetaIrrigationInit2Value')
        ThetaInit2Value = defsoil('ThetaInit3Value','ThetaForestInit3Value','ThetaIrrigationInit3Value')

        WInit1a = splitlanduse(globals.inZero.copy())
        WInit1b = splitlanduse(globals.inZero.copy())
        WInit2 =  splitlanduse(globals.inZero.copy())
        WInit1a[0] = np.where(ThetaInit1aValue[0] == -9999, self.var.WFC1a[0], ThetaInit1aValue[0] * self.var.SoilDepth1a[0])
        WInit1a[1] = np.where(ThetaInit1aValue[1] == -9999, self.var.WFC1a[1], ThetaInit1aValue[1] * self.var.SoilDepth1a[1])
        WInit1a[2] = np.where(ThetaInit1aValue[2] == -9999, self.var.WFC1a[2], ThetaInit1aValue[2] * self.var.SoilDepth1a[2])
        WInit1b[0] = np.where(ThetaInit1bValue[0] == -9999, self.var.WFC1b[0], ThetaInit1bValue[0] * self.var.SoilDepth1b[0])
        WInit1b[1] = np.where(ThetaInit1bValue[1] == -9999, self.var.WFC1b[1], ThetaInit1bValue[1] * self.var.SoilDepth1b[1])
        WInit1b[2] = np.where(ThetaInit1bValue[2] == -9999, self.var.WFC1b[2], ThetaInit1bValue[2] * self.var.SoilDepth1b[2])
        WInit2[0] = np.where(ThetaInit2Value[0] == -9999, self.var.WFC2[0], ThetaInit2Value[0] * self.var.SoilDepth2[0])
        WInit2[1] = np.where(ThetaInit2Value[1] == -9999, self.var.WFC2[1], ThetaInit2Value[1] * self.var.SoilDepth2[1])
        WInit2[2] = np.where(ThetaInit2Value[2] == -9999, self.var.WFC2[2], ThetaInit2Value[2] * self.var.SoilDepth2[2])
        # Initial soil moisture in permeable fraction of pixel
        # Set soil to field capacity if initial value
        # in settings file equals -9999
        # IMPORTANT: WInit1 and WInit2 represent the soil moisture in the
        # *permeable* fraction of the pixel *only* (since all soil moisture-related
        # calculations are done for permeable fraction only!).

        WInit1a[0] = np.where(self.var.PoreSpaceNotZero1a[0], WInit1a[0], globals.inZero)
        WInit1a[1] = np.where(self.var.PoreSpaceNotZero1a[1], WInit1a[1], globals.inZero)
        WInit1a[2] = np.where(self.var.PoreSpaceNotZero1a[2], WInit1a[2], globals.inZero)
        WInit1b[0] = np.where(self.var.PoreSpaceNotZero1b[0], WInit1b[0], globals.inZero)
        WInit1b[1] = np.where(self.var.PoreSpaceNotZero1b[1], WInit1b[1], globals.inZero)
        WInit1b[2] = np.where(self.var.PoreSpaceNotZero1b[2], WInit1b[2], globals.inZero)
        WInit2[0] = np.where(self.var.PoreSpaceNotZero2[0], WInit2[0], globals.inZero)
        WInit2[1] = np.where(self.var.PoreSpaceNotZero2[1], WInit2[1], globals.inZero)
        WInit2[2] = np.where(self.var.PoreSpaceNotZero2[2], WInit2[2], globals.inZero)
        # Set to zero if soil depth is zero
        self.var.W1a = WInit1a
        self.var.W1b = WInit1b
        self.var.W1 = np.add(self.var.W1a, self.var.W1b)
        self.var.W2 = WInit2
        # Set soil moisture to initial value

        self.var.Sat1a = splitlanduse(globals.inZero.copy())
        self.var.Sat1b = splitlanduse(globals.inZero.copy())
        self.var.Sat1 = splitlanduse(globals.inZero.copy())
        self.var.Sat2 = splitlanduse(globals.inZero.copy())


# ************************************************************
# ***** REPEATEDLY USED EXPRESSIONS IN XINANJIANG
# ***** INFILTRATION MODEL
# ************************************************************
        self.var.b_Xinanjiang = loadmap('b_Xinanjiang')
        self.var.PowerInfPot = (self.var.b_Xinanjiang + 1) / self.var.b_Xinanjiang
        # Power in infiltration equation
        # self.var.StoreMaxPervious=self.var.WS1/(self.var.b_Xinanjiang+1)
#        self.var.StoreMaxPervious = [x / (self.var.b_Xinanjiang + 1) for x in self.var.WS1a]

        self.var.StoreMaxPervious = [x / (self.var.b_Xinanjiang + 1) for x in self.var.WS1]
        # Maximum soil moisture storage in pervious fraction of
        # pixel (expressed as [mm] water slice)


# ********************************************
# ****  PowerPrefFlow
# ********************************************
        self.var.PowerPrefFlow = loadmap('PowerPrefFlow')

# ************************************************************
# ***** INITIAL VALUES
# ************************************************************
# Inputs in waterbalance model and/or initial assumption
        # CMmod
        # DSLRInit = defsoil('DSLRInitValue', 'DSLRForestInitValue','DSLRIrrigationInitValue')

        DSLRInit = defsoil('DSLRInitValue', 'DSLRForestInitValue', 'DSLRIrrigationInitValue')
        self.var.DSLR = splitlanduse(*[np.maximum(d_i, 1) for d_i in DSLRInit])
        # Days since last rainfall
        # Impose lower limit of 1 because otherwise
        # square root may be taken out of a negative number for Dtsec lt 86400!

        # CumInterceptionInit=ifthen(defined(MaskMap),scalar(loadmap('CumIntInitValue')))
        self.var.CumInterception = defsoil('CumIntInitValue', 'CumIntForestInitValue', 'CumIntIrrigationInitValue')
        #self.var.CumInterception = [CumInterceptionInit[0], CumInterceptionInit[1]]
        # initial cumulative interception, [mm]

        # Initialising cumulative output variables
        # These are all needed to compute the cumulative mass balance error


        self.var.TotalPrecipitation = globals.inZero.copy()
        # precipitation [mm]
        self.var.TaCUM = globals.inZero.copy()
        # Cumulative transpiration [mm]
        self.var.TaInterceptionCUM = globals.inZero.copy()
        # Cumulative evaporation from interception store [mm]
        self.var.ESActCUM = globals.inZero.copy()
        # Cumulative evaporation [mm]

        self.var.SoilMoistureStressDays = splitlanduse(globals.inZero.copy())
        # number of days in simulation with soil moisture stress (days)

        self.var.Theta1a = splitlanduse(globals.inZero.copy())
        self.var.Theta1b = splitlanduse(globals.inZero.copy())
        self.var.Theta2 =  splitlanduse(globals.inZero.copy())

        self.var.TaInterception = defsoil(globals.inZero.copy())
        self.var.Interception = defsoil(globals.inZero.copy())
        self.var.LeafDrainage = defsoil(globals.inZero.copy())

        self.var.Ta = splitlanduse(globals.inZero.copy())
        self.var.ESAct = splitlanduse(globals.inZero.copy())
        self.var.PrefFlow = splitlanduse(globals.inZero.copy())
        self.var.Infiltration = splitlanduse(globals.inZero.copy())
        self.var.SeepTopToSubA = splitlanduse(globals.inZero.copy())
        self.var.SeepTopToSubB = splitlanduse(globals.inZero.copy())
        self.var.SeepSubToGW = splitlanduse(globals.inZero.copy())

        self.var.Theta = splitlanduse(globals.inZero.copy())
        self.var.AvailableWaterForInfiltration = splitlanduse(globals.inZero.copy())
        self.var.RWS = splitlanduse(globals.inZero.copy())


# ************************************************************
# ***** INITIALIZATION OF IMPERVIOUS SOIL     ****************
# ************************************************************

        self.var.CumInterSealed = loadmap('CumIntSealedInitValue')
        # cumulative depression storage
        self.var.SMaxSealed = loadmap('SMaxSealed')
        # maximum depression storage for water on impervious surface
        # which is not immediately causing surface runoff  [mm]

        if option['drainedIrrigation']:
            self.var.DrainedFraction = loadmap('DrainedFraction')
            # drained fraction: water from irrigated water is directly send to channel
            # depending on the drained fraction
# ************************************************************
# ***** INITIALIZATION OF PF calculation      ****************
# ************************************************************

        if option['simulatePF']:
            self.var.HeadMax = loadmap('HeadMax')
            self.var.pF0 = defsoil(globals.inZero.copy())
            self.var.pF1 = defsoil(globals.inZero.copy())
            self.var.pF2 = defsoil(globals.inZero.copy())

    def dynamic_perpixel(self):
        """ dynamic part of the soil module
            Calculation per Pixel
        """
        self.var.TaInterceptionAll = self.var.deffraction(self.var.TaInterception) + self.var.DirectRunoffFraction * self.var.TASealed
        self.var.TaInterceptionCUM += self.var.TaInterceptionAll
        # Cumulative evaporation of intercepted water [mm]

        self.var.TaPixel = self.var.deffraction(self.var.Ta)
        # pixel-average transpiration in [mm] per timestep
        # (no transpiration from direct runoff fraction)
        self.var.TaCUM += self.var.TaPixel
        self.var.ESActPixel = self.var.deffraction(self.var.ESAct) + self.var.WaterFraction * self.var.EWaterAct
        # Pixel-average soil evaporation in [mm] per time step
        # (no evaporation from direct runoff fraction)
        self.var.ESActCUM += self.var.ESActPixel


        self.var.PrefFlowPixel = self.var.deffraction(self.var.PrefFlow)
        # Pixel-average preferential flow in [mm] per timestep
        # (no preferential flow from direct runoff fraction)
        self.var.InfiltrationPixel = self.var.deffraction(self.var.Infiltration)
        # Pixel-average infiltration in [mm] per timestep
        # (no infiltration in direct runoff fraction)


        self.var.Theta[0] = self.var.OtherFraction * (self.var.W1a[0] + self.var.W1b[0] + self.var.W2[0]) / (
            self.var.SoilDepth1a[0] + self.var.SoilDepth1b[0] + self.var.SoilDepth2[0])
        self.var.Theta[1] = self.var.ForestFraction * (self.var.W1a[1] + self.var.W1b[1] + self.var.W2[1]) / (
            self.var.SoilDepth1a[1] + self.var.SoilDepth1b[1] + self.var.SoilDepth2[1])
        self.var.Theta[2] = self.var.IrrigationFraction * (self.var.W1a[2] + self.var.W1b[2] + self.var.W2[2]) / (
            self.var.SoilDepth1a[2] + self.var.SoilDepth1b[2] + self.var.SoilDepth2[2])
        self.var.ThetaAll = np.where(self.var.SoilFraction > 0, (self.var.Theta[
            0] + self.var.Theta[1] + self.var.Theta[2]) / self.var.SoilFraction,0.0)

        self.var.SeepTopToSubPixelA = self.var.deffraction(self.var.SeepTopToSubA)
        self.var.SeepTopToSubPixelB = self.var.deffraction(self.var.SeepTopToSubB)
        self.var.SeepSubToGWPixel = self.var.deffraction(self.var.SeepSubToGW)
        # Pixel-average seepage values in [mm] per timestep
        # (no seepage from direct runoff fraction)
