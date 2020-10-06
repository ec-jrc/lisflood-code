import os
from pathlib import Path
from itertools import chain

import pytest


def pytest_addoption(parser):
    parser.addoption('-R', '--pathroot', type=lambda p: Path(p).absolute(), help='Path to Root static data directory.')
    parser.addoption('-S', '--pathstatic', type=lambda p: Path(p).absolute(), help='Path to Lisflood static data (e.g. maps)')
    parser.addoption('-M', '--pathmeteo', type=lambda p: Path(p).absolute(), help='Path to Lisflood meteo forcings')
    parser.addoption('-I', '--pathinit', type=lambda p: Path(p).absolute(), help='Path to Lisflood init data')
    parser.addoption('-O', '--pathout', type=lambda p: Path(p).absolute(), help='Path to Lisflood results')


@pytest.fixture(scope='class', autouse=True)
def options(request):
    options = dict()
    options['pathroot'] = request.config.getoption('--pathroot')
    options['pathmeteo'] = request.config.getoption('--pathmeteo') or options['pathroot']
    options['pathstatic'] = request.config.getoption('--pathstatic') or options['pathroot']
    options['pathout'] = request.config.getoption('--pathout') or options['pathroot']
    options['pathinit'] = request.config.getoption('--pathinit') or options['pathroot']
    if options.get('pathout'):
        if not options['pathout'].exists():
            options['pathout'].mkdir(parents=True)
        else:
            for f in chain(options['pathout'].glob('*.nc'), options['pathout'].glob('*.tss')):
                os.unlink(f)
    request.cls.options = options
    return options
