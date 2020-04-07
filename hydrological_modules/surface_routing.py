# -------------------------------------------------------------------------
# Name:        surface_routing module
# Purpose:
#
# Author:      burekpe
#
# Created:     29.03.2014
# Copyright:   (c) burekpe 2014
# Licence:     <your licence>
# -------------------------------------------------------------------------



from global_modules.add1 import *
from .kinematic_wave_parallel import kinematicWave


class surface_routing(object):

    """
    # ************************************************************
    # ***** SURFACE ROUTING **************************************
    # ************************************************************
    """

    def __init__(self, surface_routing_variable):
        self.var = surface_routing_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the surface_routing module
        """
        # Initial overland flow storage [m3]
        self.var.OFM3Other = makenumpy(loadmap('OFOtherInitValue'))
        self.var.OFM3Forest = makenumpy(loadmap('OFForestInitValue'))
        self.var.OFM3Direct = makenumpy(loadmap('OFDirectInitValue'))
        # initial overland flow water depth [mm]
        # for initial water in CHANNEL see CHANNEL GEOMETRY section below!
        self.var.WaterDepth = globals.inZero.copy()


# ************************************************************
# ***** ROUTING OF SURFACE RUNOFF
# ************************************************************

        Grad = np.maximum(loadmap('Grad'), loadmap('GradMin'))
        # Set gradient to minimum value to prevent MV creation later on.

        self.var.NoSubStepsOF = 1
        # Number of sub-steps applied in kinematic wave routing. Currently fixed
        # at 1 (number of timeslices in kinwavestate, flux must have ordinal datatype!)

        OFWettedPerimeter = self.var.PixelLength + 2 * self.var.MMtoM * loadmap('OFDepRef')
        # Wetted perimeter overland flow [m] pixel width +
        # 2 times fixed reference depth
        # (Note that using grid size as flow width is a bit odd, as results will depend on cell size!)

        # Alpha to separate int 3 different overland routing: forest, water and sealed area, remaining area
        # overland flow Alpha for kinematic wave
        self.var.OFAlpha = (((self.var.NManning / np.sqrt(Grad)) ** self.var.Beta) * (OFWettedPerimeter ** self.var.AlpPow)).astype(float)
        self.var.InvOFAlpha  = 1 / self.var.OFAlpha
        # Initial overland discharge [m3 s-1]
        self.var.OFQDirect = ((self.var.OFM3Direct * self.var.InvPixelLength * self.var.InvOFAlpha.loc["Direct"].values)**(self.var.InvBeta)).astype(float)
        self.var.OFQOther = ((self.var.OFM3Other * self.var.InvPixelLength * self.var.InvOFAlpha.loc["Other"].values)**(self.var.InvBeta)).astype(float)
        self.var.OFQForest = ((self.var.OFM3Forest * self.var.InvPixelLength * self.var.InvOFAlpha.loc["Forest"].values)**(self.var.InvBeta)).astype(float)


    def initialSecond(self):
        """ 2nd initialisation part of the surface routing module:
            to be called after all needed parameters are set (PixelLength, LddToChan, Alpha...)
            PRE-PROCESSING OF FLOW DIRECTION MATRIX FOR PARALLELISED KINEMATIC WAVE ROUTING
        """
        dt_surf_routing = self.var.DtSec / self.var.NoSubStepsOF
        land_mask = ~maskinfo["mask"]
        num_threads = int(binding["numCPUs_parallelKinematicWave"])
        self.direct_surface_router = kinematicWave(compressArray(self.var.LddToChan), land_mask, self.var.OFAlpha.loc["Direct"].values, self.var.Beta,\
                                                   self.var.PixelLength, dt_surf_routing, num_threads)
        self.other_surface_router = kinematicWave(compressArray(self.var.LddToChan), land_mask, self.var.OFAlpha.loc["Other"].values, self.var.Beta,\
                                                  self.var.PixelLength, dt_surf_routing, num_threads)
        self.forest_surface_router = kinematicWave(compressArray(self.var.LddToChan), land_mask, self.var.OFAlpha.loc["Forest"].values, self.var.Beta,\
                                                   self.var.PixelLength, dt_surf_routing, num_threads)


    def dynamic(self):
        """ dynamic part of the surface routing module
        """
        # ************************************************************
        # ***** COMPONENTS OF RUNOFF                               ***
        # ************************************************************
        self.var.SurfaceRunSoil = self.var.allocateDataArray([self.var.dim_landuse, self.var.dim_pixel])
        for landuse, veg_list in LANDUSE_VEGETATION.items():
            self.var.SurfaceRunSoil.loc[landuse] = (self.var.SoilFraction.loc[veg_list] * \
                    np.maximum(self.var.AvailableWaterForInfiltration.loc[veg_list] - self.var.Infiltration.loc[veg_list], 0)).sum("vegetation")

        self.var.SurfaceRunoff = self.var.DirectRunoff + self.var.SurfaceRunSoil.sum("landuse").values
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
        SideflowOther = self.var.SurfaceRunSoil.loc[["Rainfed","Irrigated"]].sum("landuse").values * self.var.MMtoM3 * self.var.InvPixelLength * self.var.InvDtSec
        SideflowForest = self.var.SurfaceRunSoil.loc["Forest"].values * self.var.MMtoM3 * self.var.InvPixelLength * self.var.InvDtSec
        # All surface runoff that is generated during current time step added as side flow [m3/s/m pixel-length]

        self.direct_surface_router.kinematicWaveRouting(self.var.OFQDirect, SideflowDirect)
        self.other_surface_router.kinematicWaveRouting(self.var.OFQOther, SideflowOther)
        self.forest_surface_router.kinematicWaveRouting(self.var.OFQForest, SideflowForest)

        self.var.OFM3Direct = self.var.PixelLength * self.var.OFAlpha.loc["Direct"].values * self.var.OFQDirect**self.var.Beta
        self.var.OFM3Other = self.var.PixelLength * self.var.OFAlpha.loc["Other"].values * self.var.OFQOther**self.var.Beta
        self.var.OFM3Forest = self.var.PixelLength * self.var.OFAlpha.loc["Forest"].values * self.var.OFQForest**self.var.Beta

        self.var.Qall = self.var.OFQDirect + self.var.OFQOther + self.var.OFQForest
        self.var.M3all = self.var.OFM3Direct + self.var.OFM3Other + self.var.OFM3Forest

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
