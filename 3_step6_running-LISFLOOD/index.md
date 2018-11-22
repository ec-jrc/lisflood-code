# Step 6: Running LISFLOOD (warm start)

Once you have initiallized LISFLOOD you can launch a "warm start". That means you can use all internal state variables ('end maps') that you have received during the initialization (see Step 5) as the initial conditions for a succeeding simulation. 
This is particularly useful if you are simulating individual flood events on a small time interval (e.g. hourly). For instance, to estimate the initial conditions just before the flood event you can do an initialization also called 'pre-run' on a *daily* time interval for the year before the flood event. Then you  can use the resulting 'end maps' as the initial conditions for the hourly simulation of the flood event.

In any case, you should be aware that values of some **internal state variables of the model** (especially lower zone storage) **are very much dependent on the parameterisation used**. Hence, suppose we have 'end maps' that were created using some parameterisation of the model (let's say parameter set *A*), then these maps should **not** be used as initial conditions for a model run with another parameterisation (parameter set *B*). If you decide to do this anyway, you are likely to encounter serious initialisation problems (but these may not be immediately visible in the output!). If you do this while calibrating the model (i.e. parameter set *B* is the calibration set), this will render the calibration exercise pretty much useless (since the output is the result of a mix of different parameter sets). However, for *FrostIndexInitValue* and *DSLRInitValue* it is perfectly safe to use the 'end maps', since the values of these maps do not depend on any calibration parameters (that is, only if you do not calibrate on any of the frost-related parameters!). If you need to calibrate for individual events (i.e.hourly), you should apply *each* parameterisation on *both * the (daily) pre-run and the 'event' run! This may seem awkward, but there is no way of getting around this (except from avoiding event-based calibration at all, which may be a good idea anyway).

## What you need to do
1) Save and use state/end maps

At the end of each model run, LISFLOOD writes maps of all internal state variables. Two different sets of maps can be stored (both sets can be saved at the same time):

- End maps: NetCDF single maps containing internal state variables values for the last simulation timestep (*StepEnd*)
- State maps: NetCDF stack maps containing internal state variables values for the *ReportSteps* period

You can use either state maps or end maps as the initial conditions for a succeeding simulation. This is particularly useful if you are simulating individual flood events on a small time interval (e.g. hourly). For instance, to estimate the initial conditions just before the flood you can do a ‘pre-run’ on a daily time interval for the year before the flood. You can then use the ‘end maps’ as the initial conditions for the hourly simulation.

- **Saving end maps**
    To save end maps to be used for later model runs, activate the "repEndMaps" option in <lfoptions> section of Settings.XML:
    ```xml
    <setoption choice="1" name="repEndMaps"/>
    ```

- **Saving state maps**
    To save state maps to be used for later model runs, activate the "repStateMaps" option in <lfoptions> section of Settings.XML:
    ```xml
    <setoption choice="1" name="repStateMaps"/>
    ```
  
Some internal state variables of the model (especially lower zone storage) are very much dependent on the parametrisation used. Hence, suppose we have ‘end maps’ that were created using some parametrisation of the model (let’s say parameter set A), then these maps should not be used as initial conditions for a model run with another parametrisation (parameter set B).

2) Using state/end maps

LISFLOOD warm start is managed by two keys in Settings XML file:

- "StepStart" which is the first output step/date from LISFLOOD model (forecast);
- "timestepInit" which is the step/date to use as the initial state (usually it's one model step before "StepStart", but it can be any date/step).

3) Two different settings are used to warm start LISFLOOD if using dates in Settings XML file; or if using steps numbers in Settings XML file

**Option 1 - Using timestamps (dates) with State files:**

CalendarDayStart = any timestamp before or equal to first output timestamp (date) (forecast); it is usually the same as StepStart  (i.e. 2015-01-10 12:00)

StepStart= timestamp of first output (forecast) (i.e. 2015-01-10 12:00)

timestepInit= timestamp of the step just before first model output (forecast) (i.e. 2015-01-10 06:00)

When LISFLOOD is reading "StepStart" and "timestepInit" as timestamps, CalendarDayStart is not used to set model start (forecast) or to set the state values to be used to warm start LISFLOOD model, so any date can be used. CalendarDayStart date must be equal to "StepStart" date or precedent. CalendarDayStart date will be used as time_unit in NetCDF files.

If "CalendarDayStart" is set to 2015-01-10 12:00 and "StepStart" is set to 2015-01-10 12:00, the first output of the model will be marked 2015-01-10 12:00 and all netCDF state files will be stored using CalendarDayStart as time_unit with "time" array starting with [0].

To warm start LISFLOOD for a 6-hourly simulation with first output on  2015-01-10 12:00, state variables values for 2015-01-10 06:00 must be used to initialize the model, so  "timestepInit" must be set to 2015-01-10 06:00.

**Option 2 - Using timesteps (step numbers) with State files:**

CalendarDayStart = timestamp of first model output (forecast)

StepStart=1

timestepInit=0

Step numbers in LISFLOOD are always referred to "CalendarDayStart". If "CalendarDayStart" is 2015-01-10 12:00 and "StepStart" is 1, this means that the first output of the model will be at 2015-01-10 12:00 and all netCDF state files will be now stored using "hours since 2015-01-10 12:00" as time_unit and "time" array starting with [0]. The first step in NetCDF state files stored by this run, will be the same as CalendarDayStart, 2015-01-10 12:00.

To warm start LISFLOOD for a 6-hourly simulation with first output on  2015-01-10 12:00 (step #1), state variables values for 2015-01-10 06:00 must be used to initialize the model, so "timestepInit" must be set to 0.

> NOTE: If State files are used to initialize LISFLOOD model run, LISFLOOD will automatically use timestamps in NetCDF files to get data for "timestepInit". If End files are used, LISFLOOD will automatically assign data from NetCDF to "timestepInit".
