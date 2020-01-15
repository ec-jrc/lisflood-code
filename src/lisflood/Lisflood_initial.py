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
from __future__ import print_function, absolute_import

import uuid

from .global_modules.settings import CutMap, LisSettings, NetCDFMetadata
from .global_modules.zusatz import DynamicModel
from .global_modules.add1 import loadsetclone, mapattrNetCDF
from .hydrological_modules.miscInitial import miscInitial

from .hydrological_modules.readmeteo import readmeteo
from .hydrological_modules.leafarea import leafarea
from .hydrological_modules.landusechange import landusechange
from .hydrological_modules.snow import snow
from .hydrological_modules.inflow import inflow
from .hydrological_modules.frost import frost
from .hydrological_modules.soil import soil
from .hydrological_modules.routing import routing
from .hydrological_modules.groundwater import groundwater
from .hydrological_modules.surface_routing import surface_routing
from .hydrological_modules.reservoir import reservoir
from .hydrological_modules.lakes import lakes
from .hydrological_modules.polder import polder
from .hydrological_modules.waterabstraction import waterabstraction
from .hydrological_modules.indicatorcalc import indicatorcalc
from .hydrological_modules.riceirrigation import riceirrigation
from .hydrological_modules.evapowater import evapowater
from .hydrological_modules.transmission import transmission
from .hydrological_modules.soilloop import soilloop
from .hydrological_modules.opensealed import opensealed
from .hydrological_modules.waterbalance import waterbalance
from .hydrological_modules.waterlevel import waterlevel
from .hydrological_modules.structures import structures

from .global_modules.output import outputTssMap
from .global_modules.stateVar import stateVar


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
        settings = LisSettings.instance()
        binding = settings.binding
        option = settings.options
        flags = settings.flags
        report_steps = settings.report_steps

        if option['readNetcdfStack']:
            # get the extent of the maps from the precipitation input maps
            # and the modelling extent from the MaskMap
            # cutmap[] defines the MaskMap inside the precipitation map
            _ = CutMap(*mapattrNetCDF(binding['E0Maps']))  # register cutmaps
            # cutmap[0], cutmap[1], cutmap[2], cutmap[3] = mapattrNetCDF(binding['E0Maps'])
        if option['writeNetcdfStack'] or option['writeNetcdf']:
            # if NetCDF is writen, the pr.nc is read to get the metadata
            # like projection
            _ = NetCDFMetadata(uuid.uuid4())  # init meta netcdf

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

        self.ReportSteps = report_steps['rep']

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
        if flags['debug']:
            # Print value of variables after initialization (from state files)
            nomefile = 'Debug_init_'+str(self.currentStep+1)+'.txt'
            ftemp1 = open(nomefile, 'w+')
            nelements = len(self.ChanM3)
            for i in range(0,nelements-1):
                if  hasattr(self,'CrossSection2Area'):
                    print(i, self.TotalCrossSectionArea[i], self.CrossSection2Area[i], self.ChanM3[i], \
                    self.Chan2M3Kin[i], file=ftemp1)
                else:
                    print(i, self.TotalCrossSectionArea[i], self.ChanM3[i], file=ftemp1)

            ftemp1.close()

    def initial(self):
        """ Initial part of LISFLOOD
            calls the initial part of the hydrological modules
        """
        # ----------------------------------------------------------------------
        # Perturbe the states
        #self.groundwater_module.var.UpperZoneK = perturbState(self.groundwater_module.var.UpperZoneK, method = "normal", minVal=0, maxVal=100, mu=self.groundwater_module.var.UpperZoneK, sigma=0.05, spatial=False)
        #self.groundwater_module.var.UZ = perturbState(self.groundwater_module.var.UZ, method = "normal", minVal=0, maxVal=100, mu=10, sigma=3, spatial=False, single=False)
        pass

# ====== METHODS ================================
    def deffraction(self, para):
        """Weighted sum over the fractions of each pixel"""
        return para[0] * self.OtherFraction + para[1] * self.ForestFraction + para[2] * self.IrrigationFraction
