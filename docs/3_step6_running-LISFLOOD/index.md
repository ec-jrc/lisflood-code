# Step 5: Running LISFLOOD (warm start)

Once you have initialized LISFLOOD you can launch a "warm start". That means you can use all internal state variables ('end maps') that you have received during the initialization (see Step 4) as the initial conditions for a succeeding simulation. 
This is particularly useful if you are simulating individual flood events on a small time interval (e.g. hourly). For instance, to estimate the initial conditions just before the flood event you can do an initialization also called 'pre-run' on a *daily* time interval for the year before the flood event. Then you  can use the resulting 'end maps' as the initial conditions for the hourly simulation of the flood event.

In any case, you should be aware that values of some **internal state variables of the model** (especially lower zone storage) **are very much dependent on the parameterisation used**. Hence, suppose we have 'end maps' that were created using some parameterisation of the model (let's say parameter set *A*), then these maps should **not** be used as initial conditions for a model run with another parameterisation (parameter set *B*). If you decide to do this anyway, you are likely to encounter serious initialisation problems (but these may not be immediately visible in the output!). If you do this while calibrating the model (i.e. parameter set *B* is the calibration set), this will render the calibration exercise pretty much useless (since the output is the result of a mix of different parameter sets). However, for *FrostIndexInitValue* and *DSLRInitValue* it is perfectly safe to use the 'end maps', since the values of these maps do not depend on any calibration parameters (that is, only if you do not calibrate on any of the frost-related parameters!). If you need to calibrate for individual events (e.g. hourly), you should apply *each* parameterisation on both the (daily) pre-run and the event run! This may seem awkward, but there is no way of getting around this (except from avoiding event-based calibration at all, which may be a good idea anyway).

## What you need to do

### 1. Save and use state/end maps

At the end of each model run, LISFLOOD writes maps of all internal state variables. Two different sets of maps can be stored (both sets can be saved at the same time):

- End maps: NetCDF single maps containing internal state variables values for the last simulation timestep (`StepEnd`).
- State maps: NetCDF stack maps containing internal state variables values for the `ReportSteps` period.

You can use either state maps or end maps as the initial conditions for a succeeding simulation. This is particularly useful if you are simulating individual flood events on a small time interval (e.g. hourly). For instance, to estimate the initial conditions just before the flood you can do a ‘pre-run’ on a daily time interval for the year before the flood. You can then use the ‘end maps’ as the initial conditions for the hourly simulation.

* **Saving end maps**. To save end maps for later model runs, activate the `repEndMaps` option in `<lfoptions>` section of the settings file (_settings.xml_):
    ```xml
    <setoption choice="1" name="repEndMaps"/>
    ```
<br>
* **Saving state maps**. To save state maps for later model runs, activate the `repStateMaps` option in `<lfoptions>` section of the settings file (_settings.xml_):
    ```xml
    <setoption choice="1" name="repStateMaps"/>
    ```
  
Some internal state variables of the model (especially lower zone storage) are very much dependent on the parametrisation used. Hence, suppose we have ‘end maps’ that were created using some parametrisation of the model (let’s say parameter set A), then these maps should not be used as initial conditions for a model run with another parametrisation (parameter set B).

### 2. Using state/end maps

LISFLOOD warm start is managed by two keys in the XML settings file:

- `StepStart` is the first output step/date from LISFLOOD model (forecast);
- `timestepInit` is the step/date to use as the initial state (usually it's one model step before `StepStart`, but it can be any date/step).

### 3. Warm start LISFLOOD

The simulation period of a LISFLOOD warm start can be defined in the settings file in two ways: either defining dates (_timestamp_) or step numbers (_timestep_). In any case, three variables are involved:

* `CalendarDaystart` sets the reference date used to save the time information in the NetCDF files.
* `StepStart` sets the time for the beginning of the simulation.
* `timestepInit` sets the time for the initial conditions. It means that the model will look for this timestep in the state maps and use it as the initial conditions.

These three variables are set in the `<lfuser>` section of the settings file.

#### Option 1. Using timestamps (dates) with state files

In this case, the three variables must be set as timestamps. Let's see an example in which we run a simulation starting the 1st October 2015 at midday with 6-hourly resolution:

```xml
<textvar name="CalendarDayStart" value="01-10-2015 12:00"/>
<textvar name="StepStart" value="01-10-2015 12:00"/>
<textvar name="timestepInit" value="01-10-2015 06:00"/>
```

`CalendarDayStart` must be equal or earlier than `StepStart`, and it will be only used to set the time unit in the NetCDF files to "hours since 2015-01-10 12:00". `StepStart` defines the beginning of the simulation at '01-10-2015 12:00'. Since `CalendarDayStart` and `StepStart` are equal, the first timestep will be saved in the NetCDF with a value of 0 (hours since `CalendarDayStart`). To do a warm run, the initial conditions must be taken from the timestep before the beginning of the simulation, that's why `timestepInit` is set 6 hours before.

#### Option 2. Using timesteps (step numbers) with state files

In this case, `CalendarDayStart` is a timestamp, and the other two variables are integers refering to that timestamp. Let's see the same example as before:

```xml
<textvar name="CalendarDayStart" value="01-10-2015 12:00"/>
<textvar name="StepStart" value="1"/>
<textvar name="timestepInit" value="0"/>
```

Again, `CalendarDayStart` defines the time unit as "hours since 2015-01-10 12:00". A `StepStart` value of 1 sets the beginning of the simulation at the same time as `CalendarDayStart`. Same as before, since these two variables are equal, the first timestep will be saved in the NetCDF file as 0. To do a warm run, `timestepInit` is set to 0 in order to look for the initial conditions at the previous timestep as `CalendarDayStart`, i.e., 2015-01-10 06:00.

> **NOTE:** If state files are used to initialize a LISFLOOD run, it will automatically use timestamps in NetCDF files to get data for `timestepInit`. If end files are used, LISFLOOD will automatically assign data from NetCDF to `timestepInit`.