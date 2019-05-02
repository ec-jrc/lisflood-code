# -------------------------------------------------------------------------
# Name:        Transmission loss module
# Purpose:
#
# Author:      burekpe
#
# Created:     29.03.2014
# Copyright:   (c) burekpe 2014
# Licence:     <your licence>
# -------------------------------------------------------------------------


from pcraster import*
from pcraster.framework import *
import sys
import os
import string
import math


from lisflood.global_modules.zusatz import *
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

