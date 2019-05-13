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
import gc


class LisfloodModel_dyn(DynamicModel):

    # =========== DYNAMIC ====================================================

    def dynamic(self):
        """ Dynamic part of LISFLOOD
            calls the dynamic part of the hydrological modules
        """
        del timeMes[:]
        # get time for operation "Start dynamic"
        timemeasure("Start dynamic")
        # date corresponding to the model time step (yyyy-mm-dd hh:mm:ss)
        self.CalendarDate = self.CalendarDayStart + datetime.timedelta(days=(self.currentTimeStep()-1) * self.DtDay)
        # day of the year corresponding to the model time step
        self.CalendarDay = int(self.CalendarDate.strftime("%j"))
        #correct method to calculate the day of the year

        # model time step
        i = self.currentTimeStep()
        if i==1:    globals.cdfFlag = [0, 0, 0, 0 ,0 ,0,0]
          # flag for netcdf output for all, steps and end
          # set back to 0,0,0,0,0,0 if new Monte Carlo run

        self.TimeSinceStart = self.currentTimeStep() - self.firstTimeStep() + 1

        if Flags['loud']:
            print "%-6i %10s" %(self.currentTimeStep(),self.CalendarDate.strftime("%d/%m/%Y %H:%M")) ,
        else:
            if not(Flags['check']):
                if (Flags['quiet']) and (not(Flags['veryquiet'])):
                    sys.stdout.write(".")
                if (not(Flags['quiet'])) and (not(Flags['veryquiet'])):
                    # Print step number and date to console
                    sys.stdout.write("\r%d" % i), sys.stdout.write("%s" % " - "+self.CalendarDate.strftime("%d/%m/%Y %H:%M"))
                    sys.stdout.flush()

        # ************************************************************
        """ up to here it was fun, now the real stuff starts
        """
        # readmeteo.py
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

        # ************************************************************
        # ****Looping soil 2 times - second time for forest fraction *
        # ************************************************************

        for soilLoop in xrange(3):
            self.soilloop_module.dynamic(soilLoop)
            # soil module is repeated 2 times:
            # 1. for remaining areas: no forest, no impervious, no water
            # 2. for forested areas
            timemeasure("Soil",loops = soilLoop + 1) # 5/6 timing after soil

        # -------------------------------------------------------------------
        # -------------------------------------------------------------------

        # ***** ACTUAL EVAPORATION FROM OPEN WATER AND SEALED SOIL ***
        self.opensealed_module.dynamic()

        # *********  WATER USE   *************************
        self.riceirrigation_module.dynamic()
        self.waterabstraction_module.dynamic()
        timemeasure("Water abstraction")

        # ***** Calculation per Pixel ********************************
        self.soil_module.dynamic_perpixel()
        timemeasure("Soil done")

        self.groundwater_module.dynamic()
        timemeasure("Groundwater")

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
            #CrossSection2Area = pcraster.max(scalar(0.0), (self.Chan2M3Kin - self.Chan2M3Start) / self.ChanLength)

        self.sumDis += self.sumDisDay
        self.ChanQAvg = self.sumDisDay/self.NoRoutSteps
        self.TotalCrossSectionArea = self.ChanM3 * self.InvChanLength
            # Total volume of water in channel per inv channel length
            # New cross section area (kinematic wave)
            # This is the value after the kinematic wave, so we use ChanM3Kin here
            # (NOT ChanQKin, which is average discharge over whole step, we need state at the end of all iterations!)

        timemeasure("After routing")  # 10 timing after channel routing

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
        timemeasure("Water balance")


        # debug 
        # Print value of variables after computation (from state files)
        if Flags['debug']:
            nomefile = 'Debug_out_'+str(self.currentStep)+'.txt'
            ftemp1 = open(nomefile, 'w+')
            nelements = len(self.ChanM3)
            for i in range(0,nelements-1):
                if  hasattr(self,'CrossSection2Area'):
                    print >> ftemp1, i, self.TotalCrossSectionArea[i], self.CrossSection2Area[i], self.ChanM3[i], \
                    self.Chan2M3Kin[i]
                else:
                    print >> ftemp1, i, self.TotalCrossSectionArea[i], self.ChanM3[i]
            ftemp1.close()



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


        # garbage collector added to free memory at the end of computation step
        gc.collect()





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

