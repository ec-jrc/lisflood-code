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
from nine import range

from pcraster import ifthenelse, downstream, lddrepair
import numpy as np

from ..global_modules.add1 import loadmap, compressArray, decompress, generateName, loadLAI
from ..global_modules.settings import MaskInfo, LisSettings
from . import HydroModule


class evapowater(HydroModule):
    """
    # ************************************************************
    # ***** EVAPORATION FROM OPEN WATER **************************
    # ************************************************************
    """
    input_files_keys = {
        'openwaterevapo': ['LakeMask', 'maxNoEva'],
        'varfractionwater': ['FracMaxWater', 'WFractionMaps']
    }
    module_name = 'EvapoWater'

    def __init__(self, evapowater_variable):
        self.var = evapowater_variable

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the evapo water module
        """

        # ************************************************************
        # ***** EVAPORATION
        # ************************************************************
        self.var.EvaCumM3 = MaskInfo.instance().in_zero()
        # water use cumulated amount
        # water use substep amount
        settings = LisSettings.instance()
        option = settings.options
        binding = settings.binding
        maskinfo = MaskInfo.instance()
        if option['openwaterevapo']:
            LakeMask = loadmap('LakeMask', pcr=True)
            lmask = ifthenelse(LakeMask != 0, self.var.LddStructuresKinematic, 5)
            LddEva = lddrepair(lmask)
            lddC = compressArray(LddEva)
            inAr = decompress(np.arange(maskinfo.info.mapC[0], dtype="int32"))
            self.var.downEva = (compressArray(downstream(LddEva, inAr))).astype("int32")
            # each upstream pixel gets the id of the downstream pixel
            self.var.downEva[lddC == 5] = maskinfo.info.mapC[0]
            self.var.maxNoEva = int(loadmap('maxNoEva'))
            # all pits gets a high number
            # still to test if this works

            # ldd only inside lakes for calculating evaporation

            if option['varfractionwater']:

                self.var.diffmaxwater = loadmap('FracMaxWater') - self.var.WaterFraction

                # Fraction of maximum extend of water  - fraction of water in lakes and rivers

                varWNo = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 370]
                self.var.varW = []  # variable fraction of water
                self.var.varW1 = []

                self.var.varW1.append(12)
                j = 0
                for i in range(1, 367):
                    if i >= varWNo[j + 1]: j += 1
                    self.var.varW1.append(j)

                for i in range(12):
                    varWName = generateName(binding['WFractionMaps'], varWNo[i])
                    self.var.varW.append(loadLAI(binding['WFractionMaps'], varWName, i))

    def dynamic_init(self):
        """ init dynamic part of the evaporation from open water
            defines the fraction of land cover
        """
        settings = LisSettings.instance()
        option = settings.options
        if option['openwaterevapo'] and option['varfractionwater']:
            relWaterFraction = self.var.varW[self.var.varW1[self.var.CalendarDay]]
            # fraction [0-1] of between min. and max. water fraction as land cover
            # min water fraction: river + lakes
            # max: lakes + rivers + swamps
            varWater = relWaterFraction * self.var.diffmaxwater
            self.var.WaterFraction = self.var.WaterFractionBase + varWater

            # all the other land cover fractions have to be recalculated:
            self.var.OtherFraction = np.maximum(self.var.OtherFractionBase - varWater, 0)
            rest = np.maximum(varWater - self.var.OtherFractionBase, 0)
            self.var.ForestFraction = np.maximum(self.var.ForestFractionBase - rest, 0)
            rest = np.maximum(rest - self.var.ForestFractionBase, 0)
            self.var.IrrigationFraction = np.maximum(self.var.IrrigationFractionBase - rest, 0)
            rest = np.maximum(rest - self.var.IrrigationFractionBase, 0)
            self.var.DirectRunoffFraction = np.maximum(self.var.DirectRunoffFractionBase - rest, 0)

            self.var.SoilFraction = self.var.ForestFraction + self.var.OtherFraction + self.var.IrrigationFraction
            # all = self.var.SoilFraction + self.var.DirectRunoffFraction + self.var.WaterFraction
            self.var.PermeableFraction = 1 - self.var.DirectRunoffFraction - self.var.WaterFraction

    def dynamic(self):
        """ dynamic part of the evaporation from open water
        """
        settings = LisSettings.instance()
        option = settings.options
        if option['openwaterevapo']:
            # ***********************************************
            # *********  EVAPORATION FROM OPEN WATER  *******
            # ***********************************************
            UpstreamEva = self.var.EWRef * self.var.MMtoM3 * self.var.WaterFraction
            # evaporation for loop is amount of water per timestep [cu m]
            # Volume of potential evaporation from water surface  per time step (conversion to [m3])
            ChanMIter = self.var.ChanM3Kin.copy()
            # for Iteration loop: First value is amount of water in the channel
            # amount of water in bankful (first line of routing)
            ChanLeft = ChanMIter * 0.1
            # 10% of the discharge must stay in the river
            self.var.EvaAddM3 = MaskInfo.instance().in_zero()
            #   real water consumption is set to 0

            for NoEvaExe in range(self.var.maxNoEva):
                ChanHelp = np.maximum(ChanMIter - UpstreamEva, ChanLeft)
                EvaIter = np.maximum(UpstreamEva - (ChanMIter - ChanHelp), 0)
                # new amount is amout - evaporation use till a limit
                # new evaporation is evaporation - water is used from channel network
                ChanMIter = ChanHelp.copy()
                self.var.EvaAddM3 += UpstreamEva - EvaIter
                # evaporation is added up; the sum is the same as sum of original water use
                # UpstreamEva = upstream(self.var.LddEva,EvaIter)
                UpstreamEva = np.bincount(self.var.downEva, weights=EvaIter)[:-1]
                # remaining water use is moved down the the river system,

            self.var.EvaAddM3Dt = self.var.EvaAddM3 * self.var.InvNoRoutSteps
            # splitting water use per timestep into water use per sub time step
            self.var.EvaCumM3 += self.var.EvaAddM3
            # summing up for water balance calculation
