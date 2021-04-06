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

import numpy as np

from ..global_modules.add1 import loadmap
from . import HydroModule


class frost(HydroModule):

    """
    # ************************************************************
    # ***** FROST INDEX IN SOIL **********************************
    # ************************************************************
    # Domain: whole pixel (permeable + direct runoff areas)
    """
    input_files_keys = {'all': ['Kfrost', 'Afrost', 'FrostIndexThreshold', 'SnowWaterEquivalent', 'FrostIndexInitValue']}
    module_name = 'Frost'

    def __init__(self, frost_variable):
        self.var = frost_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the frost index module
        """

        self.var.Kfrost = loadmap('Kfrost')
        self.var.Afrost = loadmap('Afrost')
        self.var.FrostIndexThreshold = loadmap('FrostIndexThreshold')
        self.var.SnowWaterEquivalent = loadmap('SnowWaterEquivalent')

        # FrostIndexInit=ifthen(defined(self.var.MaskMap),scalar(loadmap('FrostIndexInitValue')))
        # self.var.FrostIndex=FrostIndexInit
        self.var.FrostIndex = loadmap('FrostIndexInitValue')
        # self.var.AfrostIndex=-(1-self.var.Afrost)*self.var.FrostIndex
        # initial Frost Index value
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the frost index module
        """
        # FrostIndexChangeRate=-(1-Afrost)*FrostIndex - Tavg*exp(-0.04*Kfrost*SnowCover/SnowWaterEquivalent);

        FrostIndexChangeRate = -(1 - self.var.Afrost) * self.var.FrostIndex - self.var.Tavg * np.exp(-0.04 * self.var.Kfrost * self.var.SnowCover / self.var.SnowWaterEquivalent)
        # FrostIndexChangeRate=self.var.AfrostIndex - self.var.Tavg*      pcraster.exp(self.var.Kfrost*self.var.SnowCover*self.var.InvSnowWaterEquivalent)
        # Rate of change of frost index (expressed as rate, [degree days/day])
        # CHANGED 9 September 2004:
        # - first term should be negative
        # - second term should be subtracted, not added!!

        self.var.FrostIndex = np.maximum(self.var.FrostIndex + FrostIndexChangeRate * self.var.DtDay, 0)
        # frost index in soil [degree days]
        # based on Molnau and Bissel (1983, A Continuous Frozen Ground Index for Flood
        # Forecasting. In: Maidment, Handbook of Hydrology, p. 7.28, 7.55)
        # if Tavg is above zero, FrostIndex will stay 0
        # if Tavg is negative, FrostIndex will increase with 1 per degree C per day
        # Exponent of 0.04 (instead of 0.4 in HoH): conversion [cm] to [mm]!
        # Division by SnowDensity because SnowDepth is expressed as equivalent water
        # depth(always less than depth of snow pack)
        # SnowWaterEquivalent taken as 0.100 (based on density of 100 kg/m3) (Handbook of Hydrology, p. 7.5)
        # Afrost, (daily decay coefficient) is taken as 0.97 (Handbook of Hydrology,
        # p. 7.28)
        # Kfrost, (snow depth reduction coefficient) is taken as 0.57 [1/cm],
        # (HH, p. 7.28)
