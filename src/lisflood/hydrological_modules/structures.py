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
from pcraster import ldd, nominal

from ..global_modules.add1 import decompress, compressArray
from ..global_modules.settings import LisSettings, MaskInfo


class structures(object):
    """
    ************************************************************
    ***** STRUCTURES
    ************************************************************
    Structures such as reservoirs and lakes are modelled by interrupting the channel flow paths
    for the kinematic wave (LddKinematic). The current block of code produces:
    1. A modified LddKinematic, where a pit (sink) is inserted at all cells immediately upstream of
       a structure (can be more than 1 per structure, in case of junction of multiple branches)
     2. LddStructuresKinematic, equal to the "old" (unmodified) LddKinematic (needed to
        connect the inflow and outflow points of each structure)
    """

    def __init__(self, structures_variable):
        self.var = structures_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
    def initial(self):
        """ initial part of the structures module
        """
        self.var.LddStructuresKinematic = self.var.LddKinematic     #pcr map
        LddStructuresKinematicNp = compressArray(self.var.LddStructuresKinematic)
        # Unmodified version of LddKinematic is needed to connect inflow and outflow points
        # of each structure (called LddStructuresKinematic now)

        self.var.LddStructuresChan = self.var.LddChan   #pcr map
        LddStructuresChanNp = compressArray(self.var.LddStructuresChan)
        # Unmodified version of LddChan is needed to connect inflow and outflow points
        # of each structure (called LddStructuresChan now)

        settings = LisSettings.instance()
        option = settings.options
        if not option['InitLisflood']:
            # not done in Init Lisflood
            maskinfo = MaskInfo.instance()
            n_cells = maskinfo.info.mapC[0]
            downs = self.var.downstruct
            is_pit = downs >= n_cells

            # Cell-immediately-upstream-of-structure mask: each cell takes the
            # structure boolean of its downstream neighbour. Pit cells (no
            # downstream neighbour, flagged by the sentinel index) keep their own
            # value, matching PCRaster downstream pit semantics. downstruct is the
            # compressed downstream-cell index for the channel LDD, which equals
            # the kinematic LDD at this point in initialisation (the MCT channel
            # split happens later), so the same index serves both gathers.
            IsStructureKinematicC = np.asarray(self.var.IsStructureKinematic).astype(bool)
            IsStructureChanC = np.asarray(self.var.IsStructureChan).astype(bool)

            self.var.IsUpsOfStructureKinematicC = np.where(     #np compressed array
                is_pit, IsStructureKinematicC,
                IsStructureKinematicC[np.minimum(downs, n_cells - 1)])
            # Location of pixels immediately upstream of a structure on the LddKinematic
            self.var.IsUpsOfStructureChanC = np.where(      #np compressed array
                is_pit, IsStructureChanC,
                IsStructureChanC[np.minimum(downs, n_cells - 1)])
            # Location of pixels immediately upstream of a structure on the LddChan

            # Insert a pit (ldd=5) at each cell immediately upstream of a
            # structure. On a valid LDD this is equivalent to
            # lddrepair(ifthenelse(mask, 5, Ldd)): adding a pit cannot create a
            # loop or an off-map pointer, so LDD re-validation is a no-op. The
            # maps are rebuilt as PCRaster LDD-typed fields because later modules
            # (initialMCT/initialKinematicWave) consume them as LDDs; decompress
            # yields a scalar field, so an explicit ldd(nominal(...)) cast
            # restores the LDD type the consumers require.
            LddKinematicC = compressArray(self.var.LddKinematic)
            LddChanC = compressArray(self.var.LddChan)
            LddKinematicC[self.var.IsUpsOfStructureKinematicC] = 5
            LddChanC[self.var.IsUpsOfStructureChanC] = 5
            self.var.LddKinematic = ldd(nominal(decompress(LddKinematicC)))   #pcr map
            # Update LddKinematic by adding a pit in the pixel immediately upstream of a structure
            self.var.LddChan = ldd(nominal(decompress(LddChanC)))     #pcr map
            # Update LddChan by adding a pit in the pixel immediately upstream of a structure
