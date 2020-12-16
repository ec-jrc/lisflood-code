# Step 2: Preparing the Settings file

This page describes how to prepare your own settings file. Instead of writing the settings file completely from scratch, we suggest to use the settings template that is provided with LISFLOOD as a starting point. In order to use the template, you should make sure the following requirements are met:

  -   All input maps and tables are named according to default file names
  -   All base maps are in the right directories
  -   All tables are in one directory
  -   All meteo input is in one directory
  -   All Leaf Area Index input is in the right directories
  -   An (empty) directory where all model data can be written exists

If this is all true, the settings file can be prepared very quickly by editing the items in the 'lfuser' element. The following is a detailed description of the different sections of the 'lfuser' element. The present LISFLOOD version contains process-related parameters (not taking into account the parameters that are defined through the maps). These are all defined in the 'lfuser' element, and default values are given for each of them. Even though *any* of these parameters can be treated as calibration constants, doing so for *all* of them would lead to serious over-parameterisation problems. In the description of these parameters we will therefore provide some suggestions as to which parameters should be used for calibration, and which one are better left untouched.

For simplicity reasons, we suggest to follow the following steps:
1)	specify the file path
2)	time related specifications
3) 	parameter options
4)	chose optional model routines (which ones are available; what they do; and how to “activate” them)



### Time-related constants

The 'lfuser' section starts with a number of constants that are related to the simulation period and the time interval used. These are all defined as single values.

```xml
	<comment>                                                           	
	**************************************************************               
	TIME-RELATED CONSTANTS                                                
	**************************************************************               
	</comment>                                                          
	<textvar name="CalendarDayStart" value="01/01/1990">            
	<comment>                                                           
	Calendar day of 1st day in model run                                  
	Day of the year of first map (e.g. xx0.001) even if the model start   
	from map e.g. 500                                                     
	e.g. 1st of January: 1; 1st of June 151 (or 152 in leap year)         
	Needed to read out LAI tables correctly                               
	</comment>                                                          
	</textvar>                                                          
	<textvar name="DtSec" value="86400">                            
	<comment>                                                           
	timestep [seconds]                                                  
	</comment>                                                          
	</textvar>                                                          
	<textvar name="DtSecChannel" value="86400">                     
	<comment>                                                           
	Sub time step used for kinematic wave channel routing [seconds]     
	Within the model,the smallest out of DtSecChannel and DtSec is used   
	</comment>                                                          
	</textvar>                                                          
	<textvar name="StepStart" value="1">                            
	<comment>                                                           
	Number of first time step in simulation                               
	</comment>                                                          
	</textvar>                                                          
	<textvar name="StepEnd" value="10">                             
	<comment>                                                           
	Number of last time step in simulation                                
	</comment>                                                          
	</textvar>                                                          
	<textvar name="ReportSteps" value="endtime">                    
	<comment>                                                           
	Time steps at which to write model state maps (i.e. only              
	those maps that would be needed to define initial conditions          
	for succeeding model run)                                             
	</comment>                                                          
	</textvar>                                                          
```


**CalendarDayStart** is the calendar day of the first map in a map stack e.g. pr000000.001. Even if you start the model from time step 500, this has to be set to the calendar day of the 001 map in your map stacks. Format can be 
  a) a number:
    *Value="1" = $1^{st}$ January* 
    Value="151" = $1^{st}$ July
  Or b) a date (in different format):
    *Value="01/01/1990" = $1^{st}$ January 1990* 
    Value="05.07.1990" = $5^{st}$July 1990
    *Value="15-11-1990" = $15^{st}$ November 1990*

**DtSec** is the simulation time interval in seconds. It has a value of 86400 for a daily time interval, 3600 for an hourly interval, etcetera

**DtSecChannel** is the simulation time interval used by the kinematic wave channel routing (in seconds). Using a value that is smaller than

**DtSec** may result in a better simulation of the overall shape the calculated hydrograph (at the expense of requiring more computing time)

**StepStart** is the number of the first time step in your simulation. It is normally set to 1. Other (larger) values can be used if you want to run LISFLOOD for only a part of the time period for which you have meteo and LAI maps.

**StepEnd** is the number of the last time step in your simulation.

**ReportSteps** defines the time step number(s) at which the model state (i.e. all maps that you would need to define the initial conditions of a succeeding model run) is written. You can define this parameter in the following ways:

1. **At specific time steps**. If you like to have the state maps being written at certain time steps you can define those in a (comma separated) list. For example if you like to have the state maps for the time steps 10, 20 and 40, you need to write:

```xml
    \<textvar name="ReportSteps" value="10,20,40"\
```

2. If you like to have the state maps for the **last time step** of a model run you can use the special     'endtime' keyword, e.g.:

```xml
    \<textvar name="ReportSteps" value="endtime"\
```

3. Alternatively, in some cases you may need the state maps **at regular intervals**. In that case you can use the following syntax:

```xml
    \<textvar name="ReportSteps" value="start+increment..end"\
```

    For instance, in the following example state maps are written every
    $5^{st}$ time step, starting at time step 10, until the last time step:

```xml
    \<textvar name="ReportSteps" value="10+5..endtime"\
```

### Parameters related to evapo(transpi)ration and interception

The following parameters are all related to the simulation of evapo(transpi)ration and rainfall interception. Although they can all be defined as either a single value or as a map, we recommend using the single values that are included in the template. We do not recommend using any of these parameters as calibration constants.

```xml
	<comment>                                                           
	**************************************************************               
	PARAMETERS RELATED TO EVAPO(TRANSPI)RATION AND INTERCEPTION           
	**************************************************************               
	</comment>                                                          
	<textvar name="PrScaling" value="1">                            
	<comment>                                                           
	Multiplier applied to potential precipitation rates                   
	</comment>                                                          
	</textvar>                                                          
	<textvar name="CalEvaporation" value="1">                       
	<comment>                                                           
	Multiplier applied to potential evapo(transpi)ration rates            
	</comment>                                                          
	</textvar>                                                          
	<textvar name="LeafDrainageTimeConstant" value="1">             
	<comment>                                                           
	Time constant for water in interception store [days]                
	</comment>                                                          
	</textvar>                                                          
	<textvar name="kdf" value="0.72">                               
	<comment>                                                           
	Average extinction coefficient for the diffuse radiation flux         
	varies with crop from 0.4 to 1.1 (Goudriaan (1977))                   
	</comment>                                                          
	</textvar>                                                          
	<textvar name="AvWaterRateThreshold" value="5">                 
	<comment>                                                           
	Critical amount of available water (expressed in [mm/day]!), above  
	which 'Days Since Last Rain' parameter is set to 1                  
	</comment>                                                          
	</textvar>                                                          
	<textvar name="SMaxSealed" value="1.0">                         
	<comment>                                                           
	maximum depression storage for water on impervious surface            
	which is not immediatly causing surface runoff [mm]                 
	</comment>                                                          
	</textvar>                                                          
```

**PrScaling** is a multiplier that is applied to precipitation input (pr) [-]

**CalEvaporation** is a multiplier that is applied to the potential evapo(transpi)ration input (**ET0**, **EW0** and **ES0**) [-]

**LeafDrainageTimeConstant** ($T_{int}$) is the time constant for the interception store $[days]$

**kdf** is the average extinction for the diffuse radiation flux (Goudriaan, 1977). it is used to calculate the extinction coefficient for global radiation, $κ_{gb}$.

**AvWaterRateThreshold** defines a critical amount of water that is used as a threshold for resetting the variable $D_{slr}$. Because the equation was originally developed for daily timesteps only, the threshold is currently defined (somewhat confusingly) as an equivalent **intensity** in $[\frac{mm}{day}]$

**SMaxSealed** is the maximum depression storage on impervious surface $[mm]$. This storage is emptied by evaporation (EW0).


### Parameters related to snow and frost

The following parameters are all related to the simulation of snow accumulation, snowmelt and frost. All these parameters can be defined as either single values or maps. We recommend to start out by leaving them all at their default values. If prior data suggest major under- or overcatch problems in the observed snowfall, *SnowFactor* can be adjusted accordingly. *SnowMeltCoef* may be used as a calibration constant, but since snow observations are typically associated with large uncertainty bands, the calibration may effectively just be compensating for these input errors.

```xml
	**************************************************************               
	SNOW AND FROST RELATED PARAMETERS                                     	
	**************************************************************               
	</comment>                                                          
	<textvar name="SnowFactor" value="1">                           
	<comment>                                                           
	Multiplier applied to precipitation that falls as snow                
	</comment>                                                          
	</textvar>                                                          
	<textvar name="SnowSeasonAdj" value="1.0">                      
	<comment>                                                           
	range [mm C-1 d-1] of the seasonal variation                        
	SnowMeltCoef is the average value                                     
	</comment>                                                          
	</textvar>                                                          
	<textvar name="SnowMeltCoef" value="4.5">                       
	<comment>                                                           
	Snowmelt coefficient [mm/deg C /day]                                
	See also Martinec et al., 1998.                                       
	</comment>                                                          
	</textvar>                                                          
	<textvar name="TempMelt" value="0.0">                           
	<comment>                                                           
	Average temperature at which snow melts                               
	</comment>                                                          
	</textvar>                                                          
	<textvar name="TempSnow" value="1.0">                           
	<comment>                                                           
	Average temperature below which precipitation is snow                 
	</comment>                                                          
	</textvar>                                                          
	<textvar name="TemperatureLapseRate" value="0.0065">            
	<comment>                                                           
	Temperature lapse rate with altitude [deg C / m]                    
	</comment>                                                          
	</textvar>                                                          
	<textvar name="Afrost" value="0.97">                            
	<comment>                                                           
	Daily decay coefficient, (Handbook of Hydrology, p. 7.28)             
	</comment>                                                          
	</textvar>                                                          
	<textvar name="Kfrost" value="0.57">                            
	<comment>                                                           
	Snow depth reduction coefficient, [cm-1], (HH, p. 7.28)             
	</comment>                                                          
	</textvar>                                                          
	<textvar name="SnowWaterEquivalent" value="0.45">               
	<comment>                                                           
	Snow water equivalent, (based on snow density of 450 kg/m3) (e.g.     
	Tarboton and Luce, 1996)                                              
	</comment>                                                          
	</textvar>                                                          
	<textvar name="FrostIndexThreshold" value="56">                 
	<comment>                                                           
	Degree Days Frost Threshold (stops infiltration, percolation and      
	capillary rise)                                                       
	Molnau and Bissel found a value 56-85 for NW USA.                     
	</comment>                                                          
	</textvar>                                                          
```

**SnowFactor** is a multiplier that is applied to the rate of precipitation in case the precipitation falls as snow. Since snow is commonly underestimated in meteorological observation data, setting this multiplier to some value greater than 1 can counteract for this [-]

**SnowSeasonAdj** is the range [mm C-1 d-1] of the seasonal variation of snow melt. SnowMeltCoef is the average value.

**SnowMeltCoef** ($C_m$) is the degree-day factor that controls the rate of snowmelt $[\frac{mm}{°C \cdot day}]$

**TempMelt** ($T_m$) is the average temperature above which snow starts to melt $[°C]$

**TempSnow** is the average temperature below which precipitation is assumed to be snow $[°C]$

**TemperatureLapseRate** (**L**) is the temperature lapse rate that is used to estimate average temperature at the centroid of each pixel's elevation zones $[\frac{°C}{m}]$

**Afrost** (**A**) is the frost index decay coefficient $[day^{-1}]$. It has a value in the range 0-1.

**Kfrost** (**K**) is a snow depth reduction coefficient $[cm^{-1}]$

**SnowWaterEquivalent** ($we_s$) is the equivalent water depth of a given snow cover, expressed as a fraction [-]

**FrostIndexThreshold** is the critical value of the frost index above which the soil is considered frozen $[\frac{°C}{day}]$


### Infiltration parameters

The following two parameters control the simulation of infiltration and preferential flow. Both are empirical parameters that are treated as calibration constants, and both can be defined as single values or maps.

```xml
	<comment>                                                           
	**************************************************************               
	INFILTRATION PARAMETERS                                               
	**************************************************************               
	</comment>                                                          
	<textvar name="b\_Xinanjiang" value="0.1">                      
	<comment>                                                           
	Power in Xinanjiang distribution function                             
	</comment>                                                          
	</textvar>                                                          
	<textvar name="PowerPrefFlow" value="3">                        
	<comment>                                                           
	Power that controls increase of proportion of preferential            
	flow with increased soil moisture storage                             
	</comment>                                                          	
```

**b\_Xinanjiang** ($b$) is the power in the infiltration equation [-]

**PowerPrefFlow** ($c_{pref}$) is the power in the preferential flow equation [-]


### Groundwater parameters

The following parameters control the simulation shallow and deeper groundwater. *GwLossFraction* should be kept at 0 unless prior information clearly indicates that groundwater is lost beyond the catchment boundaries (or to deep groundwater systems). The other parameters are treated as calibration constants. All these parameters can be defined as single values or maps.

```xml
	<comment>                                                           
	**************************************************************               
	GROUNDWATER RELATED PARAMETERS                                        
	**************************************************************               
	</comment>                                                          	
	<textvar name="UpperZoneTimeConstant" value="10">               
	<comment>                                                           
	Time constant for water in upper zone [days]                        
	</comment>                                                          
	</textvar>                                                          
	<textvar name="LowerZoneTimeConstant" value="1000">             
	<comment>                                                           
	Time constant for water in lower zone [days]                        
	This is the average time a water \'particle\' remains in the          
	reservoir                                                             
	if we had a stationary system (average inflow=average outflow)        
	</comment>                                                          
	</textvar>                                                          
	<textvar name="GwPercValue" value="0.5">                        
	<comment>                                                           
	Maximum rate of percolation going from the Upper to the Lower         
	response box [mm/day]                                               
	</comment>                                                          
	</textvar>                                                          
	<textvar name="GwLoss" value="0">                               
	<comment>                                                           
	Maximum rate of percolation from the Lower response box (groundwater  
	loss) [mm/day].                                                     
	A value of 0 (closed lower boundary) is recommended as a starting     
	value                                                                 
	</comment>                                                          
	</textvar>                                                          
```

**UpperZoneTimeConstant** ($T_{uz}$) is the time constant for the upper groundwater zone $[days]$

**LowerZoneTimeConstant** ($T_{lz}$) is the time constant for the lower groundwater zone $[days]$

**GwPercValue** ($GW_{perc}$) is the maximum rate of percolation going from the upper to the lower groundwater zone $[\frac{mm}{day}]$

**GwLoss** ($f_{loss}$) is the maximum rate of percolation from the lower groundwater zone (groundwater loss) zone $[\frac{mm}{day}]$. A value of 0 (closed lower boundary) is recommended as a starting value.


### Routing parameters 

These parameters are all related to the routing of water in the channels as well as the routing of surface runoff. The multiplier *CalChanMan* can be used to fine-tune the timing of the channel routing, and it may be defined as either a single value or a map. All other parameters should be kept at their default values.

```xml
	<comment>                                                           
	**************************************************************               
	ROUTING PARAMETERS                                                    
	**************************************************************               
	</comment>                                                          
	<textvar name="CalChanMan" value="1">                           
	<comment>                                                           
	Multiplier applied to Channel Manning's n                            
	</comment>                                                          
	</textvar>                                                          
	<textvar name="beta" value="0.6">                               
	<comment>                                                           
	kinematic wave parameter: 0.6 is for broad sheet flow                 
	</comment>                                                          
	</textvar>                                                          
	<textvar name="OFDepRef" value="5">                             
	<comment>                                                           
	Reference depth of overland flow [mm], used to compute              
	overland flow Alpha for kin. wave                                     
	</comment>                                                          
	</textvar>                                                          
	<textvar name="GradMin" value="0.001">                          
	<comment>                                                           
	Minimum slope gradient (for kin. wave: slope cannot be 0)             
	</comment>                                                          
	</textvar>                                                          
	<textvar name="ChanGradMin" value="0.0001">                     
	<comment>                                                           
	Minimum channel gradient (for kin. wave: slope cannot be 0)           
	</comment>                                                          
	</textvar>                                                          
```

**CalChanMan** is a multiplier that is applied to the Manning's roughness maps of the channel system [-]

**beta** is routing coefficient $β_k$ [-]

**OFDepRef** is a reference flow depth from which the flow velocity of the surface runoff is calculated $[mm]$

**GradMin** is a lower limit for the slope gradient used in the calculation of the surface runoff flow velocity $[\frac{m}{m}]$

**ChanGradMin** is a lower limit for the channel gradient used in the calculation of the channel flow velocity $[\frac{m}{m}]$



### Parameters related to numerics 

This category only contains one parameter at the moment, which can only be a single value. We strongly recommend keeping this parameter at its default value.

```xml
	<comment>                                                           
	********************************** 
	****************************               
	PARAMETERS RELATED TO NUMERICS                                        
	********************************** 
	****************************               
	</comment>                                                          
	<textvar name="CourantCrit" value="0.4">                        
	<comment>                                                           
	Minimum value for Courant condition in soil moisture routine          
	</comment>                                                          	
	</textvar>                                                          
```

**CourantCrit** ($C_{crit}$) is the critical Courant number which controls the numerical accuracy of the simulated soil moisture fluxes [-]. Any value between 0 and 1 can be used, but using values that are too high can lead to unrealistic "jumps" in the simulated soil moisture, whereas very low values result in reduced computational performance (because many iterations will be necessary to obtain the required accuracy). Values above 1 should never be used, as they will result in a loss of mass balance. In most cases the default value of 0.4 results in sufficiently realistic simulations using just a few iterations.




### Prefixes of meteo and vegetation related variables

Here you can define the prefix that is used for each meteorological variable (and LAI and water use).

```xml
	<comment>                                                           
	**************************************************************               
	PREFIXES OF METEO AND VEGETATION RELATED VARIABLES                    
	**************************************************************               
	</comment>                                                          	
	<textvar name="PrefixPrecipitation" value="pr">                 
	<comment>                                                           
	prefix precipitation maps                                             
	</comment>                                                          
	</textvar>                                                          
	<textvar name="PrefixTavg" value="ta">                          
	<comment>                                                           
	prefix average temperature maps                                       
	</comment>                                                          
	</textvar>                                                          
	<textvar name="PrefixE0" value="e">                             
	<comment>                                                           
	prefix E0 maps                                                        
	</comment>                                                          
	</textvar>                                                          
	<textvar name="PrefixES0" value="es">                           
	<comment>                                                           
	prefix ES0 maps                                                       
	</comment>                                                          
	</textvar>                                                          
	<textvar name="PrefixET0" value="et">                           
	<comment>                                                           
	prefix ET0 maps                                                       
	</comment>                                                          
	</textvar>                                                          
	<textvar name="PrefixLAI" value="olai">                         
	<comment>                                                           
	prefix LAI maps                                                       
	</comment>                                                          
	</textvar>                                                          
	<textvar name="PrefixLAIForest" value="flai">                   
	<comment>                                                           
	prefix forest LAI maps                                                
	</comment>                                                          
	</textvar>                                                          
	<textvar name="PrefixWaterUse" value="wuse">                    
	<comment>                                                           
	prefix water use maps                                                 
	</comment>                                                          
	</textvar>                                                          
```

Each variable is read as a stack of maps. The name of each map starts with prefix, and ends with the number of the time step. All characters in between are filled with zeroes. The name of each map is made up of a total of 11 characters: 8 characters, a dot and a 3-character suffix. For instance, using a prefix 'pr' we get:

  pr000000.007   : at time step 7
  pr000035.260   : at time step 35260

> To avoid unexpected behaviour, **never** use numbers in the prefix!\
> For example:
>
> PrefixRain=pr10
>
> For the first time step this yields the following file name:
>
>   pr100000.001   
>
> But this is actually interpreted as time step 100,000,001!\
> **Therefore, do not use numbers in the prefix!**

The corresponding part of the settings file is pretty self-explanatory:

**PrefixPrecipitation** is the prefix of the precipitation maps

**PrefixTavg** is the prefix of the daily average temperature maps

**PrefixE0** is the prefix of the potential open-water evaporation maps

**PrefixES0** is the prefix of the potential bare-soil evaporation maps

**PrefixET0** is the prefix of the potential (reference) evapotranspiration maps

**PrefixLAI** is the prefix of the Leaf Area Index maps

**PrefixLAIForest** is the prefix of the forest Leaf Area Index maps

**PrefixWaterUse** is the prefix of the water use maps (optional)


### Initial conditions

As with the calibration parameters you can use both maps and single values to define the catchment conditions at the start of a simulation. Note that a couple of variables can be initialized internally in the
model (explained below). Also, be aware that the initial conditions define the state of the model at *t=(StepStart -1)*. As long as *StepStart* equals 1 this corresponds to *t=0*, but for larger values of *StepStart* this is (obviously) not the case!

```xml
	<comment>                                                           
	**************************************************************               
	INITIAL CONDITIONS                                                    
	(maps or single values)                                               
	**************************************************************               
	</comment>                                                          
	<textvar name="WaterDepthInitValue" value="0">                  	
	<comment>                                                           
	initial overland flow water depth [mm]                              
	</comment>                                                          
	</textvar>                                                          
	<textvar name="SnowCoverAInitValue" value="0">                  
	<comment>                                                           
	initial snow depth in snow zone A [mm]                              
	</comment>                                                          
	</textvar>                                                          
	<textvar name="SnowCoverBInitValue" value="0">                  
	<comment>                                                           
	initial snow depth in snow zone B [mm]                              
	</comment>                                                          
	</textvar>                                                          
	<textvar name="SnowCoverCInitValue" value="0">                  
	<comment>                                                           
	initial snow depth in snow zone C [mm]                              
	</comment>                                                          
	</textvar>                                                          
	<textvar name="FrostIndexInitValue" value="0">                  
	<comment>                                                           
	initial Frost Index value                                             
	</comment>                                                          
	</textvar>                                                          
	<textvar name="CumIntInitValue" value="0">                      
	<comment>                                                           
	cumulative interception [mm]                                        
	</comment>                                                          
	</textvar>                                                          
	<textvar name="UZInitValue" value="0">                          
	<comment>                                                           
	water in upper store [mm]                                           
	</comment>                                                          
	</textvar>                                                          
	<textvar name="DSLRInitValue" value="1">                        
	<comment>                                                           
	days since last rainfall                                              
	</comment>                                                          
	</textvar>                                                          
	<textvar name="CumIntSealedInitValue" value="0">                
	<comment>                                                           
	cumulative depression storage [mm]                                  
	</comment>                                                          
	</textvar>                                                          
	<comment>                                                           
	********************************** 
	****************************               
	The following variables can also be initialized in the model          
	internally. if you want this to happen set them to bogus value of     
	-9999                                                                 
	********************************** 
	****************************               
	</comment>                                                          
	<textvar name="LZInitValue" value="-9999">                      
	<comment>                                                           
	water in lower store [mm]                                           
	-9999: use steady-state storage                                       
	</comment>                                                          
	</textvar>                                                          
	<textvar name="TotalCrossSectionAreaInitValue" value="-9999">   
	<comment>                                                           
	initial cross-sectional area of flow in channel[m2]                 
	-9999: use half bankfull                                              
	</comment>                                                          
	</textvar>                                                          
	<textvar name="ThetaInit1Value" value="-9999">                  
	<comment>                                                           
	initial soil moisture content layer 1                                 
	-9999: use field capacity values                                      
	</comment>                                                          
	</textvar>                                                          
	<textvar name="ThetaInit2Value" value="-9999">                  
	<comment>                                                           
	initial soil moisture content layer 2                                 
	-9999: use field capacity values                                      
	</comment>                                                          
	</textvar>                                                          
	<textvar name="PrevDischarge" value="-9999">                    
	<comment>                                                           
	initial discharge from previous run for lakes, reservoirs and         
	transmission loss                                                     
	only needed for lakes reservoirs and transmission loss                
	-9999: use discharge of half bankfull                                 
	</comment>                                                          
	</textvar>                                                          
```

**WaterDepthInitValue** is the initial amount of water on the soil surface $[mm]$

**SnowCoverInitAValue** is the initial snow cover on the soil surface in elevation zone **A** $[mm]$

**SnowCoverInitBValue** is the initial snow cover on the soil surface in elevation zone **B** $[mm]$

**SnowCoverInitCValue** is the initial snow cover on the soil surface in elevation zone **C** $[mm]$

**FrostIndexInitValue** (**F** in Eq 2-5) initial value of the frost index $[\frac{°C}{day}]$

**CumIntInitValue** is the initial interception storage $[mm]$

**UZInitValue** is the initial storage in the upper groundwater zone $[mm]$

**DSLRInitValue** ($D_{slr}$ in Eq 2-20) is the initial number of days since the last rainfall event $[days]$

**CumIntSealedInitValue** is the initial value of the depression storage for the sealed part of a pixel $[mm]$

**LZInitValue** is the initial storage in the lower groundwater zone $[mm]$. In order to avoid initialization problems it is possible to let the model calculate a 'steady state' storage that will usually minimize any initialization problems. This feature is described in detail in Chapter 7 of this User Manual. To activate it, set the lfoptions element InitLisflood to 1.

**TotalCrossSectionAreaInitValue** is the initial cross-sectional area $[m^2]$ of the water in the river channels (a substitute for initial discharge, which is directly dependent on this). A value of **-9999 ** sets the initial amount of water in the channel to half bankfull.

**ThetaInit1Value** is the initial moisture content $[\frac{mm^3} {mm^3}]$ of the upper soil layer. A value of -**9999** will set the initial soil moisture content to field capacity.

**ThetaInit2Value** is the initial moisture content $[\frac{mm^3} {mm^3}]$ of the lower soil layer. A value of -**9999** will set the initial soil moisture content to field capacity

**PrevDischarge** is the initial discharge from previous run $[\frac{m^3} {s}]$ used for lakes, reservoirs and transmission loss (only needed if option is on for lakes or reservoirs or transmission loss). Note that PrevDischarge is discharge as an average over the time step (a flux) . A value of **-9999** sets the initial amount of discharge to equivalent of half bankfull.

```xml
	<comment>                                                           
	**************************************************************               
	INITIAL CONDITIONS FOREST                                             
	(maps or single values)                                               
	**************************************************************               
	</comment>                                                          
	<textvar name="CumIntForestInitValue" value="0">                
	<comment>                                                           
	cumulative interception [mm]                                        
	</comment>                                                          
	</textvar>                                                          
	<textvar name="UZForestInitValue" value="0">                    
	<comment>                                                           
	water in upper store [mm]                                           
	</comment>                                                          
	</textvar>                                                          
	<textvar name="DSLRForestInitValue" value="1">                  
	<comment>                                                           
	days since last rainfall                                              
	</comment>                                                          
	</textvar>                                                          
	<textvar name="LZForestInitValue" value="-9999">                
	<comment>                                                           
	water in lower store [mm]                                           
	-9999: use steady-state storage                                       
	</comment>                                                          
	</textvar>                                                          
	<textvar name="ThetaForestInit1Value" value="-9999">            
	<comment>                                                           
	initial soil moisture content layer 1                                 
	-9999: use field capacity values                                      
	</comment>                                                          
	</textvar>                                                          
	<textvar name="ThetaForestInit2Value" value="-9999">            
	<comment>                                                           
	initial soil moisture content layer 2                                 
	-9999: use field capacity values                                      
	</comment>                                                          
```
CumIntForestInitValue, UZForestInitValue, DSLRForestInitValue, LZForestInitValue, ThetaForestInit1Value, ThetaForestInit2Value are the initial value for the forest part of a pixel


### Using options

The 'lfoptions' element gives you additional control over what LISFLOOD is doing. Using options it is possible to switch certain parts of the model on or off. This way you can tell the model exactly which output files are reported and which ones aren't. Also, they can be used to activate a number of additional model features, such as the simulation of reservoirs and inflow hydrographs.

This guide provides a [table](https://ec-jrc.github.io/lisflood-code/4_annex_settings_and_options/) that lists all currently implemented options and their corresponding defaults. All currently implemented options are switches (1= on, 0=off). You can set as many options as you want (or none at all). Annex 11 lists all currently implemented options. Note that each option generally requires additional items in the settings file. For instance, using the inflow hydrograph option requires an input map and time series, which have to be specified in the settings file. If you want to report discharge maps at each time step, you will first have to specify under which name they will be written. The template settings file that is provided with LISFLOOD always contains file definitions for all optional output maps and time series. The use of the *output* options is described in detail in Chapter 8.

Within the 'lfoptions' element of the settings file, each option is defined using a 'setoption' element, which has the attributes 'name' and 'choice' (i.e. the actual value). For example:

```xml
	<lfoptions>                            
	<setoption choice="1" name="inflow" /> 
	</lfoptions>                           	
```
[:top:](#top)

