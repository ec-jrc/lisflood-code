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

from __future__ import print_function, absolute_import, unicode_literals

import os
import inspect
import warnings

from .errors import LisfloodError, LisfloodWarning
from ..hydrological_modules import HydroModule
from ..hydrological_modules import (surface_routing, evapowater, snow, routing, leafarea, inflow, waterlevel,
                                    waterbalance, wateruse, waterabstraction, lakes, riceirrigation, indicatorcalc,
                                    landusechange, frost, groundwater, miscInitial, soilloop, soil,
                                    reservoir, transmission)


class ModulesInputs:
    root_package = 'lisflood.hydrological_modules'
    # dict representing modules activated per option
    lisflood_modules = {
        # not optional modules
        'all': [surface_routing, snow, routing, leafarea, landusechange,
                frost, groundwater, miscInitial, soil],
        # list of modules activated by options in LisFlood settings.xml
        'inflow': [inflow],
        'wateruse': [wateruse],
        'groundwaterSmooth': [waterabstraction],
        'wateruseRegion': [waterabstraction],
        'drainedIrrigation': [soilloop, soil],
        'riceIrrigation': [riceirrigation, waterabstraction],
        'indicator': [lakes, indicatorcalc, waterabstraction],
        'openwaterevapo': [evapowater],
        'varfractionwater': [evapowater],
        'TransientLandUseChange': [landusechange, indicatorcalc, waterabstraction],
        'simulateLakes': [lakes, indicatorcalc, routing, waterabstraction, waterbalance],
        'simulateReservoirs': [reservoir, indicatorcalc, routing, waterabstraction, waterbalance],
        'simulatePF': [soilloop, soil],
        'simulateWaterLevels': [waterlevel],
        'TransLoss': [transmission],
        'gridSizeUserDefined': [miscInitial],
    }

    @classmethod
    def check(cls, settings):
        """
        :param settings: LisSettings object
        """
        binding = settings.binding
        res = 0
        all_errors = []
        total_checks = 1  # at least check PathOut
        # First check PathOut
        if not (os.path.exists(settings.output_dir) and os.path.isdir(settings.output_dir) and os.access(settings.output_dir, os.W_OK)):
            msg = '\n\nPath defined in PathOut is not writable: {}'.format(settings.output_dir)
            warnings.warn(LisfloodWarning(msg))
            all_errors.append(msg)
        else:
            res += 1

        for option, modules in cls.lisflood_modules.items():
            if not (binding.get(option) or option == 'all'):
                # module is not activated
                continue
            for hydro_module in modules:
                clzzs = [obj for n, obj in inspect.getmembers(hydro_module)
                         if inspect.isclass(obj) and issubclass(obj, HydroModule)
                         and obj is not HydroModule and str(obj.__module__) == hydro_module.__name__]
                total_checks += len(clzzs)
                for clz in clzzs:
                    module_ok, errors = clz.check_input_files(option)
                    res += int(module_ok)
                    all_errors += errors
        if res < total_checks:
            # some checks failed

            raise LisfloodError('\n\nMissing files or misconfigured paths to run LisFlood, according activated modules. '
                                'Please check your settings file {}.\n{}'.format(settings.settings_path, all_errors))


class MeteoForcings:
    @classmethod
    def check(cls, settings):
        # TODO implement
        binding = settings.binding
        pass
