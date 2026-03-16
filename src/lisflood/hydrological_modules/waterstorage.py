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

import warnings
warnings.formatwarning = lambda msg, args, *kwargs: f'{msg}\n'

import numpy as np
from ..global_modules.add1 import loadmap
from ..global_modules.settings import LisSettings, MaskInfo
from ..global_modules.errors import LisfloodError, LisfloodWarning
from . import HydroModule


class waterstorage(HydroModule):
    """
    # ************************************************************
    # ***** WATER STORAGE    *************************************
    # ************************************************************
    # Sum up water storage in individual compartements 
    """
    input_files_keys = {
        'repTWSMaps': ['LakeMask'],
        'repStorageMaps': ['LakeMask']
    }
    module_name = 'WaterStorage'

    def __init__(self, waterstorage_variable):
        self.var = waterstorage_variable

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the water storage module
        """

        # ************************************************************
        # ***** WATER STORAGE INIT
        # ************************************************************
        settings = LisSettings.instance()
        option = settings.options
        
        # load water map and separate into maps of lake and reservoir distribution
        if (not(option['InitLisflood'])) and (option['repStorageMaps'] or option['repTWSMaps']):

            LakeMask = loadmap('LakeMask')
            # find ranges of IDs for lakes [LakeID_min+1:LakeID_max] and reservoirs [ReservoirID_min+1:ReservoirID_max]
            # LakeMask   land       = 0
            #            water      = 1
            #                         or for lakes:      ID = LakeID_min + lakeID
            #                                reservoirs: ID = ReservoirID_min + reservoirID
            #                         in case LakeMask == 0 (no water defined before insertion of lake-/reservoir-IDs)
            #                         lake and reservoirs IDs are inserted with negative values
            LakeMask[LakeMask<=-9999] = np.nan
            LakeMask = np.abs(LakeMask)

            LakeID_min = 100000
            LakeID_max = 500000
            ReservoirID_min = 500000

            # extract lake distribution map
            self.var.LakeDistribution = np.where((LakeMask > LakeID_min) & (LakeMask < LakeID_max), LakeMask-LakeID_min, np.nan)
            # extract reservoir distribution map
            self.var.ReservoirDistribution = np.where((LakeMask > ReservoirID_min), LakeMask-ReservoirID_min, np.nan)

            # check number of ID with number of sites
            number_of_lakeIDs = len(
                np.unique(self.var.LakeDistribution[~np.isnan(self.var.LakeDistribution)]).astype(int))
            number_of_reservoirIDs = len(
                np.unique(self.var.ReservoirDistribution[~np.isnan(self.var.ReservoirDistribution)]).astype(int))
            if (number_of_lakeIDs < 1) | (number_of_reservoirIDs < 1):
                msg = "LakeMask map (containing no lake or reservoir IDs) not compatible for TWS calculation"
                raise LisfloodError(msg)
            if option['simulateLakes']:
                if self.var.LakeSitesCC.size != number_of_lakeIDs:
                    warnings.warn(LisfloodWarning('Number of lake IDs in map LakeMask ('+str(number_of_lakeIDs)+') not equal number of lake sites defined in map LakeSites ('+str(self.var.LakeSitesCC.size)+').'))
            if option['simulateReservoirs']:
                if self.var.ReservoirSitesCC.size != number_of_reservoirIDs:
                    warnings.warn(LisfloodWarning('Number of reservoir IDs in map LakeMask ('+str(number_of_reservoirIDs)+') not equal number of reservoir sites defined in map ReservoirSites ('+str(self.var.ReservoirSitesCC.size)+').'))


# --------------------------------------------------------------------------
# -------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the water storage module
        """
        settings = LisSettings.instance()
        option = settings.options
        maskinfo = MaskInfo.instance()
            
        
        if (not(option['InitLisflood'])) and (option['repStorageMaps'] or option['repTWSMaps']):

            # ************************************************************
            # ***** WATER STORAGE 
            # ************************************************************
            
            # river water storage [m3]
            # in routing.py: *** initial river storage is stored in
            #                    self.var.ChanM3 = self.var.TotalCrossSectionArea * self.var.ChanLength
            #                    self.var.ChanIniM3 = self.var.ChanM3.copy()
            #                    self.var.ChanM3Kin = self.var.ChanIniM3.copy().astype(float)
            #                *** split routing
            #                    self.var.Chan2M3Kin = self.var.CrossSection2Area * self.var.ChanLength + self.var.Chan2M3Start
            #                    self.var.ChanM3Kin = self.var.ChanM3 - self.var.Chan2M3Kin + self.var.Chan2M3Start
            #                *** Volume in main channel at end of computation step
            #                    self.var.ChanM3Kin = self.var.ChanLength * self.var.ChannelAlpha * self.var.ChanQKin**self.var.Beta
            #                *** floodplain routing
            #                    self.var.Chan2M3Kin = self.var.ChanLength * self.var.ChannelAlpha2 * self.var.Chan2QKin ** self.var.Beta
            #                    self.var.CrossSection2Area = (self.var.Chan2M3Kin - self.var.Chan2M3Start) * self.var.InvChanLength  
            #                    TotalCrossSectionArea = np.maximum(self.var.ChanM3Kin*self.var.InvChanLength,0.01)
            # in Lisflood_dynamic.py:
            #                *** add main channel and floodplains
            #                    self.ChanM3 = self.ChanM3Kin + selfChan2M3Kin - self.Chan2M3Start
            #                    self.TotalCrossSectionArea = self.ChanM3 * self.InvChanLength            
            #tws_riverM3 = self.var.ChanM3.copy() ?
            tws_riverM3 = self.var.TotalCrossSectionArea * self.var.ChanLength
            
            # [m3] -> [m]
            tws_riverM = tws_riverM3 / self.var.PixelArea
            
            # overlandflow water storage [m3]
            # in surface_routing.py: self.var.M3all = self.var.OFM3Direct + self.var.OFM3Other + self.var.OFM3Forest
            tws_oflowM3 = self.var.OFM3Direct + self.var.OFM3Forest + self.var.OFM3Other
            
            # [m3] -> [m]
            tws_oflowM = tws_oflowM3 / self.var.PixelArea
            
            # lake water storage [m3]
            # in lakes.py: LakeSitesC = loadmap('LakeSites')
            #              LakeSitesC[LakeSitesC < 1] = 0
            #              LakeSitesC[self.var.IsChannel == 0] = 0
            #              self.var.LakeSitesC2 = LakeSitesC 
            #
            #              LakeArea = pcraster.lookupscalar(str(binding['TabLakeArea']), LakeSitePcr)
            #              LakeAreaC = compressArray(LakeArea)
            #              self.var.LakeAreaCC = np.compress(LakeSitesC > 0, LakeAreaC)
            #
            #              self.var.LakeStorageM3CC = (LakeStorageIndicator - self.var.LakeOutflowCC* 0.5) * self.var.DtRouting
            #              self.var.LakeStorageM3CC[self.var.LakeStorageM3CC < 0] = 0
            #              self.var.LakeStorageM3CC[np.isnan(self.var.LakeStorageM3CC)] = 0
            #              self.var.LakeStorageM3BalanceCC += LakeIn * self.var.DtRouting - QLakeOutM3DtCC
            #              self.var.LakeLevelCC = self.var.LakeStorageM3CC / self.var.LakeAreaCC
            #
            #              self.var.LakeStorageM3Balance = maskinfo.in_zero()
            #              self.var.LakeStorageM3 = maskinfo.in_zero()
            #              self.var.LakeLevel = maskinfo.in_zero()
            #              np.put(self.var.LakeStorageM3Balance, self.var.LakeIndex, self.var.LakeStorageM3BalanceCC)
            #              np.put(self.var.LakeStorageM3, self.var.LakeIndex, self.var.LakeStorageM3CC)
            #              np.put(self.var.LakeLevel, self.var.LakeIndex, self.var.LakeLevelCC)
            tws_lakeM3 = np.zeros(tws_riverM3.shape, dtype=np.float32)
            if option['simulateLakes']:
                #tws_lakeM3  = self.var.LakeStorageM3.copy() ? 
                #tws_lakeM3  = self.var.LakeStorageM3Balance ?
                LakeArea = maskinfo.in_zero()
                np.put(LakeArea, self.var.LakeIndex, self.var.LakeAreaCC)
                tws_lakeM3 = self.var.LakeLevel * LakeArea
                
            # [m3] -> [m] distribute lake/river/oflow over lake areas 
            tws_lakeM = np.zeros(tws_riverM.shape, dtype=np.float32)
            lake_extent = self.var.LakeDistribution
            for n in np.unique(lake_extent[~np.isnan(lake_extent)]).astype(int):
                if n > 0:
                    lake_mask = np.nonzero(lake_extent == n)
                    if option['simulateLakes']:
                        grid_area_lake = np.nansum(self.var.PixelArea[lake_mask])
                        tws_lakeM[lake_mask] = tws_lakeM3[self.var.LakeSitesC2==n] / grid_area_lake
                        tws_riverM[lake_mask] = np.nansum(tws_riverM3[lake_mask]) / grid_area_lake
                        tws_oflowM[lake_mask] = np.nansum(tws_oflowM3[lake_mask]) / grid_area_lake
            
            # reservoir water storage [m3]
            # in routing.py: self.var.IsChannelPcr = boolean(loadmap('Channels', pcr=True))
            #                self.var.IsChannel = np.bool8(compressArray(self.var.IsChannelPcr))
            #
            # in reservoir.py: self.var.ReservoirSitesC = loadmap('ReservoirSites')
            #                  self.var.ReservoirSitesC[self.var.ReservoirSitesC < 1] = 0
            #                  self.var.ReservoirSitesC[self.var.IsChannel == 0] = 0
            #
            #                  TotalReservoirStorageM3 = lookupscalar(str(binding['TabTotStorage']), ReservoirSitePcr)
            #                  self.var.TotalReservoirStorageM3C = compressArray(TotalReservoirStorageM3)
            #                  self.var.TotalReservoirStorageM3C = np.where(np.isnan(self.var.TotalReservoirStorageM3C), 0, self.var.TotalReservoirStorageM3C)
            #                  self.var.TotalReservoirStorageM3CC = np.compress(self.var.ReservoirSitesC > 0, self.var.TotalReservoirStorageM3C)
            #
            #                  self.var.ReservoirStorageM3CC -= QResOutM3DtCC
            #                  self.var.ReservoirFillCC = self.var.ReservoirStorageM3CC / self.var.TotalReservoirStorageM3CC
            #                  self.var.ReservoirFillCC[np.isnan(self.var.ReservoirFillCC)] = 0
            #                  self.var.ReservoirFillCC[self.var.ReservoirFillCC < 0] = 0
            #
            #                  self.var.ReservoirStorageM3 = maskinfo.in_zero()
            #                  self.var.ReservoirFill = maskinfo.in_zero()
            #                  np.put(self.var.ReservoirStorageM3, self.var.ReservoirIndex, self.var.ReservoirStorageM3CC)
            #                  np.put(self.var.ReservoirFill, self.var.ReservoirIndex, self.var.ReservoirFillCC)
            tws_reservoirM3 = np.zeros(tws_riverM3.shape, dtype=np.float32)
            if option['simulateReservoirs']:  
                #tws_reservoirM3  = self.var.ReservoirStorageM3.copy() ?
                TotalReservoirStorage = maskinfo.in_zero()
                np.put(TotalReservoirStorage, self.var.ReservoirIndex, self.var.TotalReservoirStorageM3CC)
                tws_reservoirM3 = self.var.ReservoirFill * TotalReservoirStorage
            
            # [m3] -> [m] distribute reservoir/river/oflow over reservoir areas 
            tws_reservoirM = np.zeros(tws_riverM.shape, dtype=np.float32)
            reservoir_extent = self.var.ReservoirDistribution
            for n in np.unique(reservoir_extent[~np.isnan(reservoir_extent)]).astype(int):
                if n > 0:
                    reservoir_mask = np.nonzero(reservoir_extent == n)
                    if option['simulateReservoirs']:  
                        grid_area_reservoir = np.nansum(self.var.PixelArea[reservoir_mask])
                        tws_reservoirM[reservoir_mask] = tws_reservoirM3[self.var.ReservoirSitesC==n] / grid_area_reservoir
                        tws_riverM[reservoir_mask] = np.nansum(tws_riverM3[reservoir_mask]) / grid_area_reservoir
                        tws_oflowM[reservoir_mask] = np.nansum(tws_oflowM3[reservoir_mask]) / grid_area_reservoir
         
            # soil water storage [mm] -> [m]
            tws_soil1M  = ((self.var.Theta1a[0] * self.var.SoilDepth1a[0]) * self.var.OtherFraction     +
                          (self.var.Theta1a[1] * self.var.SoilDepth1a[1]) * self.var.ForestFraction    +
                          (self.var.Theta1a[2] * self.var.SoilDepth1a[2]) * self.var.IrrigationFraction
                         ) / 1000

            tws_soil2M  = ((self.var.Theta1b[0] * self.var.SoilDepth1b[0]) * self.var.OtherFraction     +
                         (self.var.Theta1b[1] * self.var.SoilDepth1b[1]) * self.var.ForestFraction    +
                         (self.var.Theta1b[2] * self.var.SoilDepth1b[2]) * self.var.IrrigationFraction
                        ) / 1000

            tws_soil3M  = ((self.var.Theta2[0] * self.var.SoilDepth2[0]) * self.var.OtherFraction     +
                          (self.var.Theta2[1] * self.var.SoilDepth2[1]) * self.var.ForestFraction    +
                          (self.var.Theta2[2] * self.var.SoilDepth2[2]) * self.var.IrrigationFraction
                        ) / 1000

            tws_soilM = tws_soil1M + tws_soil2M + tws_soil3M
                                  
            # groundwater storage [mm] -> [m], (uz,uzf,uzi,lz,fracforest,fracirrigated,fracother)
            tws_groundwaterM = ( self.var.UZ[0] * self.var.OtherFraction      + 
                                 self.var.UZ[1] * self.var.ForestFraction     +
                                 self.var.UZ[2] * self.var.IrrigationFraction +
                                 self.var.LZ  
                               ) / 1000
                               
            # snow storage [m]
            tws_snowM = self.var.SnowCover / 1000
            
            # cumulative interception storage [mm] and cumulative depression storage [mm] -> [m]
            tws_cumM = ( self.var.CumInterception[0] * self.var.OtherFraction       +
                         self.var.CumInterception[1] * self.var.ForestFraction      +
                         self.var.CumInterception[2] * self.var.IrrigationFraction  +
                         self.var.CumInterSealed  * self.var.DirectRunoffFraction
                       ) / 1000

            # total water storage maps
            self.var.riverstor     = tws_riverM + tws_oflowM
            self.var.lakestor      = tws_lakeM + tws_reservoirM
            self.var.soilstor      = tws_soilM
            self.var.gwstor        = tws_groundwaterM
            self.var.snowstor      = tws_snowM
            self.var.cumstor       = tws_cumM
            self.var.twsstor       = tws_riverM + tws_oflowM + tws_lakeM + tws_reservoirM + tws_soilM + tws_groundwaterM + tws_snowM + tws_cumM
                      
