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

from pcraster import downstream, boolean, cover, lddrepair, ifthenelse

from ..global_modules.add1 import decompress, compressArray
from ..global_modules.settings import LisSettings


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
        self.var.LddStructuresKinematic = self.var.LddKinematic
        settings = LisSettings.instance()
        option = settings.options
        if not option['InitLisflood']:
            # not done in Init Lisflood
            IsUpsOfStructureKinematic = downstream(
                self.var.LddKinematic,
                cover(boolean(decompress(self.var.IsStructureKinematic)), boolean(0))
            )
            # Get all pixels just upstream of kinematic structure locations
            self.var.IsUpsOfStructureKinematicC = compressArray(IsUpsOfStructureKinematic)
            # Unmodified version of LddKinematic is needed to connect inflow and outflow points
            # of each structure (called LddStructuresKinematic now)
            self.var.LddKinematic = lddrepair(ifthenelse(IsUpsOfStructureKinematic, 5, self.var.LddKinematic))
            # Cells just upstream of each structure are treated as pits in the kinematic wave
            # channel routing
