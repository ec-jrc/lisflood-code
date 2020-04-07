# -------------------------------------------------------------------------
# Name:        Water abstraction module
# Purpose:
#
# Author:      burekpe, rooarie
#
# Created:     13.10.2014
# Copyright:   (c) jrc 2015
# Licence:     <your licence>
# -------------------------------------------------------------------------


from global_modules.add1 import *


class waterabstraction(object):

    """
    # ************************************************************
    # ***** Water abstraction ************************************
    # ************************************************************
    """

    def __init__(self, waterabstraction_variable):
        self.var = waterabstraction_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the water abstraction module
        """

        # self.testmap=windowaverage(self.var.Elevation,5)
        # self.report(self.testmap,"test.map")

# ************************************************************
# ***** WATER USE
# ************************************************************

        if option['wateruse']:
            self.var.NoWaterUseSteps = int(loadmap('maxNoWateruse'))
            self.var.GroundwaterBodies = loadmap('GroundwaterBodies')
            self.var.FractionGroundwaterUsed = np.minimum(np.maximum(loadmap('FractionGroundwaterUsed'), 0), 1)
            self.var.FractionNonConventionalWaterUsed = loadmap('FractionNonConventionalWaterUsed')
            self.var.FractionLakeReservoirWaterUsed = loadmap('FractionLakeReservoirWaterUsed')
            self.var.EFlowThreshold = loadmap('EFlowThreshold')
            # EFlowThreshold is map with m3/s discharge, e.g. the 10th percentile discharge of the baseline run

            self.var.WUseRegionC = loadmap('WUseRegion').astype(int)
            self.var.IrrigationMult = loadmap('IrrigationMult') #  a factor (IrrigationMult) add some water (to prevent salinisation)


            # ************************************************************
            # ***** water use constant maps ******************************
            # ************************************************************

            self.var.IndustryConsumptiveUseFraction = loadmap('IndustryConsumptiveUseFraction')
             # fraction (0-1)
            self.PotentialIrrigationWaterReUseM3Annual = loadmap('IrrigationWaterReUseM3')
             # M3 per year treated waste water reuse (TEMPORARY)
            self.PotentialIrrigationWaterReUseM3Daily = self.PotentialIrrigationWaterReUseM3Annual / loadmap('IrrigationWaterReUseNumDays')
             # maximum M3 per day treated waste water reuse (TEMPORARY)
            self.ActualAccumulatedReUsedWaterM3 = globals.inZero.copy()
             # accumulated treated waste water used so far this year (restarted on January 1st every year) (TEMPORARY)
            self.var.EnergyConsumptiveUseFraction = loadmap('EnergyConsumptiveUseFraction')
             # fraction (0-1), value depends on cooling technology of power plants
            self.var.LivestockConsumptiveUseFraction = loadmap('LivestockConsumptiveUseFraction')
             # fraction (0-1)
            # Fraction of domestic (gross) abstraction that is leaked
            leak_abstraction_fraction = np.minimum(np.maximum(loadmap('LeakageFraction') * (1 - loadmap('LeakageReductionFraction')), 0.), 1.)
            # Fraction of domestic (net) demand that is leaked
            self.leak_demand_fraction = leak_abstraction_fraction / (1 - leak_abstraction_fraction)
            self.var.DomesticWaterSavingConstant = np.minimum(np.maximum(1 - loadmap('WaterSavingFraction'), 0.), 1.)
             # Domestic water saving if in place, changes this value from 1 to a value between 0 and 1, and will reduce demand and abstraction
             # so value = 0.9 if WaterSavingFraction equals 0.1 (10%)
            self.var.DomesticConsumptiveUseFraction = loadmap('DomesticConsumptiveUseFraction')
             # fraction (0-1), typically rather low ~ 0.10

            self.demand_domestic_MM = loadmap('DomesticDemandMaps')
            self.demand_industry_MM = loadmap('IndustrialDemandMaps')
            self.demand_livestock_MM = loadmap('LivestockDemandMaps')
            self.demand_energy_MM = loadmap('EnergyDemandMaps')

            if option['groundwaterSmooth']:
                self.var.GroundwaterBodiesPcr = decompress(self.var.GroundwaterBodies)
                self.var.groundwaterCatch = boolean(decompress((self.var.GroundwaterBodies *self.var.Catchments).astype(int)))
                 # nominal(scalar(GroundwaterBodies)*scalar(self.var.Catchments));
                 # smoothing for groundwater to correct error by using windowtotal, based on groundwater bodies and catchments
                self.var.LZSmoothRange = loadmap('LZSmoothRange')


            if option['wateruseRegion']:
                WUseRegion = nominal(loadmap('WUseRegion',pcr=True))
                pitWuse1 =  ifthen(self.var.AtLastPoint != 0,pcraster.boolean(1))
                pitWuse1b = ifthen(defined(pitWuse1),WUseRegion)
                   # use every existing pit in the Ldd and number them by the water regions
                   # coastal water regions can have more than one pit per water region

                pitWuseMax = areamaximum(self.var.UpArea,WUseRegion)
                pitWuse2 = ifthen(pitWuseMax == self.var.UpArea,WUseRegion)
                   # search outlets in the inland water regions by using the maximum  upstream area as criterium

                pitWuse3 = downstream(self.var.LddStructuresKinematic,WUseRegion)
                pitWuse3b = ifthen(pitWuse3 != WUseRegion,WUseRegion)
                   # search point where ldd leaves a water region

                pitWuse=cover(pitWuse1b,pitWuse2,pitWuse3b,nominal(0))
                   # join all sources of pits

                LddWaterRegion=lddrepair(ifthenelse(pitWuse == 0,self.var.LddStructuresKinematic,5))
                   # create a Ldd with pits at every water region outlet
                   # this results in a interrupted ldd, so water cannot be transfered to the next water region

                lddC = compressArray(LddWaterRegion)
                inAr = decompress(np.arange(maskinfo['mapC'][0],dtype="int32"))
                 # giving a number to each non missing pixel as id
                self.var.downWRegion = (compressArray(downstream(LddWaterRegion,inAr))).astype(np.int32)
                 # each upstream pixel gets the id of the downstream pixel
                self.var.downWRegion[lddC==5] = maskinfo['mapC'][0]
                 # all pits gets a high number


                # ************************************************************
                # ***** OUTFLOW AND INFLOW POINTS FOR WATER REGIONS **********
                # ************************************************************

                self.var.WaterRegionOutflowPoints = ifthen(pitWuse != 0,boolean(1))
	              # outflowpoints to calculate upstream inflow for balances and Water Exploitation Index
	              # both inland outflowpoints to downstream subbasin, and coastal outlets

                WaterRegionInflow1=boolean(upstream(self.var.LddStructuresKinematic,cover(scalar(self.var.WaterRegionOutflowPoints),0)))
                self.var.WaterRegionInflowPoints=ifthen(WaterRegionInflow1,boolean(1))
	              # inflowpoints to calculate upstream inflow for balances and Water Exploitation Index

            else:
                 self.var.downWRegion = self.var.downstruct.copy()
                 self.var.downWRegion = self.var.downWRegion.astype(np.int32)


# --------------------------------------------------------

            # ************************************************************
            # ***** Initialising cumulative output variables *************
            # ************************************************************

            # These are all needed to compute the cumulative mass balance error

            self.var.cumulated_CH_withdrawal = globals.inZero.copy()
            # water use cumulated amount

            self.var.IrriLossCUM = globals.inZero.copy()
            # Cumulative irrigation loss [mm]
            abstractionCUM = globals.inZero.copy()
            # Cumulative abstraction from surface water [mm]

            IrrigationWaterDemand = globals.inZero.copy()

            self.var.IrrigationType = loadmap('IrrigationType') # between 0 and 1 (0 = no additional irrigation water; 1 = adding water until fieldcapacity) (CHECK: unused?)
            self.efficiency_irrigation = loadmap('IrrigationEfficiency') * loadmap('ConveyanceEfficiency')

            self.var.GroundwaterRegionPixels= sumOverAreas(self.var.GroundwaterBodies, self.var.WUseRegionC)
            self.var.AllRegionPixels= sumOverAreas(self.var.GroundwaterBodies*0.0+1.0, self.var.WUseRegionC)
            self.var.RatioGroundWaterUse = self.var.AllRegionPixels/(self.var.GroundwaterRegionPixels+0.01)
            self.var.FractionGroundwaterUsed = np.minimum(self.var.FractionGroundwaterUsed*self.var.RatioGroundWaterUse, 1-self.var.FractionNonConventionalWaterUsed)
            self.var.FractionGroundwaterUsed[self.var.GroundwaterBodies == 0] = 0.
            # FractionGroundwaterUsed is a percentage given at national scale
            # since the water needs to come from the GroundwaterBodies pixels, the fraction needs correction for the non-Groundwaterbodies; this is done here
            # Fraction of irrigation water requirement tentatively supplied by groundwater (if EPIC is active, an irrigation-specific map is loaded):
            self.GWfed_fraction_irrigation = loadmap("irrigation_groundwater_fraction") if option['cropsEPIC'] else self.var.FractionGroundwaterUsed
            self.GWfed_fraction_irrigation[self.var.GroundwaterBodies == 0] = 0.
            self.FractionSurfaceWaterUseDomLivInd = np.maximum(np.minimum(1 - self.var.FractionGroundwaterUsed - self.var.FractionNonConventionalWaterUsed, 1), 0)


    def dynamic(self):
        """ dynamic part of the water use module
            init water use before sub step routing
        """
        if not option['wateruse']:
            return
        # ************************************************************
        # 1. Read user water demands (all users except irrigation
        # ************************************************************
        if option['TransientWaterDemandChange']:
            if option['readNetcdfStack']:
                self.demand_domestic_MM = readnetcdf(binding['DomesticDemandMaps'], self.var.currentTimeStep())
                self.demand_industry_MM = readnetcdf(binding['IndustrialDemandMaps'], self.var.currentTimeStep())
                self.demand_livestock_MM = readnetcdf(binding['LivestockDemandMaps'], self.var.currentTimeStep())
                self.demand_energy_MM = readnetcdf(binding['EnergyDemandMaps'], self.var.currentTimeStep())
            else:
                self.demand_domestic_MM = readmapsparse(binding['DomesticDemandMaps'], self.var.currentTimeStep(), self.demand_domestic_MM)
                self.demand_industry_MM = readmapsparse(binding['IndustrialDemandMaps'], self.var.currentTimeStep(), self.demand_industry_MM)
                self.demand_livestock_MM = readmapsparse(binding['LivestockDemandMaps'], self.var.currentTimeStep(), self.demand_livestock_MM)
                self.demand_energy_MM = readmapsparse(binding['EnergyDemandMaps'], self.var.currentTimeStep(), self.demand_energy_MM)
        # ************************************************************
        # 2. Livestock
        # ************************************************************
        consumption_required_livestock_MM = self.demand_livestock_MM * self.var.LivestockConsumptiveUseFraction
        consumption_GW_livestock_MM = consumption_required_livestock_MM * self.var.FractionGroundwaterUsed
        consumption_SW_required_livestock_MM = consumption_required_livestock_MM * self.FractionSurfaceWaterUseDomLivInd
        abstraction_required_livestock_M3 = self.demand_livestock_MM * self.var.MMtoM3
        abstraction_GW_livestock_M3 = self.var.FractionGroundwaterUsed * abstraction_required_livestock_M3
        abstraction_NC_livestock_M3 = self.var.FractionNonConventionalWaterUsed * abstraction_required_livestock_M3
        abstraction_SW_required_livestock_M3 = abstraction_required_livestock_M3 - abstraction_GW_livestock_M3 - abstraction_NC_livestock_M3
        # ************************************************************
        # 3. Domestic (increased by leakage and decreased by savings)
        # ************************************************************
        demand_reduced_domestic_MM = self.demand_domestic_MM  * self.var.DomesticWaterSavingConstant
        leakage_domestic_MM = self.leak_demand_fraction * demand_reduced_domestic_MM # Leakage in mm per day
        abstraction_required_domestic_MM = demand_reduced_domestic_MM + leakage_domestic_MM
        abstraction_required_domestic_M3 = abstraction_required_domestic_MM * self.var.MMtoM3
        consumption_required_domestic_MM = demand_reduced_domestic_MM * self.var.DomesticConsumptiveUseFraction # (CHECK: leakage?)
        consumption_GW_domestic_MM = consumption_required_domestic_MM * self.var.FractionGroundwaterUsed
        consumption_SW_required_domestic_MM = consumption_required_domestic_MM * self.FractionSurfaceWaterUseDomLivInd
        abstraction_GW_domestic_M3 = self.var.FractionGroundwaterUsed * abstraction_required_domestic_M3
        abstraction_NC_domestic_M3 = self.var.FractionNonConventionalWaterUsed * abstraction_required_domestic_M3
        abstraction_SW_required_domestic_M3 = abstraction_required_domestic_M3 - abstraction_GW_domestic_M3 - abstraction_NC_domestic_M3
        # ************************************************************
        # 4. Industry (decreased by re-use)
        # ************************************************************
        abstraction_required_industry_M3 = self.demand_industry_MM * self.var.MMtoM3
        consumption_required_industry_MM = self.demand_industry_MM * self.var.IndustryConsumptiveUseFraction
        consumption_GW_industry_MM = consumption_required_industry_MM * self.var.FractionGroundwaterUsed
        consumption_SW_required_industry_MM = consumption_required_industry_MM * self.FractionSurfaceWaterUseDomLivInd
        abstraction_GW_industry_M3 = self.var.FractionGroundwaterUsed * abstraction_required_industry_M3
        abstraction_NC_industry_M3 = self.var.FractionNonConventionalWaterUsed * abstraction_required_industry_M3
        abstraction_SW_required_industry_M3 = abstraction_required_industry_M3 - abstraction_GW_industry_M3 - abstraction_NC_industry_M3
        # ************************************************************
        # 5. Energy (only from surface water)
        # ************************************************************
        consumption_required_energy_MM = self.demand_energy_MM * self.var.EnergyConsumptiveUseFraction
        abstraction_SW_required_energy_M3 = self.demand_energy_MM * self.var.MMtoM3
        # ************************************************************
        # 6. Irrigation
        # ************************************************************
        # 6.1 Required consumption (amount needed to be put into the root-zone soil layers) and required abstraction
        if option["cropsEPIC"] and option["allIrrigIsEPIC"]:
            consumption_required_irrigation_MM = globals.inZero.copy()
            self.var.abstraction_required_irrigation_M3 = globals.inZero.copy()
        else: # irrigation demand = transpiration deficit multiplied by anti-salinity factor
            irr_pre = "Irrigated_prescribed" # It applies only to prescribed irrigation fraction (EPIC simulates specific irrigated crops, if any)
            self.var.Ta.loc[irr_pre] = np.maximum(np.minimum(self.var.RWS.loc[irr_pre] * self.var.potential_transpiration.loc[irr_pre],
                                                             self.var.W1.loc[irr_pre] - self.var.WWP1.loc[VEGETATION_LANDUSE[irr_pre]]), 0)
            demand_irrigation_MM = (self.var.potential_transpiration.loc[irr_pre] - self.var.Ta.loc[irr_pre]) * self.var.SoilFraction.loc[irr_pre]
            demand_irrigation_MM[self.var.isFrozenSoil] = 0 # no irrigation if the soil is frozen
            consumption_required_irrigation_MM = demand_irrigation_MM * self.var.IrrigationMult
            self.var.abstraction_required_irrigation_M3 = np.where(self.efficiency_irrigation > 0,
                                                                   consumption_required_irrigation_MM / self.efficiency_irrigation * self.var.MMtoM3, 0)
        if option["cropsEPIC"]: # Add pixel-averaged EPIC gross irrigation requirement to LISFLOOD (perscribed_irrigation fraction) irrigation demand
            consumption_required_irrigation_MM += (self.var.crop_module.NIR_mm + self.var.crop_module.irrigation_losses_atmosphere).values
            self.var.abstraction_required_irrigation_M3 += self.var.crop_module.GIR_m3.values # [mm]
        # 6.2 Amount of treated wastewater used for irrigation
        if self.var.CalendarDay == 1:
            self.ActualAccumulatedReUsedWaterM3 = globals.inZero.copy()
        WaterAvailableForReUseM3 = np.minimum(np.maximum(self.PotentialIrrigationWaterReUseM3Annual - self.ActualAccumulatedReUsedWaterM3, 0),\
                                              self.PotentialIrrigationWaterReUseM3Daily) # potential ReUsed water amount (m3) available as irrigation
        self.var.abstraction_Reuse_irrigation_M3 = np.minimum(WaterAvailableForReUseM3, self.var.abstraction_required_irrigation_M3) # actual ReUsed water amount (m3) for irrigation
        self.ActualAccumulatedReUsedWaterM3 += self.var.abstraction_Reuse_irrigation_M3 # added to the accumulated annual reuse
        fraction_irrigation_SwGw = 1. - np.where(self.var.abstraction_required_irrigation_M3 > 0,
                                                 self.var.abstraction_Reuse_irrigation_M3 / self.var.abstraction_required_irrigation_M3, 0.)
        abstraction_SwGw_required_irrigation_M3 = fraction_irrigation_SwGw * self.var.abstraction_required_irrigation_M3
        consumption_SwGw_required_irrigation_MM = fraction_irrigation_SwGw * consumption_required_irrigation_MM
        # 6.3 Partition irrigation required abstraction and consumption among ground- and surface-water resources after removing re-used water input
        abstraction_GW_required_irrigation_M3 = self.GWfed_fraction_irrigation * abstraction_SwGw_required_irrigation_M3
        abstraction_SW_required_irrigation_M3 = np.maximum(abstraction_SwGw_required_irrigation_M3 - abstraction_GW_required_irrigation_M3, 0)
        consumption_GW_required_irrigation_MM = self.GWfed_fraction_irrigation * consumption_required_irrigation_MM
        consumption_SW_required_irrigation_MM = np.maximum(consumption_SwGw_required_irrigation_MM - consumption_GW_required_irrigation_MM, 0)
        # 6.4 Regulation of groundwater abstraction for irrigation (if crop module and option are active)
        if option["cropsEPIC"] and option['regulate_GW_irrigation_abstraction']:
            abstraction_GW_actual_irrigation_M3, frac_GW_irr = self.var.crop_module.irrigation_module.GW_abstraction_rule.regulateAbstraction(abstraction_GW_required_irrigation_M3)
            consumption_GW_actual_irrigation_MM = consumption_GW_required_irrigation_MM * frac_GW_irr
        else:
            abstraction_GW_actual_irrigation_M3 = abstraction_GW_required_irrigation_M3
            consumption_GW_actual_irrigation_MM = consumption_GW_required_irrigation_MM
        # ***********************************************************************
        # 7. Aggregate required abstraction, consumption, and surface water withdrawal
        # ***********************************************************************
        # 7.1 Sum of required abstractions for WEI-D and WEI-A calculations
        self.var.abstraction_allSources_required_M3 = abstraction_required_domestic_M3 + abstraction_required_livestock_M3 +\
                                                      abstraction_required_industry_M3 + abstraction_SW_required_energy_M3 +\
                                                      self.var.PaddyRiceWaterAbstractionFromSurfaceWaterM3 + self.var.abstraction_required_irrigation_M3 
        abstraction_GW_noReturn_M3 = abstraction_GW_domestic_M3 + abstraction_GW_livestock_M3 + abstraction_GW_industry_M3
        self.var.abstraction_SwGw_required_M3 = abstraction_SW_required_domestic_M3 + abstraction_SW_required_livestock_M3 +\
                                                abstraction_SW_required_industry_M3 + abstraction_SW_required_energy_M3 +\
                                                abstraction_SW_required_irrigation_M3 + abstraction_GW_required_irrigation_M3 +\
                                                self.var.PaddyRiceWaterAbstractionFromSurfaceWaterM3 + abstraction_GW_noReturn_M3
        # 7.2 Total required consumption from surface water (SW) and groundwater (GW)
        consumption_GW_noReturn_M3 = (consumption_GW_domestic_MM + consumption_GW_livestock_MM + consumption_GW_industry_MM) * self.var.MMtoM3
        consumption_SW_required_noReturn_M3 = (consumption_SW_required_domestic_MM + consumption_SW_required_livestock_MM + consumption_SW_required_industry_MM +
                                          consumption_required_energy_MM) * self.var.MMtoM3
        self.var.consumption_SwGw_required_M3 = (consumption_GW_required_irrigation_MM + consumption_SW_required_irrigation_MM) * self.var.MMtoM3 +\
                                                self.var.PaddyRiceWaterAbstractionFromSurfaceWaterM3 + consumption_GW_noReturn_M3 + consumption_SW_required_noReturn_M3
        # 7.3 Withdrawal (abstraction minus instanteneous return flow) required from surface water bodies
        withdrawal_SW_required = consumption_SW_required_noReturn_M3 + abstraction_SW_required_irrigation_M3 + self.var.PaddyRiceWaterAbstractionFromSurfaceWaterM3
        areatotal_withdrawal_SW_required = sumOverAreas(withdrawal_SW_required, self.var.WUseRegionC)
        is_SW_withdrawal_required_WUR = areatotal_withdrawal_SW_required > 0
        # ************************************************************
        # 8. Groundwater (GW) abstraction
        # ************************************************************
        # 8.1 Actual abstraction
        self.var.abstraction_GW_actual_M3 = abstraction_GW_noReturn_M3 + abstraction_GW_actual_irrigation_M3
        # 8.2 Groundwater lower zone mass balance update
        self.var.LZ -= self.var.abstraction_GW_actual_M3 * self.var.M3toMM
        self.var.IrriLossCUM += self.var.abstraction_GW_actual_M3 # irrigation local losses accounting (CHECK)
        # 8.3 Return flow to channel (per routing time step) from groundwater users not storing water (all except irrigation)
        self.var.returnflow_GwAbs2Channel_M3_routStep = (abstraction_GW_noReturn_M3 - consumption_GW_noReturn_M3) * self.var.InvNoRoutSteps
        # ************************************************************
        # 9. Lake and reservoir abstraction
        # ************************************************************
        # 9.1 Max abstractable volumes from lakes and reservoirs: pixel values and integral over water use regions (Areatotal...)
        PotentialAbstractionFromReservoirsM3 = np.minimum(0.02 * self.var.ReservoirStorageM3, 0.01*self.var.TotalReservoirStorageM3C)
        PotentialAbstractionFromReservoirsM3 = np.where(np.isnan(PotentialAbstractionFromReservoirsM3),0,PotentialAbstractionFromReservoirsM3)
        PotentialAbstractionFromLakesM3 = 0.10 * self.var.LakeStorageM3
        PotentialAbstractionFromLakesM3 = np.where(np.isnan(PotentialAbstractionFromLakesM3),0,PotentialAbstractionFromLakesM3)
        PotentialAbstractionFromLakesAndReservoirsM3 = PotentialAbstractionFromLakesM3 + PotentialAbstractionFromReservoirsM3
        AreatotalPotentialAbstractionFromLakesAndReservoirsM3 = sumOverAreas(PotentialAbstractionFromLakesAndReservoirsM3, self.var.WUseRegionC)
        # 9.2 Water regions' required and actual abstraction from lakes (Lak) and reservoirs (Res)
        areatotal_withdrawal_LakRes_required_M3 = self.var.FractionLakeReservoirWaterUsed * areatotal_withdrawal_SW_required
        self.var.areatotal_withdrawal_LakRes_actual_M3 = np.minimum(areatotal_withdrawal_LakRes_required_M3, AreatotalPotentialAbstractionFromLakesAndReservoirsM3)
        FractionAbstractedByLakesReservoirs = np.where(is_SW_withdrawal_required_WUR, self.var.areatotal_withdrawal_LakRes_actual_M3 / areatotal_withdrawal_SW_required, 0.)
        # 9.3 Distribute actual abstractions among lakes and reservoirs inside each water region
        FractionLakesReservoirsEmptying = np.where(AreatotalPotentialAbstractionFromLakesAndReservoirsM3 > 0,
                                                   self.var.areatotal_withdrawal_LakRes_actual_M3 / AreatotalPotentialAbstractionFromLakesAndReservoirsM3, 0.)
        self.var.LakeAbstractionM3 = PotentialAbstractionFromLakesM3 * FractionLakesReservoirsEmptying
        self.var.ReservoirAbstractionM3 = PotentialAbstractionFromReservoirsM3 * FractionLakesReservoirsEmptying
        # 9.4 Update the storages of lakes and reservoirs
        self.var.LakeStorageM3 -= self.var.LakeAbstractionM3
        self.var.ReservoirStorageM3 -= self.var.ReservoirAbstractionM3
        # ************************************************************
        # 10. Channel withdrawal
        # ************************************************************
        # 10.1 Withdrawal required from channels (CH)
        areatotal_withdrawal_CH_required_M3 = np.maximum(areatotal_withdrawal_SW_required - self.var.areatotal_withdrawal_LakRes_actual_M3, 0.)
        # 10.2 Max abstractable volumes from channels, accounting for e-flow constraint
        PixelAvailableWaterFromChannelsM3 = np.maximum(self.var.ChanM3Kin - self.var.EFlowThreshold * self.var.DtSec, 0.)
        AreaTotalAvailableWaterFromChannelsM3 = sumOverAreas(PixelAvailableWaterFromChannelsM3, self.var.WUseRegionC)
        # 10.3 Actual channel withdrawal
        self.var.areatotal_withdrawal_CH_actual_M3 =  np.minimum(AreaTotalAvailableWaterFromChannelsM3, areatotal_withdrawal_CH_required_M3)
        self.var.FractionAbstractedFromChannels = np.where(AreaTotalAvailableWaterFromChannelsM3 > 0,
                                                           np.minimum(self.var.areatotal_withdrawal_CH_actual_M3 / AreaTotalAvailableWaterFromChannelsM3, 1.), 0.)
        self.var.withdrawal_CH_actual_M3 = self.var.FractionAbstractedFromChannels * PixelAvailableWaterFromChannelsM3 # daily channel abstraction
        self.var.withdrawal_CH_actual_M3_routStep = self.var.withdrawal_CH_actual_M3 * self.var.InvNoRoutSteps # channel abstraction per routing time step
        # 10.5 Surface water shortage (that from lakes/reservoirs is transferred to the required abstraction from channels)
        self.var.areatotal_shortage_SW_M3 = np.maximum(areatotal_withdrawal_CH_required_M3 - self.var.areatotal_withdrawal_CH_actual_M3, 0.)
        # ************************************************************
        # 11. Total actual abstractions from surface water bodies
        # ************************************************************
        self.var.withdrawal_SW_actual_M3 = self.var.withdrawal_CH_actual_M3 + self.var.LakeAbstractionM3 + self.var.ReservoirAbstractionM3
        self.var.areatotal_withdrawal_SW_actual_M3 = sumOverAreas(self.var.withdrawal_SW_actual_M3, self.var.WUseRegionC)
        # ************************************************************
        # 12. Channel water allocation handling scarcity
        # ************************************************************
        # 12.1 In regions with water shortage, reduce irrigation first (CHECK: allocation to perscribed paddy rice is not reduced)
        abstraction_CH_required_irrigation_M3 = abstraction_SW_required_irrigation_M3 * (1 - FractionAbstractedByLakesReservoirs)
        areatotal_abstraction_CH_required_irrigation_M3 = sumOverAreas(abstraction_CH_required_irrigation_M3, self.var.WUseRegionC)
        irrabs_minus_shortage_ATCHM3 = areatotal_abstraction_CH_required_irrigation_M3 - self.var.areatotal_shortage_SW_M3
        areatotal_abstraction_CH_actual_irrigation_M3 = np.maximum(irrabs_minus_shortage_ATCHM3, 0.)
        fraction_met_CH_irrigation = np.minimum(np.where(areatotal_abstraction_CH_required_irrigation_M3 > 0,
                                                         areatotal_abstraction_CH_actual_irrigation_M3 / areatotal_abstraction_CH_required_irrigation_M3, 0.), 1.)
        abstraction_CH_actual_irrigation_M3 = abstraction_CH_required_irrigation_M3 * fraction_met_CH_irrigation
        # 12.2 Actual channel abstractions for the sectors without return flows (ene, dom, liv, ind), accounting for shortage where needed
        withdrawal_CH_required_noReturn_M3 = consumption_SW_required_noReturn_M3 * (1 - FractionAbstractedByLakesReservoirs)
        areatotal_withdrawal_CH_required_noReturn_M3 = sumOverAreas(withdrawal_CH_required_noReturn_M3, self.var.WUseRegionC)
        areatotal_shortage_CH_beyondIrrigation_M3 = np.maximum(-irrabs_minus_shortage_ATCHM3, 0.)
        areatotal_withdrawal_CH_actual_noReturn_M3 = np.maximum(areatotal_withdrawal_CH_required_noReturn_M3 - areatotal_shortage_CH_beyondIrrigation_M3, 0.)
        fraction_met_CH_noReturn = np.minimum(np.where(areatotal_withdrawal_CH_required_noReturn_M3 > 0,
                                                       areatotal_withdrawal_CH_actual_noReturn_M3 / areatotal_withdrawal_CH_required_noReturn_M3, 0.), 1.)
        ## TEST
        #aux = (self.var.abstraction_GW_actual_M3.mean(), self.var.LakeAbstractionM3.mean(), self.var.ReservoirAbstractionM3.mean(),
        #       self.var.withdrawal_CH_actual_M3.mean())
        #print('gw: {}, lak: {}, res: {}, chan: {}, tot: {}'.format(*(aux + (sum(aux), ))))
        # 12.4 Bookkeeping for over-all water balance, and repwateruseGauges and repwateruseSites
        self.var.cumulated_CH_withdrawal += self.var.withdrawal_CH_actual_M3 # bookkeeping for over-all water balance
        if (option['repwateruseGauges']) or (option['repwateruseSites']):
            self.var.WUseSumM3 = accuflux(self.var.Ldd, decompress(self.var.withdrawal_CH_actual_M3)*self.var.InvDtSec)
        # ********************************************************************************************
        # 13. Actual surface water abstractions (except prescribed paddy rice)
        # ********************************************************************************************
        # 13.1 Irrigation
        abstraction_SW_actual_irrigation_M3 = abstraction_SW_required_irrigation_M3 * FractionAbstractedByLakesReservoirs + abstraction_CH_actual_irrigation_M3
        self.var.areatotal_abstraction_SW_actual_irrigation_M3 = sumOverAreas(abstraction_SW_actual_irrigation_M3, self.var.WUseRegionC)
        fraction_met_SW_irrigation = np.minimum(FractionAbstractedByLakesReservoirs + fraction_met_CH_irrigation * (1 - FractionAbstractedByLakesReservoirs), 1.)
        # 13.2 Other uses for which return flows are not simulated
        fraction_met_SW_noReturn = np.minimum(FractionAbstractedByLakesReservoirs + fraction_met_CH_noReturn * (1 - FractionAbstractedByLakesReservoirs), 1.)
        abstraction_SW_actual_energy_M3 = abstraction_SW_required_energy_M3 * fraction_met_SW_noReturn
        abstraction_SW_actual_domestic_M3 = abstraction_SW_required_domestic_M3 * fraction_met_SW_noReturn
        abstraction_SW_actual_livestock_M3 = abstraction_SW_required_livestock_M3 * fraction_met_SW_noReturn
        abstraction_SW_actual_industry_M3 = abstraction_SW_required_industry_M3 * fraction_met_SW_noReturn
        # ********************************************************************************************
        # 14. Actual consumptions from surface water and groundwater bodies (for WeiC, WeiP)
        # ********************************************************************************************
        consumption_actual_irrigation_MM = consumption_GW_actual_irrigation_MM + consumption_SW_required_irrigation_MM * fraction_met_SW_irrigation
        consumption_actual_energy_MM = consumption_required_energy_MM * fraction_met_SW_noReturn
        consumption_actual_domestic_MM = consumption_GW_domestic_MM + consumption_SW_required_domestic_MM * fraction_met_SW_noReturn
        consumption_actual_livestock_MM = consumption_GW_livestock_MM + consumption_SW_required_livestock_MM * fraction_met_SW_noReturn
        consumption_actual_industry_MM = consumption_GW_industry_MM + consumption_SW_required_industry_MM * fraction_met_SW_noReturn
        self.var.consumption_SwGw_actual_M3 = (consumption_actual_irrigation_MM + consumption_actual_energy_MM + consumption_actual_domestic_MM +\
                                               consumption_actual_livestock_MM + consumption_actual_industry_MM) * self.var.MMtoM3 +\
                                              self.var.PaddyRiceWaterAbstractionFromSurfaceWaterM3
        # ********************************************************************************************
        # 15. Apply irrigation to have interactions with soil/crops
        # ********************************************************************************************
        # 15.1 Apply irrigation in the interactive crop module
        self.var.abstraction_SwGw_actual_irrigation_M3 = abstraction_SW_actual_irrigation_M3 + abstraction_GW_actual_irrigation_M3
        if option["cropsEPIC"]:  # EPIC irrigation scheme: irrigation application on EPIC-simulated irrigated crops.
            irrigation_withdrawal_EPIC = self.var.crop_module.dynamic_irrigation_application() # [m3]
        else:
            irrigation_withdrawal_EPIC = 0
        # 15.2 Apply irrigation on LISFLOOD Irrigated_prescribed fraction
        if not (option["cropsEPIC"] and option["allIrrigIsEPIC"]):
            irrigation_for_prescribed = np.maximum(self.var.abstraction_SwGw_actual_irrigation_M3 - irrigation_withdrawal_EPIC, 0) 
            # real irrigation is percentage of avail/demand for waterregion * old surface + old groundwater abstraction
            IrrigationWaterDemand = irrigation_for_prescribed*self.var.M3toMM
            IrrigationWaterDemand = np.where(self.var.SoilFraction.loc[irr_pre] > 0, IrrigationWaterDemand / self.var.SoilFraction.loc[irr_pre], 0)
            # updating soil moisture of LISFLOOD on Irrigated_prescribed fraction
            Wold = self.var.W1.loc[irr_pre]
            IrrigationDemandW1b = np.maximum(IrrigationWaterDemand - (self.var.WFilla - self.var.W1a.loc[irr_pre]), 0)
            self.var.W1a.loc[irr_pre] = np.where(self.var.W1a.loc[irr_pre] >= self.var.WFilla, self.var.W1a.loc[irr_pre],
                                                 np.minimum(self.var.WFilla, self.var.W1a.loc[irr_pre] + IrrigationWaterDemand))
            self.var.W1b.loc[irr_pre] = np.where(self.var.W1b.loc[irr_pre] >= self.var.WFillb, self.var.W1b.loc[irr_pre],
                                                 np.minimum(self.var.WFillb, self.var.W1b.loc[irr_pre] + IrrigationDemandW1b))
            self.var.W1.loc[irr_pre] = self.var.W1a.loc[irr_pre] + self.var.W1b.loc[irr_pre]
            # if irrigated soil is less than Pf3 then fill up to Pf3 (if there is water demand)
            # if more than Pf3 the additional water is transpirated
            # there is no water demand if the soil is frozen
            Wdiff = self.var.W1.loc[irr_pre] - Wold
            self.var.Ta.loc[irr_pre] =  self.var.Ta.loc[irr_pre] + IrrigationWaterDemand - Wdiff
            self.var.IrriLossCUM += irrigation_for_prescribed * self.efficiency_irrigation - Wdiff * self.var.MMtoM3 * self.var.SoilFraction.loc[irr_pre]
                 # Added to TA but also
                 # for mass balance calculate the loss of irrigation water
             # AdR: irrigation demand added to W1 and Ta; so assumption here that soil moisture stays the same
                     # we could also abstract more water equivalent to satisfy Ta and bring soil moisture to pF2 or so, for later consideration#
             # self.var.Ta[2] = np.where(self.var.isFrozenSoil, globals.inZero, self.var.Ta[2])
             # transpiration is 0 when soil is frozen
        # ************************************************************
        # 16. Smooth lower zone with correction
        # ************************************************************
        if option['groundwaterSmooth']:
#                # TEST - START
#                from pylab import *
#                is_aqui = self.var.GroundwaterBodies.astype(bool)
#                aquifer_mask = np.zeros(maskinfo['shape'], bool)
#                aquifer_mask[tuple([ix[is_aqui] for ix in np.where(~maskinfo['mask'])])] = True
#                neighbours_aquifer, num_neighs = neighbours4GWsmooth(aquifer_mask, int(self.var.LZSmoothRange) / 2)
#                LZ_smoothed = self.var.LZ.copy()
#                LZ_smoothed[is_aqui] = smoothLZ(LZ_smoothed[is_aqui], neighbours_aquifer, num_neighs, .1)
#                # TEST - END
            LZPcr = decompress(self.var.LZ)
            Range=self.var.LZSmoothRange*celllength()
            LZTemp1 = ifthen(self.var.GroundwaterBodiesPcr == 1,LZPcr)
            LZTemp2 = ifthen(self.var.GroundwaterBodiesPcr == 1,windowtotal(LZTemp1,Range))
            LZTemp3 = windowtotal(LZTemp1*0+1, Range)
            LZSmooth = ifthenelse(LZTemp3 == 0,0.0,LZTemp2/LZTemp3)
            LZPcr = ifthenelse(self.var.GroundwaterBodiesPcr == 0,LZPcr,0.9*LZPcr+0.1*LZSmooth)
            diffCorr=0.1*areaaverage(LZSmooth-LZTemp1, self.var.groundwaterCatch)
            # error of 0.1  LZSmooth operation (same factor of 0.1 as above)
            LZPcr -= cover(diffCorr,0)
            # correction of LZ by the average error from smoothing operation
            self.var.LZ = compressArray(LZPcr)
#                # TEST - START
#                print('\n{}\n'.format( np.absolute(LZ_smoothed-self.var.LZ).max()))
#                if np.absolute(LZ_smoothed-self.var.LZ).max() > 1e-3:
#                    import ipdb; ipdb.set_trace()
#                # TEST - END
        # ************************************************************
        # 17. Monthly accounting of water use terms by region
        # ************************************************************
        if option['repWaterUse'] and option['wateruse']:
            prescribed_paddy_rice_abs_mm = self.var.PaddyRiceWaterAbstractionFromSurfaceWaterM3 * self.var.M3toMM
            # Required consumptions (from surface water and groundwater) by sector, including actual figure for irrigation (month, region)
            self.var.consumption_required_domestic_MM_month += (consumption_SW_required_domestic_MM + consumption_GW_domestic_MM)
            self.var.consumption_required_energy_MM_month += consumption_required_energy_MM
            self.var.consumption_required_industry_MM_month += consumption_SW_required_industry_MM + consumption_GW_industry_MM
            self.var.consumption_required_livestock_MM_month += consumption_SW_required_livestock_MM + consumption_GW_livestock_MM
            self.var.consumption_required_irrigation_MM_month += consumption_SwGw_required_irrigation_MM + prescribed_paddy_rice_abs_mm
            self.var.consumption_actual_irrigation_MM_month += consumption_actual_irrigation_MM + prescribed_paddy_rice_abs_mm
            # Irrigation abstraction (month, region)
            self.var.abstraction_allSources_required_irrigation_M3Month += self.var.abstraction_required_irrigation_M3 +\
                                                                           self.var.PaddyRiceWaterAbstractionFromSurfaceWaterM3
            self.var.abstraction_allSources_actual_irrigation_M3Month += self.var.abstraction_SwGw_actual_irrigation_M3 +\
                                                                         self.var.abstraction_Reuse_irrigation_M3 +\
                                                                         self.var.PaddyRiceWaterAbstractionFromSurfaceWaterM3
            self.var.abstraction_SwGw_required_irrigation_M3Month += abstraction_SwGw_required_irrigation_M3 +\
                                                                     self.var.PaddyRiceWaterAbstractionFromSurfaceWaterM3
            self.var.abstraction_SwGw_actual_irrigation_M3Month += self.var.abstraction_SwGw_actual_irrigation_M3 +\
                                                                   self.var.PaddyRiceWaterAbstractionFromSurfaceWaterM3
        # ************************************************************
        # 18. E-flow indicator (CHECK: move it to indicatorcalc module?)
        # ************************************************************
        self.var.EFlowIndicator = (self.var.ChanQ < self.var.EFlowThreshold).astype(np.uint8)


#from numba import njit
#from builtins import max, min
#
#@njit
#def smoothLZ(in_LZ, neighbours_aquifer, counts, weight):
#    smoothed_LZ = in_LZ.copy()
#    for p in np.arange(in_LZ.size):
#        smoothed_LZ[p] = in_LZ[neighbours_aquifer[p,:counts[p]]].mean()
#    out_LZ = (1. - weight) * in_LZ + weight * smoothed_LZ
#    out_LZ -= weight * (smoothed_LZ.mean() - in_LZ.mean()) # correct total water balance
#    return out_LZ
#
#@njit
#def neighbours4GWsmooth(aquifer_mask, halfwidth):
#    rows, cols = np.where(aquifer_mask)
#    pixels = np.full(aquifer_mask.shape, -1)
#    for p in range(rows.size):
#        pixels[rows[p],cols[p]] = p
#    neighbours = np.full((rows.size, (1 + 2*halfwidth)**2), -1)
#    counts = np.zeros(rows.size, np.int64)
#    for p in range(rows.size):
#        win_rows = windowRange(rows[p], aquifer_mask.shape[0], halfwidth)
#        win_cols = windowRange(cols[p], aquifer_mask.shape[1], halfwidth)
#        for v in win_rows:
#            for h in win_cols:
#                if pixels[v,h] != -1:
#                    neighbours[p,counts[p]] = pixels[v,h]
#                    counts[p] += 1
#    return neighbours[:,:counts.max()], counts
#    
#@njit
#def windowRange(pix, dim_size, halfwidth):
#    return range(max(0, pix - halfwidth), min(dim_size, pix + halfwidth + 1))
