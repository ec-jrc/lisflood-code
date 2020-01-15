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
from nine import range

import uuid
import sys
import datetime
import gc

from pcraster.framework import DynamicModel
import numpy as np

from .global_modules.settings import CDFFlags, LisSettings, MaskInfo


class LisfloodModel_dyn(DynamicModel):

    # =========== DYNAMIC ====================================================

    def dynamic(self):
        """ Dynamic part of LISFLOOD
            calls the dynamic part of the hydrological modules
        """
        settings = LisSettings.instance()
        option = settings.options
        flags = settings.flags
        # date corresponding to the model time step (yyyy-mm-dd hh:mm:ss)
        self.CalendarDate = self.CalendarDayStart + datetime.timedelta(days=(self.currentTimeStep()-1) * self.DtDay)
        # day of the year corresponding to the model time step
        self.CalendarDay = int(self.CalendarDate.strftime("%j"))
        # correct method to calculate the day of the year

        # model time step
        i = self.currentTimeStep()
        if i == 1:
            # flag for netcdf output for all, steps and end
            _ = CDFFlags(uuid.uuid4())  # init CDF flags

        self.TimeSinceStart = self.currentTimeStep() - self.firstTimeStep() + 1
        if flags['loud']:
            print("%-6i %10s" % (self.currentTimeStep(), self.CalendarDate.strftime("%d/%m/%Y %H:%M")))
        else:
            if not flags['checkfiles']:
                if flags['quiet'] and not flags['veryquiet']:
                    sys.stdout.write(".")
                if not flags['quiet'] and not flags['veryquiet']:
                    # Print step number and date to console
                    sys.stdout.write("\r%d" % i), sys.stdout.write("%s" % " - "+self.CalendarDate.strftime("%d/%m/%Y %H:%M"))
                    sys.stdout.flush()
        if i == self.nrTimeSteps():
            # last timestep. Send a new line to the terminal for polishness
            sys.stdout.write('\n')
            sys.stdout.flush()

        # ************************************************************
        """ up to here it was fun, now the real stuff starts
        """
        # readmeteo.py
        self.readmeteo_module.dynamic()     
        # timemeasure("Read meteo") # 1. timing after read input maps

        if flags['checkfiles']:
            return  # if check than finish here

        """ Here it starts with hydrological modules:
        """

        # ***** READ land use fraction maps***************************
        self.landusechange_module.dynamic()

        # ***** READ LEAF AREA INDEX DATA ****************************
        self.leafarea_module.dynamic()

        # ***** READ variable water fraction ****************************
        self.evapowater_module.dynamic_init()

        # ***** READ INFLOW HYDROGRAPHS (OPTIONAL)****************
        self.inflow_module.dynamic()
        # timemeasure("Read LAI") # 2. timing after LAI and inflow

        # ***** RAIN AND SNOW *****************************************
        self.snow_module.dynamic()
        # timemeasure("Snow")  # 3. timing after LAI and inflow

        # ***** FROST INDEX IN SOIL **********************************
        self.frost_module.dynamic()
        # timemeasure("Frost")  # 4. timing after frost index

        # ************************************************************
        # ****Looping soil 2 times - second time for forest fraction *
        # ************************************************************

        for soilLoop in range(3):
            self.soilloop_module.dynamic(soilLoop)
            # soil module is repeated 2 times:
            # 1. for remaining areas: no forest, no impervious, no water
            # 2. for forested areas
            # timemeasure("Soil",loops = soilLoop + 1) # 5/6 timing after soil

        # -------------------------------------------------------------------
        # -------------------------------------------------------------------

        # ***** ACTUAL EVAPORATION FROM OPEN WATER AND SEALED SOIL ***
        self.opensealed_module.dynamic()

        # *********  WATER USE   *************************
        self.riceirrigation_module.dynamic()
        self.waterabstraction_module.dynamic()
        # timemeasure("Water abstraction")

        # ***** Calculation per Pixel ********************************
        self.soil_module.dynamic_perpixel()
        # timemeasure("Soil done")

        self.groundwater_module.dynamic()
        # timemeasure("Groundwater")

        # ************************************************************
        # ***** STOP if no routing is required    ********************
        # ************************************************************
        if option['InitLisfloodwithoutSplit']:
            # InitLisfloodwithoutSplit
            # Very fast InitLisflood
            # it is only to compute Lzavin.map and skip completely the routing component
            self.output_module.dynamic()  # only lzavin
            return

        # *********  EVAPORATION FROM OPEN WATER *************
        self.evapowater_module.dynamic()
        # timemeasure("open water eva.")

        # ***** ROUTING SURFACE RUNOFF TO CHANNEL ********************
        self.surface_routing_module.dynamic()
        # timemeasure("Surface routing")  # 7 timing after surface routing

        # ***** POLDER INIT **********************************
        self.polder_module.dynamic_init()

        # ***** INLETS INIT **********************************
        self.inflow_module.dynamic_init()
        # timemeasure("Before routing")  # 8 timing before channel routing

        # ************************************************************
        # ***** LOOP ROUTING SUB TIME STEP   *************************
        # ************************************************************
        maskinfo = MaskInfo.instance()
        self.sumDisDay = maskinfo.in_zero()
        # sums up discharge of the sub steps
        for NoRoutingExecuted in range(self.NoRoutSteps):
            self.routing_module.dynamic(NoRoutingExecuted)
            #   routing sub steps
        # timemeasure("Routing", loops=NoRoutingExecuted + 1)  # 9 timing after routing

        # ----------------------------------------------------------------------

        if option['inflow']:
            self.QInM3Old = self.QInM3
            # to calculate the parts of inflow for every routing timestep
            # for the next timestep the old inflow is preserved
            self.sumIn += self.QInDt*self.NoRoutSteps

        # if option['simulatePolders']:
        # ChannelToPolderM3=ChannelToPolderM3Old;

        if option['InitLisflood'] or (not(option['SplitRouting'])):
            # kinematic routing
            self.ChanM3 = self.ChanM3Kin.copy()
            # Total channel storage [cu m], equal to ChanM3Kin
        else:
            # split routing
            self.ChanM3 = self.ChanM3Kin + self.Chan2M3Kin - self.Chan2M3Start #originale
            #self.ChanM3 = self.ChanM3Kin + self.Chan2M3Kin

        # Avoid negative values in ChanM3 and TotalCrossSectionArea
        self.ChanM3 = np.where(self.ChanM3 > 0, self.ChanM3, 0)

        # Total channel storage [cu m], equal to ChanM3Kin
        # sum of both lines
        # CrossSection2Area = pcraster.max(scalar(0.0), (self.Chan2M3Kin - self.Chan2M3Start) / self.ChanLength)

        self.sumDis += self.sumDisDay
        self.ChanQAvg = self.sumDisDay/self.NoRoutSteps
        self.TotalCrossSectionArea = self.ChanM3 * self.InvChanLength
        # Total volume of water in channel per inv channel length
        # New cross section area (kinematic wave)
        # This is the value after the kinematic wave, so we use ChanM3Kin here
        # (NOT ChanQKin, which is average discharge over whole step, we need state at the end of all iterations!)

        # timemeasure("After routing")  # 10 timing after channel routing

        # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        if not(option['dynamicWave']):
            # Dummy code if dynamic wave is not used, in which case the total cross-section
            # area equals TotalCrossSectionAreaKin, ChanM3 equals ChanM3Kin and
            # ChanQ equals ChanQKin
            WaterLevelDyn = -9999
            # Set water level dynamic wave to dummy value (needed

        if option['InitLisflood'] or option['repAverageDis']:
            self.CumQ += self.ChanQ
            self.avgdis = self.CumQ/self.TimeSinceStart
            # to calculate average discharge

        self.DischargeM3Out += np.where(self.AtLastPointC ,self.ChanQ * self.DtSec,0)
           # Cumulative outflow out of map

        # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        # Calculate water level
        self.waterlevel_module.dynamic()

        # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

        # ************************************************************
        # *******  Calculate CUMULATIVE MASS BALANCE ERROR  **********
        # ************************************************************
        self.waterbalance_module.dynamic()
        self.indicatorcalc_module.dynamic()

        # ************************************************************
        # ***** WRITING RESULTS: TIME SERIES AND MAPS ****************
        # ************************************************************
        self.output_module.dynamic()
        # timemeasure("Water balance")

        # debug 
        # Print value of variables after computation (from state files)
        if flags['debug']:
            nomefile = 'Debug_out_'+str(self.currentStep)+'.txt'
            ftemp1 = open(nomefile, 'w+')
            nelements = len(self.ChanM3)
            for i in range(0,nelements-1):
                if  hasattr(self,'CrossSection2Area'):
                    print(i, self.TotalCrossSectionArea[i], self.CrossSection2Area[i], self.ChanM3[i], \
                    self.Chan2M3Kin[i], file=ftemp1)
                else:
                    print(i, self.TotalCrossSectionArea[i], self.ChanM3[i], file=ftemp1)
            ftemp1.close()

        ### Report states if EnKF is used and filter moment
        self.stateVar_module.dynamic()
        self.indicatorcalc_module.dynamic_setzero()
        # setting monthly and yearly dindicator to zero at the end of the month (year)

        # garbage collector added to free memory at the end of computation step
        gc.collect()
