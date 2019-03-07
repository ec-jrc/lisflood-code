#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


"""
 ######################################################################

 ##       ####  ######  ######## ##        #######   #######  ########
 ##        ##  ##    ## ##       ##       ##     ## ##     ## ##     ##
 ##        ##  ##       ##       ##       ##     ## ##     ## ##     ##
 ##        ##   ######  ######   ##       ##     ## ##     ## ##     ##
 ##        ##        ## ##       ##       ##     ## ##     ## ##     ##
 ##        ##  ##    ## ##       ##       ##     ## ##     ## ##     ##
 ######## ####  ######  ##       ########  #######   #######  ########

######################################################################
"""

__authors__ = "Ad de Roo, Peter Burek, Johan van der Knijff, Niko Wanders"
__version__ = "Version: 2.02"
__date__ ="23 Apr 2016"
__copyright__ = "Copyright 2016, European Commission - Joint Research Centre"
__maintainer__ = "Ad de Roo"
__status__ = "Operation"


#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# to work with the new grid engine JRC - workaround with error on pyexpat
from pyexpat import *
import xml.dom.minidom
from netCDF4 import Dataset
from pcraster import *
from pcraster.framework import *

# ---------------------------


from Lisflood_initial import *
from Lisflood_dynamic import *
from Lisflood_monteCarlo import *
from Lisflood_EnKF import *

#class LisfloodModel(LisfloodModel_ini, LisfloodModel_dyn):
class LisfloodModel(LisfloodModel_ini, LisfloodModel_dyn, LisfloodModel_monteCarlo, LisfloodModel_EnKF):
    """ Joining the initial and the dynamic part
        of the Lisflood model
    """

# ==================================================
# ============== LISFLOOD execute ==================
# ==================================================

def Lisfloodexe():

    optionBinding(settings, optionxml)
    # read all the possible option for modelling and for generating output
    # read the settingsfile with all information about the catchments(s)
    # and the choosen option for mdelling and output
    bindkey = sorted(binding.keys())

    #os.chdir(outputDir[0])
    # this prevent from using relative path in settings!


    checkifDate('StepStart','StepEnd')

    if option['InitLisflood']: print "INITIALISATION RUN"
    print "Start - End: ",modelSteps[0]," - ", modelSteps[1]
    if Flags['loud']:
        print"%-6s %10s %11s\n" %("Step","Date","Discharge"),

    Lisflood = LisfloodModel()
    stLisflood = DynamicFramework(Lisflood, firstTimestep=modelSteps[0], lastTimeStep=modelSteps[1])
    stLisflood.rquiet = True
    stLisflood.rtrace = False


    """
    ----------------------------------------------
    Monte Carlo and Ensemble Kalman Filter setting
    ----------------------------------------------
    """

    try:
        EnKFset = option['EnKF']
    except:
        EnKFset = 0
    try:
        MCset = option['MonteCarlo']
    except:
        MCset = 0
    if option['InitLisflood']:
        MCset = 0
        EnKFset = 0
    if EnKFset and not MCset:
        msg = "Trying to run EnKF with only 1 ensemble member \n"
        raise LisfloodError(msg)
    if EnKFset and FilterSteps[0] == 0:
        msg = "Trying to run EnKF without filter timestep specified \nRunning LISFLOOD in Monte Carlo mode \n"
        print LisfloodWarning(msg)
        EnKFset = 0
    if MCset and EnsMembers[0] <= 1:
        msg = "Trying to run Monte Carlo simulation with only 1 member \nRunning LISFLOOD in deterministic mode \n"
        print LisfloodWarning(msg)
        MCset = 0
    if MCset:
        mcLisflood = MonteCarloFramework(stLisflood, nrSamples=EnsMembers[0])
        if nrCores[0] > 1:
            mcLisflood.setForkSamples(True, nrCPUs=nrCores[0])
        if EnKFset:
            kfLisflood = EnsKalmanFilterFramework(mcLisflood)
            kfLisflood.setFilterTimesteps(FilterSteps)
            print LisfloodRunInfo(mode = "Ensemble Kalman Filter", outputDir = outputDir[0], Steps = len(FilterSteps), ensMembers=EnsMembers[0], Cores=nrCores[0])
            kfLisflood.run()
        else:
            print LisfloodRunInfo(mode = "Monte Carlo", outputDir = outputDir[0], ensMembers=EnsMembers[0], Cores=nrCores[0])
            mcLisflood.run()
    else:
        """
        ----------------------------------------------
        Deterministic run
        ----------------------------------------------
        """
        print LisfloodRunInfo(mode = "Deterministic", outputDir = outputDir[0])
        stLisflood.run()
    # cProfile.run('stLisflood.run()')
    # python -m cProfile -o  l1.pstats lisf1.py settingsNew3.xml
    # gprof2dot -f pstats l1.pstats | dot -Tpng -o callgraph.png

    if Flags['printtime']:
        print "\n\nTime profiling"
        print "%2s %-17s %10s %8s" %("No","Name","time[s]","%")
        div = 1
        timeSum = np.array(timeMesSum)
        if MCset:
            div = div * EnsMembers[0]
        if EnKFset:
            div = div * (len(FilterSteps)+1)
        if EnKFset or MCset:
            timePrint = np.zeros(len(timeSum)/div)
            for i in range(len(timePrint)):
                timePrint[i] = np.sum(timeSum[range(i, len(timeSum), len(timeSum)/div)])
        else:
            timePrint = timeSum
        for i in xrange(len(timePrint)):
            print "%2i %-17s %10.2f %8.1f"  %(i,timeMesString[i],timePrint[i],100 * timePrint[i] / timePrint[-1])
    i=1

# ==================================================
# ============== USAGE ==============================
# ==================================================


def usage():
    """ prints some lines describing how to use this program
        which arguments and parameters it accepts, etc
    """
    print 'LisfloodPy - Lisflood using pcraster Python framework'
    print 'Authors: ', __authors__
    print 'Version: ', __version__
    print 'Date: ', __date__
    print 'Status: ', __status__
    print """
    Arguments list:
    settings.xml     settings file

    -q --quiet       output progression given as .
    -v --veryquiet   no output progression is given
    -l --loud        output progression given as time step, date and discharge
    -c --check       input maps and stack maps are checked, output for each input map BUT no model run
    -h --noheader    .tss file have no header and start immediately with the time series
    -t --printtime   the computation time for hydrological modules are printed
    """
    sys.exit(1)

def headerinfo():

   print "LisfloodPy ",__version__," ",__date__,
   print """
Water balance and flood simulation model for large catchments\n
(C) Institute for Environment and Sustainability
    Joint Research Centre of the European Commission
    TP122, I-21020 Ispra (Va), Italy\n"""


# ==================================================
# ============== MAIN ==============================
# ==================================================

if __name__ == "__main__":

    if len(sys.argv) < 2:
        usage()


    LF_Path = os.path.dirname(sys.argv[0])
    LF_Path = os.path.abspath(LF_Path)
    optionxml = os.path.normpath(LF_Path + "/OptionTserieMaps.xml")

    settings = sys.argv[1]    # setting.xml file

    args = sys.argv[2:]
    globalFlags(args)
    # setting of global flag e.g checking input maps, producing more output information
    if not(Flags['veryquiet']) and not(Flags['quiet']) : headerinfo()
    Lisfloodexe()
