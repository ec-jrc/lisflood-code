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

import pcraster

from ..global_modules.add1 import loadmap
from ..global_modules.settings import LisSettings
from . import HydroModule


class polder(HydroModule):

    """
    # ************************************************************
    # ***** POLDER       *****************************************
    # ************************************************************
    """
    input_files_keys = {'simulatePolders': ['PolderSites', 'TabPolderArea', 'PolderInitialLevelValue']}
    module_name = 'Polder'

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
        settings = LisSettings.instance()
        option = settings.options
        binding = settings.binding

        if option['simulatePolders']:

            PolderSites = loadmap('PolderSites')
            PolderSites = pcraster.ifthen((pcraster.defined(PolderSites) & self.var.IsChannel), PolderSites)
            # Get rid of any polders that are not part of the channel network
            # IMPORTANT: current implementation can become unstable with kin.
            # wave!!

            # Flag that is boolean(1) for polder sites and boolean(0) otherwise
            # total storage capacity of Polder area [m3]
            PolderArea = pcraster.lookupscalar(str(binding['TabPolderArea']), PolderSites)
            PolderLevel = binding['PolderInitialLevelValue']
            # Initial polder level [m]
            self.var.PolderStorageIniM3 = pcraster.cover(PolderLevel * PolderArea, pcraster.scalar(0.0))
            # Compute polder storage [m3]
            self.var.PolderStorageM3 = self.var.PolderStorageIniM3
            # Set to initial value

    @staticmethod
    def dynamic_init():
        """ dynamic part of the polder module
            initialising polders
        """
        pass

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
