
import os
import sys
import uuid
import shutil

from bs4 import BeautifulSoup

from lisfloodutilities.compare.nc import NetCDFComparator
from lisfloodutilities.compare.pcr import TSSComparator

from lisflood.global_modules.settings import LisSettings, Singleton
from lisflood.global_modules.errors import LisfloodError


def setoptions(settings_file, opts_to_set=None, opts_to_unset=None, vars_to_set=None):
    if isinstance(opts_to_set, str):
        opts_to_set = [opts_to_set]
    if isinstance(opts_to_unset, str):
        opts_to_unset = [opts_to_unset]

    opts_to_set = [] if opts_to_set is None else opts_to_set
    opts_to_unset = [] if opts_to_unset is None else opts_to_unset
    vars_to_set = {} if vars_to_set is None else vars_to_set
    with open(settings_file) as tpl:
        soup = BeautifulSoup(tpl, 'lxml-xml')
        for opt in opts_to_set:
            for tag in soup.find_all("setoption", {'name': opt}):
                tag['choice'] = '1'
                break
        for opt in opts_to_unset:
            for tag in soup.find_all("setoption", {'name': opt}):
                tag['choice'] = '0'
                break
        for textvar, value in vars_to_set.items():
            for tag in soup.find_all("textvar", {'name': textvar}):
                tag['value'] = value
                break

    # Generating XML settings_files on fly from template
    uid = uuid.uuid4()
    filename = os.path.join(os.path.dirname(settings_file), './{}_{}.xml'.format(os.path.basename(settings_file), uid))
    with open(filename, 'w') as dest:
        dest.write(soup.prettify())
    try:
        Singleton._instances = {}
        Singleton._current = {}
        settings = LisSettings(filename)
        options = settings.options
        for opt in opts_to_set:
            options[opt] = True
        for opt in opts_to_unset:
            options[opt] = False
    except LisfloodError as e:
        raise e
    finally:
        os.unlink(filename)
    return settings


def mk_path_out(p):
    path_out = os.path.join(os.path.dirname(__file__), p)
    if os.path.exists(path_out):
        shutil.rmtree(path_out)
    os.mkdir(path_out)
    return path_out


class ETRS89TestCase(object):
    case_dir = os.path.join(os.path.dirname(__file__), 'data', 'LF_ETRS89_UseCase')
    ref_dir = os.path.join(case_dir, 'reference')
    reference_files = {
        'dis': {
            'report_map': 'DischargeMaps',
            'report_tss': 'DisTS',
            '86400': {
                'map': os.path.join(ref_dir, 'output_reference_daily/dis.nc'),
                'tss': os.path.join(ref_dir, 'output_reference_daily/dis.tss'),
            },
            '21600': {
                'map': os.path.join(ref_dir, 'output_reference_6h/dis.nc'),
                'tss': os.path.join(ref_dir, 'output_reference_6h/dis.tss'),
            },
        },
        'chanq': {
            'report_map': None,
            'report_tss': 'ChanqTS',
            '86400': {
                'map': None,
                'tss': os.path.join(ref_dir, 'output_reference_daily/chanqWin.tss'),
            },
            '21600': {
                'map': None,
                'tss': os.path.join(ref_dir, 'output_reference_6h/chanqWin.tss'),
            },
        },
        'thia': {
            'report_map': 'Theta1IrrigationState',
            'report_tss': None,
            '86400': {
                'map': os.path.join(ref_dir, 'output_reference_daily/thia.nc'),
                'tss': None,
            },
            '21600': {
                'map': os.path.join(ref_dir, 'output_reference_6h/thia.nc'),
                'tss': None,
            },
        },
        'thic': {
            'report_map': 'Theta3IrrigationState',
            'report_tss': None,
            '86400': {
                'map': os.path.join(ref_dir, 'output_reference_daily/thic.nc'),
                'tss': None,
            },
            '21600': {
                'map': os.path.join(ref_dir, 'output_reference_6h/thic.nc'),
                'tss': None,
            },
        },
        'thfa': {
            'report_map': 'Theta1ForestState',
            'report_tss': None,
            '86400': {
                'map': os.path.join(ref_dir, 'output_reference_daily/thfa.nc'),
                'tss': None,
            },
            '21600': {
                'map': os.path.join(ref_dir, 'output_reference_6h/thfa.nc'),
                'tss': None,
            },
        },
        'thfc': {
            'report_map': 'Theta3ForestState',
            'report_tss': None,
            '86400': {
                'map': os.path.join(ref_dir, 'output_reference_daily/thfc.nc'),
                'tss': None,
            },
            '21600': {
                'map': os.path.join(ref_dir, 'output_reference_6h/thfc.nc'),
                'tss': None,
            },
        },
        'tha': {
            'report_map': 'Theta1State',
            'report_tss': None,
            '86400': {
                'map': os.path.join(ref_dir, 'output_reference_daily/tha.nc'),
                'tss': None,
            },
            '21600': {
                'map': os.path.join(ref_dir, 'output_reference_6h/tha.nc'),
                'tss': None,
            },
        },
        'thc': {
            'report_map': 'Theta3State',
            'report_tss': None,
            '86400': {
                'map': os.path.join(ref_dir, 'output_reference_daily/thc.nc'),
                'tss': None,
            },
            '21600': {
                'map': os.path.join(ref_dir, 'output_reference_6h/thc.nc'),
                'tss': None,
            },
        },
        'lz': {
            'report_map': 'LZState',
            'report_tss': None,
            '86400': {
                'map': os.path.join(ref_dir, 'output_reference_daily/lz.nc'),
                'tss': None,
            },
            '21600': {
                'map': os.path.join(ref_dir, 'output_reference_6h/lz.nc'),
                'tss': None,
            },
        },
        'avgdis': {
            'report_map': 'AvgDis',
            'report_tss': None,
            '86400': {
                'map': os.path.join(ref_dir, 'init_daily/avgdis.nc'),
                'tss': None,
            },
            '21600': {
                'map': os.path.join(ref_dir, 'init_6h/avgdis.nc'),
                'tss': None,
            },
        },
        'lzavin': {
            'report_map': 'LZAvInflowMap',
            'report_tss': None,
            '86400': {
                'map': os.path.join(ref_dir, 'init_daily/lzavin.nc'),
                'tss': None,
            },
            '21600': {
                'map': os.path.join(ref_dir, 'init_6h/lzavin.nc'),
                'tss': None,
            },
        },
        'mbError': {
            'report_map': None,
            'report_tss': 'WaterMassBalanceTSS',
            '86400': {
                'map': None,
                'tss': os.path.join(ref_dir, 'output_reference_daily/mbError.tss'),
            },
            '21600': {
                'map': None,
                'tss': os.path.join(ref_dir, 'output_reference_6h/mbError.tss'),
            },
        },
        'mbErrorSplitRoutingM3': {
            'report_map': None,
            'report_tss': 'MassBalanceErrorSplitRoutingTSS',
            '86400': {
                'map': None,
                'tss': os.path.join(ref_dir, 'output_reference_daily/mbErrorSplitRoutingM3.tss'),
            },
            '21600': {
                'map': None,
                'tss': os.path.join(ref_dir, 'output_reference_6h/mbErrorSplitRoutingM3.tss'),
            },
        },
    }

    def teardown_method(self):
        settings = LisSettings.instance()
        output_dir = settings.output_dir
        shutil.rmtree(output_dir)

    @classmethod
    def compare_reference(cls, variable='dis', check='map', step_length='86400'):
        """
        :param variable: variable to check. Default 'dis' (Discharge)
        :param check: either 'map' or 'tss'. Default 'map'
        :param step_length: DtSec (86400 for daily and 21600 for 6h run)
        """

        settings = LisSettings.instance()
        binding = settings.binding
        reference = cls.reference_files[variable][step_length][check]

        if check == 'map':
            output_map = os.path.normpath(binding[cls.reference_files[variable]['report_map']]) + '.nc'
            comparator = NetCDFComparator(settings.maskpath)
            comparator.compare_files(reference, output_map)
        elif check == 'tss':
            output_tss = binding[cls.reference_files[variable]['report_tss']]
            comparator = TSSComparator()
            comparator.compare_files(reference, output_tss)
        # If there are differences, test fails before reaching this line (AssertionError(s) in comparator methods)
        assert True
