# Step 5: Initialisation & cold start of LISFLOOD

Just as any other hydrological model, LISFLOOD needs to know the initial state (i.e. amount of water stored) of its internal state variables in order to be able to produce reasonable discharge simulations. However, in practice we hardly ever know the initial state of all state variables at a given time. Hence, we have to estimate the state of the initial storages in a reasonable way, which is also called the initialisation of a hydrological model.

In this subsection we will first demonstrate the effect of the model's initial state on the results of a simulation, explain the  stedy-state sorage in practice and then explain you in detail how to initialize LISFLOOD.


## The impact of the model's initial state on simulation results 

To better understand the impact of the initial model state on the results of a simulation, let's start with a simple example. The Figure below shows 3 LISFLOOD simulations of soil moisture for the upper soil layer. In the first simulation, it was assumed that the soil is initially completely saturated. In the second one, the soil was assumed to be completely dry (i.e. at residual moisture content). Finally, a third simulation was done where the initial soil moisture content was assumed to be in between these two extremes.

  ![](../media/image37.png)

  **Figure:** *Simulation of soil moisture in upper soil layer for a soil that is initially at saturation (s), at residual moisture content (r) and in between (\[s+r\]/2) *

What is clear from the Figure is that the initial amount of moisture in the soil only has a marked effect on the start of each simulation; after a couple of months the three curves converge. In other words, the  "memory" of the upper soil layer only goes back a couple of months (or, more precisely, for time lags of more than about 8 months the autocorrelation in time is negligible).

In theory, this behaviour provides a convenient and simple way to initialise a model such as LISFLOOD. Suppose we want to do a simulation of the year 1995. We obviously don't know the state of the soil at the beginning of that year. However, we can get around this by starting the simulation a bit earlier than 1995, say one year. In that case we use the year 1994 as a *warm-up* period, assuming that by the start of 1995 the influence of the initial conditions (i.e. 1-1-1994) is negligible. The very same technique can be applied to initialise LISFLOOD's other state variables, such as the amounts of water in the lower soil layer, the upper groundwater zone, the lower groundwater zone, and in the channel.

## The theory of initialisation

When setting up a model run that includes a warm-up period, most of the internal state variables can be simply set to 0 at the start of the run. This applies to the initial amount of water on the soil surface (*WaterDepthInitValue*), snow cover (*SnowCoverInitValue*), frost index (*FrostIndexInitValue*), interception storage (*CumIntInitValue*), and storage in the upper groundwater zone (*UZInitValue*). The initial value of the 'days since last rainfall event' (*DSLRInitValue*) is typically set to 1.

For the remaining state variables, initialisation is somewhat less straightforward. The amount of water in the channel (defined by *TotalCrossSectionAreaInitValue*) is highly spatially variable (and limited by the channel geometry). The amount of water that can be stored in the upper and lower soil layers (*ThetaInit1Value*, *ThetaInit2Value*) is limited by the soil's porosity. The lower groundwater zone poses special problems because of its overall slow response (discussed in a separate section below). Because of this, LISFLOOD provides the possibility to initialise these variables internally, and these special initialisation methods can be activated by setting the initial values of each of these variables to a special 'bogus' value of *-9999*. The following Table summarises these special initialisation methods:

**Table:** *LISFLOOD special initialisation methods*$^1$ 

| **Variable**          | **Description**       | **Initialisation method**     |
|-------------------------------|-------------------------------|-------------------------------|
| ThetaInit1Value / <br> ThetaForestInit2Value    | initial soil moisture content<br> upper soil layer (V/V)| set to soil moisture content <br> at field capacity |
| ThetaInit2Value / <br> ThetaForestInit2Value    | initial soil moisture content <br> lower soil layer (V/V) | set to soil moisture content <br> at field capacity |
| LZInitValue / <br> LZForestInitValue       | initial water in lower <br>  groundwater zone (mm)    | set to steady-state storage |
| TotalCrossSectionArea <br> InitValue | initial cross-sectional area <br> of water in channels              | set to half of bankfull depth      |
| PrevDischarge         | Initial discharge     | set to half of bankfull depth       |

$^1$ These special initialisation methods are activated by setting the value of each respective variable to a 'bogus' value of "-9999"*     

Note that the "-9999" 'bogus' value can *only* be used with the variables in Table x.x; for all other variables they will produce nonsense results! For that the initialisation of the lower groundwater zone is necessary.

**Initialisation of the lower groundwater zone**
Even though the use of a sufficiently long warm-up period usually results in a correct initialisation, a complicating factor is that the time needed to initialise any storage component of the model is dependent on the average residence time of the water in it. For example, the moisture content of the upper soil layer tends to respond almost instantly to LISFLOOD's meteorological forcing variables (precipitation, evapo(transpi)ration). As a result, relatively short warm-up periods are sufficient to initialise this storage component. At the other extreme, the response of the lower groundwater zone is generally very slow (especially for large values of $T_{lz}$). Consequently, to avoid unrealistic trends in the simulations, very long warm-up periods may be needed. The Figure below shows a typical example for an 8-year simulation, in which a decreasing trend in the lower groundwater zone is visible throughout the whole simulation period. Because the amount of water in the lower zone is directly proportional to the baseflow in the channel, this will obviously lead to an unrealistic long-term simulation of baseflow. Assuming the long-term climatic input is more or less constant, the baseflow (and thus the storage in the lower zone) should be free of any long-term trends (although some seasonal variation is normal). In order to avoid the need for excessive warm-up periods, LISFLOOD is capable of calculating a 'steady-state' storage amount for the lower groundwater zone. This *steady state* storage is very effective for reducing the lower zone's warm-up time. The concept of *steady state* is explained in the LISFLOOD model description (**INSERT LINK**), here we will show how it can be used to speed up the initialisation of a LISFLOOD run.


**Steady-state storage in practice**
An actual LISFLOOD simulation differs from the theoretical *steady state* in 2 ways. First, in any real simulation the inflow into the lower zone is not constant, but varies in time. This is not really a problem, since $LZ_{ss}$ can be computed from the *average* recharge. However, this is something we do not know until the end of the simulation! Also, the inflow into the lower zone is controlled by the availability of water in the upper zone, which, in turn, depends on the supply of water from the soil. Hence, it is influenced by any calibration parameters that control behaviour of soil- and subsoil (e.g. $T_{uz}$, $GW_{perc}$, $b$, and so on). This means that --when calibrating the model- the average recharge will be different for every parameter set. Note, however, that it will *always* be smaller than the value of $GW_{perc}$, which is used as an upper limit in the model. Note that the pre-run procedures include a sufficiently long warm-up period.


## What you need to do:  

### Option 1: If using Kinematic routing only (no split routing):

1) Set  initial state of all state variables to either 0,1 or -9999 (i.e. cold start with default values or internally initialized values) in Settings.XML file

2) Activate the “InitLisfloodwithoutsplit” option in <lfoptions> section of Settings.XML file using:
```xml
    <setoption choice="1" name="InitLisfloodwithoutsplit"/>
    <setoption choice="0" name="InitLisflood"/>
```
  
3) Activate reporting maps (in NetCDF format) in <lfoptions> section of Settings.XML file using::
```xml
    <setoption choice="1" name="repLZAvInflowMap"/>
    <setoption choice="1" name="repEndMaps"/>
    <setoption choice="1"  name="writeNetcdf"/>
```

4) Set split routing option to not active in in <lfoptions> section of Settings.XML file using:
```xml
    <setoption choice="0" name="SplitRouting"/>
```

5) Set the name of the reporting map for average percolation rate from upper to lower groundwater zone in <lfuser> section of Settings.XML file using:
```xml
    <textvar name="LZAvInflowMap" value="initrun/lzavin.end">
```

6) Set the name of the reporting map for average discharge map in <lfuser> section of Settings.XML file using:
```xml
    <textvar name="AvgDis" value="initrun/avgdis.end">
```

7) Run the model for a longer period (if possible more than 3 years, best for the whole modelling period)

8) Go back to the LISFLOOD settings file, and set the InitLisfloodwithoutsplit to inactive, leaving all other switches as before:

```xml
    <setoption choice="0" name="InitLisfloodwithoutsplit"/>
    <setoption choice="0" name="InitLisflood"/>
```

### If using Split routing:

1) Set  initial state of all state variables to either 0,1 or -9999 (i.e. cold start with default values or internally initialized values) in Settings.XML file

2) Activate the “InitLisflood” option in <lfoptions> section of Settings.XML file using:
```xml
    <setoption choice="0" name="InitLisfloodwithoutsplit"/>
    <setoption choice="1" name="InitLisflood"/>
```

3) Activate reporting maps (in NetCDF format) in <lfoptions> section of Settings.XML file using:
```xml
    <setoption choice="1" name="repLZAvInflowMap"/>
    <setoption choice="1" name="repEndMaps"/>
    <setoption choice="1"  name="writeNetcdf"/>
```

4) Set split routing option to not active in in <lfoptions> section of Settings.XML file using:
```xml
    <setoption choice="1" name="SplitRouting"/>
```

5) Set the name of the reporting map for average percolation rate from upper to lower groundwater zone in <lfuser> section of Settings.XML file using:
```xml
    <textvar name="LZAvInflowMap" value="initrun/lzavin.end">
```

6) Set the name of the reporting map for average discharge map in <lfuser> section of Settings.XML file using:
```xml
    <textvar name="AvgDis" value="initrun/avgdis.end">
```

7) Run the model for a longer period (if possible more than 3 years, best for the whole modelling period)

8) Go back to the LISFLOOD settings file, and set the InitLisflood inactive, leaving all other switches as before:

```xml
    <setoption choice="0" name="InitLisfloodwithoutsplit"/>
    <setoption choice="0" name="InitLisflood"/>
```

### What to do after the initialization run - Proceed with a LISFLOOD run


9) Checking the lower zone initialisation

The presence of any initialisation problems of the lower zone can be checked by adding the following line to the ‘lfoptions’ element of the settings file:

```xml
<setoption name=" repStateUpsGauges" choice="1"></setoption>
```

This tells the model to write the values of all state variables (averages, upstream of contributing area to each gauge) to time series files. The default name of the lower zone time series is ‘lzUps.tss’.



![initLZDemo](../media/image40.png)

***Figure:*** *Initialisation of lower groundwater zone with and without using a pre-run. Note the strong decreasing trend in the simulation without pre-run. *




10) At the end of the initialization run two files will be created in NetCDF format. Copy those (found in folder "out") into the folder "init":

    lzavin.end.nc
    avgdis.end.nc


11) Replace in the LISFLOOD settings file the 'bogus' values of -9999 for *LZAvInflowMap* and *AvgDis* with the actual map: 

```xml
**************************************************************
INITIAL CONDITIONS FOR THE WATER BALANCE MODEL
(can be either maps or single values)
**************************************************************
</comment>

<textvar name="LZAvInflowMap" value="$(PathInit)/lzavin.map">
<comment>
$(PathInit)/lzavin.map
Reported map of average percolation rate from upper to
lower groundwater zone (reported for end of simulation)
</comment>
</textvar>

<textvar name="AvgDis" value="$(PathInit)/avgdis.map">
<comment>
$(PathInit)/avgdis.map
CHANNEL split routing in two lines
Average discharge map [m3/s]
</comment>
</textvar>
```

12) launch LISFLOOD

To run the model, start up a command prompt (Windows) or a console window (Linux) and type 'lisflood' followed by the name of the settings file, e.g.:

```unix
lisflood settings.xml
```

If everything goes well you should see something like this:

```xml
LISFLOOD version March 01 2013 PCR2009W2M095

Water balance and flood simulation model for large catchments

(C) Institute for Environment and Sustainability

Joint Research Centre of the European Commission

TP261, I-21020 Ispra (Va), Italy

Todo report checking within pcrcalc/newcalc

Created: /nahaUsers/burekpe/newVersion/CWstjlDpeO.tmp

pcrcalc version: Mar 22 2011 (linux/x86_64)

Executing timestep 1

The LISFLOOD version "March 01 2013 PCR2009W2M095" indicates the date of the source code (01/03/2013), the oldest PCRASTER version it works with (PCR2009), the version of XML wrapper (W2) and the model version (M095).

```


> Important note:
> - Calibration parameters obtained with no split routing should never be used to run simulations with split routing and vice versa.
> - Using option InitLisfloodwithoutsplit=1 will result in an AvgDis file with zero values everywhere.
> - In case of doubts, check content of AvgDis file: if it's all zero, then split routing must be off. Note that an AvgDis file containing all zero values will automatically set LISFLOOD to no split routing, even if SplitRouting=1.

