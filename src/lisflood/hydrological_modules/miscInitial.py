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

from lisflood.global_modules.add1 import *
import netCDF4
import xarray as xr
from pyproj import Proj

def coordinatesLand(eastings_forcing, northings_forcing):
    """"""
    half_cell = maskmapAttr['cell'] / 2.
    top_row = np.where(northings_forcing == maskmapAttr['y'] - half_cell)[0][0]
    left_col = np.where(eastings_forcing == maskmapAttr['x'] + half_cell)[0][0]
    row_slice = slice(top_row, top_row + maskmapAttr['row'])
    col_slice = slice(left_col, left_col + maskmapAttr['col'])
    return [co[row_slice,col_slice][~maskinfo["mask"]] for co in np.meshgrid(eastings_forcing, northings_forcing)]

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
        # date of the first possible model run
        # computation of model steps is referred to CalendarStartDay
        self.var.CalendarDayStart = Calendar(binding['CalendarDayStart'])
        try:
           # number of time step or date of the state map to be used to initialize model run
           timestepInit.append(binding["timestepInit"])
        except: pass

        self.var.PrScaling = loadmap('PrScaling')
        self.var.CalEvaporation = loadmap('CalEvaporation')

        self.var.Precipitation = None
        self.var.Tavg = None
        self.var.ETRef = None
        self.var.ESRef = None
        self.var.EWRef = None
        # setting meteo data to none - is this necessary?

        self.var.DayCounter= 0.0
        self.var.MonthETpot= globals.inZero
        self.var.MonthETact= globals.inZero
        self.var.MonthWDemand= globals.inZero
        self.var.MonthWUse= globals.inZero
        self.var.MonthWDemand= globals.inZero
        self.var.MonthDis= globals.inZero
        self.var.MonthInternalFlow =  globals.inZero

        self.var.TotalInternalFlowM3 = globals.inZero
        self.var.PerMonthInternalFlowM3 = globals.inZero
        # total freshwater generated in the sub-area (m3), basically local P-ET-Storage
        self.var.TotalExternalInflowM3 = globals.inZero
        self.var.PerMonthExternalInflowM3 = globals.inZero
        # Total channel inflow (m3) from inlet points
        self.var.PerMonthWaterDemandM3 = globals.inZero
        self.var.PerMonthWaterUseM3 = globals.inZero

        self.var.FlagDemandBiggerUse = scalar(0.0)

        self.var.TotWEI = scalar(0.0)
        self.var.TotlWEI = scalar(0.0)
        self.var.TotCount = scalar(0.0)

        self.var.SumETpot = globals.inZero
        self.var.SumETpotact = globals.inZero

        # Read the latitude (radians) from the precipitation forcing NetCDF file
        with xr.open_dataset(binding["PrecipitationMaps"] + ".nc") as nc:
            if all([co in nc.dims for co in ("x", "y")]):
                try:
                    proj_var = [v for v in nc.data_vars.keys() if 'proj4_params' in nc[v].attrs.keys()][0]  # look for the projection variable
                except IndexError:
                    raise Exception("If using projected coordinates (x, y), a variable with the 'proj4_params' attribute must be included in the precipitation file!")
                projection = Proj(nc[proj_var].attrs['proj4_params']) # projection object obtained from the PROJ4 string
                _, lat_deg = projection(*coordinatesLand(nc.x.values, nc.y.values), inverse=True) # latitude (degrees)
            else:
                _, lat_deg = coordinatesLand(nc.lon.values, nc.lat.values)  # latitude (degrees)
        self.var.lat_rad = np.radians(lat_deg)  # latitude (radians)
