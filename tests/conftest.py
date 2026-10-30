from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption('-P', '--pathroot', type=lambda p: Path(p).absolute(),
                     help='Path to Root static data directory. '
                          'It will be PathRoot variable in settings.xml for some tests.'
                          'If missing, those tests are not executing')


def pytest_configure(config):
    # Opt-in suite-wide activation of the earthkit-hydro reporting path:
    #   LISFLOOD_TEST_EARTHKIT_ON=1 pytest tests/
    # flips the useEarthkitHydro default to True before any settings file is
    # parsed, so every end-to-end test exercises the earthkit path (the PCRaster
    # fallback stays in place for environments without earthkit-hydro).
    # Unset (default) leaves the suite on the historical OFF behaviour.
    import os
    if os.environ.get('LISFLOOD_TEST_EARTHKIT_ON') == '1':
        from lisflood.global_modules import default_options as _do
        assert 'useEarthkitHydro' in _do.default_options
        _do.default_options['useEarthkitHydro'] = True



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

