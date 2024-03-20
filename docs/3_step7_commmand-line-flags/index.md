# Step 7: Command line flags
LISFLOOD command line takes the following flags as additional arguments after the xml setting file:

```
    -q --quiet              output progression given as .
    -v --veryquiet          no output progression is given
    -l --loud               output progression given as time step, date and discharge
    -c --checkfiles         input maps and stack maps are checked, output for each input map BUT no model run
    -n --nancheck           check input maps and routing output for any NaN value generated during model run
    -h --noheader           .tss file have no header and start immediately with the time series
    -d --debug              debug outputs
    -i --initonly           only run initialisation, not the dynamic loop
    -s --skipvalreplace     skip replacement of invalid values in meteo input maps (ignore valid_min and valid_max)
```

The flags are utility flags and do not change the behaviour/parameters of the model. Here are the operational details of each flag.

- **-q --quiet       output progression given as .**
    The default on-screen output of the lisflood command is the step count and the date/time of each computational step (each step being the run of all the activated modules in sequence for each time step). By setting this "-q" flag only a dot "." will be writtend on stdout for each computational step.

- **-v --veryquiet   no output progression is given**
   The default on-screen output of the lisflood command is the step count and the date/time of each computational step (each step being the run of all the activated modules in sequence for each time step). By setting this "-v" flag there will be no output written on stdout showing the model progression. Warnings will still printed out.
   
- **-l --loud        output progression given as time step, date and discharge**
   The default on-screen output of the lisflood command is the step count and the date/time of each computational step (each step being the run of all the activated modules in sequence for each time step). By setting this "-l" flag, the output will show also the discharge value at each step.

- **-c --checkfiles  input maps and stack maps are checked, output for each input map BUT no model run**
    Check the correctness of input maps. The option generates also a table of all the input maps specified in the input xml file. The table will show name of the map, the file path (or single value of the variable), the number of non missing values (nonMV) and missing values (MV) after the comparison with the mask map and LDD map, minimum, maximum and average values for each map. In case any map have missing values, a warning will be issued on screen. The model will NOT run, the lisflood command with -c flags will only check the maps.

- **-n --nancheck    check input maps and routing output for any NaN value generated during model run**
    Check for NaN values in input maps and routing output values during the model run. This check do not include missing values (e.g. -9999) in input maps.

- **-h --noheader    .tss file have no header and start immediately with the time series**
    By default a header including number of values, value type, settings file path and date of creation is printed when generating the output time series files. Using this flag the header will not be printed in Time Series .tss output files, and the file will start immediately with values.

- **-d --debug       debug outputs**
    This flags is used to generate extensive debug txt files containing variable values for each time steps. Each file will be named as "Debug_out_&lt;stepnumber&gt;.txt"

- **-i --initonly    only run initialisation, not the dynamic loop**
    By adding this flag the model will only run the initialization and will not enter the dynamic loop (i.e. it stops before computing the first time step)

- **-s --skipvalreplace     skip replacement of invalid values in meteo input maps (ignore valid_min and valid_max)**
    By adding this flag the model will skip replacement of invalid values in meteo input maps (ignore valid_min and valid_max). In normal execution, values outside valid_min and valid_max range are replaced with NaN