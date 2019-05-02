import os
import sys
from glob import glob

from Cython.Build import cythonize

from setuptools import setup, find_packages, Extension

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, './src/'))

from lisflood.lisf1 import __version__

ext_modules = [
    Extension(
        "lisflood.hydrological_modules.kinematic_wave_parallel_tools",
        ["src/lisflood/hydrological_modules/kinematic_wave_parallel_tools.pyx"],
        extra_compile_args=["-O3", "-ffast-math", "-march=native", "-fopenmp"],
        extra_link_args=["-fopenmp"]
    )
]

readme_file = os.path.join(current_dir, 'readme.md')

with open(readme_file, 'r') as f:
    long_description = f.read()

setup(
    name='lisflood-model',
    version=__version__,
    package_dir={'': 'src'},
    py_modules=[os.path.splitext(os.path.basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    package_data={'lisflood': ['*.xml']},
    packages=find_packages('src'),
    long_description=long_description,
    long_description_content_type='text/markdown',
    description='LISFLOOD model python module',
    author='Ad de Roo, Emiliano Gelati, Peter Burek, Johan van der Knijff, Domenico Nappo',
    author_email='domenico.nappo@ext.ec.europa.eu',
    keywords='lisflood lisvap efas ecmwf',
    license='EUPL 1.2',
    url='https://github.com/ec-jrc/lisflood-model',
    install_requires=['numpy>=1.15', 'pytest', 'netCDF4', 'python-dateutil', 'numexpr', 'cython', 'docopt', 'pandas', 'xarray', 'pyproj'],
    entry_points={'console_scripts': ['lisflood = lisflood.lisf1:main']},
    ext_modules=cythonize(ext_modules, annotate=True),
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
