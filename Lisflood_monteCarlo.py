from global_modules.output import *
import pickle
import os

class LisfloodModel_monteCarlo(DynamicModel, MonteCarloModel):

    """ LISFLOOD initial part
        same as the PCRaster script -initial-
        this part is to initialize the variables
        it will call the initial part of the hydrological modules
    """

    def __init__(self):
        """ init part of the initial part
            defines the mask map and the outlet points
            initialization of the hydrological modules
        """
        DynamicModel.__init__(self)
        MonteCarloModel.__init__(self)

    def premcloop(self):
        pass
  
    def postmcloop(self):
        pass