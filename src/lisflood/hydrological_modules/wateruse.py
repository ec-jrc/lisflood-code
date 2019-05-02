# -------------------------------------------------------------------------
# Name:        Water use module
# Purpose:
#
# Author:      burekpe
#
# Created:     29.03.2014
# Copyright:   (c) burekpe 2014
# Licence:     <your licence>
# -------------------------------------------------------------------------


from pcraster import*
from pcraster.framework import *
import sys
import os
import string
import math


from lisflood.global_modules.zusatz import *
from lisflood.global_modules.add1 import *
from lisflood.global_modules.globals import *


class wateruse(object):

    """
    # ************************************************************
    # ***** WATER USE    *****************************************
    # ************************************************************
    """

    def __init__(self, wateruse_variable):
        self.var = wateruse_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """ initial part of the water use module
        """

# ************************************************************
# ***** WATER USE
# ************************************************************


    def dynamic_init(self):
        """ dynamic part of the water use module
            init water use before sub step routing
        """


