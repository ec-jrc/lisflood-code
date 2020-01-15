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
from __future__ import print_function, absolute_import, unicode_literals

from nine import iteritems

import warnings

from pcraster import numpy2pcr, Nominal, pcr2numpy, timeinputscalar
import numpy as np

from ..global_modules.settings import LisSettings
from ..global_modules.add1 import loadmap, read_tss_header, compressArray
from ..global_modules.errors import LisfloodWarning
from . import HydroModule


class inflow(HydroModule):

    """
     # ************************************************************
     # ***** READ INFLOW HYDROGRAPHS (OPTIONAL)****************
     # ************************************************************
     # If option "inflow" is set to 1 the inflow hydrograph code is used
     # otherwise dummy code is used
    """
    input_files_keys = {'inflow': ['InflowPoints', 'QInTS']}
    module_name = 'InFlow'

    def __init__(self, inflow_variable):
        self.var = inflow_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
    def initial(self):
        """ initial part of the inflow module
        """
        # ************************************************************
        # ***** INFLOW INIT
        # ************************************************************
        settings = LisSettings.instance()
        option = settings.options
        if option['inflow']:
            self.var.InflowPoints = loadmap('InflowPoints')
            self.var.QInM3Old = np.where(self.var.InflowPoints > 0, self.var.ChanQ * self.var.DtSec, 0)

            # read inflow map
            inflowmapprc = loadmap('InflowPoints', pcr=True)
            inflowmapnp = pcr2numpy(inflowmapprc, -9999)
            inflowmapnp = np.where(inflowmapnp > 0, inflowmapnp, 0)

            # get outlets ids from outlets map
            inflow_ids = np.unique(inflowmapnp)
            # drop negative values (= missing data in pcraster map)
            inflow_ids = inflow_ids[inflow_ids > 0]

            # read tss ids from tss file
            settings = LisSettings.instance()
            tss_ids = read_tss_header(settings.binding['QInTS'])

            # create a dictionary of tss id : tss id index
            id_dict = {}
            for i in range(len(tss_ids)):
                id_dict[tss_ids[i]] = tss_ids.index(tss_ids[i]) + 1

            # remove inflow point if not available in tss file
            for inf_id in inflow_ids:
                if inf_id not in tss_ids:
                    id_dict[inf_id] = 0
                    warnings.warn(LisfloodWarning("Inflow point was removed ID: %d\n" % inf_id))

            # substitute indexes to id in map
            self.var.InflowPointsMap = np.copy(inflowmapnp)
            for k, v in iteritems(id_dict):
                self.var.InflowPointsMap[inflowmapnp == k] = v

            # convert map to pcraster format
            self.var.InflowPointsMap = numpy2pcr(Nominal, self.var.InflowPointsMap, -9999)
            # Initialising cumulative output variables
            # These are all needed to compute the cumulative mass balance error

        # inflow substep amount

    def dynamic_init(self):
        """ dynamic part of the inflow module
            init inflow before sub step routing
        """

        # ************************************************************
        # ***** INLETS INIT
        # ************************************************************
        settings = LisSettings.instance()
        option = settings.options
        if option['inflow']:
            self.var.QDelta = (self.var.QInM3 - self.var.QInM3Old) * self.var.InvNoRoutSteps
            # difference between old and new inlet flow  per sub step
            # in order to calculate the amount of inlet flow in the routing loop

    def dynamic(self):
        """ dynamic part of the inflow module
        """
        settings = LisSettings.instance()
        option = settings.options
        if option['inflow']:
            settings = LisSettings.instance()
            QIn = timeinputscalar(str(settings.binding['QInTS']), self.var.InflowPointsMap)
            # Get inflow hydrograph at each inflow point [m3/s]
            QIn = compressArray(QIn)
            QIn[np.isnan(QIn)] = 0
            self.var.QInM3 = QIn * self.var.DtSec
            # Convert to [m3] per time step
            self.var.TotalQInM3 += self.var.QInM3
            # Map of total inflow from inflow hydrographs [m3]

    def dynamic_inloop(self, NoRoutingExecuted):
        """ dynamic part of the inflow routine
           inside the sub time step routing routine
        """

        # ************************************************************
        # ***** INLFLOW **********************************************
        # ************************************************************
        settings = LisSettings.instance()
        option = settings.options
        if option['inflow']:
            self.var.QInDt = (self.var.QInM3Old + (NoRoutingExecuted + 1) * self.var.QDelta) * self.var.InvNoRoutSteps
            # flow from inlets per sub step
