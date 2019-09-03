import importlib
import inspect
import os

from .errors import LisfloodError
from ..hydrological_modules import HydroModule


def is_number(v):
    try:
        float(v)
    except ValueError:
        return False
    else:
        return True


def is_path(v):
    return os.path.exists(v) or os.access(v, os.W_OK)


class ModulesInputs:
    root_package = 'lisflood.hydrological_modules'
    lisflood_modules = {
        'all': ['surface_routing', 'snow', 'routing', 'leafarea', 'landusechange', 'frost', 'groundwater'],  # not optional modules
        # list of modules activated by options in LisFlood settings.xml
        'inflow': ['inflow'],
        'wateruse': ['wateruse'],
        'groundwaterSmooth': ['waterabstraction'],
        'wateruseRegion': ['waterabstraction'],
        'drainedIrrigation': ['soilloop', 'soil'],
        'riceIrrigation': ['riceirrigation', 'waterabstraction'],
        'indicator': ['lakes', 'indicatorcalc', 'waterabstraction'],
        'openwaterevapo': ['evapowater'],
        'varfractionwater': ['evapowater'],
        'TransientLandUseChange': ['landusechange', 'indicatorcalc', 'waterabstraction'],
        'simulateLakes': ['lakes', 'indicatorcalc', 'routing', 'waterabstraction', 'waterbalance'],
        'simulateReservoirs': ['reservoir', 'indicatorcalc', 'routing', 'waterabstraction', 'waterbalance'],
        'simulatePF': ['soilloop', 'soil'],
        'simulateWaterLevels': ['waterlevel'],
        'TransLoss': ['transmission'],
        'gridSizeUserDefined': ['miscInitial'],
    }

    @classmethod
    def check(cls, settings):
        """

            :param settings: LisSettings object
            """
        binding = settings.binding
        res = False
        total_checks = 0
        for option, modules in cls.lisflood_modules.items():
            if not (binding.get(option) or option == 'all'):
                # module is not activated
                continue
            for m in modules:
                hydro_module = importlib.import_module('{}.{}'.format(cls.root_package, m))
                clzzs = [obj for n, obj in inspect.getmembers(hydro_module) if
                         inspect.isclass(obj) and issubclass(obj, HydroModule) and obj is not HydroModule]
                total_checks += len(clzzs)
                for clz in clzzs:
                    res += clz.check_input_files(option)
        if res < total_checks:
            # some checks failed
            raise LisfloodError('Missing files to run LisFlood according activated modules. '
                                'Please check your settings file {}'.format(settings.settings_path))
