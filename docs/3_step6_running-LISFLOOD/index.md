# Step 5: Running LISFLOOD 

Once you have initialized LISFLOOD you can launch the actual target run. Depending on how you define the initial conditions in this you may be doing what is called a cold start or a warm start. In any case, you must have done the initialization run previously in order to initilialize the lower groundwater zone and the river discharge (only if using kinematic wave split routing).

## A cold start run

A cold start run uses default initial conditions. As explained in the [model initialisation chapter](../3_step5_model-initialisation/), you will have to extend the simulation period an appropriate amount of time before the start of your period of interest, so that the model state variables converge to realistic values. Once you run the simulation, you will need to discard the results for that period of time at the beginning of the simulations.

To run a cold start, follow this steps:

1. Configure the settings file (_Settings.xml_):
    1. In the `<lfoptions>` element, make sure that the initialization options are deactivated.
    ```xml
        <setoption choice="0" name="InitLisfloodwithoutsplit"/>
        <setoption choice="0" name="InitLisflood"/>
    ```
    2. In the `<lfuser>` element:
        1. Define the time-related constants according to your simulation period. Remember to extend backwards the start of the run (`StepStart`) to include the warmup period. In the example below, we start the simulation October 1st 2014 for a target period starting OCtober 1st 2015, i.e., one year of warmup. More information about time-related constants can be found in the [dedicated chapter](../2_ESSENTIAL/_time-management); remember that for some variables you can use either dates or integers.
        ```xml
            <textvar name="CalendarDayStart" value="01-10-2014 12:00"/>
            <textvar name="StepStart" value="01-10-2014 12:00"/>
        ```
        
        2. Define default values for the initial conditions. For the sake of brevity, we include just a few here.
        ```xml
            <textvar name="OFDirectInitValue" value="0"/>
            <textvar name="OFOtherInitValue" value="0"/>
            <textvar name="OFForestInitValue" value=""/>
            <textvar name="SnowCoverAInitValue" value="0"/>
            <textvar name="SnowCoverBInitValue" value="0"/>
            <textvar name="SnowCoverCInitValue" value="0"/>
            <textvar name="FrostIndexInitValue" value="0"/>
            <textvar name="CumIntInitValue" value="0"/>
            <textvar name="UZInitValue" value="0"/>
            <textvar name="DSLRInitValue" value="1"/>
        ```
        
    3. In the `<lfbinding>`, define the location of the outputs from the initialization run.
    ```xml
        <textvar name="LZAvInflowMap" value="$(PathInit)/lzavin">

        <textvar name="AvgDis" value="$(PathInit)/avgdis">
    ```

<br>
2. Launch LISFLOOD. To run the model, start up a command prompt (Windows) or a console window (Linux) and type `lisflood` followed by the name of the settings file, e.g.:

```unix
lisflood settings.xml
```

## A warm start run

A warm start run uses the state variables at the end of another simulation as the initial conditions of the current simulation. 

A usual procedure is to apply the end state of a initialization run (see Step 4) as the initial conditions for a succeeding simulation. This is particularly useful if you are simulating individual flood events on a small time interval (e.g. hourly). For instance, to estimate the initial conditions just before the flood event you can do an initialization run on a *daily* time interval for the year before the flood event; then you  can use the end state as the initial conditions for the hourly simulation of the flood event.

In any case, you should be aware that values of **some internal state variables of the model are very much dependent on the parameterisation used** (especially lower zone storage). Hence, suppose we have 'end maps' that were created using some parameterisation of the model (let's say parameter set *A*), then these maps should **not** be used as initial conditions for a model run with another parameterisation (parameter set *B*). If you decide to do this anyway, you are likely to encounter serious initialisation problems (but these may not be immediately visible in the output!). If you do this while calibrating the model (i.e. parameter set *B* is the calibration set), this will render the calibration exercise pretty much useless (since the output is the result of a mix of different parameter sets). However, for `FrostIndexInitValue` and `DSLRInitValue` it is perfectly safe to use the 'end maps', since the values of these maps do not depend on any calibration parameters (as long as you do not calibrate any of the frost-related parameters!). If you need to calibrate for individual events (e.g. hourly), you should apply *each* parameterisation on both the pre-run and the event run! This may seem awkward, but there is no way of getting around this (except from avoiding event-based calibration at all, which may be a good idea anyway).

To run a warm start, you will need to create the initial conditions first, and then launch the warm start run.

### 1. Create the initial conditions

LISFLOOD can put out the state variables in two non-exclusive ways (you can get both at the same time):

- **End maps**: NetCDF single maps containing internal state variables values for the last simulation timestep (`StepEnd`). To produce end maps, activate the `repEndMaps` option in the `<lfoptions>` section of the settings file (_settings.xml_):
```xml
    <setoption choice="1" name="repEndMaps"/>
``` 
- **State maps**: NetCDF stack maps containing internal state variables values for the `ReportSteps` period. To produce end maps,  activate the `repStateMaps` option in the `<lfoptions>` section of the settings file (_settings.xml_):
```xml
    <setoption choice="1" name="repStateMaps"/>
```

You can use either state maps or end maps as the initial conditions for a succeeding simulation. One or both of the previous options must be active on the a preceding run; this previous run could be an initialization run or not (for instance, in an operational system). Hence, simulating that run creates the initial conditions for the current run.

> **NOTE:** If state files are used to initialize a LISFLOOD run, it will automatically use timestamps in NetCDF files to get data for `timestepInit`. If end files are used, LISFLOOD will automatically assign data from NetCDF to `timestepInit`.

### 2. Run LISFLOOD with warm start

To run LISFLOOD with a warm start, we need to define in the settings file the previously obtained state variables as the initial conditions. Follow this steps:

1. Configure the settings file (_Settings.xml_):
    1. In the `<lfoptions>` element, make sure that the initialization options are deactivated.
    ```xml
        <setoption choice="0" name="InitLisfloodwithoutsplit"/>
        <setoption choice="0" name="InitLisflood"/>
    ```
    2. In the `<lfuser>` element:
        1. Define the time-related constants according to your simulation period. In case you are using state maps as initial conditions, the date defined in `timestepInit` will be used to extract the initial conditions from the map stack. More information about time-related constants can be found in the [dedicated chapter](../2_ESSENTIAL/_time-management); remember that for some variables you can use either dates or integers.
        ```xml
            <textvar name="CalendarDayStart" value="01-10-2015 12:00"/>
            <textvar name="StepStart" value="01-10-2015 12:00"/>
            <textvar name="timestepInit" value="01-10-2015 06:00"/>
        ```

        2. Define the directory where the model will look for the initial contions.
        ```xml
            <textvar name="PathInit" value="$(PathRoot)/initial">
        ```
        
        3. Define the files from which the model will extract the initial conditions. For the sake of brevity, we include just a few here.
        ```xml
            <textvar name="OFDirectInitValue" value="$(PathInit)/ofdir"/>
            
            <textvar name="OFOtherInitValue" value="$(PathInit)/ofoth"/>
            
            <textvar name="OFForestInitValue" value="$(PathInit)/offor"/>
            
            <textvar name="SnowCoverAInitValue" value="$(PathInit)/scova"/>
            
            <textvar name="SnowCoverBInitValue" value="$(PathInit)/scovb"/>
            
            <textvar name="SnowCoverCInitValue" value="$(PathInit)/scovc"/>
            
            <textvar name="FrostIndexInitValue" value="$(PathInit)/frost"/>
            
            <textvar name="CumIntInitValue" value="$(PathInit)/cum"/>
            
            <textvar name="UZInitValue" value="$(PathInit)/uz"/>
            
            <textvar name="DSLRInitValue" value="$(PathInit)/dslr"/>
        ```
        
    3. In the `<lfbinding>`, define the location of the outputs from the initialization run.
    ```xml
        <textvar name="LZAvInflowMap" value="$(PathInit)/lzavin">

        <textvar name="AvgDis" value="$(PathInit)/avgdis">
    ```

<br>
2. Launch LISFLOOD. To run the model, start up a command prompt (Windows) or a console window (Linux) and type `lisflood` followed by the name of the settings file, e.g.:

```unix
lisflood settings.xml
```

[:top:](#top)