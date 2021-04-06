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

        if option['indicator']:
            # population per pixel
            self.var.Population = loadmap('Population')
            # map to mask out deserts and high mountains (to cover ETdif map, otherwise Sahara etc would pop out; meant as a drought indicator
            self.var.LandUseMask = loadmap('LandUseMask')

            if option['wateruse']:
                self.var.RegionPopulation = np.take(np.bincount(self.var.WUseRegionC, weights=self.var.Population), self.var.WUseRegionC)
                # population sum in Regions
                # set to 0 at start
                self.var.DayCounter = 0
                self.var.MonthETpotMM = maskinfo.in_zero()
                self.var.MonthETactMM = maskinfo.in_zero()
                self.var.MonthWDemandM3 = maskinfo.in_zero()
                self.var.MonthWAbstractionM3 = maskinfo.in_zero()
                self.var.MonthWConsumptionM3 = maskinfo.in_zero()
                self.var.MonthDisM3 = maskinfo.in_zero()
                self.var.MonthInternalFlowM3 = maskinfo.in_zero()
                self.var.MonthExternalInflowM3 = maskinfo.in_zero()
                self.var.RegionMonthIrrigationShortageM3 = maskinfo.in_zero()
                self.var.MonthWaterAbstractedfromLakesReservoirsM3 = maskinfo.in_zero()

                self.var.LakeStorageM3 = maskinfo.in_zero()

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
            self.var.DayCounter = self.var.DayCounter + 1.0
            self.var.MonthETpotMM = self.var.MonthETpotMM + self.var.ETRef
            self.var.MonthETactMM = self.var.MonthETactMM + self.var.deffraction(self.var.TaInterception) + self.var.TaPixel + self.var.ESActPixel

            if option['openwaterevapo']:
                self.var.MonthETactMM += self.var.EvaAddM3 * self.var.M3toMM

            self.var.MonthETdifMM = np.maximum((self.var.MonthETpotMM - self.var.MonthETactMM)*self.var.LandUseMask, maskinfo.in_zero())
            # ; land use mask can be used to mask out deserts and high mountains, where no agriculture is possible

            self.var.MonthWDemandM3 = self.var.MonthWDemandM3 + self.var.TotalDemandM3
            self.var.MonthWAbstractionM3 = self.var.MonthWAbstractionM3 + self.var.TotalAbstractionFromSurfaceWaterM3 + self.var.ReservoirAbstractionM3 + self.var.LakeAbstractionM3 + self.var.TotalAbstractionFromGroundwaterM3
            self.var.MonthWConsumptionM3 = self.var.MonthWConsumptionM3  + self.var.WUseAddM3 + self.var.ReservoirAbstractionM3 + self.var.LakeAbstractionM3 + self.var.TotalAbstractionFromGroundwaterM3
            self.var.MonthDisM3 = self.var.MonthDisM3 + self.var.ChanQAvg * self.var.DtSec

            self.var.MonthWaterAbstractedfromLakesReservoirsM3 = self.var.MonthWaterAbstractedfromLakesReservoirsM3 + self.var.ReservoirAbstractionM3 + self.var.LakeAbstractionM3

            self.var.RegionMonthIrrigationShortageM3 = self.var.RegionMonthIrrigationShortageM3 + self.var.AreatotalIrrigationShortageM3

            # INTERNAL FLOW
            self.var.MonthInternalFlowM3 = self.var.MonthInternalFlowM3 + self.var.ToChanM3Runoff

            # --------------------------------------------------------------------------

            if self.var.monthend:

                # INTERNAL FLOW
                if option['simulateReservoirs'] or option['simulateLakes']:
                    # available LakeStorageM3 and ReservoirStorageM3 for potential abstraction at end of month in region
                    self.var.RegionMonthReservoirAndLakeStorageM3 = np.take(np.bincount(self.var.WUseRegionC, weights=(self.var.ReservoirStorageM3 + self.var.LakeStorageM3)), self.var.WUseRegionC)

                # monthly abstraction from lakes and reservoirs
                self.var.RegionMonthWaterAbstractedfromLakesReservoirsM3 = np.take(np.bincount(self.var.WUseRegionC,weights=self.var.MonthWaterAbstractedfromLakesReservoirsM3),self.var.WUseRegionC)

                #PerMonthInternalFlowM3  = areatotal(cover(decompress(self.var.MonthInternalFlow),0.0),wreg)
                self.var.RegionMonthInternalFlowM3 = np.take(np.bincount(self.var.WUseRegionC,weights=self.var.MonthInternalFlowM3),self.var.WUseRegionC)
                # note Reservoir and Lake storage need to be taken into account seperately

                # EXTERNAL FLOW
                wreg = decompress(self.var.WUseRegionC)
                     # to pcraster map because of the following expression!
                self.var.RegionMonthExternalInflowM3 = compressArray(areatotal(cover(ifthen(self.var.WaterRegionInflowPoints != 0, upstream(self.var.LddStructuresKinematic,decompress(self.var.MonthDisM3))),0),wreg))

                self.var.RegionMonthWAbstractionM3 = np.take(np.bincount(self.var.WUseRegionC,weights=self.var.MonthWAbstractionM3),self.var.WUseRegionC)
                self.var.RegionMonthWConsumptionM3 = np.take(np.bincount(self.var.WUseRegionC,weights=self.var.MonthWConsumptionM3),self.var.WUseRegionC)
                self.var.RegionMonthWDemandM3      = np.take(np.bincount(self.var.WUseRegionC,weights=self.var.MonthWDemandM3),self.var.WUseRegionC)

                # Calculation of WEI: everything in m3, totalled over the water region

                UpstreamInflowM3 = self.var.RegionMonthExternalInflowM3
                LocalFreshwaterM3 = self.var.RegionMonthInternalFlowM3
                # still to be decided if reservoir and lake water availability is added here
                LocalTotalWaterDemandM3 = self.var.RegionMonthWDemandM3
                RemainingDemandM3 = np.maximum(LocalTotalWaterDemandM3 - LocalFreshwaterM3,0.0)
                # this is the demand that cannot be met by local water supply
                UpstreamInflowUsedM3 = np.minimum(RemainingDemandM3,UpstreamInflowM3)
                # the amount of upstream water an area really depends on
                FossilGroundwaterUsedM3 = np.maximum(RemainingDemandM3 - UpstreamInflowUsedM3,0.0)
                # the amount of water that cannot be met locally nor with international water
                # likely this is the amount of water drawn from deep groundwater

                self.var.WEI_Cns = np.where((UpstreamInflowM3+LocalFreshwaterM3) > 0.0,self.var.RegionMonthWConsumptionM3 / (UpstreamInflowM3+LocalFreshwaterM3),0.0)
                self.var.WEI_Abs = np.where((UpstreamInflowM3+LocalFreshwaterM3) > 0.0,self.var.RegionMonthWAbstractionM3 / (UpstreamInflowM3+LocalFreshwaterM3),0.0)
                self.var.WEI_Dem = np.where((UpstreamInflowM3+LocalFreshwaterM3) > 0.0,self.var.RegionMonthWDemandM3 / (UpstreamInflowM3+LocalFreshwaterM3),0.0)

                self.var.WaterSustainabilityIndex =  np.where(LocalTotalWaterDemandM3 > 0.0, FossilGroundwaterUsedM3 / (LocalTotalWaterDemandM3+1),0.0)
                # De Roo 2015: WTI, if above zero, indicates that situation is unsustainable
                # if index is 0 means sustainable situtation: no groundwater or desalination water used
                # if index is 1 means area relies completely on groundwater or desalination water
                # the '+1' is to prevent division by small values, leading to very large and misleading indicator values

                self.var.WaterDependencyIndex =  np.where(LocalTotalWaterDemandM3 > 0.0,  UpstreamInflowUsedM3 / (LocalTotalWaterDemandM3+1),0.0)
                # De Roo 2015: WDI, dependency on upstreamwater, as a fraction of the total local demand
                # the '+1' is to prevent division by small values, leading to very large and misleading indicator values

                self.var.WaterSecurityIndex = np.where(UpstreamInflowM3 > 0.0,  UpstreamInflowUsedM3 / (UpstreamInflowM3+1),0.0)
                # De Roo 2015: WSI, indicates the vulnerability to the available upstream water;
                # if only 10% of upstream inflow is use, WSI would be 0.1 indicating low vulnerability
                # if WSI is close to 1, situation is very vulnerable
                # the '+1' is to prevent division by small values, leading to very large and misleading indicator values

                self.var.FalkenmarkM3Capita1 = np.where(self.var.RegionPopulation > 0.0,self.var.RegionMonthInternalFlowM3*12/self.var.RegionPopulation, maskinfo.in_zero())
                self.var.FalkenmarkM3Capita2 = np.where(self.var.RegionPopulation > 0.0,LocalFreshwaterM3*12/self.var.RegionPopulation, maskinfo.in_zero())
                self.var.FalkenmarkM3Capita3 = np.where(self.var.RegionPopulation > 0.0,(UpstreamInflowM3+LocalFreshwaterM3)*12/self.var.RegionPopulation, maskinfo.in_zero())
                # FalkenmarkM3Capita1 = (TotalRegionMonthToChanM3)/TotalTimeSteps*365.25/(PopulationRegion+0.0001);
                # FalkenmarkM3Capita2 = (TotalRegionMonthToChanM3+TotalRegionMonthReservoirLakeAbstractionM3)/TotalTimeSteps*365.25/(PopulationRegion+0.0001);
                # FalkenmarkM3Capita3 = (TotalRegionMonthToChanM3+TotalRegionMonthReservoirLakeAbstractionM3+TotalRegionMonthExternalInflowM3)/TotalTimeSteps*365.25/(PopulationRegion+0.0001);
                # report(decompress(self.var.WEI_Use),'E:/test.map')

# --------------------------------------------------------------------------
    def dynamic_setzero(self):
        """ dynamic part of the indicator calculation module
            which set the monthly (yearly) values back to start
        """
        settings = LisSettings.instance()
        option = settings.options

        if option['wateruse'] and option['indicator'] and self.var.monthend:
            maskinfo = MaskInfo.instance()
            # set to 0 at the end of a month
            self.var.DayCounter = 0
            self.var.MonthETpotMM = maskinfo.in_zero()
            self.var.MonthETactMM = maskinfo.in_zero()
            self.var.MonthWDemandM3 = maskinfo.in_zero()
            self.var.MonthWAbstractionM3 = maskinfo.in_zero()
            self.var.MonthWConsumptionM3 = maskinfo.in_zero()
            self.var.MonthDisM3 = maskinfo.in_zero()
            self.var.MonthInternalFlowM3 = maskinfo.in_zero()
            self.var.MonthExternalInflowM3 = maskinfo.in_zero()
            self.var.RegionMonthIrrigationShortageM3 = maskinfo.in_zero()
            self.var.MonthWaterAbstractedfromLakesReservoirsM3 = maskinfo.in_zero()
