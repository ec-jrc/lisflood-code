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
from pcraster import Scalar, numpy2pcr, pcr2numpy,downstream, boolean
from nine import range
import numpy as np
from ..global_modules.settings import LisSettings, MaskInfo
from ..global_modules.add1 import loadmap, compressArray, decompress, makenumpy
from ..global_modules.errors import LisfloodWarning
from . import HydroModule


class mctconfluence(HydroModule):
    """
    Adds contribution from Kinematic cells to MCT cells as a lateral flow when MCT routing is enabled.
    This is for MCT cells that have upstream contributions from both kinematic and MCT cells.

    This module handles the initialization and dynamic simulation of Kinematic to MCT cells confluence.
    It injects side discharge to the downstream grid cell as lateral flow.

    Attributes:
    -----------
        var (object): An object containing all the variables used within the mctconfluence module.

    Methods:
    --------
        initial(): Sets up the initial conditions and parameters for the simulation,
                   including confluence locations.
        dynamic_inloop(NoRoutingExecuted: int): Performs dynamic calculations within the routing
                   loop to simulate the kinematic to MCT confluence.
    """

    module_name = 'MCTConfluence'

    def __init__(self, mctconfluence_variable):
        self.var = mctconfluence_variable

    def __init__(self, mctconfluence_variable):
        """
        Initializes the MCT confluence module with a given variable object.

        Parameters:
        -----------
        mctconfluence_variable: object
            An object containing the variables needed for the MCT confluence simulation.
        """

        self.var = mctconfluence_variable
        
    def initial(self):
        """
        Initiates the MCT confluence module by loading the necessary data and maps.
        """
        
        settings = LisSettings.instance()
        option = settings.options
        binding = settings.binding
        maskinfo = MaskInfo.instance()
        if option['MCTRouting']:

            inArPcr = decompress(np.arange(maskinfo.info.mapC[0], dtype="int32"))  # pcr
            # Assign a number to each non-missing pixel as cell id, starting from 0
            inAr = compressArray(inArPcr)

            down = (compressArray(downstream(self.var.LddStructuresChan, inArPcr))).astype("int32")  # np
            # assign to each pixel the cell id of the pixel it is contributing to

            maskKinematic = (compressArray(self.var.LddKinematic) == 5) & (self.var.IsUpsOfStructureKinematicC != 1)
            maskKinematic[compressArray(self.var.AtLastPoint) == 1] = False
            # find location of KIN pixels (only) in LddKin that are at the confluence with an MCT pixel
            # do not include sinks upstream of structures (lakes, reservoirs, MCT headwater pixels) and outlets

            self.var.UpsOfMCTConfluence = np.where(maskKinematic, down, 0)
            # find last KIN pixels upstream of the confluence with an MCT pixel and assign it the id of the downstream MCT pixel

            mctconfluence = maskinfo.in_zero()
            mctconfluence[np.isin(inAr, self.var.UpsOfMCTConfluence[self.var.UpsOfMCTConfluence != 0])] = 1
            # for each element in UpsOfMCTConfluence (they are Kinematic cells), get the value of the downstream cell and find the  position ix of that same value in inAr, read the inAr value and put 1 in the corrisponding position in mctconfluence
            # identify location of MCT pixels that receive a contribution from an upstream KIN pixel (with no structure on it)

            # mctconfluence[self.var.MCTHeadwaterSitesC == 1] = 0
            # # remove headwater cells from the list of confluence cells because they are treated differently
            # mctconfluence[compressArray(self.var.AtLastPoint) == 1] = 0
            # # remove outlets points if any

            self.var.MCTConfluenceSitesC = mctconfluence
            self.var.MCTConfluenceSitesCC = np.compress(mctconfluence > 0, mctconfluence)
            self.var.MCTConfluenceIndex = np.nonzero(mctconfluence)[0]


    def dynamic_init(self):
        """ Initialization of the dynamic part of the MCT confluence module
            init mct confluence before sub step routing
        """
        settings = LisSettings.instance()
        option = settings.options
        if option['MCTRouting']:
            self.var.QInConfM3Old = np.where(self.var.MCTConfluenceSitesC > 0, self.var.ChanQAvgDt * self.var.DtSec, 0)


    def dynamic_inloop(self, NoRoutingExecuted: int):
        """
        Performs the dynamic simulation of MCT confluence within the routing loop. This method
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

        self.var.QConfADDEDM3 = maskinfo.in_zero()
        
        if option['MCTRouting'] and not option['InitLisflood']:

            InvDtSecDay = 1 / float(86400)
            # InvDtSecDay=self.var.InvDtSec

            lateralflow = np.bincount(self.var.UpsOfMCTConfluence, weights=self.var.ChanQAvgDt)[self.var.MCTConfluenceIndex]  #same as Qin
            # contribution to the MCT pixel from upstream Kinematic pixels

            self.var.QInConfM3 = maskinfo.in_zero()
            np.put(self.var.QInConfM3, self.var.MCTConfluenceIndex, lateralflow * self.var.DtSec)
            self.var.QDeltaConfM3 = (self.var.QInConfM3 - self.var.QInConfM3Old) * self.var.InvNoRoutSteps
            # difference between old and new lateral flow per sub step
            # in order to calculate the amount of lateral flow in the routing loop

            self.var.QConfM3Dt = (self.var.QInConfM3Old + (NoRoutingExecuted + 1) * self.var.QDeltaConfM3) * self.var.InvNoRoutSteps
            # output to the MCT confluence cell

            self.var.QInConfM3Old = self.var.QInConfM3.copy()
            # save the lateral flow for next step

            self.var.QConfADDEDM3 += self.var.QConfM3Dt
            # adding volume to the water balance



