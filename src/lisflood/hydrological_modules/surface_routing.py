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

from ..global_modules.add1 import loadmap, makenumpy, compressArray
from ..global_modules.settings import MaskInfo, LisSettings
from .kinematic_wave_parallel import kinematicWave
from . import HydroModule


class surface_routing(HydroModule):

    """
    # ************************************************************
    # ***** SURFACE ROUTING **************************************
    # ************************************************************
    """
    input_files_keys = {'all': ['OFOtherInitValue', 'OFForestInitValue', 'OFDirectInitValue',
                                'Grad', 'GradMin', 'OFDepRef']}
    module_name = 'SurfaceRouting'

    def __init__(self, surface_routing_variable):
        self.var = surface_routing_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the surface_routing module
        """
        maskinfo = MaskInfo.instance()
        # CM mod
        OFM3OtherInit = loadmap('OFOtherInitValue')
        OFM3ForestInit = loadmap('OFForestInitValue')
        OFM3DirectInit = loadmap('OFDirectInitValue')
        self.var.WaterDepth = maskinfo.in_zero()

        # self.var.WaterDepthInit =loadmap('WaterDepthInitValue')
        # self.var.WaterDepthInit = makenumpy(self.var.WaterDepthInit)
        # self.var.WaterDepth = self.var.WaterDepthInit.copy()
        # initial overland flow water depth [mm]
        # for initial water in CHANNEL see CHANNEL GEOMETRY section below!
        ## end CM mod

        self.var.OFM3Other = makenumpy(OFM3OtherInit)
        self.var.OFM3Forest = makenumpy(OFM3ForestInit)
        self.var.OFM3Direct = makenumpy(OFM3DirectInit)

# ************************************************************
# ***** ROUTING OF SURFACE RUNOFF
# ************************************************************

        Grad = np.maximum(loadmap('Grad'), loadmap('GradMin'))
        # Set gradient to minimum value to prevent MV creation later on.

        self.var.NoSubStepsOF = 1
        # Number of sub-steps applied in kinematic wave routing of the Overland Flow.
        # Number of sub-steps applied in kinematic wave routing. Currently fixed
        # at 1 (number of timeslices in kinwavestate, flux must have ordinal datatype!)

        OFWettedPerimeter = self.var.PixelLength + 2 * self.var.MMtoM * loadmap('OFDepRef')
        # Wetted perimeter overland flow [m] pixel width +
        # 2 times fixed reference depth
        # (Note that using grid size as flow width is a bit odd, as results will depend on cell size!)

        AlpTermOF = [(self.var.NManning[0] / (np.sqrt(Grad))) ** self.var.Beta, (self.var.NManning[1] / (np.sqrt(Grad))) ** self.var.Beta, (self.var.NManning[2] / (np.sqrt(Grad))) ** self.var.Beta]
        # self.var.OFAlpha = [AlpTermOF[0]*(OFWettedPerimeter**AlpPow),AlpTermOF[1]*(OFWettedPerimeter**AlpPow),AlpTermOF[2]*(OFWettedPerimeter**AlpPow)]

        self.var.OFAlphaOther = (AlpTermOF[0] * (OFWettedPerimeter ** self.var.AlpPow)).astype(float)
        self.var.OFAlphaForest = (AlpTermOF[1] * (OFWettedPerimeter ** self.var.AlpPow)).astype(float)
        self.var.OFAlphaDirect = (AlpTermOF[2] * (OFWettedPerimeter ** self.var.AlpPow)).astype(float)
        self.var.InvOFAlphaOther  = 1 / self.var.OFAlphaOther
        self.var.InvOFAlphaForest = 1 / self.var.OFAlphaForest
        self.var.InvOFAlphaDirect = 1 / self.var.OFAlphaDirect

        # Alpha to separate int 3 different overland routing: forest, water and sealed area, remaining area
        # overland flow Alpha for kinematic wave
        # OFCrossSectionArea = self.var.MMtoM * self.var.WaterDepth * self.var.PixelLength
        # Overland flow initial cross-sectional area [m2]
        # OFM3all = OFCrossSectionArea * self.var.PixelLength
        # Initial overland flow storage [m3]
        # self.var.OFM3=[cover(OFM3all*self.var.OtherFraction,scalar(0.0)),cover(OFM3all*self.var.ForestFraction,scalar(0.0)),cover(OFM3all*(self.var.DirectRunoffFraction+self.var.WaterFraction),scalar(0.0))]

        # Initial overland discharge [m3 s-1]
        self.var.OFQDirect = ((self.var.OFM3Direct * self.var.InvPixelLength * self.var.InvOFAlphaDirect) ** self.var.InvBeta).astype(float)
        self.var.OFQOther = ((self.var.OFM3Other * self.var.InvPixelLength * self.var.InvOFAlphaOther) ** self.var.InvBeta).astype(float)
        self.var.OFQForest = ((self.var.OFM3Forest * self.var.InvPixelLength * self.var.InvOFAlphaForest) ** self.var.InvBeta).astype(float)

    def initialSecond(self):
        """ 2nd initialisation part of the surface routing module:
            to be called after all needed parameters are set (PixelLength, LddToChan, Alpha...)
            PRE-PROCESSING OF FLOW DIRECTION MATRIX FOR PARALLELISED KINEMATIC WAVE ROUTING
        """
        dt_surf_routing = self.var.DtSec / self.var.NoSubStepsOF
        maskinfo = MaskInfo.instance()
        land_mask = ~maskinfo.info.mask
        settings = LisSettings.instance()
        binding = settings.binding
        num_threads = int(binding["numCPUs_parallelKinematicWave"])
        self.direct_surface_router = kinematicWave(compressArray(self.var.LddToChan), land_mask, self.var.OFAlphaDirect, self.var.Beta,\
                                                   self.var.PixelLength, dt_surf_routing, num_threads)
        self.other_surface_router = kinematicWave(compressArray(self.var.LddToChan), land_mask, self.var.OFAlphaOther, self.var.Beta,\
                                                  self.var.PixelLength, dt_surf_routing, num_threads)
        self.forest_surface_router = kinematicWave(compressArray(self.var.LddToChan), land_mask, self.var.OFAlphaForest, self.var.Beta,\
                                                   self.var.PixelLength, dt_surf_routing, num_threads)

    def dynamic(self):
        """ dynamic part of the surface routing module
        """
        # ************************************************************
        # ***** COMPONENTS OF RUNOFF                               ***
        # ************************************************************
        self.var.SurfaceRunOther = self.var.OtherFraction * \
            np.maximum(self.var.AvailableWaterForInfiltration[0] - self.var.Infiltration[0], 0)
        self.var.SurfaceRunForest = self.var.ForestFraction * \
            np.maximum(self.var.AvailableWaterForInfiltration[1] - self.var.Infiltration[1], 0)
        self.var.SurfaceRunIrrigation = self.var.IrrigationFraction * \
            np.maximum(self.var.AvailableWaterForInfiltration[2] - self.var.Infiltration[2], 0)

        self.var.SurfaceRunoff = self.var.DirectRunoff + self.var.SurfaceRunOther + self.var.SurfaceRunForest + self.var.SurfaceRunIrrigation
        # Surface runoff for this time step (mm)
        # Note that SurfaceRunoff ONLY includes surface runoff generated during current time
        # step (WaterDepth includes routed runoff from previous steps as well)

        self.var.TotalRunoff = self.var.SurfaceRunoff + self.var.UZOutflowPixel + self.var.LZOutflowToChannelPixel

        # ************************************************************
        # ***** ROUTING SURFACE RUNOFF TO CHANNEL ********************
        # ************************************************************

        # Domain: whole pixel
        # Routing of overland flow to channel using kinematic wave
        # Note that all 'new' water is added as side-flow
        SideflowDirect = self.var.DirectRunoff * self.var.MMtoM3 * self.var.InvPixelLength * self.var.InvDtSec
        SideflowOther = (self.var.SurfaceRunOther + self.var.SurfaceRunIrrigation) * self.var.MMtoM3 * self.var.InvPixelLength * self.var.InvDtSec
        SideflowForest = self.var.SurfaceRunForest * self.var.MMtoM3 * self.var.InvPixelLength * self.var.InvDtSec
        # All surface runoff that is generated during current time step added as side flow [m3/s/m pixel-length]

        self.direct_surface_router.kinematicWaveRouting(self.var.OFQDirect, SideflowDirect)
        self.other_surface_router.kinematicWaveRouting(self.var.OFQOther, SideflowOther)
        self.forest_surface_router.kinematicWaveRouting(self.var.OFQForest, SideflowForest)

# to PCRASTER

        #SideflowDirect =  decompress(self.var.DirectRunoff * self.var.MMtoM3 * self.var.InvPixelLength * self.var.InvDtSec)
        #SideflowOther =  decompress((self.var.SurfaceRunOther + self.var.SurfaceRunIrrigation) * self.var.MMtoM3 * self.var.InvPixelLength * self.var.InvDtSec)
        #SideflowForest =  decompress(self.var.SurfaceRunForest * self.var.MMtoM3 * self.var.InvPixelLength * self.var.InvDtSec)
        # All surface runoff that is generated during current time
        # step added as side flow [m3/s/m pixel-length]

        # OFM3,OFQ=kinwavestate,kinwaveflux(LddToChan,OFM3,SideflowOF,OFAlpha,beta,NoSubStepsOF,DtSec,PixelLength)
        # self.var.OFQ=kinwaveflux(self.var.LddToChan,self.var.OFM3,SideflowOF,self.var.OFAlpha,self.var.Beta,self.var.NoSubStepsOF,self.var.DtSec,self.var.PixelLength)
        # self.var.OFM3=kinwavestate(self.var.LddToChan,self.var.OFM3,SideflowOF,self.var.OFAlpha,self.var.Beta,self.var.NoSubStepsOF,self.var.DtSec,self.var.PixelLength)

        #pcrOFM3Direct = decompress(self.var.OFM3Direct)
        #pcrOFM3Other = decompress(self.var.OFM3Other)
        #pcrOFM3Forest = decompress(self.var.OFM3Forest)

    #From here in PCRASTER format!

        #self.var.OFM3Direct = compressArray(kinwavestate(self.var.LddToChan, pcrOFM3Direct, SideflowDirect,
        #                      self.var.OFAlphaDirect, self.var.Beta, self.var.NoSubStepsOF, self.var.DtSec, self.var.PixelLengthPcr))
        #self.var.OFM3Other = compressArray(kinwavestate(self.var.LddToChan, pcrOFM3Other, SideflowOther,
        #                      self.var.OFAlphaOther, self.var.Beta, self.var.NoSubStepsOF, self.var.DtSec, self.var.PixelLengthPcr))
        #self.var.OFM3Forest = compressArray(kinwavestate(self.var.LddToChan, pcrOFM3Forest, SideflowForest,
        #                      self.var.OFAlphaForest, self.var.Beta, self.var.NoSubStepsOF, self.var.DtSec, self.var.PixelLengthPcr))
        # Route overland flow to channel using kinematic wave
        # OFQ in [m3/s]
    # End PCRASTER

        #self.var.OFQDirect = (self.var.OFM3Direct * self.var.InvPixelLength *
        #                    self.var.InvOFAlphaDirect)**(self.var.InvBeta)
        #self.var.OFQOther =(self.var.OFM3Other * self.var.InvPixelLength *
        #                    self.var.InvOFAlphaOther)**(self.var.InvBeta)
        #self.var.OFQForest=(self.var.OFM3Forest * self.var.InvPixelLength *
        #                    self.var.InvOFAlphaForest)**(self.var.InvBeta)

        self.var.OFM3Direct = self.var.PixelLength * self.var.OFAlphaDirect * self.var.OFQDirect**self.var.Beta
        self.var.OFM3Other = self.var.PixelLength * self.var.OFAlphaOther * self.var.OFQOther**self.var.Beta
        self.var.OFM3Forest = self.var.PixelLength * self.var.OFAlphaForest * self.var.OFQForest**self.var.Beta
        self.var.Qall = self.var.OFQDirect + self.var.OFQOther + self.var.OFQForest
        self.var.M3all = self.var.OFM3Direct + self.var.OFM3Other + self.var.OFM3Forest
        # Overland flow storage [m3]

        self.var.OFToChanM3 = np.where(self.var.IsChannel, self.var.Qall * self.var.DtSec, 0)

        # Overland flow in channel pixels (in [m3])is added to channel

        self.var.WaterDepth = self.var.M3all * self.var.M3toMM
        # Update water depth [mm]

        ## self.var.ToChanM3Runoff = accuflux(self.var.LddToChan, (decompress(self.var.UZOutflowPixel) + decompress(self.var.LZOutflowToChannelPixel)) * self.var.MMtoM3) + self.var.OFToChanM3

        # All runoff that enters the channel: groundwater + surface runoff
        # Note that all groundwater/inter-flow is routed to nearest river pixel
        # within one time step
        self.var.ToChanM3Runoff =  (self.var.UZOutflowPixel + self.var.LZOutflowToChannelPixel) * self.var.MMtoM3 + self.var.OFToChanM3
        self.var.ToChanM3RunoffDt = self.var.ToChanM3Runoff * self.var.InvNoRoutSteps
        # runoff of 1 substep
