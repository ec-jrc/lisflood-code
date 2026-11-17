from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption('-P', '--pathroot', type=lambda p: Path(p).absolute(),
                     help='Path to Root static data directory. '
                          'It will be PathRoot variable in settings.xml for some tests.'
                          'If missing, those tests are not executing')


def pytest_configure(config):
    # useEarthkitHydro defaults to True, so by default every end-to-end test
    # exercises the earthkit-hydro reporting path (with automatic PCRaster
    # fallback when earthkit-hydro is not installed). To cover the PCRaster
    # path, run the suite a second time with:
    #   LISFLOOD_TEST_EARTHKIT_OFF=1 pytest tests/
    # which flips the default to False before any settings file is parsed.
    import os
    if os.environ.get('LISFLOOD_TEST_EARTHKIT_OFF') == '1':
        from lisflood.global_modules import default_options as _do
        assert 'useEarthkitHydro' in _do.default_options
        _do.default_options['useEarthkitHydro'] = False



@pytest.fixture(scope='class', autouse=True)
def options(request):
    options = dict()
    options['pathroot'] = request.config.getoption('--pathroot')
    request.cls.options = options
    return options


def pytest_collection_modifyitems(config, items):
    if config.getoption('--pathroot'):
        return
    test_domain = config.getoption('--pathroot')
    skip_marker = pytest.mark.skip(reason='need -P/--pathroot argument to run')
    for item in items:
        if 'pathroot' in item.keywords and not test_domain:
            item.add_marker(skip_marker)

