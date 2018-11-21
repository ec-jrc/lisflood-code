# OptionsTserieMaps.xml

## Purpose

OptionTserieMaps.xml file is part of LISFLOOD code and it's located in the same folder as lisf1.py file. 
> This file should <span style="color:red"> NEVER</span> be changed while using LISFLOOD.


## Layout and main elements

OptionTserieMaps.xml file is organized into three different sections:


+ **lfoptions:** it contains the list of all possible LISFLOOD options (switches). Switches can have two options:

    - 0 in default = this option is by default not used;
    - 1 in default = this is used by default

    All switches are set to the default value. In order to activate/dis-activate a switch, it must be copied to Settings.xml. Values in Settings.xml file will overwrite values in OptionsTserieMaps.xml file.

    A list of all available switches can be found in the following file: LISFLOOD_switches_list.xlsx

+ **lftime:** it contains the list of all possible outputs as time series.
    Different keys can be used to describe what to store in the time series file:

    - name:             name of this variable in the settings.xml (it's the name of the key in Settings.xml file that is used for this variable)
    - outputVar:       name of the output variable in the code
    - where:            where is the time series reported: e.g. gauges, sites, 1, Catchments, LakeSites etc.
    - repoption:       time series is reported if one of these options is active
    - restrictoption:  time series is only reported if this option(s) are active
    - operation:       operation to be done before reporting e.g. mapmaximum, total (=catchmenttotal)

    ```xml
    <setserie name="RainAvUpsTS"  outputVar="Rain"  where="Gauges"  repoption="repRateUpsGauges"  restrictoption="nonInit"  operation="total" /
    ```

+ **lfmaps:** it contains the list of all possible outputs as maps.
    Different keys can be used to describe what to store in the map file:

    - name:             name of this variable in the settings.xml (it's the name of the key in Settings.xml file that is used for this variable)
    - outputVar:       name of the output variable in the code
    - unit:                what unit has this variable e.g. m, mm, degree
    - end:               reported only at last step (one of the reporting switch names must be specified here)
    - steps:             reported at report steps (one of the reporting switch names must be specified here)
    - all:                  reported on all steps (one of the reporting switch names must be specified here)
    - restrictoption:  map is only reported if this option(s) are active

    ```xml
    <setmap name="WaterDepthState"  outputVar="WaterDepth"  unit="m"  end=""  steps="repStateMaps"  all=""  restrictoption="nonInit" />
    ```
