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


from pcraster import*
from pcraster.framework import *

from lisflood.global_modules.add1 import *
from lisflood.global_modules.globals import *


class transmission(object):

    """
    # ************************************************************
    # ***** Transmission loss ************************************
    # ************************************************************
    """

    def __init__(self, transmission_variable):
        self.var = transmission_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the transmission loss module
        """

        if option['TransLoss']:
            TransArea = loadmap('TransArea')
            self.var.TransSub = loadmap('TransSub')
            # downstream area taking into account for transmission loss
            self.var.UpAreaTrans = loadmap('UpAreaTrans')
            # upstream area
            self.var.UpTrans = np.where(self.var.UpAreaTrans >= TransArea,np.bool8(1),np.bool8(0))
            # Downstream taking into accound for transmission loss
            # if upstream area (the total one) is bigger than a threshold us
            # transmission loss
            self.var.TransPower1 = loadmap('TransPower1')
            self.var.TransPower2 = 1.0 / self.var.TransPower1
            # transmission loss function

            self.var.TransCum = globals.inZero.copy()
        # Cumulative transmission loss
        # self.var.TransLossM3Dt = globals.inZero.copy()
        # substep amount of transmission loss


    def dynamic_inloop(self):
        """ dynamic part of the transmission loss routine
           inside the sub time step routing routine
        """

        # ************************************************************
        # ***** TRANSMISSION LOSS IN THE CHANNEL      ****************
        # ************************************************************
        if option['TransLoss']:


            TransOut = np.where(self.var.UpTrans,
                        (self.var.ChanQ ** self.var.TransPower2 - self.var.TransSub)
                        ** self.var.TransPower1, self.var.ChanQ)
            # transmission loss (equation: Rao and Maurer 1996, Water Resources
            # Bulletin Vol 32, No.6)

            self.var.TransLossM3Dt = (self.var.ChanQ - TransOut) * self.var.DtRouting

            #self.var.TransLossM3Dt = cover((self.var.ChanQ - TransOut) * self.var.DtRouting, scalar(0.0))
            # Loss is Q - transmission outflow
            self.var.TransCum += self.var.TransLossM3Dt
            # for mass balance

