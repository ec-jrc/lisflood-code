# -------------------------------------------------------------------------
# Name:        groundwater module
# Purpose:
#
# Author:      burekpe
#
# Created:     29.03.2014
# Copyright:   (c) burekpe 2014
# Licence:     <your licence>
# -------------------------------------------------------------------------

from global_modules.add1 import *

class groundwater(object):

    """
    # ************************************************************
    # ***** GROUNDWATER   *****************************************
    # ************************************************************
    """

    def __init__(self, groundwater_variable):
        self.var = groundwater_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the groundwater module
        """

        # ********************************************
        # ****  Groundwater
        # ********************************************
        UpperZoneTimeConstant = loadmap('UpperZoneTimeConstant', force_array=True)
        LowerZoneTimeConstant = loadmap('LowerZoneTimeConstant', force_array=True)
        self.var.UpperZoneK = np.minimum(self.var.DtDay * (1 / UpperZoneTimeConstant), 1)
        self.var.LowerZoneK = np.minimum(self.var.DtDay * (1 / LowerZoneTimeConstant), 1)
        # Reservoir constants for upper- and lower zone
        # Minimize statement in case time constants greater than DtDay (again
        # unlikely, but you never know..)

        if option['InitLisflood']:
            LZAvInflowGuess = self.var.GwPerc - self.var.GwLoss
        else:
            try:
                LZAvInflowGuess = np.minimum(loadmap('LZAvInflowMap'), self.var.GwPerc - self.var.GwLoss)
            except:
                msg = "Repeat InitLisflood: LZAvin.map does not exists or is not compatible with mask map"
                raise LisfloodError(msg)
            # Estimated average inflow rate into lower zone [mm/day]
            # By definition value cannot exceed GwPercValue!
            # LZAvinflowEstimate can be based on climatic data or baseflow
            # analysis, or directly from model (pre)run using "repLZAvInflowMap"
            # option.
        LZAvInflowGuess = makenumpy(LZAvInflowGuess)

        LZSteady = LZAvInflowGuess * LowerZoneTimeConstant
               # Steady-state amount of water in lower store [mm]
        LZInitValue = loadmap('LZInitValue')

        self.var.LZ = np.where(LZInitValue == -9999, LZSteady, LZInitValue)
        # Initialise lower store [mm] with steady-state value if LZInitValue is set to -9999
        self.var.LZThreshold = loadmap('LZThreshold')
          # lz threshold =if lz falls below this there is no outflow to the channel from lz

        self.var.UZ = self.var.initialiseVariableAllVegetation('UZInitValue')
        # Water in upper store [mm]

        # TotalGroundWaterInit=ifthenelse(defined(self.var.MaskMap),self.var.UZ+self.var.LZ,scalar(0.0))
        # total amount of initial groundwater (or, more correctly, water stored
        # in Upper and Lower Zone [mm]

        # Initialising cumulative output variables
        # These are all needed to compute the cumulative mass balance error

        self.var.GwLossCUM = globals.inZero.copy()
        # Cumulative groundwater loss [mm]
        self.var.LZInflowCUM = globals.inZero.copy()
        # Cumulative lower zone inflow [mm]
        # Needed for calculation of average LZ inflow (initialisation)

        self.var.GwPercUZLZ = self.var.allocateVariableAllVegetation()
        self.var.GwLossLZ = globals.inZero.copy()
        self.var.UZOutflow = self.var.allocateVariableAllVegetation()
        self.var.LZOutflow = globals.inZero.copy()



    def dynamic(self):
        # outflow from LZ to channel stops when LZ is below its threshold. LZ can be below its threshold because of water abstractions
        self.var.LZOutflow = np.minimum(self.var.LowerZoneK * self.var.LZ, self.var.LZ - self.var.LZThreshold)
        self.var.LZOutflow = np.maximum(self.var.LZOutflow, 0)
        self.var.LZOutflowToChannel = self.var.LZOutflow
        self.var.LZ -= self.var.LZOutflow
       	# Update upper-, lower zone storage

        self.var.UZOutflowPixel = self.var.deffraction(self.var.UZOutflow)
          # outflow from upper zone as pixel flow

        self.var.GwPercUZLZPixel = self.var.deffraction(self.var.GwPercUZLZ)
          #  Compute pixel-average flux

        self.var.LZ += self.var.GwPercUZLZPixel
      	# (ground)water in lower response box [mm]

        self.var.GwLossLZ = np.maximum(np.minimum(self.var.GwLossStep, self.var.LZ), 0)
      	# same method as GWPerc
      	# maximum value is controlled by GwLossStep (which is GWLoss*DtDay)
		# prevention to go negative, when LZ is negative
        self.var.LZ = self.var.LZ - self.var.GwLossLZ
      	# (ground)water in lower response box [mm]

        self.var.LZInflowCUM += (self.var.GwPercUZLZPixel - self.var.GwLossLZ)
     	# cumulative inflow into lower zone (can be used to improve
        self.var.LZInflowCUM = np.maximum(self.var.LZInflowCUM, 0)
	    # LZInflowCUM would become negativ, if LZInit is set to high
	    # therefore this line is preventing LZInflowCUM getting negativ

        self.var.GwLossPixel = self.var.GwLossLZ
	    # from GROUNDWATER TRANSFER to here
	    # Compute pixel-average fluxes
        self.var.GwLossCUM += self.var.GwLossPixel
	    # Accumulated groundwater loss over simulation period [mm]
        self.var.LZAvInflow = (self.var.LZInflowCUM * self.var.InvDtDay) / self.var.TimeSinceStart
	    # Average inflow into lower zone over executed time steps [mm/day]

        self.var.LZOutflowToChannelPixel = self.var.LZOutflowToChannel

