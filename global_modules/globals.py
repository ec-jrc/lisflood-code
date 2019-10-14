# -------------------------------------------------------------------------
# Name:        globals
# Purpose:
#
# Author:      burekpe
#
# Created:     26/02/2014
# Copyright:   (c) burekpe 2014
# Licence:     <your licence>
# -------------------------------------------------------------------------
from IPython.core.debugger import set_trace as jupyter_breakpoint
from IPython import embed as ipython_embed
import getopt
from collections import OrderedDict

global maskinfo,zeromap,modelSteps,xmlstring
maskinfo = {}
modelSteps=[]
xmlstring=[]

global binding, option, FlagName, Flags, ReportSteps, FilterSteps, EnsMembers, outputDir
global MMaskMap, maskmapAttr, bigmapAttr, cutmap, metadataNCDF
global timestepInit

timestepInit =[]
binding = {}
option = {}

reportTimeSerieAct = {}
reportMapsAll = {}
reportMapsSteps = {}
reportMapsEnd = {}

MMaskMap = 0
ReportSteps = {}
FilterSteps = []
EnsMembers = []
nrCores = []
outputDir = []

maskmapAttr = {}
bigmapAttr = {}
cutmap = 4 * [None]
cdfFlag = [0, 0, 0,0,0,0,0]  # flag for netcdf output for all, steps and end, monthly (steps), yearly(steps), monthly , yearly
metadataNCDF = {}

global timeMes,TimeMesString, timeMesSum
timeMes=[]
timeMesString = []  # name of the time measure - filled in dynamic
timeMesSum = []    # time measure of hydrological modules

# Mapping of vegetation types to land use fractions (and the other way around)
global VEGETATION_LANDUSE, LANDUSE_VEGETATION, PRESCRIBED_VEGETATION, PRESCRIBED_LAI
SOIL_USES = ["Rainfed", "Forest", "Irrigated"]
PRESCRIBED_VEGETATION = [fract + "_prescribed" for fract in SOIL_USES]
PRESCRIBED_LAI = OrderedDict(zip(PRESCRIBED_VEGETATION[:], ['LAIOtherMaps', 'LAIForestMaps', 'LAIIrrigationMaps']))
VEGETATION_LANDUSE = OrderedDict(zip(PRESCRIBED_VEGETATION[:], SOIL_USES[:]))
LANDUSE_VEGETATION = OrderedDict([(v, [k]) for k, v in VEGETATION_LANDUSE.items()])
LANDUSE_INPUTMAP = OrderedDict(zip(LANDUSE_VEGETATION.keys(), ["OtherFraction", "ForestFraction", "IrrigationFraction"]))

# ----------------------------------
FlagName = ['quiet', 'veryquiet', 'loud',
            'checkfiles', 'noheader', 'printtime']
Flags = {'quiet': False, 'veryquiet': False, 'loud': False,
         'check': False, 'noheader': False, 'printtime': False}


def globalFlags(arg):
    """ read flags - according to the flags the output is adjusted
        quiet,veryquiet, loud, checkfiles, noheader,printtime
    """
    try:
        opts, args = getopt.getopt(arg, 'qvlcht', FlagName)
    except getopt.GetoptError:
        usage()

    for o, a in opts:
        if o in ('-q', '--quiet'):
            Flags['quiet'] = True          # Flag[0]=1
        if o in ('-v', '--veryquiet'):
            Flags['veryquiet'] = True      # Flag[1]=1
        if o in ('-l', '--loud'):
            Flags['loud'] = True  # Loud=True
        if o in ('-c', '--checkfiles'):
            Flags['check'] = True  # Check=True
        if o in ('-h', '--noheader'):
            Flags['noheader'] = True  # NoHeader=True
        if o in ('-t', '--printtime'):
            Flags['printtime'] = True      # Flag[2]=1
