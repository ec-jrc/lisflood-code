# -------------------------------------------------------------------------
# Name:        Soil module
# Purpose:
#
# Author:      burekpe
#
# Created:     29.03.2014
# Copyright:   (c) burekpe 2014
# Licence:     <your licence>
# -------------------------------------------------------------------------

from collections import OrderedDict
from global_modules.add1 import *
import xarray as xr

def pressure2SoilMoistureFun(residual_sm, sat_sm, GenuA, GenuN, GenuM):
    """Generate a function to compute soil moisture values corresponding to characteristic pressure head levels [cm].
       IT WON'T BE NEEDED ANYMORE ONCE DATA STRUCTURES WILL ALSO HAVE A "layer" DIMENSION, TO MERGE LAYER-SPECIFIC VARIABLES (1a, 1b, 2)"""
    def Mualem(pressure):
        return residual_sm + (sat_sm - residual_sm) / ((1 + (GenuA * pressure) ** GenuN) ** GenuM)
    return Mualem


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
        if not option["cropsEPIC"]: # If EPIC is active, the rice fraction initialisation is handled by EPIC (setSoilFractions in EPIC_main.py)
            self.var.SoilFraction.loc["Rainfed_prescribed"] += self.var.RiceFraction
           # for the moment rice is treated as other fraction	        if option['varfractionwater']:
            # if the fraction of water varies then the other fraction are stored
        self.var.WaterFractionBase = self.var.WaterFraction.copy()
        self.var.SoilFractionBase =  self.var.SoilFraction.copy()
        self.var.DirectRunoffFractionBase = self.var.DirectRunoffFraction.copy()
        self.var.PermeableFraction = 1 - self.var.DirectRunoffFraction - self.var.WaterFraction
        # Permeable fraction of pixel

        # Soil Depth 1st layer [mm]
        # soil depth top layer for every landuse but forest, impervious soil
        # and water
        self.var.SoilDepth1a = self.var.defsoil('SoilDepth1','SoilDepth1Forest')
        self.var.SoilDepth1b = self.var.defsoil('SoilDepth2','SoilDepth2Forest')
        self.var.SoilDepth2  = self.var.defsoil('SoilDepth3','SoilDepth3Forest')
        self.var.SoilDepthTotal = self.var.SoilDepth1a + self.var.SoilDepth1b + self.var.SoilDepth2

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
        self.var.CropCoef = self.var.defsoil('MapCropCoef','MapForestCropCoef','MapIrrigationCropCoef')

        # crop coefficients for each land use class

        self.var.CropGroupNumber = self.var.defsoil('MapCropGroupNumber','MapForestCropGroupNumber','MapIrrigationCropGroupNumber')

        # crop group numbers for soil water depletion factor
        # self.var.NManning = [loadmap('MapN'), loadmap('MapForestN'), 0.02]
        self.var.NManning = self.var.defsoil('MapN','MapForestN', 0.02, OrderedDict([self.var.dim_runoff, self.var.dim_pixel]))
        # Manning's roughness coefficient for each land use class
        # third manning is from direct runoff
        # self.var.NManningDirect=scalar(0.02)


# ************************************************************
# ***** MAPS DERIVED FROM SOIL TEXTURE AND SOIL DEPTH ********
# ************************************************************

        # HYPRES Parameters for TopSoil:

        self.var.KSat1a = self.var.defsoil('MapKSat1', 'MapKSat1Forest')
        self.var.KSat1b = self.var.defsoil('MapKSat2', 'MapKSat2Forest')
        self.var.KSat2 = self.var.defsoil('MapKSat3')
        # Saturated conductivity for other land use and forest
        Lambda1a = self.var.defsoil('MapLambda1','MapLambda1Forest')
        Lambda1b = self.var.defsoil('MapLambda2','MapLambda2Forest')
        Lambda2 = self.var.defsoil('MapLambda3')
        # Pore-size index (for Van Genuchten parameters)
        GenuAlpha1a = self.var.defsoil('MapGenuAlpha1','MapGenuAlpha1Forest')
        GenuAlpha1b = self.var.defsoil('MapGenuAlpha2','MapGenuAlpha2Forest')
        GenuAlpha2 = self.var.defsoil('MapGenuAlpha3')
        # Van Genuchten Alpha coefficient
        ThetaS1a = self.var.defsoil('MapThetaSat1','MapThetaSat1Forest')
        ThetaS1b = self.var.defsoil('MapThetaSat2','MapThetaSat2Forest')
        ThetaS2 = self.var.defsoil('MapThetaSat3')
        # Soil moisture content at saturation [V/V]
        ThetaRes1a = self.var.defsoil('MapThetaRes1', 'MapThetaRes1Forest')
        ThetaRes1b = self.var.defsoil('MapThetaRes2', 'MapThetaRes2Forest')
        ThetaRes2 = self.var.defsoil('MapThetaRes3')
        # Soil moisture content at saturation [V/V]

        # GenuN1=Lambda+1
        GenuN1a = 1 + Lambda1a
        GenuN1b = 1 + Lambda1b
        GenuN2 = 1 + Lambda2
        # self.var.GenuM1=Lambda1/GenuN1
        self.var.GenuM1a = Lambda1a / GenuN1a
        self.var.GenuM1b = Lambda1b / GenuN1b
        self.var.GenuM2 = Lambda2 / GenuN2
        # self.var.GenuInvM1=1/self.var.GenuM1
        self.var.GenuInvM1a = 1 / self.var.GenuM1a
        self.var.GenuInvM1b = 1 / self.var.GenuM1b
        self.var.GenuInvM2 = 1 / self.var.GenuM2
        # self.var.GenuInvN1=1/GenuN1
        self.var.GenuInvN1a = 1 / GenuN1a
        self.var.GenuInvN1b = 1 / GenuN1b
        self.var.GenuInvN2 = 1 / GenuN2
        # GenuInvAlpha1=1/GenuAlpha1
        self.var.GenuInvAlpha1a = 1 / GenuAlpha1a
        self.var.GenuInvAlpha1b = 1 / GenuAlpha1b
        self.var.GenuInvAlpha2 = 1 / GenuAlpha2
        # Van Genuchten n and m coefficients
        # In previous versions both n and m were read from separate tables.
        # Since both are calculated from same pore-size index (Lambda=n-1),
        # only table of Lambda is used here (Lambda is also more commonly
        # reported in the literature, which makes any comparison easier)
        # Inverse values computed once here for improved performance
        # (inverse of N and Alpha only needed if option simulatePF is used)
        # Soil moisture [mm] at saturation:
        self.var.WS1a = ThetaS1a * self.var.SoilDepth1a
        self.var.WS1b = ThetaS1b * self.var.SoilDepth1b
        self.var.WS2 = ThetaS2 * self.var.SoilDepth2
        self.var.WS1 = self.var.WS1a + self.var.WS1b
        # Residual soil moisture [mm]:
        self.var.WRes1a = ThetaRes1a * self.var.SoilDepth1a
        self.var.WRes1b = ThetaRes1b * self.var.SoilDepth1b
        self.var.WRes2 = ThetaRes2 * self.var.SoilDepth2
        self.var.WRes1 = self.var.WRes1a + self.var.WRes1b
        # Saturation minus residual soil moisture [mm]:
        self.var.WS1WResa = self.var.WS1a - self.var.WRes1a
        self.var.WS1WResb = self.var.WS1b - self.var.WRes1b
        self.var.WS2WRes = self.var.WS2 - self.var.WRes2
        # Generate Mualem functions (van Genuchten, 1980) for the 3 soil layers:
        MualemEq1a = pressure2SoilMoistureFun(self.var.WRes1a, self.var.WS1a, GenuAlpha1a, GenuN1a, self.var.GenuM1a)
        MualemEq1b = pressure2SoilMoistureFun(self.var.WRes1b, self.var.WS1b, GenuAlpha1b, GenuN1b, self.var.GenuM1b)
        MualemEq2 = pressure2SoilMoistureFun(self.var.WRes2, self.var.WS2, GenuAlpha2, GenuN2, self.var.GenuM2)
        # Soil moisture at field capacity (pF2, 100 cm) [mm water slice]:
        self.var.WFC1a = MualemEq1a(100)
        self.var.WFC1b = MualemEq1b(100)
        self.var.WFC2 = MualemEq2(100)
        self.var.WFC1 = self.var.WFC1a + self.var.WFC1b
        # Soil moisture [mm] at pF3, 1000 cm (pressure):
        self.var.WPF3a = MualemEq1a(1000)
        self.var.WPF3b = MualemEq1b(1000)
        self.var.WPF3 = self.var.WPF3a + self.var.WPF3b
        # Soil moisture at wilting point (pF4.2, 10**4.2 cm) in [mm] water slice:
        self.var.WWP1a = MualemEq1a(15000)
        self.var.WWP1b = MualemEq1b(15000)
        self.var.WWP2 = MualemEq2(15000)
        self.var.WWP1 = self.var.WWP1a + self.var.WWP1b
        # Flag that is Boolean 1 if pixel has (any) soil moisture storage space
        # (needed to avoid divisions by zero in soil moisture calculations):
        self.var.PoreSpaceNotZero1a = np.logical_and(self.var.SoilDepth1a != 0, self.var.WS1a != 0)
        self.var.PoreSpaceNotZero1b = np.logical_and(self.var.SoilDepth1b != 0, self.var.WS1b != 0)
        self.var.PoreSpaceNotZero2 = np.logical_and(self.var.SoilDepth2 != 0, self.var.WS2 != 0)

        # ***** INITIAL VALUES for soil
        ThetaInit1aValue = self.var.initialiseVariableAllVegetation('ThetaInit1aValue')
        ThetaInit1bValue = self.var.initialiseVariableAllVegetation('ThetaInit1bValue')
        ThetaInit2Value = self.var.initialiseVariableAllVegetation('ThetaInit2Value')
        # Allocate soil moisture [mm] data structures (merge them into a single xarray.DataArray by adding a "layer" dimension !!!)
        self.var.W1a = self.var.allocateVariableAllVegetation()
        self.var.W1b = self.var.allocateVariableAllVegetation()
        self.var.W2 = self.var.allocateVariableAllVegetation()
        # Initialise soil moisture in permeable fraction of pixel:
        # Set soil to field capacity if initial value in settings file equals -9999;
        # Set to zero if soil depth is zero.
        # IMPORTANT: WInit1 and WInit2 represent the soil moisture in the *permeable* fraction of the pixel *only*
        # (since all soil moisture-related calculations are done for permeable fraction only!).
        for veg, luse in VEGETATION_LANDUSE.iteritems():
            ini_1a = np.where(ThetaInit1aValue.loc[veg] == -9999, self.var.WFC1a.loc[luse], ThetaInit1aValue.loc[veg] * self.var.SoilDepth1a.loc[luse])
            self.var.W1a.loc[veg] = np.where(self.var.PoreSpaceNotZero1a.loc[luse], ini_1a, 0)
            ini_1b = np.where(ThetaInit1bValue.loc[veg] == -9999, self.var.WFC1b.loc[luse], ThetaInit1bValue.loc[veg] * self.var.SoilDepth1b.loc[luse])
            self.var.W1b.loc[veg] = np.where(self.var.PoreSpaceNotZero1b.loc[luse], ini_1b, 0)
            ini_2 = np.where(ThetaInit2Value.loc[veg] == -9999, self.var.WFC2.loc[luse], ThetaInit2Value.loc[veg] * self.var.SoilDepth2.loc[luse])
            self.var.W2.loc[veg] = np.where(self.var.PoreSpaceNotZero2.loc[luse], ini_2, 0)
        self.var.W1 = self.var.W1a + self.var.W1b

        self.var.Sat1a = self.var.allocateVariableAllVegetation()
        self.var.Sat1b = self.var.allocateVariableAllVegetation()
        self.var.Sat1 = self.var.allocateVariableAllVegetation()
        self.var.Sat2 = self.var.allocateVariableAllVegetation()


# ************************************************************
# ***** REPEATEDLY USED EXPRESSIONS IN XINANJIANG
# ***** INFILTRATION MODEL
# ************************************************************
        self.var.b_Xinanjiang = loadmap('b_Xinanjiang')
        self.var.PowerInfPot = (self.var.b_Xinanjiang + 1) / self.var.b_Xinanjiang
        # Power in infiltration equation
        # self.var.StoreMaxPervious=self.var.WS1/(self.var.b_Xinanjiang+1)
#        self.var.StoreMaxPervious = [x / (self.var.b_Xinanjiang + 1) for x in self.var.WS1a]

        self.var.StoreMaxPervious = self.var.WS1 / (self.var.b_Xinanjiang + 1)
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
        # Days since last rainfall and initial cumulative interception [mm]
        self.var.DSLR = np.maximum(self.var.initialiseVariableAllVegetation('DSLRInitValue'), 1) # DSLR<1 may cause square root of negative number, if Dtsec > 86400!
        self.var.CumInterception = self.var.initialiseVariableAllVegetation('CumIntInitValue')
        # Initialising cumulative output variables  needed to compute the cumulative mass balance error
        self.var.TotalPrecipitation = globals.inZero.copy() # precipitation [mm]
        self.var.TaCUM = globals.inZero.copy() # Cumulative transpiration [mm]
        self.var.TaInterceptionCUM = globals.inZero.copy() # Cumulative evaporation from interception store [mm]
        self.var.ESActCUM = globals.inZero.copy() # Cumulative evaporation [mm]
        self.var.SoilMoistureStressDays = self.var.allocateVariableAllVegetation() # number of days in simulation with soil moisture stress (days)
        self.var.Theta1a = self.var.allocateVariableAllVegetation() # Theta values are just allocated here - their values are dynamically compute in soilloop.py
        self.var.Theta1b = self.var.allocateVariableAllVegetation()
        self.var.Theta2 = self.var.allocateVariableAllVegetation()
        self.var.TaInterception = self.var.allocateVariableAllVegetation()
        self.var.Interception = self.var.allocateVariableAllVegetation()
        self.var.LeafDrainage = self.var.allocateVariableAllVegetation()
        self.var.potential_transpiration = self.var.allocateVariableAllVegetation()
        self.var.Ta = self.var.allocateVariableAllVegetation()
        self.var.ESAct = self.var.allocateVariableAllVegetation()
        self.var.PrefFlow = self.var.allocateVariableAllVegetation()
        self.var.Infiltration = self.var.allocateVariableAllVegetation()
        self.var.SeepTopToSubA = self.var.allocateVariableAllVegetation()
        self.var.SeepTopToSubB = self.var.allocateVariableAllVegetation()
        self.var.SeepSubToGW = self.var.allocateVariableAllVegetation()
        self.var.Theta = self.var.allocateVariableAllVegetation()
        self.var.AvailableWaterForInfiltration = self.var.allocateVariableAllVegetation()
        self.var.RWS = self.var.allocateVariableAllVegetation().loc[self.var.prescribed_vegetation]

# ************************************************************
# ***** INITIALIZATION OF IMPERVIOUS SOIL     ****************
# ************************************************************
        self.var.CumInterSealed = loadmap('CumIntSealedInitValue')
        # cumulative depression storage
        self.var.SMaxSealed = loadmap('SMaxSealed')
        # maximum depression storage for water on impervious surface
        # which is not immediately causing surface runoff  [mm]
        self.var.DrainedFraction = loadmap('DrainedFraction') if option['drainedIrrigation'] else 0
        # drained fraction: water from irrigated water is directly send to channel
        # depending on the drained fraction
# ************************************************************
# ***** INITIALIZATION OF PF calculation      ****************
# ************************************************************
        if option['simulatePF']:
            self.var.HeadMax = loadmap('HeadMax')
            self.var.pF0 = self.var.allocateVariableAllVegetation()
            self.var.pF1 = self.var.allocateVariableAllVegetation()
            self.var.pF2 = self.var.allocateVariableAllVegetation()



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

        tot_sm = self.var.W1a + self.var.W1b + self.var.W2
        for landuse, veg_list in LANDUSE_VEGETATION.iteritems():
            self.var.Theta.loc[veg_list] = self.var.SoilFraction.loc[veg_list] * tot_sm.loc[veg_list] / self.var.SoilDepthTotal.loc[landuse]
        soil_fract_sum = self.var.SoilFraction.sum("vegetation")
        self.var.ThetaAll = np.where(soil_fract_sum > 0, self.var.Theta.sum("vegetation") / soil_fract_sum, 0)

        self.var.SeepTopToSubPixelA = self.var.deffraction(self.var.SeepTopToSubA)
        self.var.SeepTopToSubPixelB = self.var.deffraction(self.var.SeepTopToSubB)
        self.var.SeepSubToGWPixel = self.var.deffraction(self.var.SeepSubToGW)
        # Pixel-average seepage values in [mm] per timestep
        # (no seepage from direct runoff fraction)
