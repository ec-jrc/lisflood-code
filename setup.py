"""
Copyright 2019 European Union

Licensed under the EUPL, Version 1.2 or as soon they will be approved by the European Commission  subsequent versions of the EUPL (the "Licence");

You may not use this work except in compliance with the Licence.
You may obtain a copy of the Licence at:

https://joinup.ec.europa.eu/sites/default/files/inline-files/EUPL%20v1_2%20EN(1).txt

Unless required by applicable law or agreed to in writing, software distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and limitations under the Licence.

---------------------------------------------------------------------------------------------------------------------------------------
Use python setup.y upload to publish versioned tags and pypi package

python setup.py upload

It's equivalent to:

1. python setup.py sdist
2. twine upload dist/*
3. git tag {version}
4. git push --tags

Note: To upload new package on PyPi Test:
twine upload --repository-url https://test.pypi.org/legacy/ dist/*

Install

3a. Test package install
pip install --index-url https://test.pypi.org/simple/ lisflood-model==2.8.14

3b. In prod:
pip install lisflood-model
"""

import os
import sys
from glob import glob
from shutil import rmtree

from setuptools import find_packages, Extension, setup, Command, __path__ as setuppath

pip_package = os.path.normpath(os.path.join(setuppath[0], '../lisflood'))
if os.path.exists(pip_package):
    print('[-] Removing current package installed {}'.format(pip_package))
    rmtree(pip_package)

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, './src/'))

from lisflood import __version__, __authors__

print(">>>>>>>>>>>>>>>> Building LISFLOOD version {} <<<<<<<<<<<<<<<<<<".format(__version__))
try:
    # noinspection PyUnresolvedReferences
    from Cython.Build import cythonize
    HAS_CYTHON = True
except ImportError:
    HAS_CYTHON = False

src_ext = 'src/lisflood/hydrological_modules/kinematic_wave_parallel_tools.{}'
extension_ext = 'pyx' if HAS_CYTHON else 'c'

ext_modules = [
    Extension(
        'lisflood.hydrological_modules.kinematic_wave_parallel_tools',
        [src_ext.format(extension_ext)],
        extra_compile_args=['-O3', '-ffast-math', "-march=native", '-fopenmp'],
        extra_link_args=['-fopenmp']
    )
]

if HAS_CYTHON:
    ext_modules = cythonize(ext_modules)

readme_file = os.path.join(current_dir, 'README.md')
with open(readme_file, 'r') as f:
    long_description = f.read()


class UploadCommand(Command):
    """Support setup.py upload."""

    description = 'Publish lisflood-model package.'
    user_options = []

    @staticmethod
    def print_console(s):
        print('\033[1m{0}\033[0m'.format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.print_console('Removing previous builds...')
            rmtree(os.path.join(current_dir, 'dist'))
        except OSError:
            pass

        self.print_console('Building Source and Wheel (universal) distribution...')
        os.system('{0} setup.py sdist'.format(sys.executable))

        self.print_console('Uploading the package to PyPI via Twine...')
        os.system('twine upload dist/*')

        self.print_console('Pushing git tags...')
        os.system('git tag v{0}'.format(__version__))
        os.system('git push --tags')

        sys.exit()


setup(
    name='lisflood-model',
    version=__version__,
    package_dir={'': 'src/'},
    py_modules=[os.path.splitext(os.path.basename(path))[0] for path in glob('src/*.py*')],
    include_package_data=True,
    package_data={'lisflood': ['*.xml']},
    packages=find_packages('src'),
    long_description=long_description,
    long_description_content_type='text/markdown',
    description='LISFLOOD model python module',
    author=__authors__,
    author_email='domenico.nappo@ext.ec.europa.eu',
    keywords=['lisflood', 'lisvap', 'efas', 'glofas', 'ecmwf'],
    license='EUPL 1.2',
    url='https://github.com/ec-jrc/lisflood-code',
    download_url='https://github.com/ec-jrc/lisflood-code/archive/{}.tar.gz'.format(__version__),
    setup_requires=[
            # Setuptools 18.0 properly handles Cython extensions.
            'setuptools>=41.0',
            'numpy>=1.15,<1.17',
            'cython',
    ],
    install_requires=[
        'python-dateutil', 'pytest', 'docopt',
        'numpy>=1.15,<1.17', 'cython', 'netCDF4>=1.5',
        'numexpr', 'pandas>=0.24.2', 'xarray', 'pyproj', 'cftime',
    ],
    scripts=['bin/lisflood'],
    ext_modules=ext_modules,
    zip_safe=True,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Other Audience',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: European Union Public Licence 1.2 (EUPL 1.2)',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering :: Physics',
    ],
    # setup.py publish to pypi.
    cmdclass={
        'upload': UploadCommand,
        'publish': UploadCommand,
    },
)
