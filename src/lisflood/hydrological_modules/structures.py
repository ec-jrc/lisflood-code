# -------------------------------------------------------------------------
# Name:        STRUCTURES
# Purpose:
#
# Author:      burekpe
#
# Created:     08/08/2014
# Copyright:   (c) burekpe 2014
# Licence:     <your licence>
# -------------------------------------------------------------------------

from lisflood.global_modules.add1 import *

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

        if not(option['InitLisflood']):
            # not done in Init Lisflood
            IsUpsOfStructureKinematic = downstream(self.var.LddKinematic,
                cover(boolean(decompress(self.var.IsStructureKinematic)), pcraster.boolean(0)))
            # Get all pixels just upstream of kinematic structure locations
            self.var.IsUpsOfStructureKinematicC = compressArray(IsUpsOfStructureKinematic)
            # Unmodified version of LddKinematic is needed to connect inflow and outflow points
            # of each structure (called LddStructuresKinematic now)
            self.var.LddKinematic = lddrepair(ifthenelse(IsUpsOfStructureKinematic, 5
                                    , self.var.LddKinematic))
            # Cells just upstream of each structure are treated as pits in the kinematic wave
            # channel routing



 #           lddC = compressArray(self.var.LddKinematic)
 #           inAr = decompress(np.arange(maskinfo['mapC'][0],dtype="int32"))
            # giving a number to each non missing pixel as id
 #           self.var.downKin = compressArray(downstream(self.var.LddKinematic,inAr))
            # each upstream pixel gets the id of the downstream pixel
 #           self.var.downKin[lddC==5] = maskinfo['mapC'][0]
            # all pits gets a high number

