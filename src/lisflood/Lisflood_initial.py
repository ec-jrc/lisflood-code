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

import os
import uuid
from collections import OrderedDict

import numpy as np
try:
    from numba import njit, set_num_threads, get_num_threads, config as numba_config
    numba_full = True
except ImportError:
    import numba
    print('WARNING! Numba version is probably too old. Only limited functionalities will be available for Numba')
    print('Numba version: {}'.format(numba.__version__))
    from numba import njit, config as numba_config
    numba_full = False


from .global_modules.settings import CutMap, LisSettings, NetCDFMetadata, EPICSettings, MaskInfo
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
from .global_modules.add1 import readInputWithBackup
from .global_modules.add1 import NumpyModified

@njit(fastmath=False, cache=True)
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
        self.epic_settings = EPICSettings()
        self.settings = LisSettings.instance()
        self.maskinfo = MaskInfo.instance()
        binding = self.settings.binding
        option = self.settings.options
        flags = self.settings.flags
        report_steps = self.settings.report_steps

        # set the maximum number of threads that numba should use (now used in soilloop only)
        num_threads = int(binding["numCPUs_parallelNumba"])
        if (num_threads>0):
            if num_threads<=numba_config.NUMBA_NUM_THREADS:
                set_num_threads(num_threads)

        # Mapping of vegetation types to land use fractions (and the other way around)
        ##global VEGETATION_LANDUSE, LANDUSE_VEGETATION, PRESCRIBED_VEGETATION, PRESCRIBED_LAI
        self.SOIL_USES = ["Rainfed", "Forest", "Irrigated"]
        self.PRESCRIBED_VEGETATION = [fract + "_prescribed" for fract in self.SOIL_USES]
        self.PRESCRIBED_LAI = OrderedDict(zip(self.PRESCRIBED_VEGETATION[:], ['LAIOtherMaps', 'LAIForestMaps', 'LAIIrrigationMaps']))
        self.VEGETATION_LANDUSE = OrderedDict(zip(self.PRESCRIBED_VEGETATION[:], self.SOIL_USES[:]))
        
        
        
        self.LANDUSE_VEGETATION = OrderedDict([(v, [k]) for k, v in self.VEGETATION_LANDUSE.items()])
        self.LANDUSE_INPUTMAP = OrderedDict(zip(self.LANDUSE_VEGETATION.keys(), ["OtherFraction", "ForestFraction", "IrrigationFraction"]))

        if option['readNetcdfStack']:
            # get the extent of the maps from the netCDF template
            # and the modelling extent from the MaskMap
            # cutmap[] defines the MaskMap inside the precipitation map
            _ = CutMap(*mapattrNetCDF(binding['netCDFtemplate']))  # register cutmaps
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

        self.prescribed_vegetation = self.epic_settings.prescribed_vegetation
        self.interactive_vegetation = []
        if option.get('cropsEPIC'):
            self.prescribed_vegetation = self.epic_settings.prescribed_vegetation
            if int(binding["DtSec"]) != 86400:
                raise Exception("EPIC runs only using daily time steps!")
            from EPIC_modules.EPIC_main import EPIC_main # EPIC: agriculture simulator
            self.crop_module = EPIC_main(self) # EPIC: agriculture simulation
            if option["allIrrigIsEPIC"]: # the whole irrigated cropland is simulated by EPIC: remove 'Irrigated_prescribed' soil fraction
                self.prescribed_vegetation.remove('Irrigated_prescribed') # (also removed from PRESCRIBED_VEGETATION)
                self.epic_settings.vegetation_landuse.pop('Irrigated_prescribed')
                self.epic_settings.landuse_vegetation['Irrigated'] = []
                self.epic_settings.prescribe_lai.pop('Irrigated_prescribed')
            self.epic_settings.vegetation_landuse.update(self.crop_module.crop2landuse.to_dict()) # add EPIC crops to dictionary mapping vegetation fractions to land use types
            self.epic_settings.landuse_vegetation["Rainfed"] += self.crop_module.rainfed_crops.tolist()
            self.epic_settings.landuse_vegetation["Irrigated"] += self.crop_module.irrigated_crops.tolist()
            self.interactive_vegetation += self.crop_module.simulated_crops.tolist()
        self.vegetation = self.prescribed_vegetation + self.interactive_vegetation

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

        if option.get('cropsEPIC'):
            self.crop_module.initial() # EPIC: agriculture simulator

        # debug start
        if flags['debug']:
            # Print value of variables after initialization (from state files)
            nomefile = 'Debug_init_' + str(self.currentStep + 1) + '.txt'
            ftemp1 = open(nomefile, 'w+')
            nelements = len(self.ChanM3)
            for i in range(0, nelements - 1):
                if hasattr(self, 'CrossSection2Area'):
                    print(i, self.TotalCrossSectionArea[i], self.CrossSection2Area[i], self.ChanM3[i], self.Chan2M3Kin[i], file=ftemp1)
                else:
                    print(i, self.TotalCrossSectionArea[i], self.ChanM3[i], file=ftemp1)

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
        pass


# ====== METHODS ================================

    @property
    def num_pixel(self):
        """"""
        return self.maskinfo.info.mapC[0]
        # return maskinfo['mapC'][0]

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
        return ("landuse", self.epic_settings.soil_uses[:])

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

    def get_landuse_and_indexes_from_vegetation_epic(self, veg):
        """"""
        #iveg = self.coord_vegetation['vegetation'].index(veg)
        iveg = self.vegetation.index(veg)
        landuse = self.epic_settings.vegetation_landuse[veg] # landuse corresponding to vegetation fraction
        #ilanduse = self.coord_landuse['landuse'].index(landuse)
        ilanduse = self.epic_settings.soil_uses.index(landuse)
        return iveg,ilanduse,landuse

    def get_landuse_and_indexes_from_vegetation_GLOBAL(self, veg):
        """"""
        iveg = self.vegetation.index(veg)
        landuse = self.VEGETATION_LANDUSE[veg] # landuse corresponding to vegetation fraction
        ilanduse = self.SOIL_USES.index(landuse)
        return iveg,ilanduse,landuse

    def get_indexes_from_landuse_and_veg_list_GLOBAL(self, landuse, veg_list):
        """"""
        ilanduse = self.SOIL_USES.index(landuse)
        iveg_list_pres = []
        iveg_list = []
        for veg in veg_list:
            iveg_list_pres.append(self.PRESCRIBED_VEGETATION.index(veg))
            iveg_list.append(self.vegetation.index(veg))
        return iveg_list,iveg_list_pres,ilanduse

    def allocateVariableAllVegetation(self, dtype=float):
        """Allocate xarray.DataArray filled by 0 with dimensions 'vegetation' and 'pixel'. It covers all vegetation types (including EPIC crops, if simulated)."""
        return self.allocateDataArray(self.coord_vegetation, dtype)

    def allocateDataArray(self, dimensions, dtype=float):
        """Allocate xarray.DataArray filled by 0 with input dimensions.
           Argument 'dimensions' is a list of tuples of the type ('dimension name', coordinate list/array)."""
        coords = OrderedDict(dimensions)
        option = self.settings.options
        if option.get('cropsEPIC'):
            return xr.DataArray(np.zeros([len(v) for v in coords.values()], dtype), coords=coords, dims=coords.keys())
        else:
            return NumpyModified(np.zeros([len(v) for v in coords.values()], dtype), dims=coords.keys())

    def initialiseVariableAllVegetation(self, name, coords=None):
        """Load a DataArray from a model output netCDF file (typycally an end map).
        This function allows reading netCDF variables with more than 3 dimensions (time, y, x) into a xarray.DataArray.
        The coords argument is used if name does not point to a netCDF file: coordinates to allocate the DataArray before assigning a default value."""
        file_path = self.settings.binding[name]
        if os.path.exists(file_path):
            variable = ".".join(os.path.split(file_path)[1].split(".")[:-1]) # the outer join allows treating variables name of the type 'variable.end'
            try:
                with xr.open_dataset(file_path)[variable] as nc:
                    coords = [(dim, nc.coords[dim].values) for dim in nc.dims[:-2]] + [self.dim_pixel]
                    values = nc.values[...,~self.maskinfo.info.mask]  # maskinfo["mask"]
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
        option = self.settings.options
        if option.get('cropsEPIC'):
            labels = list(coords.values())[0]
            data.loc[labels[0],:] = values_1
            data.loc[labels[1],:] = readInputWithBackup(name_2, values_1)
            data.loc[labels[2],:] = readInputWithBackup(name_3, values_1)
        else:
            if (list(coords.keys())[0]=="landuse") or (list(coords.keys())[0]=="runoff"):
                data.values[0][:] = values_1
                data.values[1][:] = readInputWithBackup(name_2, values_1)
                data.values[2][:] = readInputWithBackup(name_3, values_1)
            else:
                raise Exception("Coords key not found!")
        return data

    def deffraction(self, variable):
        """Weighted sum over the soil fractions of each pixel"""
        ax_veg = variable.dims.index("vegetation")
        return _vegSum(ax_veg, variable.values, self.SoilFraction.values)
