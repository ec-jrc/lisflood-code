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


## Notes for Release 4.0.0

LISFLOOD-OS v4.0.0 includes the following changes:

1) computation of water infiltration into the soil within the soilloop.py module

2) changes in the allocation of water abstraction

3) patches in the modules riceirrigation.py and frost.py to avoid non-realistic results in specific conditions.

4) improvements in the computation of the mass balance.
 
5) bug fixes in the use of the transientlandusechange option, in the use of the option simulatePF, in the writing of the monthly outputs.

Moreover, to ensure compatibility with LISFLOOD-EPIC, modules source code is compatible with XArray variables, and XArray variables will be allocated when EPIC module is ON
LISFLOOD-EPIC has been developed by JRC-D2. When compared to LISFLOOD v3.2.0, LISFLOOD-EPIC enables a more detailed representation of crop growth and irrigation. References:  ASR - Assessing groundwater irrigation sustainability in the Euro-Mediterranean region with an integrated agro-hydrologic model (copernicus.org) , Gelati, E. et al.: Integrated model of irrigation, crop growth and water resources (LISFLOOD-EPIC): description and application in the Euro-Mediterranean area, in preparation, 2020.
Important note: EPIC modules are not *yet* available from the OS-LISFLOOD repository.

1) computation of water infiltration into the soil within the soilloop.py module
LISFLOOD v3.2.0: all the pixels of a land use fraction are allocated to a vector and the number of loops is defined by the most critical pixel. More specifically, all the pixels within the computational domain are allocated the number of iterations that are necessary to allow the numerical stability of the most critical pixel. The number of iterations consequently depends on the specific computational domain. This can lead to different results when modelling sub-catchmennts and entire basins with highly heterogenous soils.
LISFLOOD v4.0.0: pixel by pixel computation and parallelization of the computations by using the python package numba. The number of
Benefits of v4.0.0: each pixel is allocated the number of iterations that allow its numerical stability, this guarantees the consistency of results when modelling sub-catchments and the entire basin with highly heterogeneous soils. Decreased computational time due to parallel computations

2) changes in the allocation of water abstraction
LISFLOOD v3.2.0: direct abstraction of the consumptive water use.
LISFLOOD v4.0.0: abstraction of the demanded water valume for each use (industrial, domestic, energy, livestock); the consumptive water use leaves the system; the unused water volume is returned to the channels.
Minor note:  small differences in the computation of the leakages.

3) patches in the modules riceirrigation.py and frost.py to avoid non-realistic results in specific conditions.
riceirrigation.py: LISFLOOD v3.2.0: in presence of a very thick third soil layer (10^2 m) the drainage of the rice fields causes non realistic large flow discharge values in the channels.
LISFLOOD v4.0.0: only soil layers 1a and 1b are used by the rice module (for both the saturation and the drainage phases). By definition, the second soil layer includes the roots depth.
frost.py: LISFLOOD v3.2.0: there is no upper boundary to the frost index value. Rain events on deeply frozen soils are totally converted into runoff and can cause false alarms. 
LISFLOOD v4.0.0: the maximum frost index value is set to 57.


4) improvements in the computation of the mass balance.
LISFLOOD v3.2.0: the mass balance is computed by considering the input and output volumes up to the current computational step.  Small numerical errors accumulate over time and give the erroneous impression of large mass balance errors.
LISFLOOD v4.0.0: computation of the mass balance by considering the single computational step.

5) bug fixes in the use of the transientlandusechange option, in the use of the option simulatePF, in the writing of the monthly outputs.
Correct use of the rice fraction by landusechange.py DYNAMIC; use of the correct soil water content variable for the computation of pF1 (ws1a replaced ws1); correct reporting of the monthly time steps by the optional module indicatorcalc.py

Note: the users are recommneded to download the referencesettings.xml files and adapt it by inserting their own paths and modelling choices).


## Quick start

You can use conda environment to easily install dependencies.

* Install [miniconda](https://docs.conda.io/en/latest/miniconda.html)
* Create a conda env named "lisflood" and install dependencies:

```bash
conda create --name lisflood python=3.7 -c conda-forge
conda activate lisflood
conda install -c conda-forge pcraster
```

* Install lisflood-model pypi package
```bash
pip install lisflood-model
```

Command above will also install the executable `lisflood` in the conda env, so that you can run LISFLOOD with the following:
```bash
lisflood /absolute_path/to/my/local/folder/TestCatchment/settings/cold_day_base.xml
```

You can also clone the repository which contains datasets to test the model.
Follow this instruction for a basic test (included in this repository under [tests/data/TestCatchment1](https://github.com/ec-jrc/lisflood-code/tree/master/tests/data/TestCatchment1))

* Clone the master branch of this repository (you need to have git installed on your machine).

```bash
git clone --single-branch --branch master https://github.com/ec-jrc/lisflood-code.git
```

* **Install requirements into a python 3 conda env**

```bash
conda create --name lisflood python=3.7 -c conda-forge
conda activate lisflood
conda install -c conda-forge pcraster gdal
cd lisflood-code
pip install -r requirements.txt
```

If you don't use conda but a plain virtualenv, you need to install PCRaster and GDAL by your own and include its python interface in PYTHONPATH environment variable.
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
python src/lisf1.py tests/data/TestCatchment/settings/cold_day_base.xml
```

If the command above successed without errors, producing dis.nc into tests/data/TestCatchment1/outputs folder, your lisflood installation was correct.

### Docker image

You can use the updated docker image to run lisflood, so without taking care to install dependencies on your system.

#### Pull image from repository:

```bash
docker pull jrce1/lisflood:latest
```

#### Run test catchments in image:

```bash
docker run -v /absolute_path/to/my/local/folder:/usecases jrce1/lisflood:latest usecases
```

After this command, you can find all files to run tests against catchments under the directory you mapped: `/absolute_path/to/my/local/folder/`

```
/absolute_path/to/my/local/folder/LF_ETRS89_UseCase
/absolute_path/to/my/local/folder/LF_lat_lon_UseCase
```

Now, you can run LISFLOOD as a docker container to test included catchments. Only thing you need to do is to map the test catchment folder to the container folder `input`, by using -v option. 

In the XML settings file, all paths are adjusted to be relative to the very same settings file, so you don't need to edit paths, as long as you keep same folders structure.


#### Execute lisflood with a Docker image:

```bash
docker run -v /absolute_path/to/my/local/folder/LF_ETRS89_UseCase:/input jrce1/lisflood /input/settings/cold.xml
```

Once LISFLOOD finished, you find reported maps in `/absolute_path/to/my/local/folder/LF_ETRS89_UseCase/out/` folder.

### Pypi packaged LISFLOOD

LISFLOOD is also distributed as a standard python package. You can install the pip package in your Python 3 virtualenv:

```bash
pip install lisflood-model
```

Command above will also install the executable `lisflood` in the virtualenv, so that you can run LISFLOOD with the following:

```bash
lisflood /absolute_path/to/my/local/folder/TestCatchment/settings/cold_day_base.xml
```

### IMPORTANT NOTE

Please note that there are known issues when installing the LISFLOOD code on Windows (source code and pypi package). We cannot provide Windows support and strongly recommend using LINUX to install the LISFLOOD code.
Windows users are recommended to execute LISFLOOD with a Docker image.



## Collaborate

If you find an issue in our code, please follow the [GitHub flow](https://guides.github.com/introduction/flow/) to propose your changes (Fork, commit your changes and ask for a Pull Request).
You are required to run unit tests during your development and before to propose a pull request.

To execute unit tests:

```bash
pytest tests/
```

Furthermore, before to propose a pull request, there are additional tests we ask you to execute: 

```bash
pytest tests/ -m "slow
```

These tests could take 30 minutes or several hours, depending on your machine.

You can find full description and implementation details at [Test documentation](https://ec-jrc.github.io/lisflood-code/4_annex_tests/) page.

**Note**: If yuor pull request is about a new feature you may want to integrate in LISFLOOD,
ensure to include tests with good coverage for it.

For more info about pytest, see [official website](https://docs.pytest.org/en/latest/).
