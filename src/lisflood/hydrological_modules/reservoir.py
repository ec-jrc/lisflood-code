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
    The reservoir module simulates the behavior of reservoirs within a hydrological model.

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
    """
    
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
        
        raise NotImplementedError('Subclasses should implemente this!')

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

        raise NotImplementedError('Subclasses should implemente this!')

        
class Burek(Reservoir):
    
    input_files_keys = {
        'simulateReservoirs': [
            'ReservoirSites', 'TabTotStorage', # reservoir characteristics
            'TabConservativeStorageLimit', 'TabNormalStorageLimit', 'TabFloodStorageLimit', # storage limits
            'TabMinOutflow', 'TabNormalOutflow', 'TabFloodOutflow', # release attributes
            'adjust_Normal_Flood', 'ReservoirRnormqMult', # calibration parameters
             'ReservoirInitialFillValue' # initial conditions
        ]}

    def initial(self):
        """
        Initiates the reservoir module by loading the necessary data and maps, setting up the
        reservoir characteristics (e.g., storage capacities, flow limits), and determining
        initial fill levels. Issues a warning if no reservoirs are present in the simulation.
        """
        
        settings = LisSettings.instance()
        option = settings.options
        maskinfo = MaskInfo.instance()
        if option['simulateReservoirs'] and not option['InitLisflood']:

            # NoSubStepsRes=max(1,roundup(self.var.DtSec/loadmap('DtSecReservoirs')))
            # Number of sub-steps based on value of DtSecReservoirs,
            # or 1 if DtSec is smaller than DtSecReservoirs
            # DtSubRes=self.var.DtSec/loadmap('NoSubStepsRes')
            # Corresponding sub-timestep (seconds)
            binding = settings.binding

            # load reservoir locations and keep only those on the channel network
            self.var.ReservoirSitesC = loadmap('ReservoirSites')
            self.var.ReservoirSitesC[self.var.ReservoirSitesC < 1] = 0
            self.var.ReservoirSitesC[self.var.IsChannel == 0] = 0
            self.var.ReservoirSitesCC = np.compress(self.var.ReservoirSitesC > 0, self.var.ReservoirSitesC)

            # check whether there are reservoirs in the simulation
            if self.var.ReservoirSitesCC.size == 0:
                warnings.warn(LisfloodWarning('There are no reservoirs. Reservoirs simulation won\'t run'))
                option['simulateReservoirs'] = False
                option['repsimulateReservoirs'] = False
                # rebuild lists of reported files with simulateReservoirs and repsimulateReservoirs = False
                settings.build_reportedmaps_dicts()
                return
            self.var.ReservoirIndex = np.nonzero(self.var.ReservoirSitesC)[0]
            
            # Add reservoir locations to structures map 
            # (used to modify LddKinematic and to calculate LddStructuresKinematic)
            self.var.IsStructureKinematic = np.where(self.var.ReservoirSitesC > 0, np.bool8(1), self.var.IsStructureKinematic)
            
            # load reservoirs in PCRaster
            ReservoirSitePcr = loadmap('ReservoirSites', pcr=True)
            self.var.ReservoirSites = ReservoirSitePcr
            # filter out reservoirs that are not part of the channel network
            # (following logic of 'old' code the inflow into these reservoirs is
            # always zero, so either change this or leave them out!)
            ReservoirSitePcr = ifthen((defined(ReservoirSitePcr) & boolean(decompress(self.var.IsChannel))), ReservoirSitePcr)
            
            # RESERVOIR CHARACTERISTICS
            
            # reservoir storage capacity [m3]
            TotalReservoirStorageM3 = lookupscalar(str(binding['TabTotStorage']), ReservoirSitePcr)
            self.var.TotalReservoirStorageM3C = compressArray(TotalReservoirStorageM3)
            self.var.TotalReservoirStorageM3C = np.where(np.isnan(self.var.TotalReservoirStorageM3C), 0, self.var.TotalReservoirStorageM3C)
            self.var.TotalReservoirStorageM3CC = np.compress(self.var.ReservoirSitesC > 0, self.var.TotalReservoirStorageM3C)
            
            # conservative storage limit (fraction of total storage, [-])
            ConservativeStorageLimit = lookupscalar(str(binding['TabConservativeStorageLimit']), ReservoirSitePcr)
            ConservativeStorageLimitC = compressArray(ConservativeStorageLimit)
            self.var.ConservativeStorageLimitCC = np.compress(self.var.ReservoirSitesC > 0, ConservativeStorageLimitC)
            
            # normal storage limit (fraction of total storage, [-])
            NormalStorageLimit = lookupscalar(str(binding['TabNormalStorageLimit']), ReservoirSitePcr)
            NormalStorageLimitC = compressArray(NormalStorageLimit)
            self.var.NormalStorageLimitCC = np.compress(self.var.ReservoirSitesC > 0, NormalStorageLimitC)
            
            # flood storage limit (fraction of total storage, [-])
            FloodStorageLimit = lookupscalar(str(binding['TabFloodStorageLimit']), ReservoirSitePcr)
            FloodStorageLimitC = compressArray(FloodStorageLimit)
            self.var.FloodStorageLimitCC = np.compress(self.var.ReservoirSitesC > 0, FloodStorageLimitC)
            
            # non-damaging reservoir outflow [m3/s]
            NonDamagingReservoirOutflow = lookupscalar(str(binding['TabFloodOutflow']), ReservoirSitePcr)
            NonDamagingReservoirOutflowC = compressArray(NonDamagingReservoirOutflow)
            self.var.NonDamagingReservoirOutflowCC = np.compress(self.var.ReservoirSitesC > 0, NonDamagingReservoirOutflowC)
            
            # Normal reservoir outflow [m3/s]
            NormalReservoirOutflow = lookupscalar(str(binding['TabNormalOutflow']), ReservoirSitePcr)
            NormalReservoirOutflowC = compressArray(NormalReservoirOutflow)
            self.var.NormalReservoirOutflowCC = np.compress(self.var.ReservoirSitesC > 0, NormalReservoirOutflowC)
            
            # minimum reservoir outflow [m3/s]
            MinReservoirOutflow = lookupscalar(str(binding['TabMinOutflow']), ReservoirSitePcr)
            MinReservoirOutflowC = compressArray(MinReservoirOutflow)
            self.var.MinReservoirOutflowCC = np.compress(self.var.ReservoirSitesC > 0, MinReservoirOutflowC)
            
            # RESERVOIR MODEL PARAMETERS
            
            # adjuste normal storage limit
            adjust_Normal_Flood = loadmap('adjust_Normal_Flood')
            adjust_Normal_FloodC = makenumpy(adjust_Normal_Flood)
            adjust_Normal_FloodCC = np.compress(self.var.ReservoirSitesC > 0, adjust_Normal_FloodC)
            self.var.AdjNormalStorageLimitCCCC = self.var.NormalStorageLimitCC + adjust_Normal_FloodCC * (self.var.FloodStorageLimitCC - self.var.NormalStorageLimitCC)
            
            # adjusted normal outflow
            ReservoirRnormqMult = loadmap('ReservoirRnormqMult')
            ReservoirRnormqMultC = makenumpy(ReservoirRnormqMult)
            ReservoirRnormqMultCC = np.compress(self.var.ReservoirSitesC > 0, ReservoirRnormqMultC)
            self.var.NormalReservoirOutflowCC = self.var.NormalReservoirOutflowCC * ReservoirRnormqMultCC
            # make sure the normal outflow is withing the minimum and non-damaging outflows
            self.var.NormalReservoirOutflowCC = np.maximum(self.var.NormalReservoirOutflowCC, self.var.MinReservoirOutflowCC + 0.01)
            self.var.NormalReservoirOutflowCC = np.minimum(self.var.NormalReservoirOutflowCC, self.var.NonDamagingservoirOutflowCC - 0.01)
            
            # INITIAL CONDITIONS
            
            # initial reservoir fill (fraction of total storage, [-])
            # -9999: assume reservoirs are filled to normal storage limit
            ReservoirInitialFillValue = loadmap('ReservoirInitialFillValue')
            
            if np.max(ReservoirInitialFillValue) == -9999:
                ReservoirInitialFill = self.var.NormalStorageLimitCC,
            else:
                ReservoirInitialFill = np.compress(self.var.ReservoirSitesC > 0, ReservoirInitialFillValue)
            self.var.ReservoirFillCC = ReservoirInitialFill
            
            # initial reservoir storage [m3]
            ReservoirStorageIniM3CC = ReservoirInitialFill * self.var.TotalReservoirStorageM3CC
            self.var.ReservoirStorageM3CC = ReservoirStorageIniM3CC.copy()
            self.var.ReservoirStorageIniM3 = maskinfo.in_zero()
            np.put(self.var.ReservoirStorageIniM3, self.var.ReservoirIndex, ReservoirStorageIniM3CC)
            
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
            
            InvDtSecDay = 1 / float(86400) #JCR: should this be constant for any temporal resolution??
            # InvDtSecDay = self.var.InvDtSec
            
            # storage limits
            conservative_fill = self.var.ConservativeStorageLimitCC
            normal_fill = self.var.NormalStorageLimitC
            adj_normal_fill = self.var.AdjNormalStorageLimitCCCC
            flood_fill = self.var.FloodStorageLimitCC
            emergency_fill = self.var.EmergencyStorageLimitCC

            # representative outflows
            min_outflow = self.var.minReservoirOutflowCC
            normal_outflow = self.var.NormalReservoirOutflowCC
            flood_outflow = self.var.FloodReservoirOutflowCC
            
            # reservoir inflow in [m3/s]
            # (LddStructuresKinematic equals LddKinematic, but without the pits/sinks upstream of the structure
            # locations; note that using Ldd here instead would introduce MV!)
            inflow = np.bincount(self.var.downstruct, weights=self.var.ChanQ)[self.var.ReservoirIndex]

            # reservoir inflow per timestep (routing step) [m3] 
            inflow_m3 = inflow * self.var.DtRouting

            # update reservoir storage [m3] and filling [-]
            if NoRoutingExecuted == 0:
                self.var.ReservoirStorageM3CC = np.compress(self.var.ReservoirSitesC > 0, self.var.ReservoirStorageM3)
            self.var.ReservoirStorageM3CC += inflow_m3
            self.var.ReservoirFillCC = self.var.ReservoirStorageM3CC / self.var.TotalReservoirStorageM3CC
            
            # outflow [m3/s]
            outflow = np.minimum(min_outflow, self.var.ReservoirStorageM3CC * InvDtSecDay)
            # conservative zone
            outflow = np.where(
                self.var.ReservoirFillCC > 2 * cons_fill,
                min_outflow + (normal_outflow - min_outflow) * (self.var.ReservoirFillCC - 2 * cons_fill) / (normal_fill - 2 * cons_fill),
                outflow
            )
            # normal zone
            outflow = np.where(
                self.var.ReservoirFillCC > normal_fill,
                normal_outflow,
                outflow
            )
            # NEW 24-9-2004: linear transition between normal and non-damaging outflow
            outflow = np.where(
                self.var.ReservoirFillCC > adj_normal_fill,
                normal_outflow + (flood_outflow - normal_outflow) * (self.var.ReservoirFillCC - adj_normal_fill) / (flood_fill - adj_normal_fill),
                outflow
            )
            # flood zone
            temp = np.minimum(flood_outflow, np.maximum(inflow * 1.2, normal_outflow))
            outflow = np.where(
                self.var.ReservoirFillCC > flood_fill,
                np.maximum((self.var.ReservoirFillCC - flood_fill - 0.01) * self.var.TotalReservoirStorageM3CC * InvDtSecDay, temp),
                outflow
            )
            # limit outflow if it's larger than 1.2 times the inflow and larger than the normal outflow, and the storage is below the flood limit
            outflow = np.where((outflow > 1.2 * inflow) &
                               (outflow > normal_outflow) &
                               (self.var.ReservoirFillCC < flood_fill),
                               np.minimum(outflow, np.maximum(inflow, normal_outflow)),
                               outflow)
            
            # reservoir outflow in [m3] per sub step
            outflow_m3 = outflow * self.var.DtRouting
            # make sure the outflow is as much as the availabel water, and that the reservoir doesn't exceed its capacity
            outflow_m3 = np.minimum(outflow_m3, self.var.ReservoirStorageM3CC)
            outflow_m3 = np.maximum(outflow_m3, self.var.ReservoirStorageM3CC - self.var.TotalReservoirStorageM3CC)
            
            # update reservoir storage [m3] and filling [-]
            self.var.ReservoirStorageM3CC -= outflow_m3
            self.var.ReservoirFillCC = self.var.ReservoirStorageM3CC / self.var.TotalReservoirStorageM3CC

            # CM: Check ReservoirStorageM3CC for negative values and set them to zero
            self.var.ReservoirFillCC[np.isnan(self.var.ReservoirFillCC)] = 0
            self.var.ReservoirFillCC[self.var.ReservoirFillCC < 0] = 0

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
                    
                        
class Hanazaki(Reservoir):
    
    input_files_keys = {'simulateReservoirs': [
        'ReservoirSites', 'TabTotStorage', 'TabCatchmentArea' # reservoir characteristics
        'TabConservativeStorageLimit', 'TabFloodStorageLimit', # storage limits
        'TabMinOutflow', 'TabNormalOutflow', 'TabFloodOutflow', # release attributes
        # calibration parameters
        'ReservoirInitialFillValue' # initial conditions
    ]}

    def initial(self):
        """
        Initiates the reservoir module by loading the necessary data and maps, setting up the
        reservoir characteristics (e.g., storage capacities, flow limits), and determining
        initial fill levels. Issues a warning if no reservoirs are present in the simulation.
        """
        
        settings = LisSettings.instance()
        option = settings.options
        maskinfo = MaskInfo.instance()
        if option['simulateReservoirs'] and not option['InitLisflood']:

            binding = settings.binding

            # load reservoir locations and keep only those on the channel network
            reservoirs = loadmap('ReservoirSites')
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
            
            # Add reservoir locations to structures map 
            # (used to modify LddKinematic and to calculate LddStructuresKinematic)
            self.var.IsStructureKinematic = np.where(self.var.ReservoirSitesC > 0, np.bool8(1), self.var.IsStructureKinematic)
            
            # load reservoirs in PCRaster
            reservoirs_pcr = loadmap('ReservoirSites', pcr=True)
            self.var.ReservoirSites = reservoirs_pcr
            # filter out reservoirs that are not part of the channel network
            # (following logic of 'old' code the inflow into these reservoirs is
            # always zero, so either change this or leave them out!)
            reservoirs_pcr = ifthen((defined(reservoirs_pcr) & boolean(decompress(self.var.IsChannel))), reservoirs_pcr)
            
            # RESERVOIR CHARACTERISTICS
            
            # reservoir storage capacity [m3]
            total_storage = lookupscalar(str(binding['TabTotStorage']), reservoirs_pcr)
            total_storage = compressArray(total_storage)
            self.var.TotalReservoirStorageM3C = np.where(np.isnan(total_storage), 0, total_storage)
            self.var.TotalReservoirStorageM3CC = np.compress(self.var.ReservoirSitesC > 0, self.var.TotalReservoirStorageM3C)
            
            # reservoir catchment area [m2]
            catchment_area = lookupscalar(str(binding['TabCatchmentArea']), reservoirs_pcr)
            catchment_area = compressArray(catchment_area)
            self.var.CatchmentAreaM2CC = np.compress(self.var.ReservoirSitesC > 0, catchment_area)
            
            # STORAGE LIMITS
            
            # flood storage limit (fraction of total storage [-])
            flood_storage = lookupscalar(str(binding['TabFloodStorageLimit']), reservoirs_pcr)
            flood_storage = compressArray(flood_storage)
            self.var.FloodStorageLimitCC = np.compress(self.var.ReservoirSitesC > 0, flood_storage)
            
            # emergency storage limit (fraction of total storage [-])
            # the upper 20% of the flood storage capacicty
            self.var.EmergencyStorageLimitCC = 0.8 + 0.2 * self.var.FloodStorageLimitCC 
            
            # emergency storage limit (fraction of total storage [-])
            # 50% of the water use capacity
            self.var.ConservativeStorageLimitCC = 0.5 * self.var.FloodStorageLimitCC 
            
            # RELEASE ATTRIBUTES
            
            # minimum reservoir outflow [m3/s]
            MinReservoirOutflow = lookupscalar(str(binding['TabMinOutflow']), reservoirs_pcr)
            MinReservoirOutflowC = compressArray(MinReservoirOutflow)
            self.var.MinReservoirOutflowCC = np.compress(self.var.ReservoirSitesC > 0, MinReservoirOutflowC)
            
            # normal outflow [m3/s]
            normal_outflow = lookupscalar(str(binding['TabNormalOutflow']), reservoirs_pcr)
            normal_outflow = compressArray(normal_outflow)
            self.var.NormalReservoirOutflowCC = np.compress(self.var.ReservoirSitesC > 0, normal_outflow)
            
            # flood-control outflow [m3/s]
            flood_outflow = lookupscalar(str(binding['TabFloodOutflow']), reservoirs_pcr)
            flood_outflow = compressArray(flood_outflow)
            self.var.FloodReservoirOutflowCC = np.compress(self.var.ReservoirSitesC > 0, flood_outflow)
            
            # release coefficient
            self.var.k = np.maximum(1 - 5 * self.var.TotalReservoirStorageM3cCC * (1 - self.var.FloodStorageLimitCC) / self.var.CatchmentAreaM2, 0)
                        
            # RESERVOIR MODEL PARAMETERS
            
            # # flood storage limit (fraction of total storage [-])
            # flood_storage = loadmap('flood_limit')
            # flood_storage = makenumpy(flood_storage)
            # flood_storage = np.compress(self.var.ReservoirSitesC > 0, flood_storage)
            # self.var.FloodStorageLimitCC = flood_storage
            
            # # adjusted normal outflow
            # ReservoirRnormqMult = loadmap('ReservoirRnormqMult')
            # ReservoirRnormqMultC = makenumpy(ReservoirRnormqMult)
            # ReservoirRnormqMultCC = np.compress(self.var.ReservoirSitesC > 0, ReservoirRnormqMultC)
            # self.var.NormalReservoirOutflowCC = self.var.NormalReservoirOutflowCC * ReservoirRnormqMultCC
            # # make sure the normal outflow is withing the minimum and non-damaging outflows
            # self.var.NormalReservoirOutflowCC = np.maximum(self.var.NormalReservoirOutflowCC, self.var.MinReservoirOutflowCC + 0.01)
            # self.var.NormalReservoirOutflowCC = np.minimum(self.var.NormalReservoirOutflowCC, self.var.NonDamagingservoirOutflowCC - 0.01)
            
            # INITIAL CONDITIONS
            
            # initial reservoir fill (fraction of total storage, [-])
            # -9999: assume reservoirs are filled to normal storage limit
            initial_fill = loadmap('ReservoirInitialFillValue')
            if np.max(initial_fill) == -9999:
                initial_fill = self.var.NormalStorageLimitCC,
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
            
            InvDtSecDay = 1 / float(86400) #JCR: should this be constant for any temporal resolution??
            # InvDtSecDay = self.var.InvDtSec
            
            # storage limits
            conservative_fill = self.var.ConservativeStorageLimitCC
            flood_fill = self.var.FloodStorageLimitCC
            emergency_fill = self.var.EmergencyStorageLimitCC

            # representative outflows
            min_outflow = self.var.minReservoirOutflowCC
            normal_outflow = self.var.NormalReservoirOutflowCC
            conservative_outflow = normal_outflow * conservative_fill / flood_fill
            flood_outflow = self.var.FloodReservoirOutflowCC
            
            # reservoir inflow in [m3/s]
            # (LddStructuresKinematic equals LddKinematic, but without the pits/sinks upstream of the structure
            # locations; note that using Ldd here instead would introduce MV!)
            inflow = np.bincount(self.var.downstruct, weights=self.var.ChanQ)[self.var.ReservoirIndex]

            # reservoir inflow per timestep (routing step) [m3] 
            inflow_m3 = inflow * self.var.DtRouting
            
            # flood event
            inflow_mask = inflow >= flood_outflow

            # update reservoir storage [m3] and filling [-]
            if NoRoutingExecuted == 0:
                self.var.ReservoirStorageM3CC = np.compress(self.var.ReservoirSitesC > 0, self.var.ReservoirStorageM3)
            self.var.ReservoirStorageM3CC += inflow_m3
            self.var.ReservoirFillCC = self.var.ReservoirStorageM3CC / self.var.TotalReservoirStorageM3CC
            
            # outflow [m3/s]
            outflow = np.minimum(min_outflow, self.var.ReservoirStorageM3CC * InvDtSecDay)
            # conservative zone
            outflow = np.where(
                self.var.ReservoirFillCC <= conservative_fill,
                normal_outflow * self.var.ReservoirFillCC / conservative_fill,
                outflow
            )
            # normal zone and NO flood inflow
            outflow = np.where(
                (self.var.ReservoirFillCC > conservative_fill) & (self.var.ReservoirFillCC <= emergency_fill) & ~inflow_mask,
                conservative_outflow + ((self.var.ReservoirFillCC - conservative_fill) / (emergency_fill - conservative_fill))**2 * (flood_outflow - normal_outlflow * conservative_fill / flood_fill),
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
            self.var.ReservoirFillCC = self.var.ReservoirStorageM3CC / self.var.TotalReservoirStorageM3CC

            # CM: Check ReservoirStorageM3CC for NaN or negative values and set them to zero
            self.var.ReservoirFillCC[np.isnan(self.var.ReservoirFillCC)] = 0
            self.var.ReservoirFillCC[self.var.ReservoirFillCC < 0] = 0

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
                    
                    
def get_reservoir(model: Literal['burek', 'hanazaki'] = 'hanazaki', reservoir_variable):
    """
    Creates an instance of the reservoir model.

    Parameters:
    -----------
    model: string
        The name of the reservoir model to instantiate ('burek' or 'hanazaki').
    reservoir_variable: object
        An object containing the variables needed for the reservoir simulation.

    Returns:
    --------
    An instance of the specified reservoir model.
    """

    if model.lower() == 'burek':
        return Burek(reservoir_variable)
    elif model.lower() == 'hanazaki':
        return Hanazaki(reservoir_variable)
    else:
        raise ValueError(f"Unknown reservoir model: {model}. Only 'hanazaki' and 'burek' are implemented.")