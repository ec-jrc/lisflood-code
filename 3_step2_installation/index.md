## Step 1: Installation of the LISFLOOD model

There are several ways to get lisflood model and to run it on your machines: 

1. Using the Docker image `efas/lisflood`
2. Using pip tool together with conda to easily install dependencies
3. Obtaining the source code, by cloning repository or downloading source distribution, and install dependencies.

The suggested way is using the official Docker image, since it's not trivial to install PCRaster and GDAL for average users.

In this page all different options are described. Feel free to pick up what suits you best.

 
### A) Docker image (suggested)


You can use the updated docker image to run lisflood, so without taking care to install dependencies on your system.
First, you pull image from repository.

```bash
docker pull efas/lisflood
```

Copy Test catchment files from container to your host, using mapped volumes. `usecases` is the folder in docker where test catchments are.

```bash
docker run -v /absolute_path/to/my/local/folder:/usecases efas/lisflood:latest usecases
```

After this command, you can find all files to run a test against a catchment under the directory you mapped: `/absolute_path/to/my/local/folder/TestCatchment`


Now, you can run LISFLOOD as a docker container to test the catchment. Only thing you need to do is to map the TestCatchment folder 
to the container folder `input`, by using Docker `-v` option. 
In the XML settings file, all paths are adjusted to be relative to the very same settings file, so you don't need to edit paths, as long as you keep same folders structure.


Execute the following docker command to run the simulation:

```bash
docker run -v /absolute_path/to/my/local/folder/TestCatchment:/input efas/lisflood /input/settings/cold_day_base.xml
```

Once LISFLOOD finished, you can find reported maps in `/absolute_path/to/my/local/folder/TestCatchment/outputs/` folder.


### B) Pypi packaged LISFLOOD and conda env

Using conda environment is very handy since installing latest PCRaster and its dependencies is pretty straightforward.

1. Install [miniconda](https://docs.conda.io/en/latest/miniconda.html) 
2. Create a conda env named "lisflood" and install dependencies:
```
conda create --name lisflood python=3.7 -c conda-forge
conda activate lisflood
conda install -c conda-forge pcraster
pip install lisflood-model
```

Command above will also install the executable `lisflood` in the conda env, so that you can run LISFLOOD with the following:
```bash
lisflood /absolute_path/to/my/local/folder/TestCatchment/settings/cold_day_base.xml
```

*Note:* You can use a straight python virtualenvironment to install lisflood-model package but then you have to setup PCRaster/GDAL/NetCDF libraries.

### C) Using the python souce code

You can download code and dataset for testing the model (or to contribute with bug fixes or new features).
Follow this instruction for a basic test (a catchment included in this repository under
[tests/data/TestCatchment](https://github.com/ec-jrc/lisflood-code/tree/master/tests/data/TestCatchment))

1. **Clone the master branch of this repository (you need to have git installed on your machine).**

    ```bash
    git clone --single-branch --branch master https://github.com/ec-jrc/lisflood-code.git
    ```

2. **Install requirements into a python 3 conda env**

```bash
conda create --name lisflood python=3.7 -c conda-forge
conda activate lisflood
conda install -c conda-forge pcraster
cd lisflood-code
pip install -r requirements.txt
```

If you don't use conda but a plain virtualenv, you need to install PCRaster and GDAL by your own and include its python interface in PYTHONPATH environment variable.
For details, please follow instruction on [official docs](http://pcraster.geo.uu.nl/getting-started/pcraster-on-linux/).
    

3. **Compile the cython module kinematic_wave_parallel_tool**
   
   To compile this Cython module to enable OpenMP multithreading (parallel kinematic wave):
    
     * Delete the files *.so (if any) in directory hydrological-modules  
     * Inside the hydrological_modules folder, execute `python compile_kinematic_wave_parallel_tools.py build_ext --inplace`  

   Important: the module has to be compiled on the machine where the model is run - the resulting binary is not portable.  
  
   Then in the settings file the option "numberParallelThreadsKinematicWave" may take the following values:
  
      * "0"           : auto-detection of the machine/node's number of CPUs (all CPUs are used minus 1) (do not set it if other simulations are running on the same machine/node)
      * "1"           : serial execution (not parallel)
      * "2", "3", ... : manual setting of the number of parallel threads.
                        (if exceeding the number of CPUs, the option is set to "0")
                        
   ```xml
   <textvar name="numCPUs_parallelKinematicWave" value="3"/>
   ```
  
4. **Run a cold run for the test catchment**

    Now that your environment should be set up to run lisflood, you may try with a prepared settings file for TestCatchment:
    
    ```bash
    python src/lisf1.py tests/data/TestCatchment/settings/cold_day_base.xml
    ```
4. **Run LISFLOOD unit tests**

    ```bash
    pytest tests/
    ```
  
If commands above succeeded without errors, producing dis.nc into tests/data/TestCatchment/outputs folder, your lisflood installation was correct.
