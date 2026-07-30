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
# warnings.formatwarning = lambda msg, args, *kwargs: f'{msg}\n'

import numpy as np
from ..global_modules.add1 import loadmap
from ..global_modules.settings import LisSettings, MaskInfo
from ..global_modules.errors import LisfloodWarning
from . import HydroModule


class waterstorage(HydroModule):
    """
    # ************************************************************
    # ***** WATER STORAGE    *************************************
    # ************************************************************
    # Sum up water storage in individual compartements 
    """
    input_files_keys = {
        'repTWSMaps': ['LakeExtent','ReservoirExtent'],
        'repStorageMaps': ['LakeExtent','ReservoirExtent']
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

            # Precompute lake extent masks and areas (static, don't change during simulation)
            self.var.lake_extent_masks = {}    # dict: lake_id -> pixel indices
            self.var.lake_extent_areas = {}    # dict: lake_id -> total grid area [m2]
            if option['simulateLakes']:
                self.var.LakeDistribution = loadmap('LakeExtent')
                lake_ids = np.unique(self.var.LakeDistribution[~np.isnan(self.var.LakeDistribution)]).astype(int)
                number_of_lakeIDs = len(lake_ids[lake_ids != 0])
                if (number_of_lakeIDs == 0):
                    warnings.warn(LisfloodWarning('LakeExtent map contains no lake IDs. Please check consistency between LakeExtent map and model domain.'))
                if self.var.LakeSitesCC.size != number_of_lakeIDs:
                    warnings.warn(LisfloodWarning('Number of lake IDs in map LakeExtent ('+str(number_of_lakeIDs)+') not equal to number of lake sites defined in map LakeSites ('+str(self.var.LakeSitesCC.size)+').'))
                lake_extent = self.var.LakeDistribution
                for n in np.unique(lake_extent[~np.isnan(lake_extent)]).astype(int):
                    if n != 0:
                        mask = np.nonzero(lake_extent == n)
                        self.var.lake_extent_masks[n] = mask
                        self.var.lake_extent_areas[n] = np.nansum(self.var.PixelArea[mask])

            # Precompute reservoir extent masks and areas (static)
            self.var.reservoir_extent_masks = {}
            self.var.reservoir_extent_areas = {}
            if option['simulateReservoirs']:
                self.var.ReservoirDistribution = loadmap('ReservoirExtent')
                res_ids = np.unique(self.var.ReservoirDistribution[~np.isnan(self.var.ReservoirDistribution)]).astype(int)
                number_of_reservoirIDs = len(res_ids[res_ids != 0])
                if (number_of_reservoirIDs == 0):
                    warnings.warn(LisfloodWarning('ReservoirExtent map contains no reservoir IDs. Please check consistency between ReservoirExtent map and model domain.'))
                if self.var.ReservoirSitesCC.size != number_of_reservoirIDs:
                    warnings.warn(LisfloodWarning('Number of reservoir IDs in map ReservoirExtent ('+str(number_of_reservoirIDs)+') not equal to number of reservoir sites defined in map ReservoirSites ('+str(self.var.ReservoirSitesCC.size)+').'))
                reservoir_extent = self.var.ReservoirDistribution
                for n in np.unique(reservoir_extent[~np.isnan(reservoir_extent)]).astype(int):
                    if n != 0:
                        mask = np.nonzero(reservoir_extent == n)
                        self.var.reservoir_extent_masks[n] = mask
                        self.var.reservoir_extent_areas[n] = np.nansum(self.var.PixelArea[mask])


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

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
            tws_riverM3 = self.var.TotalCrossSectionArea * self.var.ChanLength
            
            # [m3] -> [m]
            tws_riverM = tws_riverM3 / self.var.PixelArea
            
            # overlandflow water storage [m3]
            tws_oflowM3 = self.var.OFM3Direct + self.var.OFM3Forest + self.var.OFM3Other
            
            # [m3] -> [m]
            tws_oflowM = tws_oflowM3 / self.var.PixelArea
            
            # lake water storage [m3]
            tws_lakeM3 = np.zeros(tws_riverM3.shape, dtype=np.float32)
            # lake water storage [m]
            tws_lakeM = np.zeros(tws_riverM.shape, dtype=np.float32)

            if option['simulateLakes']:
                LakeArea = maskinfo.in_zero()
                np.put(LakeArea, self.var.LakeIndex, self.var.LakeAreaCC)
                tws_lakeM3 = self.var.LakeLevel * LakeArea

                # [m3] -> [m] distribute lake/river/oflow over lake areas
                for n, lake_mask in self.var.lake_extent_masks.items():
                    grid_area_lake = self.var.lake_extent_areas[n]
                    tws_lakeM[lake_mask] = tws_lakeM3[self.var.LakeSitesC2==n] / grid_area_lake
                    tws_riverM[lake_mask] = np.nansum(tws_riverM3[lake_mask]) / grid_area_lake
                    tws_oflowM[lake_mask] = np.nansum(tws_oflowM3[lake_mask]) / grid_area_lake
            
            # reservoir water storage [m3]
            tws_reservoirM3 = np.zeros(tws_riverM3.shape, dtype=np.float32)
            # reservoir water storage [m]
            tws_reservoirM = np.zeros(tws_riverM.shape, dtype=np.float32)

            if option['simulateReservoirs']:
                TotalReservoirStorage = maskinfo.in_zero()
                np.put(TotalReservoirStorage, self.var.ReservoirIndex, self.var.TotalReservoirStorageM3CC)
                tws_reservoirM3 = self.var.ReservoirFill * TotalReservoirStorage

                # [m3] -> [m] distribute reservoir/river/oflow over reservoir areas
                for n, reservoir_mask in self.var.reservoir_extent_masks.items():
                    grid_area_reservoir = self.var.reservoir_extent_areas[n]
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