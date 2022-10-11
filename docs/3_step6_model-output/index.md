# Step 6: Default LISFLOOD output

LISFLOOD can generate a wide variety of output. Output is generated as either maps or time series (netCDF format, which can be visualised with any netCDF viewer e.g. [Panoply](https://www.giss.nasa.gov/tools/panoply/download/)). 
Reporting of output files can be switched on and off using options in the LISFLOOD settings file. Also, a number of output files are specific to other optional modules, 
such as the simulation of reservoirs. The following table lists all the output time series that are reported by default (note that the file names can always be changed by the user, although this is not recommended):

***Table:*** *LISFLOOD default output time series.*   

| **File name**                 | **Units**               | **Description**                                                                          |
|-------------------------------|-------------------------|------------------------------------------------------------------------------------------|
| **RATE VARIABLES AT GAUGES**  |                         |                                                                                          |
| dis.tss                       | $\frac{m^3}{s}$         | $^{1,2}$ channel discharge                                                               |
| **NUMERICAL CHECKS**          |                         |                                                                                          |
|  mbError.tss                  | $m^3$                   | $^2$ cumulative mass balance error                                                       |
| mbErrorMm.tss                 | $mm$                    | $^2$ cumulative mass balance error, expressed as mm water slice (average over catchment) |
| NoSubStepsChannel.tss         | \-                      | $^2$ number of sub-steps needed for channel routing                                      |
| steps.tss                     | \-                      | $^2$ number of sub-steps needed for gravity-based soil moisture routine                  |

$^1$ Output only if option 'InitLisflood' = 1 (pre-run) \
$^2$ Output only if option'InitLisflood' = 0  

To speed up the pre-run and to prevent that results are taken from the pre-run, all additional output is disabled if option 'InitLisflood' = 1 is chosen. With 'InitLisflood' = 1 the output is limited to *dis.tss, lzavin.map, lzavin\_forest.map* and some other initial maps if additional option like e.g. the double kinematic wave is chosen.

In addition to these time series, by default LISFLOOD reports maps of all state variables at the last timestep of a simulation[^5]. These maps can be used to define the initial conditions of a succeeding simulation. For instance, you can do a 1-year simulation on a daily time step, and use the 'end maps' of this simulation to simulate a flood event using an hourly time step. The Table below and **Annex 13** list all these maps. Note that some state variables are valid for the whole pixel, whereas others are only valid for a sub-domain of each pixel. This is indicated in the last column of the table.

***Table:*** *LISFLOOD default state variable output maps. These maps can be used to define the initial conditions of another simulation. 
All maps can be either in netCDF or PCRaster format. In PCRaster format, filenames will be 0 filled and extension represents the timestep (e.g. scovc000.002)*     

| **File name**      | **Description**                                                                     | **Units**             | **Domain**                        |
|--------------------|-------------------------------------------------------------------------------------|-----------------------|-----------------------------------|
|                    |  **AVERAGE RECHARGE MAP <br>(for lower groundwater zone)** <br>(option InitLisflood)|                       |                                   |
| lzavin.map         | $^1$ average inflow to lower zone                                                   | $\frac{mm}{timestep}$ | other fraction                    |
| lzavin\_forest.map | $^1$ average inflow to lower zone (forest)                                          | $\frac{mm}{timestep}$ | forest fraction                   |
|                    | **INITIAL CONDITION MAPS  <br>at defined time steps** <br> (option *repStateMaps*)  |                       |                                   |
| wdepth             | $^2$ waterdepth                                                                     | $mm$                  | whole pixel                       |
| chcro              | $^2$ channel cross-sectional area                                                   | $m^2$                 | channel                           |
| dslr               | $^2$ days since last rain variable                                                  | $days$                | other pixel                       |
| scova              | $^2$ snow cover zone *A*                                                            | $mm$                  | snow zone A ($\frac{1}{3}$ pixel) |
| scovb              | $^2$ snow cover zone *B*                                                            | $mm$                  | snow zone B ($\frac{1}{3}$ pixel) |
| scovc              | $^2$ snow cover zone *C*                                                            | $mm$                  | snow zone C ($\frac{1}{3}$ pixel) |
| frost              | $^2$ frost index                                                                    | $\frac{°C}{days}$     | other pixel                       |
| cumi               | $^2$ cumulative interception                                                        | $mm$                  | other pixel                       |
| thtop              | $^2$ soil moisture upper layer                                                      | $\frac{mm^3} {mm^3}$  | other fraction                    |
| thsub              | $^2$ soil moisture lower layer                                                      | $\frac{mm^3} {mm^3}$  | other fraction                    |
| lz                 | $^2$ water in lower zone                                                            | $mm$                  | other fraction                    |
| uz                 | $^2$ water in upper zone                                                            | $mm$                  | other fraction                    |
| dslF               | $^2$ days since last rain variable (forest)                                         | $days$                | forest pixel                      |
| cumF               | $^2$ cumulative interception (forest)                                               | $mm$                  | forest pixel                      |
| thFt               | $^2$ soil moisture upper layer (forest)                                             | $\frac{mm^3} {mm^3}$  | forest fraction                   |
| thFs               | $^2$ soil moisture lower layer (forest)                                             | $\frac{mm^3} {mm^3}$  | forest fraction                   |
| lzF                | $^2$ water in lower zone (forest)                                                   | $mm$                  | forest fraction                   |
| uzF                | $^2$ water in upper zone (forest)                                                   | $mm$                  | forest fraction                   |
| cseal              | $^2$ water in depression storage (sealed)                                           | $mm$                  | sealed fraction                   |

$^1$ Output only if option 'InitLisflood' = 1 (pre-run) \
$^2$ Output only if option 'InitLisflood' = 0  

# Additional output

Apart from the default output, the model can --optionally- generate some additional time series and maps. Roughly this additional output falls in either of the following categories:

**Time series**

-  Time series with values of **model state variables at user-defined locations** (sites); reporting of these time series can be activated using the option *repStateSites=1.* Note that 'sites' can be either individual pixels or larger areas (e.g. catchments, administrative areas, and so on). In case of larger areas the model reports the average value for each respective area.

-  Time series with values of **model rate variables at user-defined locations** (sites); reporting of these time series can be activated using the option *repRateSites=1*

-  Time series with values of **meteorological input variables, averaged over the area upstream of each gauge location**; reporting of these time series can be activated using the option *repMeteoUpsGauges=1*

-  Time series with values of **model state variables, averaged over area upstream of each gauge location**; reporting of these time series can be activated using the option *repStateUpsGauges=1*

-  Time series with values of **model rate variables, averaged over area upstream of each gauge location**; reporting of these time series can be activated using the option *repRateUpsGauges=1*

-  Time series that are specific to other **options** (e.g. simulation of reservoirs).

**Maps**

-  Maps of **discharge** at each time step; reporting of these maps can be activated using the option *repDischargeMaps=1*

-  Maps with values of **driving meteorological values** at each time step

-  Maps with values of **model rate variables** at each time step

-  Maps that are specific to other **options** (e.g. simulation of reservoirs).

In addition, some additional maps and time series may be reported for debugging purposes. In general these are not of any interest to the LISFLOOD user, so they remain undocumented here.

> Note that the options *repStateUpsGauges*, *repRateUpsGauges* and *repDischargeMaps* tend to slow down the execution of the model quite dramatically. For applications of the model where performance is critical (e.g. automated calibration runs), we advise to keep them switched off, if possible. 

Note again the domains for which variables are valid: all *rate variables* are reported as pixel-average values. Soil moisture and groundwater storage are reported for the permeable fraction of each pixel only. The reported snow cover is the average of the snow depths in snow zones A, B and C.

By default, the names of the reported discharge maps start with the prefix '*dis*'. This [**Annex**](../4_annex_output-files/) summarises all options to report additional output maps. 
