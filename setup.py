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
python setup.py sdist

To upload new package on PyPi Test:
twine upload --repository-url https://test.pypi.org/legacy/ dist/*

To upload new package on PyPi:
twine upload dist/*

Test package install
pip install --index-url https://test.pypi.org/simple/ lisflood-model==2.8.6

In prod:
pip install lisflood-model
"""

import os
import sys
from glob import glob

try:
    from Cython.Build import cythonize
except ImportError:
    def cythonize(*args, **kwargs):
        from Cython.Build import cythonize
        return cythonize(*args, **kwargs)

from setuptools import setup, find_packages, Extension

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, './src/'))
from lisflood.metainfo import __version__, __authors__

readme_file = os.path.join(current_dir, 'README.md')

ext_modules = [
    Extension(
        "lisflood.hydrological_modules.kinematic_wave_parallel_tools",
        ["src/lisflood/hydrological_modules/kinematic_wave_parallel_tools.pyx"],
        extra_compile_args=["-O3", "-ffast-math", "-march=native", "-fopenmp"],
        extra_link_args=["-fopenmp"]
    )
]

with open(readme_file, 'r') as f:
    long_description = f.read()

setup(
    name='lisflood-model',
    version=__version__,
    package_dir={'lisflood': 'src/lisflood/'},
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
    url='https://github.com/ec-jrc/lisflood-model',
    download_url='https://github.com/ec-jrc/lisflood-code/archive/{}.tar.gz'.format(__version__),
    setup_requires=[
            # Setuptools 18.0 properly handles Cython extensions.
            'setuptools>=18.0',
            'cython',
    ],
    install_requires=[
        'numpy>=1.15', 'pytest', 'netCDF4', 'python-dateutil',
        'numexpr', 'cython', 'docopt', 'pandas', 'xarray', 'pyproj'
    ],
    entry_points={'console_scripts': ['lisflood = lisflood.lisf1:main']},
    # ext_modules=cythonize(ext_modules, annotate=True),
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
)
