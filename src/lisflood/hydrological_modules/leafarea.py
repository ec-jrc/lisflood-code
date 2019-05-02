# -------------------------------------------------------------------------
# Name:        LEAF AREA INDEX (LAI) module
# Purpose:
#
# Author:      burekpe
#
# Created:     04/03/2014
# Copyright:   (c) burekpe 2014
# Licence:     <your licence>
# -------------------------------------------------------------------------

from lisflood.global_modules.add1 import *

class leafarea(object):

    """
   # ************************************************************
   # ***** LEAF AREA INDEX DATA ****************************
   # ************************************************************
    """

    def __init__(self, leafarea_variable):
        self.var = leafarea_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
    def initial(self):
        """ initial part of the leaf area index module
        """

        self.var.kgb = 0.75 * loadmap('kdf')
        # extinction coefficient for global solar radiation [-]
        # kdf= extinction coefficient for diffuse visible light [-], varies between
        # 0.4 and 1.1

        # LAINr=[1,32,60,91,121,152,182,213,244,274,305,335,370]
        LAINr = [1, 11, 21, 32, 42, 52, 60, 70, 80, 91, 101, 111, 121, 131, 141, 152, 162, 172, 182,
                 192, 202, 213, 223, 233, 244, 254, 264, 274, 284, 294, 305, 315, 325, 335, 345, 355, 370]

        self.var.LAIX = [[0 for x in xrange(36)] for x in xrange(3)]
        self.var.LAI = [0, 0]
        self.var.L1 = []

        # self.var.L1.append(36)
        j = 0
        for i in xrange(367):
            if i >= LAINr[j + 1]:
                j += 1
            self.var.L1.append(j)
            # print i,self.L1[i],LAINr1[self.L1[i]]

        for i in xrange(36):
            LAIName = generateName(binding['LAIOtherMaps'], LAINr[i])
            self.var.LAIX[0][i] = loadLAI(binding['LAIOtherMaps'], LAIName, i)

            LAIName = generateName(binding['LAIForestMaps'], LAINr[i])
            self.var.LAIX[1][i] = loadLAI(binding['LAIForestMaps'], LAIName, i)

            LAIName = generateName(binding['LAIIrrigationMaps'], LAINr[i])
            self.var.LAIX[2][i] = loadLAI(binding['LAIIrrigationMaps'], LAIName, i)


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the leaf area index module
        """

        i = self.var.L1[self.var.CalendarDay]
        self.var.LAI = [self.var.LAIX[0][i], self.var.LAIX[1][i],self.var.LAIX[2][i]]

        # Leaf Area Index, average over whole pixel [m2/m2]
        self.var.LAITerm = [np.exp(-self.var.kgb * self.var.LAI[0]), np.exp(-self.var.kgb * self.var.LAI[1]),np.exp(-self.var.kgb * self.var.LAI[2])]
