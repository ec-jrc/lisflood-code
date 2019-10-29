# -------------------------------------------------------------------------
# Name:        MiscInitial
# Purpose:
#
# Author:      pb
#
# Created:     29.03.2014
# Copyright:   (c) pb 2014
# Licence:     <your licence>
# -------------------------------------------------------------------------

from global_modules.add1 import *


class miscInitial(object):

    """
    Miscellaneous repeatedly used expressions
    """

    def __init__(self, misc_variable):
        self.var = misc_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the misc module
        """

        if option['gridSizeUserDefined']:

            # <lfoption name="gridSizeUserDefined" choice="1" default="0">
            # If option gridsizeUserDefined is activated, users can specify grid size properties
            # in separate maps. This is useful whenever this information cannot be derived from
            # the location attributes of the base maps (e.g. lat/lon systems or non-equal-area
            # projections)
            # Limitation: always assumes square grid cells (not rectangles!). Size of grid cells
            # may vary across map though

            self.var.PixelLengthPcr = loadmap('PixelLengthUser',pcr=True)
            self.var.PixelLength = compressArray(self.var.PixelLengthPcr)
            # Length of pixel [m]
            # Area of pixel [m2]
            self.var.PixelAreaPcr = loadmap('PixelAreaUser',pcr=True)
            self.var.PixelArea = compressArray(self.var.PixelAreaPcr)

        else:
            # Default behaviour: grid size is derived from location attributes of
            # base maps. Requirements:
            # - Maps are in some equal-area projection
            # - Length units meters
            # - All grid cells have the same size

            # Length of pixel [m]
            #self.var.PixelLength = celllength()
            self.var.PixelLengthPcr = celllength()
            self.var.PixelLength = maskmapAttr['cell']

            # Area of pixel [m2]
            self.var.PixelAreaPcr = self.var.PixelLength ** 2
            self.var.PixelArea=np.empty(maskinfo['mapC'])
            self.var.PixelArea.fill(self.var.PixelLength ** 2)

#            self.var.PixelArea = spatial(self.var.PixelArea)
            # Convert to spatial expresion (otherwise this variable cannnot be
            # used in areatotal function)

# -----------------------------------------------------------------
        # Miscellaneous repeatedly used expressions (as suggested by GF)

        self.var.InvPixelLength = 1.0 / self.var.PixelLength
        # Inverse of pixel size [1/m]
        self.var.DtSec = loadmap('DtSec')
        self.var.DtDay = self.var.DtSec / 86400
        # Time step, expressed as fraction of day (used to convert
        # rate variables that are expressed as a quantity per day to
        # into an amount per time step)
        self.var.InvDtSec = 1 / self.var.DtSec
        # Inverse of time step [1/s]
        self.var.InvDtDay = 1 / self.var.DtDay
        # Inverse of time step [1/d]
        self.var.DtSecChannel = loadmap('DtSecChannel')
        # Sub time step used for kinematic wave channel routing [seconds]
        # within the model,the smallest out of DtSecChannel and DtSec is used

        self.var.MMtoM = 0.001
        # Multiplier to convert wate depths in mm to meters
        self.var.MtoMM = 1000
        # Multiplier to convert wate depths in meters to mm
        self.var.MMtoM3 = 0.001 * self.var.PixelArea
        # self.var.MMtoM3=0.001*float(celllength())**2
        # Multiplier to convert water depths in mm to cubic
        # metres
        self.var.M3toMM = 1 / self.var.MMtoM3
        # Multiplier to convert from cubic metres to mm water slice

        self.var.GwLoss = loadmap('GwLoss')
        self.var.GwPerc = np.maximum(loadmap('GwPercValue'), self.var.GwLoss)
        # new Gwloss  PB 12.11.2009
        # if GWloss > GwPercValue -> GwPerc = GwLoss
        self.var.GwPercStep = self.var.GwPerc * self.var.DtDay
        # Percolation from upper to lower groundwater zone, expressed as
        # amount per time step
        self.var.GwLossStep = self.var.GwLoss * self.var.DtDay
        # change similar to GwPercStep

        # ************************************************************
        # ***** Some additional stuff
        # ************************************************************
        # CM: date of the first possible model run
        # CM: computation of model steps is referred to CalendarStartDay
        self.var.CalendarDayStart = Calendar(binding['CalendarDayStart'])
        try:
           # CM: number of time step or date of the state map to be used to initialize model run
           timestepInit.append(binding["timestepInit"])
        except: pass

        self.var.PrScaling = loadmap('PrScaling')
        self.var.CalEvaporation = loadmap('CalEvaporation')
        # Multiplier applied to potential evapo(transpi)ration rates

        self.var.Precipitation = None
        self.var.Tavg = None
        self.var.ETRef = None
        self.var.ESRef = None
        self.var.EWRef = None
        # setting meteo data to none - is this necessary?

        # CM mod: to be removed?
        # self.var.EndOfMonthTable="D:/LisfloodWorld2/tables/EndOfMonth.txt"
	     #   # '1' if last day of the month, '0' if not
        #
        # self.var.DayCounterMap ="./outMonth/Days"
        # self.var.ETpotMonthly="./outMonth/ETpot"
        # self.var.ETactMonthly="./outMonth/ETact"
        # self.var.WDMonthly="./outMonth/WD"
        # self.var.WUMonthly="./outMonth/WU"
        # self.var.DisMonthly="./outMonth/FlowE"
        # self.var.FlowIMonthly = "./outMonth/FlowI"
        #
        # self.var.WEI_Use = "./outMonth/WEIu"
        # self.var.WEI_Demand = "./outMonth/WEId"
        # self.var.lWEI_Use = "./outMonth/lWEIu"
        # self.var.lWEI_Demand = "./outMonth/lWEId"
        # self.var.WDI = "./outMonth/WDI"
        #
        #
        # self.var.FlagDemandUse="./outMonth/DaysDemandGTUSE.map"
        # self.var.torun="./torun"
        # CM mod: end



        self.var.DayCounter= 0.0
        self.var.MonthETpot= globals.inZero
        self.var.MonthETact= globals.inZero
        self.var.MonthWDemand= globals.inZero
        self.var.MonthWUse= globals.inZero
        self.var.MonthWDemand= globals.inZero
        self.var.MonthDis= globals.inZero
        self.var.MonthInternalFlow =  globals.inZero


        self.var.TotalInternalFlowM3 =  globals.inZero
        self.var.PerMonthInternalFlowM3 =  globals.inZero
	# total freshwater generated in the sub-area (m3), basically local P-ET-Storage
        self.var.TotalExternalInflowM3 =  globals.inZero
        self.var.PerMonthExternalInflowM3 =  globals.inZero
	 # Total channel inflow (m3) from inlet points
        self.var.PerMonthWaterDemandM3 =  globals.inZero
        self.var.PerMonthWaterUseM3 =  globals.inZero

        self.var.FlagDemandBiggerUse =  scalar(0.0)


        self.var.TotWEI =  scalar(0.0)
        self.var.TotlWEI =  scalar(0.0)
        self.var.TotCount =  scalar(0.0)

        self.var.SumETpot =  globals.inZero
        self.var.SumETpotact =   globals.inZero
