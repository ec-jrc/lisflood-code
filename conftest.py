from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption('-P', '--pathroot', type=lambda p: Path(p).absolute(),
                     help='Path to Root static data directory. '
                          'It will be PathRoot variable in settings.xml for some tests.'
                          'If missing, those tests are not executing')


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
