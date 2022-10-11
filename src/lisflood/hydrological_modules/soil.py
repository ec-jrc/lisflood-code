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

import numpy as np

from ..global_modules.settings import MaskInfo, LisSettings
from ..global_modules.add1 import loadmap, defsoil
from . import HydroModule
from collections import OrderedDict
#from global_modules.add1 import *
import xarray as xr


def pressure2SoilMoistureFun(residual_sm, sat_sm, GenuA, GenuN, GenuM):
    """Generate a function to compute soil moisture values corresponding to characteristic pressure head levels [cm].
       IT WON'T BE NEEDED ANYMORE ONCE DATA STRUCTURES WILL ALSO HAVE A "layer" DIMENSION, TO MERGE LAYER-SPECIFIC VARIABLES (1a, 1b, 2)"""
    def Mualem(pressure):
        return residual_sm + (sat_sm - residual_sm) / ((1 + (GenuA * pressure) ** GenuN) ** GenuM)
    return Mualem


class soil(HydroModule):

    """
    # ************************************************************
    # ***** SOIL         *****************************************
    # ************************************************************
    """
    input_files_keys = {'all': ['SoilDepth1', 'SoilDepth1Forest', 'SoilDepth2', 'SoilDepth2Forest',
                                'SoilDepth3', 'SoilDepth3Forest', 'CourantCrit', 'LeafDrainageTimeConstant',
                                'AvWaterRateThreshold', 'MapCropCoef', 'MapForestCropCoef', 'MapIrrigationCropCoef',
                                'MapCropGroupNumber', 'MapForestCropGroupNumber', 'MapIrrigationCropGroupNumber',
                                'MapN', 'MapForestN', 'MapKSat1', 'MapKSat1Forest', 'MapKSat2', 'MapKSat2Forest', 'MapKSat3',
                                'MapLambda1', 'MapLambda1Forest', 'MapLambda2', 'MapLambda2Forest', 'MapLambda3',
                                'MapGenuAlpha1', 'MapGenuAlpha1Forest', 'MapGenuAlpha2', 'MapGenuAlpha2Forest', 'MapGenuAlpha3',
                                'MapThetaSat1', 'MapThetaSat1Forest', 'MapThetaSat2', 'MapThetaSat2Forest', 'MapThetaSat3',
                                'MapThetaRes1', 'MapThetaRes1Forest', 'MapThetaRes2', 'MapThetaRes2Forest', 'MapThetaRes3',
                                'ThetaInit1Value', 'ThetaForestInit1Value', 'ThetaIrrigationInit1Value',
                                'ThetaInit2Value', 'ThetaForestInit2Value', 'ThetaIrrigationInit2Value',
                                'ThetaInit3Value', 'ThetaForestInit3Value', 'ThetaIrrigationInit3Value',
                                'b_Xinanjiang', 'PowerPrefFlow',
                                'DSLRInitValue', 'DSLRForestInitValue', 'DSLRIrrigationInitValue',
                                'CumIntInitValue', 'CumIntForestInitValue', 'CumIntIrrigationInitValue',
                                'CumIntSealedInitValue', 'SMaxSealed'],
                        'drainedIrrigation': ['DrainedFraction'],
                        'simulatePF': ['HeadMax']}
    module_name = 'Soil'

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
        settings = LisSettings.instance()
        option = settings.options
        binding = settings.binding
        maskinfo = MaskInfo.instance()
        if not option["cropsEPIC"]: # If EPIC is active, the rice fraction initialisation is handled by EPIC (setSoilFractions in EPIC_main.py)
            self.var.SoilFraction.values[self.var.vegetation.index('Rainfed_prescribed')] += self.var.RiceFraction

        # for the moment rice is treated as other fraction
        # if the fraction of water varies then the other fraction are stored
        self.var.WaterFractionBase = self.var.WaterFraction.copy()
        self.var.OtherFractionBase = self.var.OtherFraction.copy()
        self.var.IrrigationFractionBase = self.var.IrrigationFraction.copy()
        self.var.ForestFractionBase = self.var.ForestFraction.copy()
        self.var.DirectRunoffFractionBase = self.var.DirectRunoffFraction.copy()
        self.var.PermeableFraction = 1 - self.var.DirectRunoffFraction - self.var.WaterFraction
        # Permeable fraction of pixel

        # Soil Depth 1st layer [mm]
        # soil depth top layer for every landuse but forest, impervious soil
        # and water

        self.var.SoilDepth1a = self.var.defsoil('SoilDepth1', 'SoilDepth1Forest')
        self.var.SoilDepth1b = self.var.defsoil('SoilDepth2', 'SoilDepth2Forest')
        self.var.SoilDepth2 = self.var.defsoil('SoilDepth3', 'SoilDepth3Forest')
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
        self.var.CropCoef = self.var.defsoil('MapCropCoef', 'MapForestCropCoef', 'MapIrrigationCropCoef')

        # crop coefficients for each land use class
        self.var.CropGroupNumber = self.var.defsoil('MapCropGroupNumber', 'MapForestCropGroupNumber', 'MapIrrigationCropGroupNumber')

        # crop group numbers for soil water depletion factor        
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
        Lambda1a = self.var.defsoil('MapLambda1', 'MapLambda1Forest')
        Lambda1b = self.var.defsoil('MapLambda2', 'MapLambda2Forest')
        Lambda2 = self.var.defsoil('MapLambda3')
        # Pore-size index (for Van Genuchten parameters)
        GenuAlpha1a = self.var.defsoil('MapGenuAlpha1', 'MapGenuAlpha1Forest')
        GenuAlpha1b = self.var.defsoil('MapGenuAlpha2', 'MapGenuAlpha2Forest')
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
       
        self.var.PoreSpaceNotZero1a = np.logical_and(self.var.SoilDepth1a != 0, self.var.WS1a != 0)
        self.var.PoreSpaceNotZero1b = np.logical_and(self.var.SoilDepth1b != 0, self.var.WS1b != 0)
        self.var.PoreSpaceNotZero2 = np.logical_and(self.var.SoilDepth2 != 0, self.var.WS2 != 0)

        # ***** INITIAL VALUES for soil
        
        if not option["cropsEPIC"]: 
       
           ThetaInit1aValue = self.var.allocateVariableAllVegetation()
           ThetaInit1bValue = self.var.allocateVariableAllVegetation()
           ThetaInit2Value = self.var.allocateVariableAllVegetation()

           iveg = self.var.vegetation.index('Rainfed_prescribed')           
           ThetaInit1aValue.values[iveg] = loadmap('ThetaInit1Value')
           ThetaInit1bValue.values[iveg] = loadmap('ThetaInit2Value')
           ThetaInit2Value.values[iveg] = loadmap('ThetaInit3Value')
           
           iveg = self.var.vegetation.index('Forest_prescribed')
           ThetaInit1aValue.values[iveg] = loadmap('ThetaForestInit1Value')
           ThetaInit1bValue.values[iveg] = loadmap('ThetaForestInit2Value')
           ThetaInit2Value.values[iveg] = loadmap('ThetaForestInit3Value')
           
           iveg = self.var.vegetation.index('Irrigated_prescribed')
           ThetaInit1aValue.values[iveg] = loadmap('ThetaIrrigationInit1Value')
           ThetaInit1bValue.values[iveg] = loadmap('ThetaIrrigationInit2Value')
           ThetaInit2Value.values[iveg] = loadmap('ThetaIrrigationInit3Value')
        else:
            ThetaInit1aValue = self.var.initialiseVariableAllVegetation('ThetaInit1Value')
            ThetaInit1bValue = self.var.initialiseVariableAllVegetation('ThetaInit2Value')
            ThetaInit2Value = self.var.initialiseVariableAllVegetation('ThetaInit3Value')
        
  
        # Allocate soil moisture [mm] data structures (merge them into a single xarray.DataArray by adding a "layer" dimension !!!)
        self.var.W1a = self.var.allocateVariableAllVegetation()
        self.var.W1b = self.var.allocateVariableAllVegetation()
        self.var.W2 = self.var.allocateVariableAllVegetation()
        # Initialise soil moisture in permeable fraction of pixel:
        # Set soil to field capacity if initial value in settings file equals -9999;
        # Set to zero if soil depth is zero.
        # IMPORTANT: WInit1 and WInit2 represent the soil moisture in the *permeable* fraction of the pixel *only*
        # (since all soil moisture-related calculations are done for permeable fraction only!).

        for veg, luse in self.var.VEGETATION_LANDUSE.items():
            iveg = self.var.vegetation.index(veg)
            iluse = self.var.SOIL_USES.index(luse)
            ini_1a = np.where(ThetaInit1aValue[iveg] == -9999, self.var.WFC1a[iluse], ThetaInit1aValue[iveg] * self.var.SoilDepth1a[iluse])
            self.var.W1a[iveg] = np.where(self.var.PoreSpaceNotZero1a[iluse], ini_1a, 0)
            ini_1b = np.where(ThetaInit1bValue[iveg] == -9999, self.var.WFC1b[iluse], ThetaInit1bValue[iveg] * self.var.SoilDepth1b[iluse])
            self.var.W1b[iveg] = np.where(self.var.PoreSpaceNotZero1b[iluse], ini_1b, 0)
            ini_2 = np.where(ThetaInit2Value[iveg] == -9999, self.var.WFC2[iluse], ThetaInit2Value[iveg] * self.var.SoilDepth2[iluse])
            self.var.W2[iveg] = np.where(self.var.PoreSpaceNotZero2[iluse], ini_2, 0)
        self.var.W1 = self.var.W1a + self.var.W1b
                    

        self.var.Sat1a = self.var.allocateVariableAllVegetation()
        self.var.Sat1b = self.var.allocateVariableAllVegetation()
        self.var.Sat1 = self.var.allocateVariableAllVegetation()
        self.var.Sat2 = self.var.allocateVariableAllVegetation()
        '''
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

        ThetaInit1aValue = defsoil('ThetaInit1Value', 'ThetaForestInit1Value', 'ThetaIrrigationInit1Value')
        ThetaInit1bValue = defsoil('ThetaInit2Value', 'ThetaForestInit2Value', 'ThetaIrrigationInit2Value')
        ThetaInit2Value = defsoil('ThetaInit3Value', 'ThetaForestInit3Value', 'ThetaIrrigationInit3Value')

        WInit1a = splitlanduse(maskinfo.in_zero())
        WInit1b = splitlanduse(maskinfo.in_zero())
        WInit2 = splitlanduse(maskinfo.in_zero())
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

        WInit1a[0] = np.where(self.var.PoreSpaceNotZero1a[0], WInit1a[0], maskinfo.in_zero())
        WInit1a[1] = np.where(self.var.PoreSpaceNotZero1a[1], WInit1a[1], maskinfo.in_zero())
        WInit1a[2] = np.where(self.var.PoreSpaceNotZero1a[2], WInit1a[2], maskinfo.in_zero())
        WInit1b[0] = np.where(self.var.PoreSpaceNotZero1b[0], WInit1b[0], maskinfo.in_zero())
        WInit1b[1] = np.where(self.var.PoreSpaceNotZero1b[1], WInit1b[1], maskinfo.in_zero())
        WInit1b[2] = np.where(self.var.PoreSpaceNotZero1b[2], WInit1b[2], maskinfo.in_zero())
        WInit2[0] = np.where(self.var.PoreSpaceNotZero2[0], WInit2[0], maskinfo.in_zero())
        WInit2[1] = np.where(self.var.PoreSpaceNotZero2[1], WInit2[1], maskinfo.in_zero())
        WInit2[2] = np.where(self.var.PoreSpaceNotZero2[2], WInit2[2], maskinfo.in_zero())
        # Set to zero if soil depth is zero
        self.var.W1a = WInit1a
        self.var.W1b = WInit1b
        self.var.W1 = np.add(self.var.W1a, self.var.W1b)
        self.var.W2 = WInit2
        # Set soil moisture to initial value

        self.var.Sat1a = splitlanduse(maskinfo.in_zero())
        self.var.Sat1b = splitlanduse(maskinfo.in_zero())
        self.var.Sat1 = splitlanduse(maskinfo.in_zero())
        self.var.Sat2 = splitlanduse(maskinfo.in_zero())
        '''

        # ************************************************************
        # ***** REPEATEDLY USED EXPRESSIONS IN XINANJIANG
        # ***** INFILTRATION MODEL
        # ************************************************************
        self.var.b_Xinanjiang = loadmap('b_Xinanjiang')
    
        if isinstance(self.var.b_Xinanjiang, float):
           MAP = []
           MAP = maskinfo.in_zero() +   self.var.b_Xinanjiang
           self.var.b_Xinanjiang = []
           self.var.b_Xinanjiang = MAP
               
        self.var.PowerInfPot = (self.var.b_Xinanjiang + 1) / self.var.b_Xinanjiang
        # Power in infiltration equation
        self.var.StoreMaxPervious = self.var.WS1 / (self.var.b_Xinanjiang + 1)
        # Maximum soil moisture storage in pervious fraction of
        # pixel (expressed as [mm] water slice)

        # ********************************************
        # ****  PowerPrefFlow
        # ********************************************
        self.var.PowerPrefFlow = loadmap('PowerPrefFlow')
                
        if isinstance(self.var.PowerPrefFlow, float):
           MAP = []
           MAP = maskinfo.in_zero() +   self.var.PowerPrefFlow
           self.var.PowerPrefFlow = []
           self.var.PowerPrefFlow = MAP

           
        # ************************************************************
        # ***** INITIAL VALUES
        # ************************************************************
        # Inputs in waterbalance model and/or initial assumption
        # CMmod
        # DSLRInit = defsoil('DSLRInitValue', 'DSLRForestInitValue','DSLRIrrigationInitValue')
        
        
        if not option["cropsEPIC"]: 
           self.var.DSLR = self.var.allocateVariableAllVegetation()
           ivegRainfedPrescribed = self.var.vegetation.index('Rainfed_prescribed')
           ivegForestPrescribed = self.var.vegetation.index('Forest_prescribed')
           ivegIrrigatedPrescribed = self.var.vegetation.index('Irrigated_prescribed')

           self.var.DSLR[ivegRainfedPrescribed] = loadmap('DSLRInitValue')
           self.var.DSLR[ivegForestPrescribed]  = loadmap('DSLRForestInitValue')
           self.var.DSLR[ivegIrrigatedPrescribed]  = loadmap('DSLRIrrigationInitValue')
           self.var.DSLR[ivegRainfedPrescribed]  = np.where(self.var.DSLR[ivegRainfedPrescribed]<1,1,self.var.DSLR[ivegRainfedPrescribed])
           self.var.DSLR[ivegForestPrescribed]  = np.where(self.var.DSLR[ivegForestPrescribed]<1,1,self.var.DSLR[ivegForestPrescribed])
           self.var.DSLR[ivegIrrigatedPrescribed]  = np.where(self.var.DSLR[ivegIrrigatedPrescribed]<1,1,self.var.DSLR[ivegIrrigatedPrescribed])
        else:
           self.var.DSLR = np.maximum(self.var.initialiseVariableAllVegetation('DSLRInitValue'), 1) # DSLR<1 may cause square root of negative number, if Dtsec > 86400!
        
        if not option["cropsEPIC"]:  
           self.var.CumInterception = self.var.allocateVariableAllVegetation()
           self.var.CumInterception[ivegRainfedPrescribed] = loadmap('CumIntInitValue')
           self.var.CumInterception[ivegForestPrescribed] = loadmap('CumIntForestInitValue')
           self.var.CumInterception[ivegIrrigatedPrescribed] = loadmap('CumIntIrrigationInitValue')
        else:
           self.var.CumInterception = self.var.initialiseVariableAllVegetation('CumIntInitValue')
        
        # Initialising cumulative output variables  needed to compute the cumulative mass balance error
        self.var.TotalPrecipitation =  maskinfo.in_zero() # precipitation [mm]
        self.var.TaCUM =  maskinfo.in_zero() # Cumulative transpiration [mm]
        self.var.TaWB = maskinfo.in_zero() # Cumulative transpiration [mm] at the end of the computational time step (waterbalance.py)
        self.var.TaInterceptionCUM =  maskinfo.in_zero() # Cumulative evaporation from interception store [mm]
        self.var.TaInterceptionWB =  maskinfo.in_zero() # Evaporation from interception store [mm] at the end of the computational time step (waterbalance.py)
        self.var.ESActCUM =  maskinfo.in_zero() # Cumulative evaporation [mm]
        self.var.ESActWB = maskinfo.in_zero() # Cumulative evaporation [mm] at the end of the computational time step (waterbalance.py)
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
        ivegvalues = []
        for veg in self.var.prescribed_vegetation:
            ivegvalues.append(self.var.vegetation.index(veg))
        self.var.RWS = self.var.allocateVariableAllVegetation()[ivegvalues]


        # ************************************************************
        # ***** INITIALIZATION OF IMPERVIOUS SOIL     ****************
        # ************************************************************

        self.var.CumInterSealed = loadmap('CumIntSealedInitValue')
        
        # cumulative depression storage
        self.var.SMaxSealed = loadmap('SMaxSealed')
        # maximum depression storage for water on impervious surface
        # which is not immediately causing surface runoff  [mm]

        settings = LisSettings.instance()
        option = settings.options

        if option['drainedIrrigation']:
            self.var.DrainedFraction = loadmap('DrainedFraction')
        else: 
            self.var.DrainedFraction = 0.0 ##### STEF: the master simply do not assign this!
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
        self.var.TaInterceptionWB = self.var.TaInterceptionAll
        # Cumulative evaporation of intercepted water [mm]

        self.var.TaPixel = self.var.deffraction(self.var.Ta)
        # pixel-average transpiration in [mm] per timestep
        # (no transpiration from direct runoff fraction)
        self.var.TaCUM += self.var.TaPixel
        self.var.TaWB = self.var.TaPixel
        self.var.ESActPixel = self.var.deffraction(self.var.ESAct) + self.var.WaterFraction * self.var.EWaterAct
        # Pixel-average soil evaporation in [mm] per time step
        # (no evaporation from direct runoff fraction)
        self.var.ESActCUM += self.var.ESActPixel
        self.var.ESActWB = self.var.ESActPixel

        self.var.PrefFlowPixel = self.var.deffraction(self.var.PrefFlow)
        # Pixel-average preferential flow in [mm] per timestep
        # (no preferential flow from direct runoff fraction)
        self.var.InfiltrationPixel = self.var.deffraction(self.var.Infiltration)
        # Pixel-average infiltration in [mm] per timestep
        # (no infiltration in direct runoff fraction)
        tot_sm = self.var.W1a + self.var.W1b + self.var.W2
        for landuse, veg_list in self.var.LANDUSE_VEGETATION.items():
            iveg_list,iveg_list_pres,ilanduse = self.var.get_indexes_from_landuse_and_veg_list_GLOBAL(landuse, veg_list)
            self.var.Theta[iveg_list] = self.var.SoilFraction[iveg_list_pres] * tot_sm[iveg_list] / self.var.SoilDepthTotal[ilanduse]
        ax_veg=self.var.SoilFraction.dims.index("vegetation")
        soil_fract_sum = np.sum(self.var.SoilFraction,ax_veg)
        self.var.ThetaAll = np.where(soil_fract_sum > 0, np.sum(self.var.Theta,ax_veg) / soil_fract_sum, 0)

        self.var.SeepTopToSubPixelA = self.var.deffraction(self.var.SeepTopToSubA)
        self.var.SeepTopToSubPixelB = self.var.deffraction(self.var.SeepTopToSubB)
        self.var.SeepSubToGWPixel = self.var.deffraction(self.var.SeepSubToGW)
        # Pixel-average seepage values in [mm] per timestep
        # (no seepage from direct runoff fraction)
        
        # the variables below were added to report catchment-averaged soil moisture profiles
        self.var.Theta1aPixel = self.var.deffraction(self.var.Theta1a)
        self.var.Theta1bPixel = self.var.deffraction(self.var.Theta1b)
        self.var.Theta2Pixel = self.var.deffraction(self.var.Theta2)
