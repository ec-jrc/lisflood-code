# -------------------------------------------------------------------------
# Name:        INFLOW HYDROGRAPHS module (OPTIONAL)
# Purpose:
#
# Author:      burekpe
#
# Created:     04/03/2014
# Copyright:   (c) burekpe 2014
# Licence:     <your licence>
# -------------------------------------------------------------------------


import math
from global_modules.add1 import *


class inflow(object):

    """
     # ************************************************************
     # ***** READ INFLOW HYDROGRAPHS (OPTIONAL)****************
     # ************************************************************
     # If option "inflow" is set to 1 the inflow hydrograph code is used
     # otherwise dummy code is used
    """

    def __init__(self, inflow_variable):
        self.var = inflow_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
    def initial(self):
        """ initial part of the inflow module
        """
        # ************************************************************
        # ***** INFLOW INIT
        # ************************************************************


        if option['inflow']:
            self.var.InflowPoints = loadmap('InflowPoints')
            self.var.QInM3Old = np.where(self.var.InflowPoints>0,self.var.ChanQ * self.var.DtSec,0)
            #self.var.QInM3Old = cover(ifthen(defined(self.var.InflowPoints), self.var.ChanQ * self.var.DtSec), scalar(0.0))
            # Initialising cumulative output variables
            # These are all needed to compute the cumulative mass balance error

#        self.var.QInDt = globals.inZero.copy()
        # inflow substep amount

    def dynamic_init(self):
        """ dynamic part of the inflow module
            init inflow before sub step routing
        """

        # ************************************************************
        # ***** INLETS INIT
        # ************************************************************
        if option['inflow']:
            self.var.QDelta = (self.var.QInM3 - self.var.QInM3Old) * self.var.InvNoRoutSteps
            # difference between old and new inlet flow  per sub step
            # in order to calculate the amount of inlet flow in the routing loop

    def dynamic(self):
        """ dynamic part of the inflow module
        """

        if option['inflow']:
            QIn = timeinputscalar(binding['QInTS'], loadmap('InflowPoints',pcr=True))
            # Get inflow hydrograph at each inflow point [m3/s]
            QIn = compressArray(QIn)
            QIn[np.isnan(QIn)]=0
            self.var.QInM3 = QIn * self.var.DtSec
            #self.var.QInM3 = cover(QIn * self.var.DtSec, 0)
            # Convert to [m3] per time step
            self.var.TotalQInM3 += self.var.QInM3
            # Map of total inflow from inflow hydrographs [m3]


    def dynamic_inloop(self,NoRoutingExecuted):
        """ dynamic part of the inflow routine
           inside the sub time step routing routine
        """

        # ************************************************************
        # ***** INLFLOW **********************************************
        # ************************************************************
        if option['inflow']:
            self.var.QInDt = (self.var.QInM3Old + (NoRoutingExecuted + 1) * self.var.QDelta) * self.var.InvNoRoutSteps
            # flow from inlets per sub step
