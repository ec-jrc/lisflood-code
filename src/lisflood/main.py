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

from __future__ import print_function, absolute_import, division

import uuid
import os
import sys
import datetime

src_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(src_dir):
    sys.path.append(src_dir)

from pcraster.framework import EnsKalmanFilterFramework, MonteCarloFramework

from .global_modules.checkers import ModulesInputs
from .global_modules.zusatz import DynamicFramework
from .Lisflood_EnKF import LisfloodModel_EnKF
from .Lisflood_dynamic import LisfloodModel_dyn

from .Lisflood_initial import LisfloodModel_ini
from .Lisflood_monteCarlo import LisfloodModel_monteCarlo
from .global_modules.settings import LisSettings, CDFFlags
from .global_modules.errors import LisfloodRunInfo, LisfloodWarning, LisfloodError
from .global_modules.settings import calendar, inttodate
from . import __authors__, __version__, __date__, __status__


class LisfloodModel(LisfloodModel_ini, LisfloodModel_dyn, LisfloodModel_monteCarlo, LisfloodModel_EnKF):
    """ Joining the initial and the dynamic part
        of the Lisflood model
    """
    pass

# ==================================================
# ============== LISFLOOD execute ==================
# ==================================================


def lisfloodexe(lissettings=None):

    _ = CDFFlags(uuid.uuid4())
    if isinstance(lissettings, str):
        # we passed file path
        lissettings = LisSettings(lissettings)
    else:
        # deal with LisSettings instance
        lissettings = LisSettings.instance() if lissettings is None else lissettings

    try:
        ModulesInputs.check(lissettings)
    except LisfloodError as e:
        print(e)
        sys.exit(1)

    binding = lissettings.binding
    option = lissettings.options
    report_steps = lissettings.report_steps
    flags = lissettings.flags
    model_steps = lissettings.model_steps
    filter_steps = lissettings.filter_steps
    # read all the possible option for modelling and for generating output
    # read the settingsfile with all information about the catchments(s)
    # and the choosen option for mdelling and output
    # bindkey = sorted(binding.keys())

    # remove steps from ReportSteps that are not included in simulation period
    for key in report_steps:
        report_steps[key] = [x for x in report_steps[key] if model_steps[0] <= x <= model_steps[1]]
        # ReportSteps[key] = [x for x in ReportSteps[key] if x >= modelSteps[0]]
        # ReportSteps[key] = [x for x in ReportSteps[key] if x <= modelSteps[1]]

    if option['InitLisflood']:
        print("INITIALISATION RUN")

    print("Start Step - End Step: ", model_steps[0], " - ", model_steps[1])
    print("Start Date - End Date: ",
          inttodate(model_steps[0] - 1, calendar(binding['CalendarDayStart'], binding['calendar_type'])),
          " - ",
          inttodate(model_steps[1] - 1, calendar(binding['CalendarDayStart'], binding['calendar_type'])))

    if flags['loud']:
        # print state file date
        print("State file Date: ")
        try:
            print(inttodate(calendar(binding["timestepInit"], binding['calendar_type']),
                            calendar(binding['CalendarDayStart'], binding['calendar_type'])))
        except:
            print(calendar(binding["timestepInit"], binding['calendar_type']))

        # CM: print start step and end step for reporting model state maps
        print("Start Rep Step  - End Rep Step: ", report_steps['rep'][0], " - ", report_steps['rep'][-1])
        print("Start Rep Date  - End Rep Date: ",
              inttodate(calendar(report_steps['rep'][0] - 1, binding['calendar_type']), calendar(binding['CalendarDayStart'], binding['calendar_type'])),
              " - ",
              inttodate(calendar(report_steps['rep'][-1] - 1), calendar(binding['CalendarDayStart'], binding['calendar_type'])))

        # messages at model start
        print("%-6s %10s %11s\n" % ("Step", "Date", "Discharge"))

    # Lisflood is an instance of the class LisfloodModel
    # LisfloodModel includes 2 methods : initial and dynamic (formulas applied at every timestep)
    Lisflood = LisfloodModel()
    # stLisflood is an instance of the class DynamicFramework

    stLisflood = DynamicFramework(Lisflood, firstTimestep=model_steps[0], lastTimeStep=model_steps[1])
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
    if EnKFset and filter_steps[0] == 0:
        msg = "Trying to run EnKF without filter timestep specified \nRunning LISFLOOD in Monte Carlo mode \n"
        print(LisfloodWarning(msg))
        EnKFset = 0
    if MCset and lissettings.ens_members[0] <= 1:
        msg = "Trying to run Monte Carlo simulation with only 1 member \nRunning LISFLOOD in deterministic mode \n"
        print(LisfloodWarning(msg))
        MCset = 0
    if MCset:
        mcLisflood = MonteCarloFramework(stLisflood, nrSamples=lissettings.ens_members[0])
        if lissettings.nrcores[0] > 1:
            mcLisflood.setForkSamples(True, nrCPUs=lissettings.nrcores[0])
        if EnKFset:
            kfLisflood = EnsKalmanFilterFramework(mcLisflood)
            kfLisflood.setFilterTimesteps(filter_steps)
            print(LisfloodRunInfo(mode="Ensemble Kalman Filter", outputDir=lissettings.output_dir[0],
                                  Steps=len(filter_steps),
                                  ensMembers=lissettings.ens_members[0], Cores=lissettings.nrcores[0]))
            kfLisflood.run()
        else:
            print(LisfloodRunInfo(mode = "Monte Carlo", outputDir=lissettings.output_dir[0],
                                  ensMembers=lissettings.ens_members[0], Cores=lissettings.nrcores[0]))
            mcLisflood.run()
    else:
        """
        ----------------------------------------------
        Deterministic run
        ----------------------------------------------
        """
        print(LisfloodRunInfo(mode="Deterministic", outputDir=lissettings.output_dir[0]))
        stLisflood.run()

# ==================================================
# ============== USAGE ==============================
# ==================================================


def usage():
    """ prints some lines describing how to use this program
        which arguments and parameters it accepts, etc
    """

    print('LisfloodPy - Lisflood using pcraster Python framework')
    print('Authors: ', __authors__)
    print('Version: ', __version__)
    print('Date: ', __date__)
    print('Status: ', __status__)
    print("""
    Arguments list:
    settings.xml     settings file

    -q --quiet       output progression given as .
    -v --veryquiet   no output progression is given
    -l --loud        output progression given as time step, date and discharge
    -c --check       input maps and stack maps are checked, output for each input map BUT no model run
    -h --noheader    .tss file have no header and start immediately with the time series
    -d --debug       debug outputs
    """)
    sys.exit(1)


def headerinfo():

    print("LisfloodPy ", __version__, " ", __date__)
    print("""
Water balance and flood simulation model for large catchments\n
(C) Institute for Environment and Sustainability
    Joint Research Centre of the European Commission
    TP122, I-21020 Ispra (Va), Italy\n""")


# ==================================================
# ============== MAIN ==============================
# ==================================================


def main():
    # if arguments are missing display usage info
    if len(sys.argv) < 2:
        usage()

    # setting.xml file
    settings = sys.argv[1]
    lissettings = LisSettings(settings)
    flags = lissettings.flags
    if not (flags['veryquiet'] or flags['quiet']):
        headerinfo()
    lisfloodexe(lissettings)
