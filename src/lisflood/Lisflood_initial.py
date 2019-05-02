# -------------------------------------------------------------------------
# Name:       Lisflood Model Initial
# Purpose:
#
# Author:      burekpe
#
# Created:     27/02/2014
# Copyright:   (c) burekpe 2014
# Licence:     <your licence>
# -------------------------------------------------------------------------


from lisflood.hydrological_modules.miscInitial import *

from lisflood.hydrological_modules.readmeteo import *
from lisflood.hydrological_modules.leafarea import *
from lisflood.hydrological_modules.inflow import *
from lisflood.hydrological_modules.landusechange import *
from lisflood.hydrological_modules.snow import *
from lisflood.hydrological_modules.frost import *
from lisflood.hydrological_modules.soil import *
from lisflood.hydrological_modules.routing import *
from lisflood.hydrological_modules.groundwater import *
from lisflood.hydrological_modules.surface_routing import *
from lisflood.hydrological_modules.reservoir import *
from lisflood.hydrological_modules.lakes import *
from lisflood.hydrological_modules.polder import *
#from lisflood.hydrological_modules.wateruse import *
from lisflood.hydrological_modules.waterabstraction import *
from lisflood.hydrological_modules.indicatorcalc import *

from lisflood.hydrological_modules.riceirrigation import *

from lisflood.hydrological_modules.evapowater import *
from lisflood.hydrological_modules.transmission import *

from lisflood.hydrological_modules.soilloop import *
from lisflood.hydrological_modules.opensealed import *
from lisflood.hydrological_modules.waterbalance import *
from lisflood.hydrological_modules.waterlevel import *
from lisflood.hydrological_modules.structures import *

from global_modules.output import *
from global_modules.stateVar import *

# --------------------------------------------
class LisfloodModel_ini(DynamicModel):

    """ LISFLOOD initial part
        same as the PCRaster script -initial-
        this part is to initialize the variables
        it will call the initial part of the hydrological modules
    """

    def __init__(self):
        """ init part of the initial part
            defines the mask map and the outlet points
            initialization of the hydrological modules
        """
        DynamicModel.__init__(self)

        # try to make the maskmap more flexible e.g. col, row,x1,y1  or x1,x2,y1,y2
        self.MaskMap = loadsetclone('MaskMap')

        if option['readNetcdfStack']:
            # get the extent of the maps from the precipitation input maps
            # and the modelling extent from the MaskMap
            # cutmap[] defines the MaskMap inside the precipitation map
            cutmap[0], cutmap[1], cutmap[2], cutmap[3] = mapattrNetCDF(binding['E0Maps'])
        if option['writeNetcdfStack'] or option['writeNetcdf']:
            # if NetCDF is writen, the pr.nc is read to get the metadata
            # like projection
            metaNetCDF()

        # ----------------------------------------

        # include all the hydrological modules
        self.misc_module = miscInitial(self)
        self.readmeteo_module = readmeteo(self)
        self.landusechange_module = landusechange(self)
        self.leafarea_module = leafarea(self)
        self.snow_module = snow(self)
        self.frost_module = frost(self)
        self.inflow_module = inflow(self)
        self.soil_module = soil(self)
        self.routing_module = routing(self)
        self.groundwater_module = groundwater(self)
        self.surface_routing_module = surface_routing(self)
        self.reservoir_module = reservoir(self)
        self.lakes_module = lakes(self)
        self.polder_module = polder(self)
#
        self.waterabstraction_module = waterabstraction(self)
        self.indicatorcalc_module = indicatorcalc(self)

        self.riceirrigation_module = riceirrigation(self)
        self.evapowater_module = evapowater(self)
        self.transmission_module = transmission(self)

        self.soilloop_module = soilloop(self)
        self.opensealed_module = opensealed(self)
        self.waterbalance_module = waterbalance(self)
        self.waterlevel_module = waterlevel(self)
        self.structures_module = structures(self)

        # --------------------------------------

        # include stateVar modules
        self.stateVar_module = stateVar(self)

        # run intial misc to get all global variables
        self.misc_module.initial()

        # include output of tss and maps
        self.output_module = outputTssMap(self)

        MMaskMap = self.MaskMap
        # for checking maps

        self.ReportSteps = ReportSteps['rep']

        self.landusechange_module.initial()

        self.snow_module.initial()
        self.frost_module.initial()
        self.leafarea_module.initial()

        self.soil_module.initial()
        self.routing_module.initial()

        self.groundwater_module.initial()
        self.waterlevel_module.initial()

        self.inflow_module.initial()
        self.surface_routing_module.initial()

        self.reservoir_module.initial()
        self.lakes_module.initial()
        self.polder_module.initial()

        self.transmission_module.initial()
        self.output_module.initial()

        self.structures_module.initial()
        # Structures such as reservoirs and lakes are modelled by interrupting the channel flow paths

        # ----------------------------------------------------------------------
        # ----------------------------------------------------------------------

        self.routing_module.initialSecond()
        # CHANNEL INITIAL SPLIT UP IN SECOND CHANNEL
        self.surface_routing_module.initialSecond()
        self.evapowater_module.initial()
        self.riceirrigation_module.initial()
        self.waterabstraction_module.initial()
        self.indicatorcalc_module.initial()

        self.waterbalance_module.initial()
        # calculate initial amount of water in the catchment


        # debug start
        if Flags['debug']:
            # Print value of variables after initialization (from state files)
            nomefile = 'Debug_init_'+str(self.currentStep+1)+'.txt'
            ftemp1 = open(nomefile, 'w+')
            nelements = len(self.ChanM3)
            for i in range(0,nelements-1):
                if  hasattr(self,'CrossSection2Area'):
                    print >> ftemp1, i, self.TotalCrossSectionArea[i], self.CrossSection2Area[i], self.ChanM3[i], \
                    self.Chan2M3Kin[i]
                else:
                    print >> ftemp1, i, self.TotalCrossSectionArea[i], self.ChanM3[i]

            ftemp1.close()




# ====== INITIAL ================================
    def initial(self):
        """ Initial part of LISFLOOD
            calls the initial part of the hydrological modules
        """
        # ----------------------------------------------------------------------
        # Perturbe the states
        #self.groundwater_module.var.UpperZoneK = perturbState(self.groundwater_module.var.UpperZoneK, method = "normal", minVal=0, maxVal=100, mu=self.groundwater_module.var.UpperZoneK, sigma=0.05, spatial=False)
        #self.groundwater_module.var.UZ = perturbState(self.groundwater_module.var.UZ, method = "normal", minVal=0, maxVal=100, mu=10, sigma=3, spatial=False, single=False)
        #pass

# ====== METHODS ================================
    def deffraction(self, para):
        """Weighted sum over the fractions of each pixel"""
        return para[0] * self.OtherFraction + para[1] * self.ForestFraction + para[2] * self.IrrigationFraction
