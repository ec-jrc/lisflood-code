"""

Copyright 2019 European Union

Licensed under the EUPL, Version 1.2 or as soon they will be approved by the European Commission
subsequent versions of the EUPL (the "Licence");

You may not use this work except in compliance with the Licence.
You may obtain a copy of the Licence at:

https://joinup.ec.europa.eu/sites/default/files/inline-files/EUPL%20v1_2%20EN(1).txt

Unless required by applicable law or agreed to in writing,
software distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and limitations under the Licence.

"""

from __future__ import print_function, absolute_import
from nine import range

import warnings

from pcraster.operations import ifthen, boolean, defined, lookupscalar
import numpy as np

from ..global_modules.settings import LisSettings, MaskInfo
from ..global_modules.add1 import loadmap, compressArray, decompress, makenumpy
from ..global_modules.errors import LisfloodWarning
from . import HydroModule


class Reservoir(HydroModule):
    """
    The reservoir module simulates the behaviour of reservoirs within a hydrological model using
    the routine developed by Hanazaki et al. (2022).

    This module handles the initialization and dynamic simulation of reservoirs, accounting for
    inflow, outflow, and storage capacity. It includes functionality to model the effects of
    reservoirs on the flow regime, such as storage changes and flow regulation based on
    predefined operational rules.

    Attributes:
    -----------
        var (object): An object containing all the variables used within the reservoir module.

    Methods:
    --------
        initial(): Sets up the initial conditions and parameters for the reservoir simulation,
                   including reservoir locations, storage capacities, limits, and initial storage.
        dynamic_inloop(NoRoutingExecuted: int): Performs dynamic calculations within the routing
                   loop to simulate inflow, storage, and controlled outflow from the reservoirs.

    Referenecs:
    -----------
    Hanazaki, R., Yamazaki, D., Yoshimura, K.: Development of a Reservoir Flood Control Scheme for
    Global Flood Models, Journal of Advances in Modeling Earth Systems, 14,
    https://doi.org/10.1029/2021MS002944, 2022.
    """
    
    input_files_keys = {
        'simulateReservoirs': [
            'ReservoirSites', 'ReservoirTotalStorage', # reservoir characteristics
            'ReservoirMinOutflow', 'ReservoirNormalOutflow', 'ReservoirFloodOutflow', # release attributes
            'ReservoirFloodStorage', 'ReservoirFloodOutflowFactor', # calibration parameters
            'ReservoirInitialFill', # initial conditions
    ]}
    
    module_name = 'Reservoir'

    def __init__(self, reservoir_variable):
        """
        Initializes the reservoir module with a given variable object.

        Parameters:
        -----------
        reservoir_variable: object
            An object containing the variables needed for the reservoir simulation.
        """

        self.var = reservoir_variable
        
    def initial(self):
        """
        Initiates the reservoir module by loading the necessary data and maps, setting up the
        reservoir characteristics (e.g., storage capacities, flow limits), and determining
        initial fill levels. Issues a warning if no reservoirs are present in the simulation.
        """
        
        settings = LisSettings.instance()
        option = settings.options
        binding = settings.binding
        maskinfo = MaskInfo.instance()
        if option['simulateReservoirs']:
            # load reservoir locations and keep only those on the channel network
            reservoirs = loadmap('ReservoirSites')                  # moved here to use the caching feature during calibration
            reservoirs[(reservoirs < 1) | (self.var.IsChannel == 0)] = 0
            self.var.ReservoirSitesC = reservoirs
            self.var.ReservoirSitesCC = np.compress(reservoirs > 0, reservoirs)
            self.var.ReservoirIndex = np.nonzero(reservoirs)[0]

            # check whether there are reservoirs in the simulation
            if self.var.ReservoirSitesCC.size == 0:
                warnings.warn(LisfloodWarning('There are no reservoirs. Reservoirs simulation won\'t run'))
                option['simulateReservoirs'] = False
                option['repsimulateReservoirs'] = False
                # rebuild lists of reported files with simulateReservoirs and repsimulateReservoirs = False
                settings.build_reportedmaps_dicts()
                return
            ReservoirSitePcr = loadmap('ReservoirSites', pcr=True)    # moved here to use the caching feature during calibration

        if option['simulateReservoirs'] and not option['InitLisflood']:
            
            # Add reservoir locations to structures map 
            # (used to modify LddKinematic and to calculate LddStructuresKinematic)
            self.var.IsStructureKinematic = np.where(self.var.ReservoirSitesC > 0, np.bool8(1), self.var.IsStructureKinematic)
            # Add reservoir locations to structures map (used to modify LddKinematic
            # and to calculate LddStructuresKinematic)
            self.var.IsStructureChan = np.where(self.var.ReservoirSitesC > 0, np.bool8(1), self.var.IsStructureChan)
            # Add reservoir locations to structures map (used to modify LddChan
            # and to calculate LddStructuresChan)
            
            self.var.ReservoirSites = ReservoirSitePcr
            # filter out reservoirs that are not part of the channel network
            # (following logic of 'old' code the inflow into these reservoirs is
            # always zero, so either change this or leave them out!)
            ReservoirSitePcr = ifthen((defined(ReservoirSitePcr) & boolean(decompress(self.var.IsChannel))), ReservoirSitePcr)
            
            # RESERVOIR CHARACTERISTICS
            
            # reservoir storage capacity [m3]
            total_storage = lookupscalar(str(binding['ReservoirTotalStorage']), ReservoirSitePcr)
            total_storage = compressArray(total_storage)
            self.var.TotalReservoirStorageM3C = np.where(np.isnan(total_storage), 0, total_storage)
            self.var.TotalReservoirStorageM3CC = np.compress(self.var.ReservoirSitesC > 0, self.var.TotalReservoirStorageM3C)
            
            # reservoir catchment area [m2]
            catchment_area = loadmap('UpAreaTrans')
            catchment_area = makenumpy(catchment_area)
            self.var.CatchmentAreaM2 = np.compress(self.var.ReservoirSitesC > 0, catchment_area)
            
            # MODEL PARAMETERS

            # flood storage limit (fraction of total storage [-])
            if str(binding['ReservoirFloodStorage']).endswith('txt'):
                flood_storage = lookupscalar(str(binding['ReservoirFloodStorage']), ReservoirSitePcr)
                flood_storage = compressArray(flood_storage)
            else:
                flood_storage = loadmap('ReservoirFloodStorage')
                flood_storage = makenumpy(flood_storage)
            self.var.FloodStorageLimit = np.compress(self.var.ReservoirSitesC > 0, flood_storage)

            # factor of the flood outflow
            if str(binding['ReservoirFloodOutflowFactor']).endswith('txt'):
                factor_outflow = lookupscalar(str(binding['ReservoirFloodOutflowFactor']), ReservoirSitePcr)
                factor_outflow = compressArray(factor_outflow)
            else:
                factor_outflow = loadmap('ReservoirFloodOutflowFactor')
                factor_outflow = makenumpy(factor_outflow)
            factor_outflow = np.where(factor_outflow <= 0, 0.3, factor_outflow)
            factor_outflow = np.compress(self.var.ReservoirSitesC > 0, factor_outflow)

            # STORAGE LIMITS
            
            # emergency storage limit (fraction of total storage [-])
            # the upper 20% of the flood storage capacicty
            self.var.EmergencyStorageLimit = 0.8 + 0.2 * self.var.FloodStorageLimit 
            
            # conservative storage limit (fraction of total storage [-])
            # 50% of the water use capacity
            self.var.ConservativeStorageLimit = 0.5 * self.var.FloodStorageLimit 
            
            # RELEASE ATTRIBUTES
            
            # minimum reservoir outflow [m3/s]
            MinReservoirOutflow = lookupscalar(str(binding['ReservoirMinOutflow']), ReservoirSitePcr)
            MinReservoirOutflowC = compressArray(MinReservoirOutflow)
            self.var.MinReservoirOutflow = np.compress(self.var.ReservoirSitesC > 0, MinReservoirOutflowC)
            
            # normal outflow [m3/s]
            normal_outflow = lookupscalar(str(binding['ReservoirNormalOutflow']), ReservoirSitePcr)
            normal_outflow = compressArray(normal_outflow)
            self.var.NormalReservoirOutflow = np.compress(self.var.ReservoirSitesC > 0, normal_outflow)
            
            # flood-control outflow [m3/s]
            flood_outflow = lookupscalar(str(binding['ReservoirFloodOutflow']), ReservoirSitePcr)
            flood_outflow = compressArray(flood_outflow)
            flood_outflow = np.compress(self.var.ReservoirSitesC > 0, flood_outflow)
            self.var.FloodReservoirOutflow = np.maximum(self.var.NormalReservoirOutflow, factor_outflow * flood_outflow)
            
            # INITIAL CONDITIONS
            
            # initial reservoir fill (fraction of total storage, [-]) 
            # -9999: assume reservoirs are filled to 80% of the flood storage limit
            initial_fill = loadmap('ReservoirInitialFill')
            if np.max(initial_fill) == -9999:
                initial_fill = 0.8 * self.var.FloodStorageLimit,
            else:
                initial_fill = np.compress(self.var.ReservoirSitesC > 0, initial_fill)
            self.var.ReservoirFillCC = initial_fill
            
            # initial reservoir storage [m3]
            initial_storage = initial_fill * self.var.TotalReservoirStorageM3CC
            self.var.ReservoirStorageM3CC = initial_storage.copy()
            self.var.ReservoirStorageIniM3 = maskinfo.in_zero()
            np.put(self.var.ReservoirStorageIniM3, self.var.ReservoirIndex, initial_storage)
            
            # update storage [m3]
            self.var.ReservoirStorageM3 = self.var.ReservoirStorageIniM3

    def dynamic_inloop(self, NoRoutingExecuted: int):
        """
        Performs the dynamic simulation of reservoirs within the routing loop. This method updates
        inflows, storage, and outflows for each reservoir based on the current timestep's flow
        conditions. It also handles the transition between different storage zones of the reservoir
        and applies the operational rules for outflow regulation.

        Parameters:
        -----------
        NoRoutingExecuted: integer
            The number of routing sub-steps that have been executed. This parameter is used to manage
            the accumulation of inflow and outflow over the routing steps.
        """

        settings = LisSettings.instance()
        option = settings.options
        maskinfo = MaskInfo.instance()
        
        if option['simulateReservoirs'] and not option['InitLisflood']:
            ReservoirStorageM3CC_init = np.compress(self.var.ReservoirSitesC > 0, self.var.ReservoirStorageM3)
            # Storage volume [m3] at the beginning of the sub-step (routing sub-step)

            InvDtSecDay = 1 / float(86400)
            # InvDtSecDay=self.var.InvDtSec
            
            # storage limits
            conservative_fill = self.var.ConservativeStorageLimit
            flood_fill = self.var.FloodStorageLimit
            emergency_fill = self.var.EmergencyStorageLimit

            # representative outflows
            min_outflow = self.var.MinReservoirOutflow
            normal_outflow = self.var.NormalReservoirOutflow
            conservative_outflow = normal_outflow * conservative_fill / flood_fill
            flood_outflow = self.var.FloodReservoirOutflow

            # reservoir inflow in [m3/s]
            # (LddStructuresKinematic equals LddKinematic, but without the pits/sinks upstream of the structure
            # locations; note that using Ldd here instead would introduce MV!)
            inflow = np.bincount(self.var.downstruct, weights=self.var.ChanQAvgDt)[self.var.ReservoirIndex]

            # Reservoir inflow in [m3] per timestep (routing sub-step)
            inflow_m3 = inflow * self.var.DtRouting
            
            # flood event
            inflow_mask = inflow >= flood_outflow

            # current reservoir storage [m3]
            if NoRoutingExecuted == 0:
                self.var.ReservoirStorageM3CC = np.compress(self.var.ReservoirSitesC > 0, self.var.ReservoirStorageM3)

            # release coefficient
            self.var.k = np.maximum(1 - (self.var.TotalReservoirStorageM3CC - self.var.ReservoirStorageM3CC) / (self.var.CatchmentAreaM2 * 0.2), 0)

            # update reservoir storage [m3] and filling [-]
            self.var.ReservoirStorageM3CC += inflow_m3
            self.var.ReservoirFillCC = self.var.ReservoirStorageM3CC / self.var.TotalReservoirStorageM3CC
            
            # outflow [m3/s]
            outflow = np.minimum(min_outflow, self.var.ReservoirStorageM3CC * InvDtSecDay)
            # conservative zone
            outflow = np.where(
                self.var.ReservoirFillCC <= conservative_fill,
                normal_outflow * self.var.ReservoirFillCC / flood_fill,
                outflow
            )
            # normal zone and NO flood inflow
            outflow = np.where(
                (self.var.ReservoirFillCC > conservative_fill) & (self.var.ReservoirFillCC <= emergency_fill) & ~inflow_mask,
                conservative_outflow + ((self.var.ReservoirFillCC - conservative_fill) / (emergency_fill - conservative_fill))**2 * (flood_outflow - normal_outflow * conservative_fill / flood_fill),
                outflow
            )
            # normal zone and flood inflow
            outflow = np.where(
                (self.var.ReservoirFillCC > conservative_fill) & (self.var.ReservoirFillCC <= flood_fill) & inflow_mask,
                conservative_outflow + (self.var.ReservoirFillCC - conservative_fill) / (flood_fill - conservative_fill) * (flood_outflow - conservative_outflow),
                outflow
            )
            # flood zone and flood inflow
            outflow = np.where(
                (self.var.ReservoirFillCC > flood_fill) & (self.var.ReservoirFillCC <= emergency_fill) & inflow_mask,
                flood_outflow + self.var.k * (self.var.ReservoirFillCC - flood_fill) / (emergency_fill - flood_fill) * (inflow - flood_outflow),
                outflow
            )
            # emergency zone and NO flood inflow
            outflow = np.where(
                (self.var.ReservoirFillCC > emergency_fill) & ~inflow_mask,
                flood_outflow,
                outflow
            )
            # emergency zone and flood inflow
            outflow = np.where(
                (self.var.ReservoirFillCC > emergency_fill) & inflow_mask,
                inflow,
                outflow
            )
            
            # reservoir outflow in [m3] per sub step
            outflow_m3 = outflow * self.var.DtRouting
            # make sure the outflow is as much as the available water, and that the reservoir doesn't exceed its capacity
            outflow_m3 = np.minimum(outflow_m3, self.var.ReservoirStorageM3CC)
            outflow_m3 = np.maximum(outflow_m3, self.var.ReservoirStorageM3CC - self.var.TotalReservoirStorageM3CC)
            
            # update reservoir storage [m3] and filling [-]
            self.var.ReservoirStorageM3CC -= outflow_m3

            # Check ReservoirStorageM3CC for negative values and set them to zero, then update the outflow
            if any(self.var.ReservoirStorageM3CC < 0):
                warnings.warn(LisfloodWarning("WARNING! ReservoirStorageM3CC contains negative values."))
                self.var.ReservoirStorageM3CC[self.var.ReservoirStorageM3CC < 0] = 0
                outflow_m3 = ReservoirStorageM3CC_init + inflow_m3 - self.var.ReservoirStorageM3CC

            self.var.ReservoirFillCC = self.var.ReservoirStorageM3CC / self.var.TotalReservoirStorageM3CC

            # expanding the size as input for routing routine
            # this is released to the channel again at each sub timestep
            self.var.QResOutM3Dt = maskinfo.in_zero()
            np.put(self.var.QResOutM3Dt, self.var.ReservoirIndex, outflow_m3)
            
            if option['repsimulateReservoirs']:
                # inflow and outflow to the reservoir is sumed up over the sub timesteps and stored in m/s
                if NoRoutingExecuted == 0:
                    # set to zero at first timestep
                    self.var.ReservoirInflowM3S = maskinfo.in_zero()
                    self.var.ReservoirOutflowM3S = maskinfo.in_zero()
                    self.var.sumResInCC = inflow_m3
                    self.var.sumResOutCC = outflow_m3
                else:
                    self.var.sumResInCC += inflow_m3
                    self.var.sumResOutCC += outflow_m3

            if NoRoutingExecuted == (self.var.NoRoutSteps - 1):

                # expanding the size after last sub timestep
                self.var.ReservoirStorageM3 = maskinfo.in_zero()
                self.var.ReservoirFill = maskinfo.in_zero()
                np.put(self.var.ReservoirStorageM3, self.var.ReservoirIndex, self.var.ReservoirStorageM3CC)
                np.put(self.var.ReservoirFill, self.var.ReservoirIndex, self.var.ReservoirFillCC)

                if option['repsimulateReservoirs']:
                    np.put(self.var.ReservoirInflowM3S, self.var.ReservoirIndex, self.var.sumResInCC / self.var.DtSec)
                    np.put(self.var.ReservoirOutflowM3S, self.var.ReservoirIndex, self.var.sumResOutCC / self.var.DtSec)