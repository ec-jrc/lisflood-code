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
from lisflood.global_modules.add1 import *


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

            # read inflow map
            inflowmapprc = loadmap('InflowPoints',pcr=True)
            inflowmapnp = (inflowmapprc, -9999)
            inflowmapnp = np.where(inflowmapnp>0,inflowmapnp,0)

            # get outlets ids from outlets map
            inflowId = np.unique(inflowmapnp)
            # drop negative values (= missing data in pcraster map)
            inflowId = inflowId[inflowId > 0]

            # read tss ids from tss file
            tssId = read_tss_header(binding['QInTS'])

            # create a dictionary of tss id : tss id index
            id_dict = {}
            for i in range(len(tssId)):
                id_dict[tssId[i]] = tssId.index(tssId[i]) +1

            # remove inflow point if not available in tss file
            for i in range(len(inflowId)):
                if inflowId[i] in tssId:
                    pass
                else:
                    id_dict[inflowId[i]] = 0
                    msg = "Inflow point was removed ID:", str(inflowId[i]) ,"\n"
                    print LisfloodWarning(msg)


            # substitute indexes to id in map
            self.var.InflowPointsMap = np.copy(inflowmapnp)
            for k, v in id_dict.iteritems(): self.var.InflowPointsMap[inflowmapnp==k] = v

            # convert map to pcraster format
            # self.var.InflowPointsMap = decompress(self.var.InflowPointsMap)
            self.var.InflowPointsMap = numpy2pcr(Nominal, self.var.InflowPointsMap, -9999)
            tempnpinit = pcr2numpy(self.var.InflowPointsMap,-9999)
            pass

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
            QIn = timeinputscalar(binding['QInTS'], self.var.InflowPointsMap)

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
