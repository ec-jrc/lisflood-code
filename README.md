# Lisflood code

Source code of lisflood model.

You can download code and datasets for testing the model.
Follow this instruction for a basic test (Drina catchment, included in this repository under [tests/data/Drina](https://github.com/ec-jrc/lisflood-code/tree/master/tests/data/Drina))

1. Clone the master branch of this repository (you need to have git installed on your machine).

```bash
git clone --single-branch --branch master https://github.com/ec-jrc/lisflood-code.git
```

2. Install requirements into a python 2.7 virtualenv

```bash
cd lisflood-code
pip install -r requirements.txt
```

You need to install PCRaster and include its python interface in PYTHONPATH environment variable.
For details, please follow instruction on [official docs](http://pcraster.geo.uu.nl/getting-started/pcraster-on-linux/).

3. Compile the cython module kinematic_wave_parallel_tool

To compile this Cython module to enable OpenMP multithreading (parallel kinematic wave):

* Delete the files *.so (if any) in directory hydrological-modules  

* Inside the hydrological_modules folder, execute "python2 compile_kinematic_wave_parallel_tools.py build_ext --inplace"  

Important: the module has to be compiled on the machine where the model is run - the resulting binary is not portable.  

Then in the settings file the option "numberParallelThreadsKinematicWave" may take the following values:
    - "0"           : auto-detection of the machine/node's number of CPUs (all CPUs are used minus 1) (do not set it if other simulations are running on the same machine/node)
    - "1"           : serial execution (not parallel)
    - "2", "3", ... : manual setting of the number of parallel threads.
                      (if exceeding the number of CPUs, the option is set to "0") -->  
```xml
<textvar name="numCPUs_parallelKinematicWave" value="3"/>
```
4. Run a cold run for the Drina test catchment

Now your environment should be set up to run lisflood. Try with a prepared settings file for Drina catchment:

```bash
python src/lisflood/lisf1.py tests/data/Drina/settings/lisfloodSettings_cold_day_base.xml
```

If the command above successed without errors, producing dis.nc into tests/data/Drina/outputs folder, your lisflood installation was correct.

### Docker image


You can use the updated docker image to run lisflood, so without taking care to install dependencies on your system.
First, you pull image from repository.

```bash
docker pull efas/lisflood:latest
```

Copy Drina catchment files from container to your host, using mapped directories.

```bash
docker run -v /absolute_path/to/my/local/folder:/usecases efas/lisflood:latest usecases
```

After this command, you can find all files to run a test against Drina catchment under the directory you mapped: `/absolute_path/to/my/local/folder/Drina`


Now, you can run LISFLOOD as a docker container to test the Drina catchment. Only thing you need to do is to map the Drina folder to the container folder `input`, by using -v option. 
In the XML settings file, all paths are adjusted to be relative to the very same settings file, so you don't need to edit paths, as long as you keep same folders structure.


Execute the following to run the simulation:

```bash
docker run -v /absolute_path/to/my/local/folder/Drina:/input efas/lisflood /input/settings/lisfloodSettings_cold_day_base.xml
```

Once LISFLOOD finished, you can find reported maps in `/absolute_path/to/my/local/folder/Drina/outputs/` folder.

### Pypi packaged LISFLOOD

LISFLOOD is also distributed as a standard python package. You can install the pip package in your Python 2.7<sup>[1](#footnote1)</sup> virtualenv:

```bash
pip install lisflood-model
```

Command above will also install the executable `lisflood` in the virtualenv, so that you can run LISFLOOD with the following:

```bash
lisflood /absolute_path/to/my/local/folder/Drina/settings/lisfloodSettings_cold_day_base.xml
```

<a id="footnote1" name="footnote1">1</a>: We planned to migrate to Python 3 in a few months.
