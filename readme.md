# Lisflood code

Source code of lisflood model
Temporary Readme file for Collaborators only. 

To compile this Cython module to enable OpenMP multithreading (parallel kinematic wave):
1)Delete the files *.so (if any) in directory hydrological-modules \\
2) execute "python compile_kinematic_wave_parallel_tools.py build_ext --inplace" \\
Important: the module has to be compiled on the machine where the model is run - the resulting binary is not portable.

Then in the settings file the option "numberParallelThreadsKinematicWave" may take the following values:
    - "0"           : auto-detection of the machine/node's number of CPUs (all CPUs are used minus 1) (do not set it if other simulations are running on the same machine/node)
    - "1"           : serial execution (not parallel)
    - "2", "3", ... : manual setting of the number of parallel threads.
                      (if exceeding the number of CPUs, the option is set to "0") -->

<textvar name="numCPUs_parallelKinematicWave" value="30"/>
