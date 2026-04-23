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

            mctsource = loadmap('InflowPoints')     ### temporary da cambiare addiungendo una chiave in settings
            mctsource[(mctsource < 1) | (self.var.IsChannel == 0)] = 0
            # load MCT source locations and keep only those on the channel network


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

            self.var.CheckpointSitesC = ((mctsource == 1) | (mctheadwater == 1)).astype(int)  #np
            # merge source points and headwater points to create the full list of checkpoints

            self.var.CheckpointSitesC = mctsource
            self.var.CheckpointSitesCC = np.compress(mctsource > 0, mctsource)
            self.var.CheckpointIndex = np.nonzero(mctsource)[0]


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
            inflow = np.bincount(self.var.downstruct, weights=self.var.ChanQAvgDt)[self.var.ReservoirIndex]

            # reservoir outflow in [m3] per sub step
            outflow_m3 = inflow * self.var.DtRouting

            # expanding the size as input for routing routine
            # this is released to the channel again at each sub timestep
            self.var.QResOutM3Dt = maskinfo.in_zero()
            np.put(self.var.QResOutM3Dt, self.var.ReservoirIndex, outflow_m3)


            if NoRoutingExecuted == (self.var.NoRoutSteps - 1):

                # expanding the size after last sub timestep
                self.var.ReservoirStorageM3 = maskinfo.in_zero()
                self.var.ReservoirFill = maskinfo.in_zero()
                np.put(self.var.ReservoirStorageM3, self.var.ReservoirIndex, self.var.ReservoirStorageM3CC)
                np.put(self.var.ReservoirFill, self.var.ReservoirIndex, self.var.ReservoirFillCC)
