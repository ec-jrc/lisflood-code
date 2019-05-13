"""

Copyright 2019 European Union

Licensed under the EUPL, Version 1.2 or as soon they will be approved by the European Commission  subsequent versions of the EUPL (the "Licence");

You may not use this work except in compliance with the Licence.
You may obtain a copy of the Licence at:

https://joinup.ec.europa.eu/sites/default/files/inline-files/EUPL%20v1_2%20EN(1).txt

Unless required by applicable law or agreed to in writing, software distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and limitations under the Licence.

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
from metainfo import __authors__, __version__, __date__, __status__


class LisfloodModel(LisfloodModel_ini, LisfloodModel_dyn, LisfloodModel_monteCarlo, LisfloodModel_EnKF):
    """ Joining the initial and the dynamic part
        of the Lisflood model
    """

# ==================================================
# ============== LISFLOOD execute ==================
# ==================================================


def Lisfloodexe(settings, optionxml):

    # read options and bindings and launch Lisflood model computation
    # returns option binding and ReportSteps - global dictionaries
    optionBinding(settings, optionxml)
    # read all the possible option for modelling and for generating output
    # read the settingsfile with all information about the catchments(s)
    # and the choosen option for mdelling and output
    bindkey = sorted(binding.keys())

    #os.chdir(outputDir[0])
    # this prevent from using relative path in settings!


    checkifDate('StepStart','StepEnd')
    # check 'StepStart' and 'StepEnd' to be >0 and 'StepStart'>'StepEnd'
    # return modelSteps

    # remove steps from ReportSteps that are not included in simulation period
    for key in list(ReportSteps.keys()):  ## creates a list of all keys
        ReportSteps[key] = [x for x in ReportSteps[key] if x >= modelSteps[0]]
        ReportSteps[key] = [x for x in ReportSteps[key] if x <= modelSteps[1]]

    if option['InitLisflood']: print "INITIALISATION RUN"

    #print start step and end step
    print "Start Step - End Step: ",modelSteps[0]," - ", modelSteps[1]
    print "Start Date - End Date: ",inttoDate(modelSteps[0]-1,Calendar(binding['CalendarDayStart']))," - ",\
        inttoDate(modelSteps[1]-1,Calendar(binding['CalendarDayStart']))


    if Flags['loud']:
        # print state file date
        print "State file Date: ",
        try:
            print inttoDate(Calendar(binding["timestepInit"]), Calendar(binding['CalendarDayStart']))
        except:
            print Calendar(binding["timestepInit"])

        # CM: print start step and end step for reporting model state maps
        print "Start Rep Step  - End Rep Step: ", ReportSteps['rep'][0], " - ", ReportSteps['rep'][-1]
        print "Start Rep Date  - End Rep Date: ", inttoDate(Calendar(ReportSteps['rep'][0] - 1),
                                                            Calendar(binding['CalendarDayStart'])), \
            " - ", inttoDate(Calendar(ReportSteps['rep'][-1] - 1), Calendar(binding['CalendarDayStart']))

        # messages at model start
        print"%-6s %10s %11s\n" %("Step","Date","Discharge"),


    # Lisflood is an instance of the class LisfloodModel
    # LisfloodModel includes 2 methods : initial and dynamic (formulas applied at every timestep)
    Lisflood = LisfloodModel()
    # stLisflood is an instance of the class DynamicFramework

    stLisflood = DynamicFramework(Lisflood, firstTimestep=modelSteps[0], lastTimeStep=modelSteps[1])
    stLisflood.rquiet = True
    stLisflood.rtrace = False


    """
    ----------------------------------------------
    Monte Carlo and Ensemble Kalman Filter setting
    ----------------------------------------------
    """
    # Ensemble Kalman filter
    try:
        EnKFset = option['EnKF']
    except:
        EnKFset = 0
    # MonteCarlo
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
    # run of the model inside the DynamicFramework
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
    -d --debug       debug outputs
    """
    sys.exit(1)


def headerinfo():

   print "LisfloodPy ", __version__, " ", __date__,
   print """
Water balance and flood simulation model for large catchments\n
(C) Institute for Environment and Sustainability
    Joint Research Centre of the European Commission
    TP122, I-21020 Ispra (Va), Italy\n"""


# ==================================================
# ============== MAIN ==============================
# ==================================================


def main():
    # if arguments are missing display usage info
    if len(sys.argv) < 2:
        usage()

    # global settings
    # global optionxml
    optionxml = get_optionxml_path()

    # setting.xml file
    settings = sys.argv[1]

    # arguments list
    args = sys.argv[2:]

    # Flags - set model behavior (quiet,veryquiet, loud, checkfiles, noheader,printtime,debug)
    globalFlags(args)
    # setting of global flag e.g checking input maps, producing more output information
    if not (Flags['veryquiet']) and not (Flags['quiet']):
        headerinfo()
    Lisfloodexe(settings, optionxml)


def get_optionxml_path():
    # read OptionTserieMaps.xml in the same folder as Lisflood main (lisf1.py)
    LF_Path = os.path.dirname(os.path.abspath(sys.argv[0]))
    # OptionTserieMaps.xml file
    optionxml = os.path.normpath(os.path.join(LF_Path, "OptionTserieMaps.xml"))
    if not os.path.exists(optionxml):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        optionxml = os.path.normpath(os.path.join(current_dir, "OptionTserieMaps.xml"))
    return optionxml


if __name__ == "__main__":
    sys.exit(main())
