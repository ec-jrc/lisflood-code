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

from global_modules.output import *


class LisfloodModel_EnKF(DynamicModel, MonteCarloModel, EnKfModel):

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
        EnKfModel.__init__(self)

    def setState(self):
        ### Create some random model simulations
        ### This is done for each ensemble member individually
        values = np.random.normal(0,1,5)
        #print str("Model") + str(values)
        ## Return values to EnKF framework
        return values

    def setObservations(self):
        ## Create some random observations
        values = np.random.normal(0,1,5)

        # creating the observation matrix (nrObservations x nrSamples)
        # here without added noise
        observations = numpy.array([values,]*self.nrSamples()).transpose()

        # creating the covariance matrix (nrObservations x nrObservations)
        # here just random values
        covariance = numpy.random.random((5, 5))

        ## Return observations to EnKF framework
        self.setObservedMatrices(observations, covariance)

    def resume(self):
        sample = str(self.currentSampleNumber())

        updateVec = self.getStateVector(sample)

        #print str("update") + str(updateVec)
        self.stateVar_module.resume()
