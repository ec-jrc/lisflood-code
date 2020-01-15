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

from pcraster import celllength, scalar

import xarray as xr
from pyproj import Proj
import numpy as np

from ..global_modules.add1 import loadmap, compressArray
from ..global_modules.settings import calendar, MaskAttrs, MaskInfo, LisSettings
from . import HydroModule


def coordinatesLand(eastings_forcing, northings_forcing):
    """"""
    maskattrs = MaskAttrs.instance()
    half_cell = maskattrs['cell'] / 2.
    top_row = np.where(np.round(northings_forcing, 5) == np.round(maskattrs['y'] - half_cell, 5))[0][0]
    left_col = np.where(np.round(eastings_forcing, 5) == np.round(maskattrs['x'] + half_cell, 5))[0][0]
    row_slice = slice(top_row, top_row + maskattrs['row'])
    col_slice = slice(left_col, left_col + maskattrs['col'])
    maskinfo = MaskInfo.instance()
    return [co[row_slice, col_slice][~maskinfo.info.mask] for co in np.meshgrid(eastings_forcing, northings_forcing)]


class miscInitial(HydroModule):

    """
    Miscellaneous repeatedly used expressions
    """
    input_files_keys = {'all': ['DtSecChannel', 'DtSec', 'GwLoss', 'GwPercValue', 'PrScaling', 'CalEvaporation'],
                        'gridSizeUserDefined': ['PixelLengthUser', 'PixelAreaUser']}
    module_name = 'MiscInitial'

    def __init__(self, misc_variable):
        self.var = misc_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the misc module
        """
        settings = LisSettings.instance()
        option = settings.options
        binding = settings.binding
        maskinfo = MaskInfo.instance()
        maskattrs = MaskAttrs.instance()
        if option['gridSizeUserDefined']:

            # <lfoption name="gridSizeUserDefined" choice="1" default="0">
            # If option gridsizeUserDefined is activated, users can specify grid size properties
            # in separate maps. This is useful whenever this information cannot be derived from
            # the location attributes of the base maps (e.g. lat/lon systems or non-equal-area
            # projections)
            # Limitation: always assumes square grid cells (not rectangles!). Size of grid cells
            # may vary across map though

            self.var.PixelLengthPcr = loadmap('PixelLengthUser', pcr=True)
            self.var.PixelLength = compressArray(self.var.PixelLengthPcr)
            # Length of pixel [m]
            # Area of pixel [m2]
            self.var.PixelAreaPcr = loadmap('PixelAreaUser', pcr=True)
            self.var.PixelArea = compressArray(self.var.PixelAreaPcr)

        else:
            # Default behaviour: grid size is derived from location attributes of
            # base maps. Requirements:
            # - Maps are in some equal-area projection
            # - Length units meters
            # - All grid cells have the same size

            # Length of pixel [m]
            self.var.PixelLengthPcr = celllength()
            self.var.PixelLength = maskattrs['cell']
            # Area of pixel [m2]
            self.var.PixelAreaPcr = self.var.PixelLength ** 2
            self.var.PixelArea=np.empty(maskinfo.info.mapC)
            self.var.PixelArea.fill(self.var.PixelLength ** 2)

#            self.var.PixelArea = spatial(self.var.PixelArea)
            # Convert to spatial expresion (otherwise this variable cannnot be
            # used in areatotal function)

# -----------------------------------------------------------------
        # Miscellaneous repeatedly used expressions (as suggested by GF)

        self.var.InvPixelLength = 1.0 / self.var.PixelLength
        # Inverse of pixel size [1/m]
        self.var.DtSec = loadmap('DtSec')
        self.var.DtDay = self.var.DtSec / 86400.
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
        # date of the first possible model run
        # computation of model steps is referred to CalendarStartDay
        self.var.CalendarDayStart = calendar(binding['CalendarDayStart'], binding['calendar_type'])
        self.var.PrScaling = loadmap('PrScaling')
        self.var.CalEvaporation = loadmap('CalEvaporation')

        self.var.Precipitation = None
        self.var.Tavg = None
        self.var.ETRef = None
        self.var.ESRef = None
        self.var.EWRef = None
        # setting meteo data to none - is this necessary?

        self.var.DayCounter = 0.0
        self.var.MonthETpot = maskinfo.in_zero()
        self.var.MonthETact = maskinfo.in_zero()
        self.var.MonthWDemand = maskinfo.in_zero()
        self.var.MonthWUse= maskinfo.in_zero()
        self.var.MonthWDemand= maskinfo.in_zero()
        self.var.MonthDis= maskinfo.in_zero()
        self.var.MonthInternalFlow = maskinfo.in_zero()

        self.var.TotalInternalFlowM3 = maskinfo.in_zero()
        self.var.PerMonthInternalFlowM3 = maskinfo.in_zero()
        # total freshwater generated in the sub-area (m3), basically local P-ET-Storage
        self.var.TotalExternalInflowM3 = maskinfo.in_zero()
        self.var.PerMonthExternalInflowM3 = maskinfo.in_zero()
        # Total channel inflow (m3) from inlet points
        self.var.PerMonthWaterDemandM3 = maskinfo.in_zero()
        self.var.PerMonthWaterUseM3 = maskinfo.in_zero()

        self.var.FlagDemandBiggerUse = scalar(0.0)

        self.var.TotWEI = scalar(0.0)
        self.var.TotlWEI = scalar(0.0)
        self.var.TotCount = scalar(0.0)

        self.var.SumETpot = maskinfo.in_zero()
        self.var.SumETpotact = maskinfo.in_zero()

        # Read the latitude (radians) from the precipitation forcing NetCDF file
        with xr.open_dataset(binding["PrecipitationMaps"] + ".nc") as nc:
            if all([co in nc.dims for co in ("x", "y")]):
                try:
                    # look for the projection variable
                    proj_var = [v for v in nc.data_vars.keys() if 'proj4_params' in nc[v].attrs.keys()][0]
                    # proj4 string
                    proj4_params = nc[proj_var].attrs['proj4_params']
                    # projection object obtained from the PROJ4 string
                except IndexError:
                    try:
                        proj4_params = binding['proj4_params']
                    except KeyError:
                        raise Exception("If using projected coordinates (x, y), a variable with the 'proj4_params' "
                                        "attribute must be included in the precipitation file or in settings file!")

                # projection object obtained from the PROJ4 string
                projection = Proj(proj4_params)
                _, lat_deg = projection(*coordinatesLand(nc.x.values, nc.y.values), inverse=True)  # latitude (degrees)
            else:
                _, lat_deg = coordinatesLand(nc.lon.values, nc.lat.values)  # latitude (degrees)
        self.var.lat_rad = np.radians(lat_deg)  # latitude (radians)
