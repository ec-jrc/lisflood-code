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


class snow(object):

    """
    # ************************************************************
    # ***** RAIN AND SNOW *****************************************
    # ************************************************************

    # Domain: snow calculations evaluated for center points of 3 sub-pixel
    # snow zones A, B, and C, which each occupy one-third of the pixel surface
    #
    # Variables 'snow' and 'rain' at end of this module are the pixel-average snowfall and rain
    #
    # Zone A: lower third
    # Zone B: center third
    # Zone C: upper third
    """

    def __init__(self, snow_variable):
        self.var = snow_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the snow module
        """
        
        self.var.DeltaTSnow = 0.9674 * loadmap('ElevationStD') * loadmap('TemperatureLapseRate')

        # Difference between (average) air temperature at average elevation of
        # pixel and centers of upper- and lower elevation zones [deg C]
        # ElevationStD:   Standard Deviation of the DEM from Bodis (2009)
        # 0.9674:    Quantile of the normal distribution: u(0,833)=0.9674
        #              to split the pixel in 3 equal parts.
        self.var.SnowDayDegrees = 360 / 365.25
        # day of the year to degrees: the sine function returning the snowmelt coefficient has annual periodicity

        # First and last day-of-year for the "summer icemelt season" (approx. 1/4 year over summer) in the Northern (N) and Southern (S) hemispheres
        self.icemelt_start_N, self.icemelt_end_N = 165, 257 # first and last day-of-year for summer icemelt in the Northern hemisphere
        self.icemelt_start_S, self.icemelt_end_S = 347, 74 # first and last day-of-year for summer icemelt in the Southern hemisphere (+182 days wrt N)

        self.var.IceDayDegrees = 2 * self.var.SnowDayDegrees
        # days of summer (15th June-15th Sept.) to degrees: the sine function returning the icemelt coeff. has 1/2 year period, so it makes 1/2 cycle in 1 summer season
        self.var.SnowSeason = loadmap('SnowSeasonAdj') * 0.5
        # default value of range  of seasonal melt factor is set to 1
        # 0.5 x range of sinus function [-1,1]
        self.var.TempSnow = loadmap('TempSnow')
        self.var.SnowFactor = loadmap('SnowFactor')
        self.var.SnowMeltCoef = loadmap('SnowMeltCoef')
        self.var.TempMelt = loadmap('TempMelt')

        SnowCoverAInit = loadmap('SnowCoverAInitValue')
        SnowCoverBInit = loadmap('SnowCoverBInitValue')
        SnowCoverCInit = loadmap('SnowCoverCInitValue')
        self.var.SnowCoverS = [SnowCoverAInit, SnowCoverBInit, SnowCoverCInit]

        # initial snow depth in elevation zones A, B, and C, respectively  [mm]
        self.var.SnowCoverInit = (SnowCoverAInit + SnowCoverBInit + SnowCoverCInit) / 3
        # Pixel-average initial snow cover: average of values in 3 elevation zones
        self.var.SnowCover = globals.inZero.copy()


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the snow module
        """
        self.var.Snow = globals.inZero.copy()
        self.var.Rain = globals.inZero.copy()
        self.var.SnowMelt = globals.inZero.copy()
        self.var.SnowCover = globals.inZero.copy()

        # Snowmelt
        hemisphere_N = self.var.lat_rad > 0
        snowmelt_coeff = np.sin(np.radians((self.var.CalendarDay - 81) * self.var.SnowDayDegrees))

        SeasSnowMeltCoef = self.var.SnowSeason * np.where(hemisphere_N, snowmelt_coeff, -snowmelt_coeff) + self.var.SnowMeltCoef # N and S hemispheres have opposite-sign cycles

        # Icemelt
	    #####################################################
        # # Bugfix from Emiliano - uncomment to make it work
        # # Check if the current day is in the "summer icemelt season" for the Northern (N) and Southern (S) hemispheres
        is_summer_icemelt_N = (self.var.CalendarDay > self.icemelt_start_N) & (self.var.CalendarDay < self.icemelt_end_N)
        is_summer_icemelt_S = (self.var.CalendarDay > self.icemelt_start_S) | (self.var.CalendarDay < self.icemelt_end_S)
        # Icemelt coefficient: the sine function is the same for both hemispheres due to the imposed 1/2 periodicity; the mask is shifted 6 months
        _ice_melt_coeff = np.sin(np.radians((self.var.CalendarDay - self.icemelt_start_N) * self.var.IceDayDegrees))
        ice_melt_coeff_N = _ice_melt_coeff if is_summer_icemelt_N else 0
        ice_melt_coeff_S = _ice_melt_coeff if is_summer_icemelt_S else 0
        SummerSeason = np.where(hemisphere_N, ice_melt_coeff_N, ice_melt_coeff_S)

        #####################################################
        # Bugfix for global simulations - LA 17/7/2018 - uncomment to make it work
        # This bugfix is on hold waiting for approval from main developer
        # Constants
        #SVE= 127.5     # Shifted Vernal Equinox (in days) = Vernal Equinox (20 March) + day shift to have the peak of Summer season on a desired day (9th August instead of 21 June)
        #Sc = 1361      # Solar constant (not really important in this case, as long as it is divided by a meaningful scale parameter)
        #SCp= 400       # Scale parameter of the SummerSeason coefficient
        #SHp= 0.6       # Shape parameter of the SummerSeason coefficient

        #LatRad = 2*np.pi*self.var.lat_rad/360  #Latitude in radians
        #Dec = np.arcsin(0.3987*np.sin(2*np.pi*(self.var.CalendarDay-SVE)/365.25)) #Declination (i.e., CalendarDay in radians)
        
        #H1 = np.arccos(np.sign(-1*np.tan(Dec)*np.tan(LatRad)))
        #H0 = np.arccos(-1*np.tan(Dec)*np.tan(LatRad))
        
        #SSc1=np.maximum(0,Sc/np.pi*(H1*np.sin(LatRad)*np.sin(Dec)+np.sin(H1)*np.cos(LatRad)*np.cos(Dec))/SCp-SHp)
        #SSc0=np.maximum(0,Sc/np.pi*(H0*np.sin(LatRad)*np.sin(Dec)+np.sin(H0)*np.cos(LatRad)*np.cos(Dec))/SCp-SHp)
        
        #mask = np.absolute(-1*np.tan(Dec)*np.tan(LatRad))>1
        # SScoef=np.where(mask,SSc1,SSc0) # org
        #SummerSeason=np.where(mask,SSc1,SSc0) # changed name back to SummerSeason

        ########################################################
        #Previous version with hardcoded dates:
        #if (self.var.CalendarDay > 165) and (self.var.CalendarDay < 260):
        #    SummerSeason = np.sin(math.radians((self.var.CalendarDay - 165) * self.var.IceDayDegrees))
        #else:
        #    SummerSeason = 0.0
        ########################################################


        for i in xrange(3):
            TavgS = self.var.Tavg + self.var.DeltaTSnow * (i - 1)
            # Temperature at center of each zone (temperature at zone B equals Tavg)
            # i=0 -> highest zone
            # i=2 -> lower zone
            SnowS = np.where(TavgS < self.var.TempSnow, self.var.SnowFactor * self.var.Precipitation, globals.inZero)
            # Precipitation is assumed to be snow if daily average temperature is below TempSnow
            # Snow is multiplied by correction factor to account for undercatch of
            # snow precipitation (which is common)
            RainS = np.where(TavgS >= self.var.TempSnow, self.var.Precipitation, globals.inZero)
            # if it's snowing then no rain
            SnowMeltS = (TavgS - self.var.TempMelt) * SeasSnowMeltCoef * (1 + 0.01 * RainS) * self.var.DtDay


            if i < 2:
                IceMeltS = self.var.Tavg * 7.0 * self.var.DtDay * SummerSeason
                # if i = 0 and 1 -> higher and middle zone
            else:
                IceMeltS = TavgS * 7.0 * self.var.DtDay * SummerSeason

            SnowMeltS = np.maximum(np.minimum(SnowMeltS + IceMeltS, self.var.SnowCoverS[i]), globals.inZero)
            self.var.SnowCoverS[i] = self.var.SnowCoverS[i] + SnowS - SnowMeltS

            self.var.Snow += SnowS
            self.var.Rain += RainS
            self.var.SnowMelt += SnowMeltS
            self.var.SnowCover += self.var.SnowCoverS[i]

        self.var.Snow /= 3
        self.var.Rain /= 3
        self.var.SnowMelt /= 3
        self.var.SnowCover /= 3

        self.var.TotalPrecipitation += self.var.Snow + self.var.Rain
        # total precipitation in pixel [mm]



