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

from pcraster import scalar, numpy2pcr, Nominal, setclone, Boolean, pcr2numpy, upstream
from pcraster import Scalar, numpy2pcr, Nominal, setclone, Boolean, pcr2numpy

from nine import range

import warnings

from pcraster.operations import ifthen, boolean, defined, lookupscalar
import numpy as np

from ..global_modules.settings import LisSettings, MaskInfo
from ..global_modules.add1 import loadmap, compressArray, decompress, makenumpy
from ..global_modules.errors import LisfloodWarning
from . import HydroModule


class mctheadwater(HydroModule):
    """
    Adds upstream discharge as a lateral flux at headwater and source grid cells when MCT routing is enabled.

    This module handles the initialization and dynamic simulation of checkpoints, accounting for
    inflow and outflow. It can be used in MCT channels to account for headwater/source grid cells.
    It injects upstream discharge to the downstream grid cell as lateral inflow.

    Attributes:
    -----------
        var (object): An object containing all the variables used within the reservoir module.

    Methods:
    --------
        initial(): Sets up the initial conditions and parameters for the simulation,
                   including headwater/source locations.
        dynamic_inloop(NoRoutingExecuted: int): Performs dynamic calculations within the routing
                   loop to simulate inflow and outflow from the headwater/source.
    """
    
    # input_files_keys = {'mctheadwater': ['Checkpoints']}
    module_name = 'MCTHeadwater'

    def __init__(self, mctheadwater_variable):
        self.var = mctheadwater_variable

    def __init__(self, mctheadwater_variable):
        """
        Initializes the MCT headwater/source module with a given variable object.

        Parameters:
        -----------
        mctheadwater_variable: object
            An object containing the variables needed for the MCT headwater/source simulation.
        """

        self.var = mctheadwater_variable
        
    def initial(self):
        """
        Initiates the MCT headwater/source module by loading the necessary data and maps.
        """
        
        settings = LisSettings.instance()
        option = settings.options
        binding = settings.binding
        maskinfo = MaskInfo.instance()
        if option['MCTRouting']:

            # mctsource = loadmap('InflowPoints')     ### temporary da cambiare addiungendo una chiave in settings
            # mctsource[(mctsource < 1) | (self.var.IsChannel == 0)] = 0
            # # load MCT source locations and keep only those on the channel network


            UpStreamPcr = upstream(self.var.LddChan, scalar(self.var.IsChannelPcr))
            UpStream = pcr2numpy(UpStreamPcr, 0)
            # identify all channel pixels that do not have any contributing pixel from upstream (head pixels)

            UpStreamMCTPcr = upstream(self.var.LddChan, scalar(self.var.IsChannelMCTPcr))
            UpStreamMCT = pcr2numpy(UpStreamMCTPcr, 0)
            # identify all MCT pixels that do not have any contributing pixel from upstream (MCT head pixels)

            mctheadwater = (self.var.mctmask & (UpStreamMCT == 0) & (UpStream != 0)).astype(int)
            # identify pixels in the MCT network that are head MCT pixels and are not general head pixels

            mctheadwater = compressArray(numpy2pcr(Scalar, mctheadwater, 0))
            mctheadwater[np.isnan(mctheadwater)] = 0.0
            # flatten and add mask

            # self.var.CheckpointSitesC = ((mctsource == 1) | (mctheadwater == 1)).astype(int)  #np
            # # merge source points and headwater points to create the full list of checkpoints

            self.var.MCTHeadwaterSitesC = mctheadwater
            self.var.MCTHeadwaterSitesCC = np.compress(mctheadwater > 0, mctheadwater)
            self.var.MCTHeadwaterIndex = np.nonzero(mctheadwater)[0]

            # Add MCT headwater locations to structures map
            # (used to modify LddKinematic and to calculate LddStructuresKinematic)
            self.var.IsStructureKinematic = np.where(self.var.MCTHeadwaterSitesC > 0, np.bool8(1), self.var.IsStructureKinematic)
            # Add reservoir locations to structures map (used to modify LddKinematic
            # and to calculate LddStructuresKinematic)
            self.var.IsStructureChan = np.where(self.var.MCTHeadwaterSitesC > 0, np.bool8(1), self.var.IsStructureChan)
            # Add reservoir locations to structures map (used to modify LddChan
            # and to calculate LddStructuresChan)


    def dynamic_init(self):
        """ Initialization of the dynamic part of the MCT headwater module
            init mct headwater before sub step routing
        """

        # ************************************************************
        # ***** HEADWATER INIT
        # ************************************************************
        settings = LisSettings.instance()
        option = settings.options
        if option['MCTRouting']:
            self.var.QInHeadM3Old = np.where(self.var.MCTHeadwaterSitesC > 0, self.var.ChanQAvgDt * self.var.DtSec, 0)  # self.var.QInM3Old
            # difference between old and new headwater flow  per sub step
            # in order to calculate the amount of headwater flow in the routing loop
            pass



    def dynamic_inloop(self, NoRoutingExecuted: int):
        """
        Performs the dynamic simulation of MCT headwater/source within the routing loop. This method
        injects upstream discharge to the downstream grid cell as lateral inflow.

        Parameters:
        -----------
        NoRoutingExecuted: integer
            The number of routing sub-steps that have been executed. This parameter is used to manage
            the accumulation of inflow and outflow over the routing steps.
        """

        settings = LisSettings.instance()
        option = settings.options
        maskinfo = MaskInfo.instance()
        
        if option['MCTRouting'] and not option['InitLisflood']:

            InvDtSecDay = 1 / float(86400)
            # InvDtSecDay=self.var.InvDtSec

            # reservoir inflow in [m3/s]
            # (LddStructuresKinematic equals LddKinematic, but without the pits/sinks upstream of the structure
            # locations; note that using Ldd here instead would introduce MV!)
            inflow = np.bincount(self.var.downstruct, weights=self.var.ChanQAvgDt)[self.var.MCTHeadwaterIndex]  #same as Qin
            # inflow = self.var.ChanQAvgDt[7] #this is just to make it the same as the inflow run  REMOVE

            self.var.QInHeadM3 = maskinfo.in_zero()
            np.put(self.var.QInHeadM3, self.var.MCTHeadwaterIndex, inflow * self.var.DtSec)
            self.var.QDeltaM3 = (self.var.QInHeadM3 - self.var.QInHeadM3Old) * self.var.InvNoRoutSteps

            self.var.QHeadM3Dt = (self.var.QInHeadM3Old + (NoRoutingExecuted + 1) * self.var.QDeltaM3) * self.var.InvNoRoutSteps
            # output to the MCT headwater cells

            self.var.QInHeadM3Old = self.var.QInHeadM3.copy()
            # save the upstream inflow for next step
            pass


