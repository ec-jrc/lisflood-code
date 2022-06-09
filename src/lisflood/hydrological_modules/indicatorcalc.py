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

import datetime

from pcraster import areatotal, cover, ifthen, upstream
import numpy as np

from ..global_modules.add1 import loadmap, readnetcdf, decompress, compressArray
from ..global_modules.settings import LisSettings, MaskInfo
from . import HydroModule


class indicatorcalc(HydroModule):

    """
    # ************************************************************
    # ***** Indicator calculation ************************************
    # ************************************************************
    """
    input_files_keys = {'indicator': ['Population', 'LandUseMask'],
                        'TransientLandUseChange': ['PopulationMaps']}
    module_name = 'IndicatorCalculation'

    def __init__(self, indicatorcalc_variable):
        self.var = indicatorcalc_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the indicator calculation module
        """

        self.var.monthend = False
        self.var.yearend = False
        settings = LisSettings.instance()
        binding = settings.binding
        option = settings.options
        maskinfo = MaskInfo.instance()
        try:
            self.var.DefineEndofYear = int(binding['DefineEndofYear'])
        except (ValueError, KeyError):
            self.var.DefineEndofYear = 365

        if option['indicator'] and option['wateruse']:
            self.var.Population = loadmap('Population') # population per pixel
            self.var.LandUseMask = loadmap('LandUseMask')
            self.var.RegionPopulation = np.take(np.bincount(self.var.WUseRegionC, weights=self.var.Population), self.var.WUseRegionC)
            self.dynamic_setzero()
            
            self.var.DayCounter = 0           
            self.var.MonthETpotMM = maskinfo.in_zero() 
            self.var.MonthETactMM = maskinfo.in_zero() 
           
            

    def dynamic(self):
        """ dynamic part of the indicator calculation module
        """
        settings = LisSettings.instance()
        binding = settings.binding
        option = settings.options
        maskinfo = MaskInfo.instance()
        if option['TransientLandUseChange']:
            self.var.Population = readnetcdf(binding['PopulationMaps'], self.var.currentTimeStep())
            self.var.RegionPopulation = np.take(np.bincount(self.var.WUseRegionC, weights=self.var.Population), self.var.WUseRegionC)
            # population sum in Regions

        if option['wateruse'] and option['indicator']:
            # check if it is the last monthly or annual time step
            next_date_time = self.var.CalendarDate + datetime.timedelta(seconds=int(binding["DtSec"]))
            self.var.monthend = next_date_time.month != self.var.CalendarDate.month
            self.var.yearend = next_date_time.year != self.var.CalendarDate.year
            # sum up every day
            self.var.DayCounter += 1
            
            self.var.MonthETpotMM = self.var.MonthETpotMM + self.var.ETRef 
            self.var.MonthETactMM = self.var.MonthETactMM + self.var.deffraction(self.var.TaInterception) + self.var.TaPixel + self.var.ESActPixel 

            if option['openwaterevapo']: 
                self.var.MonthETactMM += self.var.EvaAddM3 * self.var.M3toMM 

            self.var.MonthETdifMM = np.maximum((self.var.MonthETpotMM - self.var.MonthETactMM)*self.var.LandUseMask, maskinfo.in_zero())  
            # ; land use mask can be used to mask out deserts and high mountains, where no agriculture is possible            

            self.var.MonthAbstractionRequiredAllSourcesM3 += self.var.abstraction_allSources_required_M3
            self.var.MonthAbstractionRequiredSurfaceGroundWaterM3 += self.var.abstraction_SwGw_required_M3
            self.var.MonthAbstractionRequiredSurfaceWaterM3 += self.var.abstraction_SW_required_M3
            self.var.MonthConsumptionRequiredM3 += self.var.consumption_SwGw_required_M3
            self.var.MonthConsumptionActualM3 += self.var.consumption_SwGw_actual_M3
            self.var.MonthDisM3     =	self.var.MonthDisM3 + self.var.ChanQAvg * self.var.DtSec

            self.var.MonthWaterAbstractedfromLakesReservoirsM3 = self.var.MonthWaterAbstractedfromLakesReservoirsM3 + self.var.ReservoirAbstractionM3 + self.var.LakeAbstractionM3
            self.var.RegionMonthIrrigationShortageM3 = self.var.RegionMonthIrrigationShortageM3 + self.var.areatotal_shortage_SW_M3
            self.var.MonthInternalFlowM3 = self.var.MonthInternalFlowM3 + self.var.ToChanM3Runoff
            
            if self.var.monthend:

                # INTERNAL FLOW
                # available LakeStorageM3 and ReservoirStorageM3 for potential abstraction at end of month in region  
                if option['simulateLakes'] and option['simulateReservoirs']:            
                   self.var.RegionMonthReservoirAndLakeStorageM3 = np.take(np.bincount(self.var.WUseRegionC,weights=self.var.ReservoirStorageM3+self.var.LakeStorageM3),self.var.WUseRegionC)
                   # monthly abstraction from lakes and reservoirs
                   self.var.RegionMonthWaterAbstractedfromLakesReservoirsM3 = np.take(np.bincount(self.var.WUseRegionC,weights=self.var.MonthWaterAbstractedfromLakesReservoirsM3),self.var.WUseRegionC)
                
                self.var.RegionMonthInternalFlowM3 = np.take(np.bincount(self.var.WUseRegionC,weights=self.var.MonthInternalFlowM3),self.var.WUseRegionC)
                   # note Reservoir and Lake storage need to be taken into account seperately

                # EXTERNAL FLOW
                wreg = decompress(self.var.WUseRegionC)
                     # to pcraster map because of the following expression!
                self.var.RegionMonthExternalInflowM3 = compressArray(areatotal(cover(ifthen(self.var.WaterRegionInflowPoints != 0, upstream(self.var.LddStructuresKinematic,decompress(self.var.MonthDisM3))),0),wreg))
                self.var.RegionMonthAbstractionRequiredAllSourcesM3 =  np.take(np.bincount(self.var.WUseRegionC,weights=self.var.MonthAbstractionRequiredAllSourcesM3),self.var.WUseRegionC)
                self.var.RegionMonthAbstractionRequiredSurfaceGroundWaterM3 = np.take(np.bincount(self.var.WUseRegionC,weights=self.var.MonthAbstractionRequiredSurfaceGroundWaterM3),self.var.WUseRegionC)
                self.var.RegionMonthAbstractionRequiredSurfaceWaterM3 = np.take(np.bincount(self.var.WUseRegionC,weights=self.var.MonthAbstractionRequiredSurfaceWaterM3),self.var.WUseRegionC)
                self.var.RegionMonthConsumptionRequiredM3 = np.take(np.bincount(self.var.WUseRegionC,weights=self.var.MonthConsumptionRequiredM3),self.var.WUseRegionC)
                self.var.RegionMonthConsumptionActualM3 = np.take(np.bincount(self.var.WUseRegionC,weights=self.var.MonthConsumptionActualM3),self.var.WUseRegionC)


                # Calculation of WEI: everything in m3, totalled over the water region

                self.var.UpstreamInflowM3 = self.var.RegionMonthExternalInflowM3
                self.var.LocalFreshwaterM3 = self.var.RegionMonthInternalFlowM3
                # still to be decided if reservoir and lake water availability is added here
                self.var.LocalTotalWaterDemandM3 = self.var.RegionMonthAbstractionRequiredAllSourcesM3
                RemainingDemandM3 = np.maximum(self.var.LocalTotalWaterDemandM3 - self.var.LocalFreshwaterM3,0.0)
                # this is the demand that cannot be met by local water supply
                self.var.UpstreamInflowUsedM3 = np.minimum(RemainingDemandM3,self.var.UpstreamInflowM3)
                # the amount of upstream water an area really depends on
                self.var.FossilGroundwaterUsedM3 = np.maximum(RemainingDemandM3 - self.var.UpstreamInflowUsedM3,0.0)
                # the amount of water that cannot be met locally nor with international water
                # likely this is the amount of water drawn from deep groundwater
                freshwater_total = self.var.UpstreamInflowM3 + self.var.LocalFreshwaterM3
                is_freshwater_available = freshwater_total > 0
                self.var.WEI_Dem = np.where(is_freshwater_available, self.var.RegionMonthAbstractionRequiredAllSourcesM3 / freshwater_total, 0.)
                self.var.WEI_Abs = np.where(is_freshwater_available, self.var.RegionMonthAbstractionRequiredSurfaceGroundWaterM3 / freshwater_total, 0.)
                self.var.WEI_Cns = np.where(is_freshwater_available, self.var.RegionMonthConsumptionRequiredM3 / freshwater_total, 0.)
                self.var.WEI_Plus = np.where(is_freshwater_available, self.var.RegionMonthConsumptionActualM3 / freshwater_total, 0.)
                ## TEST
                #print('WEI_D: {}, WEI_+: {}'.format(self.var.WEI_Dem.mean(), self.var.WEI_Plus.mean()))

                self.var.WaterSustainabilityIndex =  np.where(self.var.LocalTotalWaterDemandM3 > 0,
                                                              self.var.FossilGroundwaterUsedM3 / (self.var.LocalTotalWaterDemandM3+1),0.0)
                # De Roo 2015: WTI, if above zero, indicates that situation is unsustainable
                # if index is 0 means sustainable situtation: no groundwater or desalination water used
                # if index is 1 means area relies completely on groundwater or desalination water
                # the '+1' is to prevent division by small values, leading to very large and misleading indicator values

                self.var.WaterDependencyIndex =  np.where(self.var.LocalTotalWaterDemandM3 > 0, self.var.UpstreamInflowUsedM3 / (self.var.LocalTotalWaterDemandM3+1),0)
                # De Roo 2015: WDI, dependency on upstreamwater, as a fraction of the total local demand
                # the '+1' is to prevent division by small values, leading to very large and misleading indicator values

                self.var.WaterSecurityIndex = np.where(self.var.UpstreamInflowM3 > 0,  self.var.UpstreamInflowUsedM3 / (self.var.UpstreamInflowM3+1),0)
                # De Roo 2015: WSI, indicates the vulnerability to the available upstream water;
                # if only 10% of upstream inflow is use, WSI would be 0.1 indicating low vulnerability
                # if WSI is close to 1, situation is very vulnerable
                # the '+1' is to prevent division by small values, leading to very large and misleading indicator values

                self.var.FalkenmarkM3Capita1 =  np.where(self.var.RegionPopulation > 0.0,self.var.RegionMonthInternalFlowM3*12/self.var.RegionPopulation,0)
                self.var.FalkenmarkM3Capita2 =  np.where(self.var.RegionPopulation > 0.0,self.var.LocalFreshwaterM3*12/self.var.RegionPopulation,0)
                self.var.FalkenmarkM3Capita3 =  np.where(self.var.RegionPopulation > 0.0,freshwater_total*12/self.var.RegionPopulation,0)
                if option['repWaterUse']:
                    # Required consumptions (from surface water and groundwater) by sector, including actual figure for irrigation (month, region)
                    self.var.consumption_required_domestic_M3MonthRegion = np.take(np.bincount(self.var.WUseRegionC,weights=self.var.consumption_required_domestic_MM_month),self.var.WUseRegionC)
                    self.var.consumption_required_energy_M3MonthRegion =  np.take(np.bincount(self.var.WUseRegionC,weights=self.var.consumption_required_energy_MM_month * self.var.MMtoM3),self.var.WUseRegionC)
                    self.var.consumption_required_industry_M3MonthRegion = np.take(np.bincount(self.var.WUseRegionC,weights=self.var.consumption_required_industry_MM_month * self.var.MMtoM3),self.var.WUseRegionC)
                    self.var.consumption_required_livestock_M3MonthRegion = np.take(np.bincount(self.var.WUseRegionC,weights=self.var.consumption_required_livestock_MM_month *self.var.MMtoM3),self.var.WUseRegionC)
                    self.var.consumption_required_irrigation_M3MonthRegion = np.take(np.bincount(self.var.WUseRegionC,weights=self.var.consumption_required_irrigation_MM_month * self.var.MMtoM3),self.var.WUseRegionC)
                    self.var.consumption_actual_irrigation_M3MonthRegion = np.take(np.bincount(self.var.WUseRegionC,weights=self.var.consumption_actual_irrigation_MM_month *self.var.MMtoM3),self.var.WUseRegionC)
                    # Irrigation abstraction (month, self.var.WUseRegionC), region)
                    self.var.abstraction_allSources_required_irrigation_M3MonthRegion =np.take(np.bincount(self.var.WUseRegionC,weights=self.var.abstraction_allSources_required_irrigation_M3Month),self.var.WUseRegionC)
                    self.var.abstraction_allSources_actual_irrigation_M3MonthRegion =np.take(np.bincount(self.var.WUseRegionC,weights=self.var.abstraction_allSources_actual_irrigation_M3Month),self.var.WUseRegionC)
                    self.var.abstraction_SwGw_required_irrigation_M3MonthRegion =np.take(np.bincount(self.var.WUseRegionC,weights=self.var.abstraction_SwGw_required_irrigation_M3Month),self.var.WUseRegionC)
                    self.var.abstraction_SwGw_actual_irrigation_M3MonthRegion =np.take(np.bincount(self.var.WUseRegionC,weights=self.var.abstraction_SwGw_actual_irrigation_M3Month),self.var.WUseRegionC)

         
# --------------------------------------------------------------------------
    def dynamic_setzero(self):
        """ dynamic part of the indicator calculation module
            which set the monthly (yearly) values back to start
        """
        settings = LisSettings.instance()
        option = settings.options
        maskinfo = MaskInfo.instance()  

        self.var.DayCounter = 0
        self.var.MonthETpotMM = maskinfo.in_zero() 
        self.var.MonthETactMM = maskinfo.in_zero()  
        self.var.MonthAbstractionRequiredAllSourcesM3 =  maskinfo.in_zero()
        self.var.MonthAbstractionRequiredSurfaceGroundWaterM3 =  maskinfo.in_zero()
        self.var.MonthAbstractionRequiredSurfaceWaterM3 =  maskinfo.in_zero()
        self.var.MonthConsumptionActualM3 =  maskinfo.in_zero()
        self.var.MonthConsumptionRequiredM3 =  maskinfo.in_zero()
        self.var.MonthDisM3 =  maskinfo.in_zero()
        self.var.MonthInternalFlowM3 =  maskinfo.in_zero()
        self.var.MonthExternalInflowM3 = maskinfo.in_zero()
        self.var.RegionMonthIrrigationShortageM3 = maskinfo.in_zero()
        self.var.MonthWaterAbstractedfromLakesReservoirsM3 =  maskinfo.in_zero()

        # Required consumptions (from surface water and groundwater) by sector, including actual figure for irrigation (month, region)
        ##self.var.consumption_required_domestic_MM_month = np.zeros(self.var.num_pixel)
        self.var.consumption_required_domestic_MM_month =  np.zeros(self.var.num_pixel) 
        self.var.consumption_required_energy_MM_month = np.zeros(self.var.num_pixel)
        self.var.consumption_required_industry_MM_month = np.zeros(self.var.num_pixel)
        self.var.consumption_required_livestock_MM_month = np.zeros(self.var.num_pixel)
        self.var.consumption_required_irrigation_MM_month = np.zeros(self.var.num_pixel)
        self.var.consumption_actual_irrigation_MM_month = np.zeros(self.var.num_pixel)
        # Irrigation abstraction (month, region)
        self.var.abstraction_allSources_required_irrigation_M3Month = np.zeros(self.var.num_pixel)
        self.var.abstraction_allSources_actual_irrigation_M3Month = np.zeros(self.var.num_pixel)
        self.var.abstraction_SwGw_required_irrigation_M3Month = np.zeros(self.var.num_pixel)
        self.var.abstraction_SwGw_actual_irrigation_M3Month = np.zeros(self.var.num_pixel)                                 

        
            
