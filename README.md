# Lisflood OS

This repository hosts source code of LISFLOOD model.
Go to [Lisflood OS page](https://ec-jrc.github.io/lisflood/) for more information.

Other useful resources

| **Project**         | **Documentation**                                         | **Source code**                                              |
| ------------------- | --------------------------------------------------------- | ------------------------------------------------------------ |
| Lisflood            | [Model docs](https://ec-jrc.github.io/lisflood-model/)    | https://github.com/ec-jrc/lisflood-code (this repository)    |
|                     | [User guide](https://ec-jrc.github.io/lisflood-code/)     |                                                              |
| Lisvap              | [Docs](https://ec-jrc.github.io/lisflood-lisvap/)         | https://github.com/ec-jrc/lisflood-lisvap                    |
| Calibration tool    | [Docs](https://ec-jrc.github.io/lisflood-calibration/)    | https://github.com/ec-jrc/lisflood-calibration               |
| Lisflood Utilities  |                                                           | https://github.com/ec-jrc/lisflood-utilities                 |
| Lisflood Usecases   |                                                           | https://github.com/ec-jrc/lisflood-usecases                  |


## Quick start

You can download code and datasets for testing the model.
Follow this instruction for a basic test (included in this repository under [tests/data/TestCatchment1](https://github.com/ec-jrc/lisflood-code/tree/master/tests/data/TestCatchment1))

1. Clone the master branch of this repository (you need to have git installed on your machine).

```bash
git clone --single-branch --branch master https://github.com/ec-jrc/lisflood-code.git
```

2. Install requirements into a Python 3 virtualenv. 
We recommend to follow the instructions on [virtualenv docs](https://virtualenv.pypa.io/en/latest/). 
Assuming you've activated your virtual environment, you can now install requirements with pip:

```bash
cd lisflood-code  # move into lisflood-code project directory
pip install -r requirements.txt
```

* GDAL should be installed as well. To install GDAL C library and gdal python library on debian/ubuntu systems, we found good instructions [here](https://mothergeo-py.readthedocs.io/en/latest/development/how-to/gdal-ubuntu-pkg.html).
 
If you already have GDAL installed in your computer, make sure that the GDAL and the python gdal library have the same version.


You need to install PCRaster (4.2.x is first version which works with Python3) and include its python interface in PYTHONPATH environment variable.
For details, please follow instruction on [official docs](http://pcraster.geo.uu.nl/getting-started/pcraster-on-linux/).

3. Compile the cython module kinematic_wave_parallel_tool

To compile this Cython module to enable OpenMP multithreading (parallel kinematic wave):

* Delete the files *.so (if any) in directory hydrological-modules  

* Inside the hydrological_modules folder, execute "python compile_kinematic_wave_parallel_tools.py build_ext --inplace"  

Important: the module has to be compiled on the machine where the model is run - the resulting binary is not portable.  

Then in the settings file the option "numberParallelThreadsKinematicWave" may take the following values:
    - "0"           : auto-detection of the machine/node's number of CPUs (all CPUs are used minus 1) (do not set it if other simulations are running on the same machine/node)
    - "1"           : serial execution (not parallel)
    - "2", "3", ... : manual setting of the number of parallel threads.
                      (if exceeding the number of CPUs, the option is set to "0") -->  
```xml
<textvar name="numCPUs_parallelKinematicWave" value="3"/>
```
4. Run a cold run for the test catchment

Now your environment should be set up to run lisflood. Try with a prepared settings file for one of the two test catchments:

```bash
python src/lisf1.py tests/data/TestCatchment1/settings/lisfloodSettings_cold_day_base.xml
```

If the command above successed without errors, producing dis.nc into tests/data/TestCatchment1/outputs folder, your lisflood installation was correct.

### Docker image


You can use the updated docker image to run lisflood, so without taking care to install dependencies on your system.
First, you pull image from repository.

```bash
docker pull efas/lisflood:latest
```

Copy catchment files from container to your host, using mapped directories.

```bash
docker run -v /absolute_path/to/my/local/folder:/usecases efas/lisflood:latest usecases
```

After this command, you can find all files to run a test against a catchment under the directory you mapped: `/absolute_path/to/my/local/folder/TestCatchment1`


Now, you can run LISFLOOD as a docker container to test included catchments. Only thing you need to do is to map the TestCatchment1 folder to the container folder `input`, by using -v option. 
In the XML settings file, all paths are adjusted to be relative to the very same settings file, so you don't need to edit paths, as long as you keep same folders structure.


Execute the following to run the simulation:

```bash
docker run -v /absolute_path/to/my/local/folder/TestCatchment1:/input efas/lisflood /input/settings/cold_day_base.xml
```

Once LISFLOOD finished, you can find reported maps in `/absolute_path/to/my/local/folder/TestCatchment1/outputs/` folder.

### Pypi packaged LISFLOOD

LISFLOOD is also distributed as a standard python package. You can install the pip package in your Python 3 virtualenv:

```bash
pip install lisflood-model
```

Command above will also install the executable `lisflood` in the virtualenv, so that you can run LISFLOOD with the following:

```bash
lisflood /absolute_path/to/my/local/folder/TestCatchment1/settings/lisfloodSettings_cold_day_base.xml
```

## Collaborate

If you find an issue in our code, please follow the [GitHub flow](https://guides.github.com/introduction/flow/) to propose your changes (Fork, commit your changes and ask for a Pull Request).
When you develop, you need to run our "acceptance" tests. We have two test catchments, that can run with tox on py27, py36, py37 environments.
Simply execute `tox` on comman line from project folder.

Tox tests can last minutes. You can also just use pytest and run tests in a single environment (e.g. Python 3.7).
This is often enough and will save you some time if you need to run tests frequently.
 
`pytest tests/ -s`
