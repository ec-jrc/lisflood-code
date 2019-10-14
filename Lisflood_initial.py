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
import xarray as xr
from numba import njit
from collections import OrderedDict

from hydrological_modules.miscInitial import *

from hydrological_modules.readmeteo import *
from hydrological_modules.leafarea import *
from hydrological_modules.inflow import *
from hydrological_modules.landusechange import *
from hydrological_modules.snow import *
from hydrological_modules.frost import *
from hydrological_modules.soil import *
from hydrological_modules.routing import *
from hydrological_modules.groundwater import *
from hydrological_modules.surface_routing import *
from hydrological_modules.reservoir import *
from hydrological_modules.lakes import *
from hydrological_modules.polder import *
#from hydrological_modules.wateruse import *
from hydrological_modules.waterabstraction import *
from hydrological_modules.indicatorcalc import *

from hydrological_modules.riceirrigation import *

from hydrological_modules.evapowater import *
from hydrological_modules.transmission import *

#from hydrological_modules.soilloop_OLD import * # TEST SOILLOOP SPEED-UP
from hydrological_modules.soilloop import *
from hydrological_modules.opensealed import *
from hydrological_modules.waterbalance import *
from hydrological_modules.waterlevel import *
from hydrological_modules.structures import *

from global_modules.output import *
from global_modules.stateVar import *
from global_modules.add1 import readInputWithBackup


@njit(fastmath=True)
def _vegSum(ax_veg, variable, soil_fracs):
    return (soil_fracs * variable).sum(ax_veg)


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

#        self.soilloop_module_OLD = soilloop_OLD(self) # TEST SOILLOOP SPEED-UP
        self.soilloop_module = soilloop(self)
        self.opensealed_module = opensealed(self)
        self.waterbalance_module = waterbalance(self)
        self.waterlevel_module = waterlevel(self)
        self.structures_module = structures(self)

        self.prescribed_vegetation = PRESCRIBED_VEGETATION
        self.interactive_vegetation = []
        if option["cropsEPIC"]:
            if int(binding["DtSec"]) != 86400:
                raise Exception("EPIC runs only using daily time steps!")
            from EPIC_modules.EPIC_main import EPIC_main # EPIC: agriculture simulator
            self.crop_module = EPIC_main(self) # EPIC: agriculture simulation
            if option["allIrrigIsEPIC"]: # the whole irrigated cropland is simulated by EPIC: remove 'Irrigated_prescribed' soil fraction
                self.prescribed_vegetation.remove('Irrigated_prescribed') # (also removed from PRESCRIBED_VEGETATION)
                _ = VEGETATION_LANDUSE.pop('Irrigated_prescribed')
                LANDUSE_VEGETATION['Irrigated'] = []
                _ = PRESCRIBED_LAI.pop('Irrigated_prescribed')
            VEGETATION_LANDUSE.update(self.crop_module.crop2landuse.to_dict()) # add EPIC crops to dictionary mapping vegetation fractions to land use types
            LANDUSE_VEGETATION["Rainfed"] += self.crop_module.rainfed_crops.tolist()
            LANDUSE_VEGETATION["Irrigated"] += self.crop_module.irrigated_crops.tolist()
            self.interactive_vegetation += self.crop_module.simulated_crops.tolist()
        self.vegetation = self.prescribed_vegetation + self.interactive_vegetation

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
        self.soilloop_module.initial()

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

        if option["cropsEPIC"]:
            self.crop_module.initial() # EPIC: agriculture simulator

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

    @property
    def num_pixel(self):
        """"""
        return maskinfo['mapC'][0]

    @property
    def dim_pixel(self):
        """"""
        return ("pixel", np.arange(self.num_pixel))

    @property
    def dim_vegetation(self):
        """"""
        return ("vegetation", self.vegetation[:])

    @property
    def dim_landuse(self):
        """"""
        return ("landuse", SOIL_USES[:])

    @property
    def dim_runoff(self):
        """"""
        return ("runoff", ["Other", "Forest", "Direct"])

    @property
    def coord_landuse(self):
        """"""
        return OrderedDict([self.dim_landuse, self.dim_pixel])

    @property
    def coord_vegetation(self):
        """"""
        return OrderedDict([self.dim_vegetation, self.dim_pixel])

    @property
    def coord_prescribed_vegetation(self):
        """"""
        return OrderedDict([("vegetation", self.prescribed_vegetation[:]), self.dim_pixel])

    def allocateVariableAllVegetation(self, dtype=float):
        """Allocate xarray.DataArray filled by 0 with dimensions 'vegetation' and 'pixel'. It covers all vegetation types (including EPIC crops, if simulated)."""
        return self.allocateDataArray(self.coord_vegetation, dtype)

    def allocateDataArray(self, dimensions, dtype=float):
        """Allocate xarray.DataArray filled by 0 with input dimensions.
           Argument 'dimensions' is a list of tuples of the type ('dimension name', coordinate list/array)."""
        coords = OrderedDict(dimensions)
        return xr.DataArray(np.zeros(map(len, coords.values()), dtype), coords=coords, dims=coords.keys())

    def initialiseVariableAllVegetation(self, name, coords=None):
        """Load a DataArray from a model output netCDF file (typycally an end map).
        This function allows reading netCDF variables with more than 3 dimesnions (time, y, x) into a xarray.DataArray.
        The coords argument is used if name does not point to a netCDF file: coordinates to allocate the DataArray before assigning a default value."""
        file_path = binding[name]
        if os.path.exists(file_path):
            variable = ".".join(os.path.split(file_path)[1].split(".")[:-1]) # the outer join allows treating variables name of the type 'variable.end'
            try:
                with xr.open_dataset(file_path)[variable] as nc:
                    coords = [(dim, nc.coords[dim].values) for dim in nc.dims[:-2]] + [self.dim_pixel]
                    values = nc.values[...,~maskinfo["mask"]]
            except:
                raise Exception("{} must be a netCDF file! Check the input {} in the settings file!".format(file_path, name))
        else:
            try:
                if coords is None:
                    coords = self.coord_vegetation
                values = float(file_path)
            except:
                raise Exception("The input {} must be either the path to a netCDF file or a string that can be converted to a float!".format(name))
        output = self.allocateDataArray(coords)
        output[:] = values
        return output

    def defsoil(self, name_1, name_2=None, name_3=None, coords=None):
        """Load input/parameter static maps for 3 pixel fractions and arrange them in a xarray.DataArray.
           Default fractions: Rainfed, Forest, Irrigated. Other fractions can be specified via the coords keyword argument """
        if coords is None:
            coords = self.coord_landuse
        data = self.allocateDataArray(coords)
        values_1 = readInputWithBackup(name_1)
        labels = coords.values()[0]
        data.loc[labels[0],:] = values_1
        data.loc[labels[1],:] = readInputWithBackup(name_2, values_1)
        data.loc[labels[2],:] = readInputWithBackup(name_3, values_1)
        return data

    def deffraction(self, variable):
        """Weighted sum over the soil fractions of each pixel"""
        ax_veg = variable.dims.index("vegetation")
        return _vegSum(ax_veg, variable.values, self.SoilFraction.values)
