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


from lisflood.global_modules.add1 import *


class opensealed(object):

    """
    # ************************************************************
    # ***** SOIL LOOP    *****************************************
    # ************************************************************
    """

    def __init__(self, opensealed_variable):
        self.var = opensealed_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the open water and sealed soil module
        """
        # ************************************************************
        # ***** ACTUAL EVAPORATION FROM OPEN WATER AND SEALED SOIL ***
        # ************************************************************

        self.var.RainSnowmelt = np.maximum(self.var.Rain + self.var.SnowMelt, globals.inZero)
        # Water available for the impervious soil and water bodies during this
        # timestep [mm]      #


        self.var.EWaterAct = np.minimum(self.var.EWRef, self.var.RainSnowmelt)
        self.var.EWaterAct = np.maximum(self.var.EWaterAct * 1.0, globals.inZero)
        # actual evaporation from water is potential evaporation of water bodies


        self.var.InterSealed =np.maximum(self.var.SMaxSealed - self.var.CumInterSealed, globals.inZero)
        self.var.InterSealed = np.minimum(self.var.InterSealed, self.var.RainSnowmelt)
        # Interception (in [mm] per time step);
        # to simulate initial loss and depression storage
        self.var.CumInterSealed += self.var.InterSealed


        self.var.TASealed = np.maximum(np.minimum(self.var.CumInterSealed, self.var.EWRef), globals.inZero)
        # evaporation of initial loss and depression storage using potential
        # evaporation of water bodies
        self.var.CumInterSealed = np.maximum(self.var.CumInterSealed - self.var.TASealed, globals.inZero)
        # evaporated water is subtracted from Cumulative depression storage;


        self.var.DirectRunoff = self.var.DirectRunoffFraction * (self.var.RainSnowmelt - self.var.InterSealed) + self.var.WaterFraction *  (self.var.RainSnowmelt - self.var.EWaterAct)
        # Direct runoff during this time step [mm] (added to surface runoff later)
        # but overland routing is done separately for forest, water and sealed
        # and remaing areas

