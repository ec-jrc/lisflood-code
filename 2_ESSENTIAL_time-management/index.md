# Time management (start, end, re-start simulations)

## Time convention within LISFLOOD model

LISFLOOD model follows an "end of timestep" naming convention for timestamps of both input (forcings) and output data.

Accordingly,  if timestamp "02/01/2017 06:00" is used for naming a time step of daily  accumulated rainfall data, that time step will contain rainfall  accumulation between  "01/01/2017 06:00" and "02/01/2017 06:00" (see  following figure)

![](../media/image62.png)

Outputs  of LISFLOOD model will use the same naming convention. If timestamp  "02/01/2017 06:00" is used for naming a time step of daily dischage  (output), that time step will contain average discharge over the period  between  "01/01/2017 06:00" and "02/01/2017 06:00" (see following  figure)

![](../media/image63.png)

In Settings file, three different keys are used to specify start date, end date and state file date for LISFLOOD simulation:

- **StepStart:** this key specifies the starting date of the simulation. The starting date is also the date of the first LISFLOOD output.
  In Settings.xml*:  <textvar name="StepStart" value="02/01/2017 06:00">*
  For  example, if we set StepStart to "02/01/2017 06:00", this means that  LISFLOOD will automatically use forcing data with timestamp "02/01/2017  06:00" (i.e. accumulated rainfall over the period between "01/01/2017  06:00" and "02/01/2017 06:00") and it will also store outputs with the  same timestamp (i.e. average discharge over the period between  "01/01/2017 06:00" and "02/01/2017 06:00").
- **StepEnd:** this key specifies the end date of the simulation. The end date is also the date of the last LISFLOOD output.
  In Settings.xml*:  <textvar name="StepEnd value="05/01/2017 06:00">*
  For  example, if we set StepEnd to "05/01/2017 06:00", this means that last  output from LISFLOOD run will have timestamp "05/01/2017 06:00"
- **timestepInit:**  this key is used to specify which timestamp must be used to retrieve  information from existing state files (i.e. from a previous simulation)
  For  example, if we want to start a new simulation at "03/01/2017 06:00" and  we want to use hydrological state information from the last time step,  we will set timestepInit to "02/01/2017 06:00". Outputs with timestamp  "02/01/2017 06:00" will be used to initialize the model, while the first  output of the simulation will be be store with timestamp "03/01/2017  06:00"

![](../media/image64.png)

> <span style="color:red"> **Both timestamps and time steps ALWAYS refer to the END of the TIME INTERVAL!**</span>


## Using timestamps

Timestamps  (dates) can now be used to set start date and end date of LISFLOOD  simulation. Dates can be used for keys: StepStart, StepEnd and  timestepInit in Settings.xml file. ReportSteps can only be provided as  time steps numbers and are referred to CalendarDayStart.

Date formats accepted include:

```
DATE_FORMATS = ['%d/%m/%Y %H:%M', '%Y/%m/%d %H:%M', '%d/%m/%Y', '%Y/%m/%d',
                '%d/%m/%y %H:%M', '%y/%m/%d %H:%M', '%d/%m/%y', '%y/%m/%d',
                '%d-%m-%Y %H:%M', '%Y-%m-%d %H:%M', '%d-%m-%Y', '%Y-%m-%d',
                '%d-%m-%y %H:%M', '%y-%m-%d %H:%M', '%d-%m-%y', '%y-%m-%d',
                '%d.%m.%Y %H:%M', '%Y.%m.%d %H:%M', '%d-%m-%Y', '%Y.%m.%d',
                '%d.%m.%y %H:%M', '%y.%m.%d %H:%M', '%d.%m.%y', '%y.%m.%d']
```

If hours:minutes are not specified, LISFLOOD will automatically set them to 00:00

When  using timestamps, CalendarDayStart key in Settings.xml is only used  internally to transform timestamps to model's time steps and it is  usually set equal to StepStart,

StepStart, StepEnd and  timestepInit are used to access NetCDF files containing forcings and  state variables, and to create output NetCDF files.

## Using time steps

Time  steps can still be used to set start step and end step of LISFLOOD  simulation. ReportSteps can only be provided as time steps numbers.

All steps numbers are referred to CalendarDayStart

When  using time steps, dates (including hours and minutes) to retrieve data  for forcings and state variables are automatically determined by  LISFLOOD.

```xml
	<comment>                                                           	
	**************************************************************               
	TIME-RELATED CONSTANTS                                                
	**************************************************************               
	</comment>                                                          
	<textvar name="CalendarDayStart" value="01/01/2015 06:00">            
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
	<textvar name="DtSecChannel" value="3600">                     
	<comment>                                                           
	Sub time step used for kinematic wave channel routing [seconds]     
	Within the model,the smallest out of DtSecChannel and DtSec is used   
	</comment>                                                          
	</textvar>                                                          
	<textvar name="StepStart" value="03/01/2015 06:00">                            
	<comment>                                                           
	Number of first time step in simulation                               
	</comment>                                                          
	</textvar>                                                          
	<textvar name="StepEnd" value="05/01/2015 06:00">                             
	<comment>                                                           
	Number of last time step in simulation                                
	</comment>                                                          
	</textvar>                                                          
	<textvar name="ReportSteps" value="1..5">                    
	<comment>                                                           
	Time steps at which to write model state maps (i.e. only              
	those maps that would be needed to define initial conditions          
	for succeeding model run)                                             
	</comment>                                                          
	</textvar>                                                          
```

