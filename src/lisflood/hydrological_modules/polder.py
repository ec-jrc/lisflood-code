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


class polder(object):

    """
    # ************************************************************
    # ***** POLDER       *****************************************
    # ************************************************************
    """

    def __init__(self, polder_variable):
        self.var = polder_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the polder
         module
        """
        # ************************************************************
        # ***** POLDERS
        # ************************************************************


        if option['simulatePolders']:

            g = 9.81
            # Acceleration due to gravity [m /s^2]
            expPolder = 3 / 2
            # Exponent in weir equation [-]
            PolderSites = loadmap('PolderSites')
            PolderSites = ifthen(
                (defined(PolderSites) & self.var.IsChannel), PolderSites)
            # Get rid of any polders that are not part of the channel network
            # IMPORTANT: current implementation can become unstable with kin.
            # wave!!
            IsPolder = pcraster.boolean(PolderSites)
            # Flag that is boolean(1) for polder sites and boolean(0) otherwise
            PolderTotalCapacity = lookupscalar(
                binding['TabPolderTotalCapacity'], PolderSites)
            # total storage capacity of Polder area [m3]
            PolderArea = lookupscalar(binding['TabPolderArea'], PolderSites)
            # Area of polder [m2]
            PolderOFWidth = lookupscalar(
                binding['TabPolderOFWidth'], PolderSites)
            # Width of polder in-/outflow weir [m]
            PolderBottomLevel = lookupscalar(
                binding['TabPolderBottomLevel'], PolderSites)
            # Bottom level of polder, measured above bottom level of channel
            # [m]
            PolderOpeningTime = lookupscalar(
                binding['TabPolderOpeningTime'], PolderSites)
            # Time step at which each polder is opened (regulated mode)
            PolderReleaseTime = lookupscalar(
                binding['TabPolderReleaseTime'], PolderSites)
            # Time step at which water stored in each polder is released back
            # to the channel (regulated mode)

            PolderOpeningTime = loadmap('PolderOpeningTime')
            PolderReleaseTime = loadmap('PolderReleaseTime')
            UnregulatedFlag = ifthen(
                (PolderOpeningTime == -9999) | (PolderReleaseTime == -9999), pcraster.nominal(1))
            # Flag to indicate all polders that are unregulated
            PolderLevel = PolderInitialLevelValue
            # Initial polder level [m]
            self.var.PolderStorageIniM3 = cover(
                PolderLevel * PolderArea, scalar(0.0))
            # Compute polder storage [m3]
            self.var.PolderStorageM3 = self.var.PolderStorageIniM3
            # Set to initial value
            PolderCapacity = pcraster.max(
                PolderTotalCapacity - PolderStorageM3, scalar(0.0))
            # Remaining storage capacity of polder [m3]

#        else:
            # Set polder storage to zero if no polders are simulated
            # (dummy code)
#            self.var.PolderStorageIniM3 = scalar(0.0)
            # Initial polder storage [m3]
#            self.var.PolderStorageM3 = self.var.PolderStorageIniM3

        # Initialising cumulative output variables
        # These are all needed to compute the cumulative mass balance error

#        self.var.ChannelToPolderM3Dt = globals.inZero.copy()

    @staticmethod
    def dynamic_init():
        """ dynamic part of the polder module
            initialising polders
        """

        # ************************************************************
        # ***** POLDER
        # ************************************************************
        # if option['InitLisflood']==False:    # only with no InitLisflood
        # if option['simulatePolders']:
        # #
        # #
        # ClosedFlag=if(time() lt PolderOpeningTime, nominal(2));
        # FillingFlag=if(time() ge PolderOpeningTime and time() lt PolderReleaseTime, nominal(3));
        # EmptyingFlag=if(time() ge PolderReleaseTime, nominal(4));
        # Flags to indicate that regulated polders are closed/filling/emptying
        # (yields nonsense results for unregulated polders, but see below!)
        # #
        # #            PolderStatus=cover(UnregulatedFlag,ClosedFlag, FillingFlag,EmptyingFlag);
        # Status of polder. PolderStatus can assume the following values:
        # #        		#
        # 1: unregulated (PolderOpeningTime or PolderReleaseTime equal to -9999)
        # 2: closed (time step smaller than PolderOpeningTime)
        # 3: filling (time step greater than or equal to PolderOpeningTime and smaller than PolderReleaseTime)
        # 4: emptying (time step greater than or equal to PolderReleaseTime)
        # #
        # #
        # Water heads in channel (hc) and polder (hp) (i.e. water levels above outflow opening)
        # #
        # hc=if(IsPolder,max(WaterLevelDyn-PolderBottomLevel,0.0),0.0);
        # Head in channel [m]
        # hp=if(IsPolder,PolderLevel,0.0);
        # Head in polder
        # #
        # First compute weir factor
        # #
        # weirFactor=if(hc eq hp,0);
        # Weir factor equals zero if heads are identical in channel and polder (no flow)
        # #
        # weirFactor=if(hc gt hp, sqrt(1-((hp/hc)**16)), weirFactor);
        # hc greater than hp, so flow from channel into polder
        # #
        # weirFactor=if(hp gt hc, sqrt(1-((hc/hp)**16)), weirFactor);
        # gp > hc, so flow from polder back into channel
        # #
        # Compute fluxes from Poleni's modified weir equation
        # #
        # QChannelToPolder=if(hc gt hp,mu*weirFactor*PolderOFWidth*sqrt(2*g)*(hc**expPolder),0.0);
        # QPolderToChannel=if(hp gt hc,mu*weirFactor*PolderOFWidth*sqrt(2*g)*(hp**expPolder),0.0);
        # In- and outgoing fluxes [cu m/s] (both either positive or zero)
        # #
        # Correct fluxes for storage capacity and actual storage
        # #
        # QChannelToPolder=min(QChannelToPolder,PolderCapacity*InvDtSec);
        # No flow into polder beyond its capacity
        # #
        # #        	QPolderToChannel=min(QPolderToChannel, PolderStorageM3*InvDtSec);
        # No flow out of polder once it is empty
        # #
        # Correct fluxes for polder status (in case of regulated polders)
        # #
        # QChannelToPolder=if(PolderStatus eq 2 or PolderStatus eq 4, 0.0, QChannelToPolder);
        # No flow into polder if polder is closed or emptying
        # #
        # QPolderToChannel=if(PolderStatus eq 2 or PolderStatus eq 3, 0.0, QPolderToChannel);
        # No flow out of polder if polder is closed or filling
        # #
        # #        	PolderFlux=cover(QChannelToPolder-QPolderToChannel, 0.0);
        # Polder flux [cu m/s]. Positive for flow from channel to polder, negative for polder to channel
        # #
        # ChannelToPolderM3=PolderFlux*DtSec;
        # Water to (positive) or from (negative) polder [cu m]
        # #
        # #         	PolderStorageM3 += ChannelToPolderM3;
        # New polder storage [m] (remember ChannelToPolderM3 is *negative* while polder is emptying, hence
        # PolderStorageM3 will decrease in that case)
        # #
        # PolderLevel=PolderStorageM3/PolderArea;
        # New polder level [m]
        # #
        # PolderCapacity=max(PolderTotalCapacity-PolderStorageM3,0.0);
        # Remaining storage capacity of polder [cu m]
        # #
        # #
        # QDeltaPolder=(ChannelToPolderM3-ChannelToPolderM3Old)*InvNoRoutSteps;
        # Water to (positive) or from (negative) polder [cu m]
        # #

    @staticmethod
    def dynamic_inloop():
        """ dynamic part of the polder routine
           inside the sub time step routing routine
        """

        # ************************************************************
        # ***** POLDER
        # ************************************************************

        # if option['simulatePolders']:
        # #
        # ChannelToPolderM3Dt=(ChannelToPolderM3Old+(NoRoutingExecuted+1)*QDeltaPolder)*InvNoRoutSteps;
        # flow from (or to) polder per substep
        # #
        pass
