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

from pcraster import scalar, upstream
from pcraster import Scalar, numpy2pcr, pcr2numpy
from pcraster import downstream, boolean, cover, lddrepair, ifthenelse
from nine import range
import numpy as np
from ..global_modules.settings import LisSettings, MaskInfo
from ..global_modules.add1 import loadmap, compressArray, decompress, makenumpy
from ..global_modules.errors import LisfloodWarning
from . import HydroModule


class mctheadwater(HydroModule):
    """
    Adds contribution from Kinematic cells to MCT cells as a lateral flow when MCT routing is enabled.
    This is for MCT cells that have upstream contributions from both kinematic cells only.

    This module handles the initialization and dynamic simulation of MCT headwater cells.
    It injects upstream discharge from kinematic cells to the downstream MCT grid cell as lateral flow.

    Attributes:
    -----------
        var (object): An object containing all the variables used within the mctheadwater module.

    Methods:
    --------
        initial(): Sets up the initial conditions and parameters for the simulation,
                   including headwater locations.
        dynamic_inloop(NoRoutingExecuted: int): Performs dynamic calculations within the routing
                   loop to simulate the kinematic to MCT confluence.
    """

    module_name = 'MCTHeadwater'

    def __init__(self, mctheadwater_variable):
        self.var = mctheadwater_variable

    def __init__(self, mctheadwater_variable):
        """
        Initializes the MCT headwater module with a given variable object.

        Parameters:
        -----------
        mctheadwater_variable: object
            An object containing the variables needed for the MCT headwater simulation.
        """

        self.var = mctheadwater_variable
        
    def initial(self):
        """
        Initiates the MCT headwater module by loading the necessary data and maps.
        """
        
        settings = LisSettings.instance()
        option = settings.options
        binding = settings.binding
        maskinfo = MaskInfo.instance()
        if option['MCTRouting']:

            UpStreamPcr = upstream(self.var.LddChan, scalar(self.var.IsChannelPcr))
            UpStream = pcr2numpy(UpStreamPcr, 0)
            # identify all channel pixels that do not have any contributing pixel from upstream (head pixels)

            UpStreamMCTPcr = upstream(self.var.LddChan, scalar(self.var.IsChannelMCTPcr))
            UpStreamMCT = pcr2numpy(UpStreamMCTPcr, 0)
            # identify all MCT pixels that do not have any contributing pixel from upstream (MCT head pixels)

            mctheadwater = (self.var.mctmask & (UpStreamMCT == 0) & (UpStream != 0)).astype(int)
            # identify pixels in the MCT network that are head MCT pixels and are not general head pixels

            mctheadwaterPcr = numpy2pcr(Scalar, mctheadwater, 0)

            mctheadwater = compressArray(mctheadwaterPcr)
            mctheadwater[np.isnan(mctheadwater)] = 0.0
            # flatten and add mask

            # mctheadwater[compressArray(self.var.AtLastPoint) == 1] = 0
            # # remove outlets points if any

            self.var.MCTHeadwaterSitesC = mctheadwater
            self.var.MCTHeadwaterSitesCC = np.compress(mctheadwater > 0, mctheadwater)
            self.var.MCTHeadwaterIndex = np.nonzero(mctheadwater)[0]

            # # Add MCT headwater locations to structures map
            # # (used to modify LddKinematic and to calculate LddStructuresKinematic)
            # self.var.IsStructureKinematic = np.where(self.var.MCTHeadwaterSitesC > 0, np.bool8(1), self.var.IsStructureKinematic)
            # # Add reservoir locations to structures map (used to modify LddKinematic
            # # and to calculate LddStructuresKinematic)
            # self.var.IsStructureChan = np.where(self.var.MCTHeadwaterSitesC > 0, np.bool8(1), self.var.IsStructureChan)
            # # Add reservoir locations to structures map (used to modify LddChan
            # # and to calculate LddStructuresChan)

            # at this point, Ldd already have pits upstream of reservoirs and lakes
            IsUpsOfMCTHeadwaterKinematic = downstream(     #pcr map
                self.var.LddKinematic,
                cover(boolean(decompress(self.var.MCTHeadwaterSitesC)), boolean(0))
            )
            # Find location of pixels immediately upstream of an MCT Headwater pixel on the LddKinematic

            IsUpsOfMCTHeadwaterChan = downstream(      #pcr map
                self.var.LddChan,
                cover(boolean(decompress(self.var.MCTHeadwaterSitesC)), boolean(0))
            )
            # Find location of pixels immediately upstream of a structure on the LddChan

            self.var.LddKinematic = lddrepair(ifthenelse(IsUpsOfMCTHeadwaterKinematic, 5, self.var.LddKinematic))  #pcr map
            # Update LddKinematic by adding a pit in the pixel immediately upstream of a MCT headwater pixel
            self.var.LddChan = lddrepair(ifthenelse(IsUpsOfMCTHeadwaterChan, 5, self.var.LddChan))     #pcr map
            # Update LddChan by adding a pit in the pixel immediately upstream of a MCT headwater pixel


    def dynamic_init(self):
        """ Initialization of the dynamic part of the MCT headwater module
            init mct headwater before sub step routing
        """
        settings = LisSettings.instance()
        option = settings.options
        if option['MCTRouting']:
            self.var.QInHeadM3Old = np.where(self.var.MCTHeadwaterSitesC > 0, self.var.ChanQAvgDt * self.var.DtSec, 0)  # self.var.QInM3Old


    def dynamic_inloop(self, NoRoutingExecuted: int):
        """
        Performs the dynamic simulation of MCT headwater within the routing loop. This method
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

        # self.var.QHeadADDEDM3 = maskinfo.in_zero()
        
        if option['MCTRouting'] and not option['InitLisflood']:

            InvDtSecDay = 1 / float(86400)
            # InvDtSecDay=self.var.InvDtSec

            inflow = np.bincount(self.var.downstruct, weights=self.var.ChanQAvgDt)[self.var.MCTHeadwaterIndex]  #same as Qin
            # contribution to the MCT pixel from upstream Kinematic pixels

            # ########
            # debug
            # inflow = self.var.ChanQAvgDt[7]  # this is just to make it the same as the inflow run  REMOVE
            # ########

            self.var.QInHeadM3 = maskinfo.in_zero()
            np.put(self.var.QInHeadM3, self.var.MCTHeadwaterIndex, inflow * self.var.DtSec)
            self.var.QDeltaM3 = (self.var.QInHeadM3 - self.var.QInHeadM3Old) * self.var.InvNoRoutSteps
            # difference between old and new headwater flow  per sub step
            # in order to calculate the amount of headwater flow in the routing loop

            self.var.QHeadM3Dt = (self.var.QInHeadM3Old + (NoRoutingExecuted + 1) * self.var.QDeltaM3) * self.var.InvNoRoutSteps
            # output to the MCT headwater cells

            self.var.QInHeadM3Old = self.var.QInHeadM3.copy()
            # save the upstream flow for next step

            # self.var.QHeadADDEDM3 += self.var.QHeadM3Dt



