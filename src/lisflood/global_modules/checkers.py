import os
import inspect

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
        res = False
        total_checks = len(settings.output_dir)  # at least check PathOut
        # First check PathOut
        for path_out in settings.output_dir:
            if not (os.path.exists(path_out) and os.path.isdir(path_out) and os.access(path_out, os.W_OK)):
                print(LisfloodWarning('\n\nPath defined in PathOut is not writable: {}'.format(path_out)))
            else:
                res += True

        for option, modules in cls.lisflood_modules.items():
            if not (binding.get(option) or option == 'all'):
                # module is not activated
                continue
            for hydro_module in modules:
                # hydro_module = importlib.import_module('{}.{}'.format(cls.root_package, m))
                # hydro_module_str = '{}.{}'.format(cls.root_package, m)
                clzzs = [obj for n, obj in inspect.getmembers(hydro_module)
                         if inspect.isclass(obj) and issubclass(obj, HydroModule)
                         and obj is not HydroModule and str(obj.__module__) == hydro_module.__name__]
                total_checks += len(clzzs)
                for clz in clzzs:
                    res += clz.check_input_files(option)
        if res < total_checks:
            # some checks failed
            raise LisfloodError('\n\nMissing files or misconfigured paths to run LisFlood, according activated '
                                'modules. '
                                'Please check your settings file {}'.format(settings.settings_path))


class MeteoForcings:
    @classmethod
    def check(cls, settings):
        binding = settings.binding
        pass
