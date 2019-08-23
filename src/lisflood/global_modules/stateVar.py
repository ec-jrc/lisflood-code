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
from __future__ import absolute_import

from lisflood.global_modules.settings import CDFFlags
from .add1 import *


# CM: new-style class in Python 2.x
class stateVar(object):

    """
    # ************************************************************
    # ***** ROUTING      *****************************************
    # ************************************************************
    """

    def __init__(self, stateVar_variable):
        self.var = stateVar_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
    def dynamic(self):
        """ reporting of state variables in dynamic part
        """
        settings = LisSettings.instance()
        option = settings.options
        filter_steps = settings.filter_steps
        try:
            EnKFset = option['EnKF']
        except:
            EnKFset = 0

        if EnKFset and self.var.currentTimeStep() in filter_steps:
            sample = str(self.var.currentSampleNumber())
            dumpObject("StartDate", self.var.CalendarDayStart, sample)
            ## Snow
            dumpObject("SnowCover", self.var.SnowCoverS, sample)
            ## Soil Moisture
            dumpObject("Intercept", self.var.Interception, sample)
            dumpObject("CumIntercept", self.var.CumInterception, sample)
            dumpObject("Frost", self.var.FrostIndex, sample)
            dumpObject("W1a", self.var.W1a, sample)
            dumpObject("W1b", self.var.W1b, sample)
            dumpObject("W1", self.var.W1, sample)
            dumpObject("W2", self.var.W2, sample)
            dumpObject("DSLR", self.var.DSLR, sample)
            ## Groundwater
            dumpObject("UZ", self.var.UZ, sample)
            dumpObject("LZ", self.var.LZ, sample)
            ## Lakes
            if option['simulateLakes']:
                dumpObject("LakeStorageM3", self.var.LakeStorageM3CC, sample)
                dumpObject("LakeOutflow", self.var.LakeOutflow, sample)
            ## Routing
            dumpObject("ChanM3Kin", self.var.ChanM3Kin, sample)
            dumpObject("ChanQ", self.var.ChanQ, sample)
            dumpObject("ToChan", self.var.ToChanM3RunoffDt, sample)
            try:
                dumpObject("Chan2M3Kin", self.var.Chan2M3Kin, sample)
                dumpObject("Sideflow1Chan", self.var.Sideflow1Chan, sample)
            except:
                pass
            ## Overland
            dumpObject("OFM3Direct", self.var.OFM3Direct, sample)
            dumpObject("OFM3Other", self.var.OFM3Other, sample)
            dumpObject("OFM3Forest", self.var.OFM3Forest, sample)
            ### Reservoirs
            if option['simulateReservoirs']:
                dumpObject("ReservoirStorageM3CC", self.var.ReservoirStorageM3CC, sample)
                dumpObject("ReservoirFill", self.var.ReservoirFill, sample)
                dumpObject("QResOutM3Dt", self.var.QResOutM3Dt, sample)
            try:
                dumpObject("Tss", self.var.Tss, sample)
            except:
                pass
            cdfflags = CDFFlags.instance()
            dumpObject("cdfFlag", cdfflags, sample)

    def resume(self):

        sample = str(self.var.currentSampleNumber())
        updateVec = self.var.getStateVector(sample)
        self.var.CalendarDayStart = loadObject("StartDate", sample)
        ## Snow
        self.var.SnowCoverS = loadObject("SnowCover", sample)
        ## Soil Moisture
        self.var.Interception = loadObject("Intercept", sample)
        self.var.CumInterception = loadObject("CumIntercept", sample)
        self.var.FrostIndex = loadObject("Frost", sample)
        self.var.W1a = loadObject("W1a", sample)
        self.var.W1b = loadObject("W1b", sample)
        self.var.W1 = loadObject("W1", sample)
        self.var.W2 = loadObject("W2", sample)
        self.var.DSLR = loadObject("DSLR", sample)
        ## Groundwater
        self.var.UZ = loadObject("UZ", sample)
        self.var.LZ = loadObject("LZ", sample)
        ## Lakes
        settings = LisSettings.instance()
        option = settings.options
        if option['simulateLakes']:
            self.var.LakeStorageM3CC = loadObject("LakeStorageM3", sample)
            self.var.LakeOutflow = loadObject("LakeOutflow", sample)
        ## Routing
        self.var.ChanM3Kin = loadObject("ChanM3Kin", sample)
        self.var.ChanQ = loadObject("ChanQ", sample)
        self.var.ToChanM3RunoffDt = loadObject("ToChan", sample)
        try:
            self.var.Chan2M3Kin = loadObject("Chan2M3Kin", sample)
            self.var.Sideflow1Chan = loadObject("Sideflow1Chan", sample)
        except:
            pass
        ## Overland
        self.var.OFM3Direct = loadObject("OFM3Direct", sample)
        self.var.OFM3Other = loadObject("OFM3Other", sample)
        self.var.OFM3Forest = loadObject("OFM3Forest", sample)
        ### Reservoirs
        if option['simulateReservoirs']:
            self.var.ReservoirStorageM3CC = loadObject("ReservoirStorageM3CC", sample)
            self.var.ReservoirFill = loadObject("ReservoirFill", sample)
            self.var.QResOutM3Dt = loadObject("QResOutM3Dt", sample)
        try:
            self.output_module.var.Tss = loadObject("Tss", sample)
        except:
            pass
        cdfflags = CDFFlags.instance()
        cdfflags.set(loadObject("cdfFlag", sample))
        # globals.cdfFlag = loadObject("cdfFlag", sample)
