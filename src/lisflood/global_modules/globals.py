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

# CM: getopt module is a parser for command line options (consider using argparse module instead)
import getopt

# CM: defining global variables
# global maskinfo,zeromap,modelSteps,xmlstring
global maskinfo         # CM: Definition of compressed mask array and info how to blow it up again
maskinfo = {}

# CM mod
# not used
# global zeromap

global modelSteps       # CM: list of start and end time step for the model (modelSteps[0] = start; modelSteps[1] = end)
modelSteps=[]

# CMmod Non e' necessario che sia una variabile globale
global xmlstring
xmlstring=[]

# global binding, option, FlagName, Flags, ReportSteps, FilterSteps, EnsMembers, outputDir
global binding          # CM: dictionary of all model's options and settings for running ang managing the model
binding = {}

global option           # CM: dictionary of all model's options and settings for running ang managing the model
option = {}

global FlagName         # CM: dictionary of flags defining model's behavior (quiet,veryquiet, loud, checkfiles, noheader,printtime, debug)

global Flags            # CM: dictionary of flags defining model's behavior (quiet,veryquiet, loud, checkfiles, noheader,printtime, debug)

global ReportSteps      # CM: reporting steps for state maps
ReportSteps = {}

global FilterSteps      # CM: used only in Kalmanf filter option
FilterSteps = []

global EnsMembers       # CM: used only in Kalmanf filter option
EnsMembers = []

global outputDir        # CM: path of directory to store model outputs
outputDir = []

# global MMaskMap, maskmapAttr, bigmapAttr, cutmap, metadataNCDF
global MMaskMap         # CM: mask for checking maps
MMaskMap = 0

global maskmapAttr      # CM: attributes of masking map (clonemap) - dictionary
maskmapAttr = {}

# CM mod
# not used
# global bigmapAttr
# bigmapAttr = {}

global cutmap           # CM: defines the MaskMap inside the forcing maps
cutmap = [0, 1, 0, 1]

global metadataNCDF     # CM: store map metadata from netcdf default file (or e0.nc)
metadataNCDF = {}

global timestepInit     # CM: if initial conditions are stored as netCDF with different time steps this variable indicates which time step to use either as date e.g. 1/1/2010 or as number e.g. 5
timestepInit =[]

#CMmod Add definition of cdfFlag as global variable
global cdfFlag
cdfFlag = [0,0, 0,0,0,0,0]  # flag for netcdf output for end, steps, all, monthly (steps), yearly(steps), monthly , yearly

# global timeMes,TimeMesString, timeMesSum
global timeMes          # time measure - filled in dynamic
timeMes=[]

global TimeMesString    # name of the time measure - filled in dynamic
timeMesString = []

global timeMesSum       # time measure of hydrological modules
timeMesSum = []


# CM: initializing variables
reportTimeSerieAct = {}
reportMapsAll = {}
reportMapsSteps = {}
reportMapsEnd = {}
nrCores = []

# ----------------------------------
# CM: set names of input arguments
# CM: initializing Flags to false values
Flags = {'quiet': False, 'veryquiet': False, 'loud': False,
         'check': False, 'noheader': False, 'printtime': False,
         'debug':False}

FlagName = ['quiet', 'veryquiet', 'loud',
            'checkfiles', 'noheader', 'printtime',
            'debug']

def globalFlags(arg):
    """ Read flags for model launching options
    
    Read flags for model lounching options: according to the flags the output is adjusted
    (quiet,veryquiet, loud, checkfiles, noheader, printtime, debug)
        
    :param arg: model argument argument
    :return: 
    """
    try:
        opts, args = getopt.getopt(arg, 'qvlchtd', FlagName)
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
        if o in ('-d', '--debug'):
            Flags['debug'] = True
