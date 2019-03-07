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

#getopt module is a parser for command line options (consider using argparse module instead)
import getopt

#defining global variables

global maskinfo         #Definition of compressed mask array and info how to blow it up again
maskinfo = {}


global modelSteps       #list of start and end time step for the model (modelSteps[0] = start; modelSteps[1] = end)
modelSteps=[]
xmlstring=[]

global binding          #dictionary of all model's options and settings for running ang managing the model
binding = {}

global option           #dictionary of all model's options and settings for running ang managing the model
option = {}

global FlagName         #dictionary of flags defining model's behavior (quiet,veryquiet, loud, checkfiles, noheader,printtime, debug)

global Flags            #dictionary of flags defining model's behavior (quiet,veryquiet, loud, checkfiles, noheader,printtime, debug)

global ReportSteps      #reporting steps for state maps
ReportSteps = {}

global FilterSteps      #used only in Kalmanf filter option
FilterSteps = []

global EnsMembers       #used only in Kalmanf filter option
EnsMembers = []

global outputDir        #path of directory to store model outputs
outputDir = []

# global MMaskMap, maskmapAttr, bigmapAttr, cutmap, metadataNCDF
global MMaskMap         #mask for checking maps
MMaskMap = 0

global maskmapAttr      #attributes of masking map (clonemap) - dictionary
maskmapAttr = {}


global cutmap           #defines the MaskMap inside the forcing maps
cutmap = [0, 1, 0, 1]

global metadataNCDF     #store map metadata from netcdf default file (or e0.nc)
metadataNCDF = {}

global timestepInit     #if initial conditions are stored as netCDF with different time steps this variable indicates which time step to use either as date e.g. 1/1/2010 or as number e.g. 5
timestepInit =[]


global cdfFlag
cdfFlag = [0,0, 0,0,0,0,0]  # flag for netcdf output for end, steps, all, monthly (steps), yearly(steps), monthly , yearly

# global timeMes,TimeMesString, timeMesSum
global timeMes          # time measure - filled in dynamic
timeMes=[]

global TimeMesString    # name of the time measure - filled in dynamic
timeMesString = []

global timeMesSum       # time measure of hydrological modules
timeMesSum = []


#initializing variables
reportTimeSerieAct = {}
reportMapsAll = {}
reportMapsSteps = {}
reportMapsEnd = {}
nrCores = []

# ----------------------------------
#set names of input arguments
#initializing Flags to false values
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
