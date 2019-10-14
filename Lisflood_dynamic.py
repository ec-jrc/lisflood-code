# -------------------------------------------------------------------------
# Name:       Lisflood Model Dynamic
# Purpose:
#
# Author:      burekpe
#
# Created:     27/02/2014
# Copyright:   (c) burekpe 2014
# Licence:     <your licence>
# -------------------------------------------------------------------------

import pandas as pd
from global_modules.add1 import *

class LisfloodModel_dyn(DynamicModel):

    # =========== DYNAMIC ====================================================

    def dynamic(self):
        """ Dynamic part of LISFLOOD
            calls the dynamic part of the hydrological modules
        """
        del timeMes[:]
        timemeasure("Start dynamic")
        self.CalendarDate = self.CalendarDayStart + datetime.timedelta(days=(self.currentTimeStep()-1) * self.DtDay)
        aux_days = num2date(np.arange(366), "days since {}-01-01".format(self.CalendarDate.year), binding["CalendarConvention"])
        self.CalendarDay = 1 + np.where(np.array([self.CalendarDate]) == aux_days)[0][0]

        i = self.currentTimeStep()
        if i==1:
            globals.cdfFlag = [0, 0, 0, 0 ,0 ,0,0]
        if i == int(binding["StepStart"]):
            self._datetime_sim_start = pd.datetime.now() # date and time when the simulation is started
            self._num_timesteps = int(binding["StepEnd"]) - int(binding["StepStart"]) + 1 # number of time steps to be simulated
            print("Simulation started on " + self._datetime_sim_start.strftime('%Y-%m-%d %H:%M'))
            estimated_end_msg = ""
        else:
            _steps_done = i - int(binding["StepStart"])
            _datetime_sim_end = self._datetime_sim_start + self._num_timesteps * (pd.datetime.now() - self._datetime_sim_start) / _steps_done # expected simulation end datetime
            estimated_end_msg = "(estimated simulation end: {})".format(_datetime_sim_end.strftime('%Y-%m-%d %H:%M'))

          # flag for netcdf output for all, steps and end
          # set back to 0,0,0,0,0,0 if new Monte Carlo run

        self.TimeSinceStart = self.currentTimeStep() - self.firstTimeStep() + 1

        if Flags['loud']:
            print("%-6i %10s" %(self.currentTimeStep(),self.CalendarDate.strftime("%d/%m/%Y")))
        else:
            if not(Flags['check']):
                if (Flags['quiet']) and (not(Flags['veryquiet'])):
                    sys.stdout.write(".")
                if (not(Flags['quiet'])) and (not(Flags['veryquiet'])):
                    sys.stdout.write("\r{}    {}".format(i, estimated_end_msg))
                    sys.stdout.flush()

        # ************************************************************
        """ up to here it was fun, now the real stuff starts
        """
        self.readmeteo_module.dynamic()
        timemeasure("Read meteo") # 1. timing after read input maps

        if Flags['check']: return  # if check than finish here

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
        timemeasure("Read LAI") # 2. timing after LAI and inflow

        # ***** RAIN AND SNOW *****************************************
        self.snow_module.dynamic()
        timemeasure("Snow")  # 3. timing after LAI and inflow

        # ***** FROST INDEX IN SOIL **********************************
        self.frost_module.dynamic()
        timemeasure("Frost")  # 4. timing after frost index

        # ***** EPIC AGRICULTURE MODEL - 1ST PART: CROP STATE AND ENVIRONMENT *******************
        if option["cropsEPIC"]:
##              t0 = pd.datetime.now() # TIMING
            self.crop_module.dynamic_state()
##              print('dynamic_state: ', (pd.datetime.now() - t0).total_seconds()) # TIMING

        # *************************************************************************************
        # **** Loop over vegetation fractions: 1. processes depending directly on the canopy
        # *************************************************************************************
#        VARS_CANOPY = ['Interception', 'TaInterception', 'LeafDrainage', 'CumInterception', 'potential_transpiration', 'RWS', 'Ta',
#                       'SoilMoistureStressDays', 'W1a', 'W1b', 'W1'] # TEST SOILLOOP SPEED-UP
#        backup = self.soilloop_module.backup(VARS_CANOPY) # TEST SOILLOOP SPEED-UP
#         t0 = pd.datetime.now() # TIMING
        self.soilloop_module.dynamic_canopy()
#         print('soilloop_module.dynamic_canopy: ', (pd.datetime.now() - t0).total_seconds()) # TIMING
#        new_vals = self.soilloop_module.backup(VARS_CANOPY)                                 # TEST SOILLOOP SPEED-UP
#        self.soilloop_module.reset(backup)                                                         # TEST SOILLOOP SPEED-UP
#        t0 = pd.datetime.now()                                                                     # TEST SOILLOOP SPEED-UP
#        for loop, fraction_name in enumerate(self.vegetation):                                    # TEST SOILLOOP SPEED-UP
#            self.soilloop_module_OLD.dynamic_canopy(fraction_name)                                 # TEST SOILLOOP SPEED-UP
#            timemeasure("Soil - part 1 (canopy)", loops=loop + 1) # 5/6 timing after soil          # TEST SOILLOOP SPEED-UP
#        print('soilloop_module_OLD.dynamic_canopy: ', (pd.datetime.now() - t0).total_seconds())        # TEST SOILLOOP SPEED-UP
#        self.soilloop_module.compare(new_vals)                                                # TEST SOILLOOP SPEED-UP
        timemeasure("Soil - part 1 (canopy)")

        # ***** EPIC AGRICULTURE MODEL - 2ND PART: CROP GROWTH AND LIMITNG FACTORS *************
        if option["cropsEPIC"]:
#             t0 = pd.datetime.now() # TIMING
            self.crop_module.dynamic_growth()
#             print('dynamic_growth: ', (pd.datetime.now() - t0).total_seconds()) # TIMING

        # **************************************************************************************
        # **** Loop over vegetation fractions: 2. internal soil processes
        # **************************************************************************************
#        VARS_SOIL = ['AvailableWaterForInfiltration', 'DSLR', 'ESAct', 'PrefFlow', 'Infiltration', 'W1a', 'W1b', 'W1', 'W2',
#                     'SeepTopToSubA', 'SeepTopToSubB', 'SeepSubToGW', 'UZOutflow', 'UZ', 'GwPercUZLZ', 'Theta1a',
#                     'Theta1b', 'Theta2', 'Sat1a', 'Sat1b', 'Sat1', 'Sat2'] # TEST SOILLOOP SPEED-UP
#        backup = self.soilloop_module.backup(VARS_SOIL)                # TEST SOILLOOP SPEED-UP
#         t0 = pd.datetime.now() # TIMING
        self.soilloop_module.dynamic_soil()
#         print('soilloop_module.dynamic_soil: ', (pd.datetime.now() - t0).total_seconds()) # TIMING
#        new_vals = self.soilloop_module.backup(VARS_SOIL)                                 # TEST SOILLOOP SPEED-UP
#        self.soilloop_module.reset(backup)                                                # TEST SOILLOOP SPEED-UP
#        t0 = pd.datetime.now()                                                                 # TEST SOILLOOP SPEED-UP
#        for loop, fraction_name in enumerate(self.vegetation):                                 # TEST SOILLOOP SPEED-UP
#            self.soilloop_module_OLD.dynamic_soil(fraction_name)                                   # TEST SOILLOOP SPEED-UP
#            timemeasure("Soil - part 2 (soil)", loops=loop + 1) # 5/6 timing after soil        # TEST SOILLOOP SPEED-UP
#        print('soilloop_module_OLD.dynamic_soil: ', (pd.datetime.now() - t0).total_seconds())      # TEST SOILLOOP SPEED-UP
#        self.soilloop_module.compare(new_vals)                                            # TEST SOILLOOP SPEED-UP
        timemeasure("Soil - part 2 (soil)")

        # ***** EPIC AGRICULTURE MODEL - 3RD PART: CROP IRRIGATION WATER REQUIREMENTS **********
#         t0 = pd.datetime.now() # TIMING
        if option["cropsEPIC"]:
            self.crop_module.dynamic_irrigation_requirement()
#         print('dynamic_irrigation_requirement: ', (pd.datetime.now() - t0).total_seconds()) # TIMING

        # ***** ACTUAL EVAPORATION FROM OPEN WATER AND SEALED SOIL ***
        self.opensealed_module.dynamic()

        # *********  WATER USE + EPIC AGRICULTURE MODEL - 4TH PART: CROP IRRIGATION APPLICATION (ONLY IF EPIC IS SWITCHED ON) *************************
#         t0 = pd.datetime.now() # TIMING
        self.riceirrigation_module.dynamic() 
        self.waterabstraction_module.dynamic()
        timemeasure("Water abstraction")
#         print('waterabstraction: ', (pd.datetime.now() - t0).total_seconds()) # TIMING

        # ***** EPIC AGRICULTURE MODEL - 5TH PART: WRITE OUTPUT **********
#         t0 = pd.datetime.now() # TIMING
        if option["cropsEPIC"]:
            self.crop_module.dynamic_write_output()
#         print('EPIC output: ', (pd.datetime.now() - t0).total_seconds()) # TIMING

        # ***** Calculation per Pixel ********************************
#         t0 = pd.datetime.now() # TIMING
        self.soil_module.dynamic_perpixel()
        timemeasure("Soil done")
#         print('soil_perpixel: ', (pd.datetime.now() - t0).total_seconds()) # TIMING

#         t0 = pd.datetime.now() # TIMING
        self.groundwater_module.dynamic()
        timemeasure("Groundwater")
#         print('Groundwater', (pd.datetime.now() - t0).total_seconds()) # TIMING

        # ************************************************************
        # ***** STOP if no routing is required    ********************
        # ************************************************************
        if option['InitLisfloodwithoutSplit']:
            # InitLisfloodwithoutSplit
            # Very fast InitLisflood
            # it is only to compute Lzavin.map and skip completely the routing component
            self.output_module.dynamic() # only lzavin

            timemeasure("After fast init")
            for i in xrange(len(timeMes)):
                if self.currentTimeStep() == self.firstTimeStep():
                   timeMesSum.append(timeMes[i] - timeMes[0])
                else: timeMesSum[i] += timeMes[i] - timeMes[0]

            return


        # *********  EVAPORATION FROM OPEN WATER *************
        self.evapowater_module.dynamic()
        timemeasure("open water eva.")

        # ***** ROUTING SURFACE RUNOFF TO CHANNEL ********************
        self.surface_routing_module.dynamic()
        timemeasure("Surface routing")  # 7 timing after surface routing

        # ***** POLDER INIT **********************************
        self.polder_module.dynamic_init()

        # ***** INLETS INIT **********************************
        self.inflow_module.dynamic_init()
        timemeasure("Before routing")  # 8 timing before channel routing

        # ************************************************************
        # ***** LOOP ROUTING SUB TIME STEP   *************************
        # ************************************************************
        self.sumDisDay = globals.inZero.copy()
        # sums up discharge of the sub steps
        for NoRoutingExecuted in xrange(self.NoRoutSteps):
            self.routing_module.dynamic(NoRoutingExecuted)
            #   routing sub steps
        timemeasure("Routing",loops = NoRoutingExecuted + 1)  # 9 timing after routing

        # ----------------------------------------------------------------------

        if option['inflow']:
            self.QInM3Old = self.QInM3
            # to calculate the parts of inflow for every routing timestep
            # for the next timestep the old inflow is preserved
            self.sumIn += self.QInDt*self.NoRoutSteps

        # if option['simulatePolders']:
        # ChannelToPolderM3=ChannelToPolderM3Old;

        if option['InitLisflood'] or (not(option['SplitRouting'])):
            self.ChanM3 = self.ChanM3Kin.copy()
                # Total channel storage [cu m], equal to ChanM3Kin
        else:
            self.ChanM3 = self.ChanM3Kin + self.Chan2M3Kin - self.Chan2M3Start
            #self.ChanM3 = self.ChanM3Kin + self.Chan2M3Kin - self.Chan2M3Start
                # Total channel storage [cu m], equal to ChanM3Kin
                # sum of both lines
            #CrossSection2Area = pcraster.max(scalar(0.0), (self.Chan2M3Kin - self.Chan2M3Start) / self.ChanLength)

        self.sumDis += self.sumDisDay
        self.ChanQAvg = self.sumDisDay/self.NoRoutSteps
        self.TotalCrossSectionArea = self.ChanM3 * self.InvChanLength
            # New cross section area (kinematic wave)
            # This is the value after the kinematic wave, so we use ChanM3Kin here
            # (NOT ChanQKin, which is average discharge over whole step, we need state at the end of all iterations!)

        timemeasure("After routing")  # 10 timing after channel routing

        # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        if not(option['dynamicWave']):
            # Dummy code if dynamic wave is not used, in which case the total cross-section
            # area equals TotalCrossSectionAreaKin, ChanM3 equals ChanM3Kin and
            # ChanQ equals ChanQKin
            WaterLevelDyn = np.nan
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
        timemeasure("Water balance")



        ### Report states if EnKF is used and filter moment
        self.stateVar_module.dynamic()
        timemeasure("State report")

        timemeasure("All dynamic")


        for i in xrange(len(timeMes)):
            if self.currentTimeStep() == self.firstTimeStep():
                timeMesSum.append(timeMes[i] - timeMes[0])
            else: timeMesSum[i] += timeMes[i] - timeMes[0]



        self.indicatorcalc_module.dynamic_setzero()
           # setting monthly and yearly dindicator to zero at the end of the month (year)





        """
     # self.var.WaterRegionOutflowPoints self.var.WaterRegionInflowPoints
        report(self.WaterRegionOutflowPoints,'D:\Lisflood_runs\LisfloodWorld2\out\wateroutpt.map')
        report(self.WaterRegionInflowPoints,'D:\Lisflood_runs\LisfloodWorld2\out\waterInpt.map')

        # report(self.map2,'mapx.map')
        # self.Tss['UZTS'].sample(Precipitation)
        # self.report(self.Precipitation,binding['TaMaps'])





       #WUse=(WUse*PixelArea*0.001)/2592000;
       # if mm maps are used:
	   # mm per month to m3/s  : x Pixelarea * mmtom / sec in a month

        #self.SumETpot += self.ETRef
        #self.SumET = SumET + MonthETact + TaInterception + TaPixel + ESActPixel + EvaAddM3 * M3toMM;
        #SumTrun += ToChanM3Runoff;



        WUse = decompress((self.TotalAbstractionFromGroundwaterM3 + self.TotalAbstractionFromSurfaceWaterM3) * self.DtSec)
        WaterDemandM3= areatotal(cover(WUse,0.0),wreg)
        WaterUseM3 = areatotal(cover(decompress(self.WUseAddM3),0.0),wreg)
        self.FlagDemandBiggerUse = self.FlagDemandBiggerUse + ifthenelse((WaterDemandM3*0.9) > WaterUseM3,scalar(1.0),scalar(0.0))




        self.TotWEI = self.TotWEI + ifthenelse(EndOfMonth > 0,WEI_Use,scalar(0.0))
        self.TotWEI = ifthenelse(self.currentTimeStep() < 365,scalar(0.0),self.TotWEI)
        self.TotlWEI =  self.TotlWEI + ifthenelse(EndOfMonth > 0,lWEI_Use,scalar(0.0))
        self.TotlWEI = ifthenelse(self.currentTimeStep() < 365,scalar(0.0),self.TotlWEI)
        self.TotCount = self.TotCount + ifthenelse(EndOfMonth > 0 ,scalar(1.0),scalar(0.0))
        self.TotCount = ifthenelse(self.currentTimeStep() < 365,scalar(0.0),self.TotCount)


        # self.CalendarDate.strftime("%d/%m/%Y"))
        """

