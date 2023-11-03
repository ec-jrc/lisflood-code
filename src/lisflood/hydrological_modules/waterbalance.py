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

import numpy as np
from ..global_modules.add1 import compressArray
from ..global_modules.settings import LisSettings, MaskInfo

from ..global_modules.add1 import loadmap, readnetcdf

class waterbalance(object):

    """
    # ************************************************************
    # ***** CUMULATIVE MASS BALANCE ERROR*************************
    # ************************************************************
    # Cumulative mass balance error is calculated at outflow point (pit) of
    # each catchment (no pixel values)! In- and outgoing terms below are all
    # cumulative over entire simulation.

    """

    def __init__(self, waterbalance_variable):
        self.var = waterbalance_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the water balance module
        """

        # ************************************************************
        # ***** WATER BALANCE INIT
        # ************************************************************

        # Calculate initial amount of water in catchment (needed to keep track of
        # cumulative mass balance error)
        settings = LisSettings.instance()
        option = settings.options

        if (not(option['InitLisflood'])) and option['repMBTs']:
            # not done in Init Lisflood

            ChannelInitM3 = self.var.ChanIniM3
            if not(option['InitLisflood']):    # only with no InitLisflood
                if option['simulateLakes']:
                    ChannelInitM3 += self.var.LakeStorageIniM3
                if option['simulateReservoirs']:
                    ChannelInitM3 += self.var.ReservoirStorageIniM3
                if option['simulatePolders']:
                    ChannelInitM3 += self.var.PolderStorageIniM3

            ax_veg=self.var.SoilFraction.dims.index("vegetation")        
            Hill1 = np.sum(self.var.SoilFraction * (self.var.CumInterception + self.var.W1 + self.var.W2 + self.var.UZ),ax_veg)
            Hill1 += self.var.LZ            
            
            OverlandInitM3 = self.var.OFM3Other + self.var.OFM3Forest + self.var.OFM3Direct

            HillslopeInitM3 = (self.var.SnowCoverInit + Hill1 +
                               self.var.DirectRunoffFraction * self.var.CumInterSealed) * self.var.MMtoM3 + OverlandInitM3
            # Initial water stored at hillslope elements [m3]
            # Note that WInit1, WInit2 and TotalGroundWaterInit are defined for the pixel's permeable fraction
            # only, which is why we need to multiply with PermeableFraction to get the volumes right (no soil moisture
            # or groundwater is stored at all in the direct runoff fraction!)
            # MMtoM3 equals MMtoM*PixelArea, which may (or may not) be
            # spatially variable

            self.var.WaterInit = np.take(np.bincount(self.var.Catchments, weights=ChannelInitM3), self.var.Catchments)
            self.var.WaterInit += np.take(np.bincount(self.var.Catchments, weights=HillslopeInitM3), self.var.Catchments)

            # Initial water stored [m3]
            # Inclusion of DischargeM3Structures: adding this corrects a (relatively small) offset that occurs otherwise
            # if structures (reservoirs, lakes) are used.
            #DisStructure = cover(ifthen(
            #    self.var.IsUpsOfStructureKinematic, self.var.ChanQ * self.var.DtRouting), scalar(0.0))

            DisStructure = np.where(self.var.IsUpsOfStructureKinematicC, self.var.ChanQ * self.var.DtRouting, 0)
            
            # Discharge upstream of structure locations (coded as pits) in [m3/time step]
            # Needed for mass balance error calculations (see comment to calculation of WaterInit below)
            # Inclusion of DischargeM3Structures: adding this corrects a (relatively small) offset that occurs otherwise
            # if structures (reservoirs, lakes) are used.
            # calculation of structur influence happens before routing, therefore the initial state is used at the structure onece to often
            # (because it is not routed yet to the structure)

            if option['simulateLakes']:
                DisStructure += np.where(compressArray(self.var.IsUpsOfStructureLake), 0.5 * self.var.ChanQ * self.var.DtRouting, 0)

                # DisStructure += cover(ifthen(self.var.IsUpsOfStructureLake,
                #  0.5 * self.var.ChanQ * self.var.DtRouting), scalar(0.0))
                # because Modified Puls Method is use, some additional offset
                # has to be added
            
            self.var.DischargeM3StructuresIni = np.take(np.bincount(self.var.Catchments, weights=DisStructure), self.var.Catchments)


# --------------------------------------------------------------------------
# -------------------------------------------------------------------------

    def dynamic(self):
        """ dynamic part of the water balance module
        """
        settings = LisSettings.instance()
        option = settings.options        
        maskinfo = MaskInfo.instance()
        
        if (not(option['InitLisflood'])) and option['repMBTs']:

            # ************************************************************
            # ***** CUMULATIVE MASS BALANCE ERROR*************************
            # ************************************************************

            # Cumulative mass balance error is calculated at outflow point (pit) of
            # each catchment (no pixel values)! In- and outgoing terms below are all
            # cumulative over entire simulation.

            # This comes in:
            #WaterIn = areatotal(cover(decompress(self.var.sumIn), scalar(0.0)), catch) + areatotal(
            #    decompress(self.var.TotalPrecipitation) * self.var.MMtoM3, catch)
        
            self.var.sumInWB[np.isnan(self.var.sumInWB)] = 0
            WaterIn = np.take(np.bincount(self.var.Catchments, weights=self.var.sumInWB),self.var.Catchments)
            WaterIn += np.take(np.bincount(self.var.Catchments, weights=self.var.TotalPrecipitationWB*self.var.MMtoM3), self.var.Catchments)
               # Accumulated incoming water [cu m]
            # NOTE: It is NOT possible to nest all terms into one areatotal statement because channel-related maps have MV for non-channel
            # pixels, resulting in MV creation when adding directly!!
            # MMtoM3 equals MMtoM*PixelArea, which may (or may not) be
            # spatially variable

            # This is stored:
            ChannelStoredM3 = self.var.ChanM3.copy()
            if option['simulateLakes']:
                ChannelStoredM3 += self.var.LakeStorageM3Balance
            if option['simulateReservoirs']:
                ChannelStoredM3 += self.var.ReservoirStorageM3
            if option['simulatePolders']:
                ChannelStoredM3 += self.var.PolderStorageM3

            # ChannelStoredM3=ChanM3 + ReservoirStorageM3 + LakeStorageM3 + PolderStorageM3;
            # Water stored in channel network [m3] (including reservoirs,
            # lakes, polders)
 
            ax_veg=self.var.SoilFraction.dims.index("vegetation")            
            Hill1 = self.var.LZ + np.sum(self.var.SoilFraction * (self.var.CumInterception + self.var.W1 + self.var.W2 + self.var.UZ),ax_veg)                                                 
            HillslopeStoredM3 = (self.var.WaterDepth + self.var.SnowCover + Hill1 + self.var.DirectRunoffFraction * self.var.CumInterSealed) * self.var.MMtoM * self.var.PixelArea
            
            # Water stored at hillslope elements [m3]
            # Note that W1, W2 and TotalGroundWater are defined for the pixel's permeable fraction
            # only, which is why we need to multiply with PermeableFraction to get the volumes right (no soil moisture
            # or groundwater is stored at all in the direct runoff fraction!)

            # OverlandM3 = self.var.OFM3Other + self.var.OFM3Forest + self.var.OFM3Direct

            #WaterStored = areatotal(decompress(ChannelStoredM3), catch) + areatotal(decompress(HillslopeStoredM3), catch)
            WaterStored = np.take(np.bincount(self.var.Catchments,weights=ChannelStoredM3),self.var.Catchments)
            WaterStored += np.take(np.bincount(self.var.Catchments,weights=HillslopeStoredM3),self.var.Catchments)

            if option['TransientLandUseChange'] and (self.var.DynamicLandCoverDelta > 0.0):
                 self.var.ForestFraction = self.var.ForestFraction_nextstep        
                 self.var.DirectRunoffFraction = self.var.DirectRunoffFraction_nextstep
                 self.var.WaterFraction = self.var.WaterFraction_nextstep
                 self.var.IrrigationFraction = self.var.IrrigationFraction_nextstep
                 self.var.RiceFraction = self.var.RiceFraction_nextstep
                 self.var.OtherFraction = self.var.OtherFraction_nextstep  
                 self.var.SoilFraction[0] =  self.var.OtherFraction
                 self.var.SoilFraction[1] =  self.var.ForestFraction 
                 self.var.SoilFraction[2] =  self.var.IrrigationFraction   

                 if not option["cropsEPIC"]: # If EPIC is active, the rice fraction initialisation is handled by EPIC (setSoilFractions in EPIC_main.py)
                    self.var.SoilFraction.values[self.var.vegetation.index('Rainfed_prescribed')] += self.var.RiceFraction

                 Hill1 = self.var.LZ + (self.var.SoilFraction * (self.var.CumInterception + self.var.W1 + self.var.W2 + self.var.UZ)).sum("vegetation").values
                 HillslopeStoredM3 = (self.var.WaterDepth + self.var.SnowCover + Hill1 + self.var.DirectRunoffFraction * self.var.CumInterSealed) * self.var.MMtoM * self.var.PixelArea                
                 WaterStored_nextstep =np.take(np.bincount(self.var.Catchments,weights=ChannelStoredM3),self.var.Catchments)
                 WaterStored_nextstep += np.take(np.bincount(self.var.Catchments,weights=HillslopeStoredM3),self.var.Catchments)

            # Total water stored [m3]
            # This goes out:
            HillslopeOutM3 = (self.var.TaWB + self.var.TaInterceptionWB + self.var.ESActWB + self.var.GwLossWB) * self.var.MMtoM3
            # Water that goes out of the system at the hillslope level [m3]
            # (evaporation and groundwater loss)

            ##sum1 = self.var.sumDis.copy()
            sum1 = self.var.ChanQAvg.copy()
            sum1[self.var.AtLastPointC == 0] = 0
            WaterOut = np.take(np.bincount(self.var.Catchments,weights=sum1 * self.var.DtSec),self.var.Catchments)
            WaterOut += np.take(np.bincount(self.var.Catchments,weights=HillslopeOutM3),self.var.Catchments)

            #WaterOut = areatotal(cover(ifthen(
            #    self.var.AtLastPoint, self.var.sumDis * self.var.DtRouting), scalar(0.0)), catch)
            #WaterOut += areatotal(decompress(HillslopeOutM3), catch)
            if option['simulateLakes']:
                WaterOut += np.take(np.bincount(self.var.Catchments, weights=self.var.EWLakeWBM3),self.var.Catchments)  #### EWLakeCUMM3 is not updated! Always = 0!!
            if option['openwaterevapo']:
                WaterOut += np.take(np.bincount(self.var.Catchments, weights=self.var.EvaWBM3),self.var.Catchments)
            if option['TransLoss']:
                WaterOut += np.take(np.bincount(self.var.Catchments, weights=self.var.TransCum),self.var.Catchments)
            if option['wateruse']:
                print('WARNING: the water balance module has NOT been verified yet when the option wateruse is ON!')
                WaterOut += np.take(np.bincount(self.var.Catchments, weights=self.var.IrriLossCUM),self.var.Catchments)
                WaterOut += np.take(np.bincount(self.var.Catchments, weights=self.var.wateruseCum),self.var.Catchments)
            # Accumulated outgoing water [cu m]
            # Inclusion of DischargeM3Structures is because at structure locations the water in the channel is added to the structure
            # (i.e. storage at reservoirs/lakes is accounted for twice). Of course this is not really a 'loss', but merely a correction
            # for this double counting)
            # new 12.11.09 PB
            # added cumulative transmission loss
            DisStru = np.where(self.var.IsUpsOfStructureKinematicC, self.var.ChanQ * self.var.DtRouting, 0)
            DischargeM3Structures = np.take(np.bincount(self.var.Catchments, weights=DisStru), self.var.Catchments)

            # on the last time step lakes and reservoirs calculated with the previous routing results
            # so the last (now routed) discharge has to be added to the mass balance
            # (-> the calculation odf the structures is done before the routing)

            if option['simulateLakes']:
                DisLake = maskinfo.in_zero()
                np.put(DisLake, self.var.LakeIndex, 0.5 * self.var.LakeInflowCC * self.var.DtRouting)
                DischargeM3Lake = np.take(np.bincount(self.var.Catchments, weights=DisLake),self.var.Catchments)
                #DischargeM3Lake = areatotal(cover(0.5 * self.var.LakeInflow * self.var.DtRouting, scalar(0.0)), catch)
                # because Modified Puls Method is using QIn=(Qin1+Qin2)/2, we need a correction
                #  DisStr=Disstr+0.5*LakeInflow - 0.5 * LakeInit
                #  0.5 * LakeInit: is already done in DischargeM3StructuresIni
                DischargeM3Structures += DischargeM3Lake
                # Discharge just upstream of structure locations (coded as pits) in [cu m / time step]
                # Needed for mass balance error calculations, because of double counting of structure
                # storage and water in the channel.

            DischargeM3Structures -= self.var.DischargeM3StructuresIni  
            # minus the initial DischargeStructure
            # Old: DischargeM3Structures=areatotal(cover(ifthen(self.var.IsUpsOfStructureKinematic,self.var.ChanQ*self.var.DtSec),null),self.var.Catchments)
            # Discharge just upstream of structure locations (coded as pits) in [cu m / time step]
            # Needed for mass balance error calculations, because of double counting of structure
            # storage and water in the channel.
            # Mass balance:
            self.var.MBError = self.var.WaterInit + WaterIn - WaterStored - WaterOut - DischargeM3Structures
            # Totl mass balance error per catchment [cu m]. Mass balance error is computed for each computational time step.
  
            CatchArea = np.take(np.bincount(self.var.Catchments, weights=self.var.PixelArea),self.var.Catchments)
            self.var.MBErrorMM = self.var.MtoMM * self.var.MBError / CatchArea
            # Mass balance error per unit area of the catchment [mm water slice]. Mass balance error is computed for each computational time step.
            

            self.var.WaterInit = WaterStored + DischargeM3Structures
            if option['TransientLandUseChange'] and (self.var.DynamicLandCoverDelta > 0.0):
                 self.var.WaterInit = WaterStored_nextstep + DischargeM3Structures
            # update the water storage             
            
            # the lines below compute the ratio between the total mass balance error and the water storage [m3/m3] and the average sum of the fractions for each catchemnt. 
            # MBErrorStorage and  AverageFractions are useful to analyse the mass balance error values.
            sumFractionsa11 = []
            SumFractions = []
            numpixels = []
            self.var.MBErrorStorage = []
            self.var.AverageFractions = []
            sumFractionsa11 = self.var.ForestFraction + self.var.DirectRunoffFraction  + self.var.WaterFraction  + self.var.IrrigationFraction + self.var.OtherFraction  
            # self.var.RiceFraction is already included in self.var.OtherFraction
            SumFractions = np.take(np.bincount(self.var.Catchments, weights=sumFractionsa11),self.var.Catchments)
            ones = maskinfo.in_zero() + 1.0
            numpixels = np.take(np.bincount(self.var.Catchments, weights=ones),self.var.Catchments) 
            self.var.MBErrorStorage = self.var.MBError/(self.var.WaterInit)  
            self.var.AverageFractions = SumFractions/numpixels