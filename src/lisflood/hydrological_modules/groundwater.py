"""

Copyright 2019 European Union

Licensed under the EUPL, Version 1.2 or as soon they will be approved by the European Commission
subsequent versions of the EUPL (the "Licence");

You may not use this work except in compliance with the Licence.
You may obtain a copy of the Licence at:

https://joinup.ec.europa.eu/sites/default/files/inline-files/EUPL%20v1_2%20EN(1).txt

Unless required by applicable law or agreed to in writing, software distributed under the Licence is distributed
on an "AS IS" basis, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and limitations under the Licence.

"""
from __future__ import absolute_import, print_function

import numpy as np

from ..global_modules.add1 import loadmap, makenumpy, defsoil
from ..global_modules.settings import LisSettings, MaskInfo
from ..global_modules.errors import LisfloodError
from . import HydroModule


class groundwater(HydroModule):
    """
    # ************************************************************
    # ***** GROUNDWATER   *****************************************
    # ************************************************************
    """
    input_files_keys = {'all': ['UpperZoneTimeConstant', 'LowerZoneTimeConstant', 'LZInitValue',
                                'LZThreshold', 'UZInitValue', 'UZForestInitValue', 'UZIrrigationInitValue']}
    module_name = 'GroundWater'

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
        UpperZoneTimeConstant = loadmap('UpperZoneTimeConstant')
        LowerZoneTimeConstant = loadmap('LowerZoneTimeConstant')
        self.var.UpperZoneK = np.minimum(self.var.DtDay * (1 / UpperZoneTimeConstant), 1)
        self.var.LowerZoneK = np.minimum(self.var.DtDay * (1 / LowerZoneTimeConstant), 1)
        # Reservoir constants for upper- and lower zone
        # Minimize statement in case time constants greater than DtDay (again
        # unlikely, but you never know..)
        settings = LisSettings.instance()
        option = settings.options
        maskinfo = MaskInfo.instance()
        if option['InitLisflood']:
            LZAvInflowGuess = self.var.GwPerc - self.var.GwLoss
        else:
            try:
                LZAvInflowGuess = np.minimum(loadmap('LZAvInflowMap'), self.var.GwPerc - self.var.GwLoss)
            except Exception as e:
                msg = "{} Repeat InitLisflood: LZAvin map not existing or not compatible with mask map".format(str(e))
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
        # Initialise lower store with steady-state value
        # if LZInitValue is set to -9999

        # Water in lower store [mm]
        self.var.LZThreshold = loadmap('LZThreshold')
        # lz threshold =if lz falls below this there is no outflow to the channel from lz

        # UZInitValue=scalar(loadmap('UZInitValue'))
        # UZInit=ifthen(defined(self.var.MaskMap),UZInitValue)
        self.var.UZ = defsoil('UZInitValue', 'UZForestInitValue', 'UZIrrigationInitValue')
        # Water in upper store [mm]

        # TotalGroundWaterInit=ifthenelse(defined(self.var.MaskMap),self.var.UZ+self.var.LZ,scalar(0.0))
        # total amount of initial groundwater (or, more correctly, water stored
        # in Upper and Lower Zone [mm]

        # Initialising cumulative output variables
        # These are all needed to compute the cumulative mass balance error

        self.var.GwLossCUM = maskinfo.in_zero()
        # Cumulative groundwater loss [mm]
        self.var.LZInflowCUM = maskinfo.in_zero()
        # Cumulative lower zone inflow [mm]
        # Needed for calculation of average LZ inflow (initialisation)

        self.var.GwPercUZLZ = defsoil(maskinfo.in_zero())
        self.var.GwLossLZ = maskinfo.in_zero()
        self.var.UZOutflow = defsoil(maskinfo.in_zero())
        self.var.LZOutflow = maskinfo.in_zero()

    def dynamic(self):
        # outflow from LZ to channel stops when LZ is below its threshold.
        # LZ can be below its threshold because of water abstractions
        self.var.LZOutflow = np.minimum(self.var.LowerZoneK * self.var.LZ, self.var.LZ - self.var.LZThreshold)
        # Outflow out of lower zone [mm per model timestep]

        self.var.LZOutflow = np.maximum(self.var.LZOutflow, 0)
        # No outflow if LZ is below threshold
        self.var.LZOutflowToChannel = self.var.LZOutflow
        # And the remaining amount goes to the channel

        self.var.LZ -= self.var.LZOutflow
        # Update upper-, lower zone storage

        self.var.UZOutflowPixel = self.var.deffraction(self.var.UZOutflow)
        # outflow from upper zone as pixel flow
        # to surface routing

        self.var.GwPercUZLZPixel = self.var.deffraction(self.var.GwPercUZLZ)
        #  Compute pixel-average flux
        # to Lower Zone

        self.var.LZ += self.var.GwPercUZLZPixel
        # (ground)water in lower response box [mm]

        self.var.GwLossLZ = np.maximum(np.minimum(self.var.GwLossStep, self.var.LZ), 0.0)
        # same method as GWPerc
        # maximum value is controlled by GwLossStep (which is GWLoss*DtDay)
        # prevention to go negative, when LZ is negative
        self.var.LZ = self.var.LZ - self.var.GwLossLZ
        # (ground)water in lower response box [mm]

        self.var.LZInflowCUM += (self.var.GwPercUZLZPixel - self.var.GwLossLZ)
        # cumulative inflow into lower zone (can be used to improve
        self.var.LZInflowCUM = np.maximum(self.var.LZInflowCUM, 0.0)
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
