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
            IsUpsOfStructureKinematic = downstream(     #pcr map
                self.var.LddKinematic,
                cover(boolean(decompress(self.var.IsStructureKinematic)), boolean(0))
            )
            # Downstream assigns to result the expression value of the neighbouring downstream cell
            # Over is used to cover missing values on an expression with values taken from one or more different expression(s)
            # Decompress is numpy2pcr
            # Find location of pixels immediately upstream of a structure on the LddKinematic

            IsUpsOfStructureChan = downstream(      #pcr map
                self.var.LddChan,
                cover(boolean(decompress(self.var.IsStructureChan)), boolean(0))
            )
            # Find location of pixels immediately upstream of a structure on the LddChan

            self.var.IsUpsOfStructureKinematicC = compressArray(IsUpsOfStructureKinematic)  #np compressed array
            # Location of pixels immediately upstream of a structure on the LddKinematic
            self.var.IsUpsOfStructureChanC = compressArray(IsUpsOfStructureChan)    #np compressed array
            # Location of pixels immediately upstream of a structure on the LddChan

            self.var.LddKinematic = lddrepair(ifthenelse(IsUpsOfStructureKinematic, 5, self.var.LddKinematic))  #pcr map
            # Update LddKinematic by adding a pit in the pixel immediately upstream of a structure
            self.var.LddChan = lddrepair(ifthenelse(IsUpsOfStructureChan, 5, self.var.LddChan))     #pcr map
            # Update LddChan by adding a pit in the pixel immediately upstream of a structure
