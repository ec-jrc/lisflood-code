# Testing LISFLOOD developments

In this document we report details about all kind of tests we execute during development cycles.

## Unit tests

In [tests/](https://github.com/ec-jrc/lisflood-code/tree/master/tests) folder of lisflood-code repository there are several unit 
tests ensuring that all *helper components* of Lisflood work as expected. 
These components are not strictly related to the hydrological model but are essential for the execution.

Unit tests are executed mocking I/O, to keep them reasonably fast.

Please note that in same folder there are other tests that actually test the model in a black-box fashion. 
These tests are much slower as they execute lisflood for longer periods and write on disk results (TSS and netCDF maps) which are compared to a *test oracle dataset*.
See the dedicated paragraph on this page for more details.

Static data and fixtures (i.e. static maps and meteo forcings) comes from two catchments. They are netCDF files cut in space (catchment area) and time (year 2000).

In tests where values comparison are needed, we use [lisfloodutilities.compare](https://github.com/ec-jrc/lisflood-utilities/blob/master/src/lisfloodutilities/compare/__init__.py) 
helper classes (NetCDFComparator, TSSComparator).

### Testing Options
In LF, you activate/deactivate a hydrological module by setting 1/0 in *lfoptions* section of the input XML settings file.
  
This test ensures that all modules are called/not called when activated/not activated. 
The following table summarize the matrix of combinations of options we test:

| **setoption**     | **BASIC** | **SPLIT ROUTING ONLY** | **RESERVOIRS ONLY** | **LAKES ONLY** | **RICE ONLY** | **WATER ABSTRACTION ONLY** | **PF ONLY** | **FULL** |
| ----------------- | --------- | ---------------------- | ------------------- | -------------- | ------------- | -------------------------- | ----------- | -------- |
| groundwaterSmooth | 0         | 0                      | 0                   | 0              | 0             | 1                          | 0           | 1        |
| wateruse          | 0         | 0                      | 0                   | 0              | 0             | 1                          | 0           | 1        |
| TransientWaterDemandChange | 0| 0                      | 0                   | 0              | 0             | 1                          | 0           | 1        |
| wateruseRegion    | 0         | 0                      | 0                   | 0              | 0             | 1                          | 0           | 1        |
| drainedIrrigation | 0         | 0                      | 0                   | 0              | 0             | 0                          | 0           | 1        |
| riceIrrigation    | 0         | 0                      | 0                   | 0              | 1             | 0                          | 0           | 1        |
| openwaterevapo    | 0         | 0                      | 0                   | 0              | 0             | 0                          | 0           | 1        |
| simulateLakes     | 0         | 0                      | 0                   | 1              | 0             | 0                          | 0           | 1        |
| simulateReservoirs| 0         | 0                      | 1                   | 0              | 0             | 0                          | 0           | 1        |
| simulatePF        | 0         | 0                      | 0                   | 0              | 0             | 0                          | 1           | 1        |
| SplitRouting      | 0         | 1                      | 0                   | 0              | 0             | 0                          | 0           | 1        |
   
#### Implementation

[test_options.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_options.py)

We define a test for each combination from the table above then we check that a particular function inside the module is called with expected arguments. 
We use a mocked `loadmap` function (the function that LF uses to load netCDF or PCRaster maps) and check that it's called/not called as expected by the module under test.

**Example: test_rice_only**
Only option *riceIrrigation* is set, then we mock function *loadmap* imported from rice.py and other modules.

* Test asserts that loadmap is never called from other modules (e.g. reservoir).
* Test asserts that loadmap is called with following arguments from riceirrigation module:

```python
from unittest.mock import call
import lisflood
...
...
def test_rice_only(self):
    ...
    calls = [call('RiceFlooding'), call('RicePercolation'), call('RicePlantingDay1'), call('RiceHarvestDay1'), call('RicePlantingDay2'), call('RiceHarvestDay2')]
    lisflood.hydrological_modules.riceirrigation.loadmap.assert_has_calls(calls)
    assert not lisflood.hydrological_modules.reservoir.loadmap.called
    ...
```

### Testing state maps and end maps
Make sure that LISFLOOD prints state maps and end maps. Last step in state maps must be identical to the only step in end maps.

#### Implementation
[test_state_end_maps.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_state_end_maps.py)

* test_no_reported - assert that no .nc and .tss files are being written when no report options are set
* test_end_reported - assert that only End Maps are reported when 'repEndMaps' is activated
* test_state_reported - assert that only State Maps are reported when 'repStateMaps' is activated
* test_end_state_reported - assert that State Maps and End Maps are reported and that last timestep values in State Maps are equal to the values in End Maps. 


### Testing reporting maps
Make sure that LISFLOOD prints maps when reporting options are active.
In LF, you activate/deactivate report maps/tss options by setting 1/0 in *lfoptions* section of the input XML settings file.

| **setoption**         |
| --------------------- |
| repDischargeMaps      |
| repsimulateLakes      |
| repsimulateReservoirs |
| repSnowMaps           |
| repPFMaps             |
| repLZMaps             |
| repUZMaps             |
| repGwPercUZLZMaps     |
| repTotalAbs           |
| repTotalWUse          |
| repWIndex             |

#### Implementation
[test_reported_maps.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_reported_maps.py)

In order to test that a specific map is written when a report map option is activated, 
we mock the ```lisflood.global_modules.output.writenet``` (the function LF uses to write netCDF maps) and assert that 
it was called with expected arguments.

**Example: test_rep_snowmaps**
Activate repSnowMaps and repStateMaps and assert that writenet function was called with argument 'SnowMaps'.

*Note: the actual code asserting writenet calls is in TestSettings._reported_map method.*

```python
def test_rep_snowmaps(self):
        self._reported_map(self.settings_file, opts_to_set=['repSnowMaps', 'repStateMaps'],
                           map_to_check='SnowMaps')
```


### Testing reporting timeseries (TSS files)
Make sure that LISFLOOD prints TSS files when reporting options are active.

| **setoption**     |
| ------------------|
| repDischargeTs    |
| repStateUpsGauges |
| repRateUpsGauges  |
| repMeteoUpsGauges |

#### Implementation
[test_reported_tss.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_reported_tss.py)

In order to test that a specific TSS is written when a report tss option is activated, 
we mock the ```lisflood.global_modules.output.TimeoutputTimeseries``` (the PCRaster framework class that LF uses to write TSS files)
 and assert that it was initiliazed with expected arguments.

**Example: test_rep_dischargetss**
Activate repDischargeTs and assert that a TimeoutputTimeseries object was initialized with the TSS filename 'disWin.tss' (as defined in XML settings file used for this test).

*Note: the actual code asserting TimeoutputTimeseries calls is in TestSettings._reported_tss method.*

```python
def test_rep_dischargetss(self):
        self._reported_tss(self.settings_files['full'],
                           opts_to_set=['repDischargeTs'],
                           tss_to_check='disWin.tss')
```

### Testing Init run
Make sure LISFLOOD can run an initial run to generate AVGDIS and LZAVIN maps with proper extension (.nc or .map)

#### Implementation
*Note*: the test was moved to [test_reported_maps.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_reported_maps.py).

Test asserts that writenet was called with 'AvgDis' and 'LZAvInflowMap' arguments (LF variables for avgdis.nc and lzavin.nc files) and with the correct filename.
 

```python
def test_prerun(self):
  self._reported_map(self.settings_files['initrun'], 
    map_to_check=['AvgDis', 'LZAvInflowMap'],
    files_to_check=['avgdis.nc', 'lzavin.nc'])

```

### Testing StepStart and StepEnd variables
To define start and end simulation timesteps in LF you may use date time notation (21/12/2000 06:00) or integer timesteps (e.g. 215, calculated from CalendarDayStart using DtSec steps).
We need to ensure that either using dates or integers for StepStart and StepEnd gives equivalent setups.

Tests are done with daily and 6hourly timesteps (i.e. DtSec=86400 and DtSec=21600).

#### Implementation
[test_dates_steps.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_dates_steps.py)

Execute lisflood with report options activated, using dates formats for StepStart and StepEnd and a daily timestep. 
Then execute lisflood with same setup, this time using integers for StepStart and StepEnd.
**Assert that results are identical.**

Test is repeated for 6hourly timesteps.

**Example: test_dates_steps_day**

```python
import datetime

from lisfloodutilities.compare import NetCDFComparator

from lisflood.global_modules.settings import MaskInfo
from lisflood.main import lisfloodexe

...
...

def test_dates_steps_day(self):
    settings_a = self.setoptions(self.settings_files['full'],
                                 opts_to_set=['repStateMaps', 'repEndMaps', 'repDischargeMaps',
                                              'repSnowMaps', 'repLZMaps', 'repUZMaps'],
                                 vars_to_set={'StepStart': '30/07/2000 06:00', 'StepEnd': '01/08/2000 06:00',
                                              'PathOut': '$(PathRoot)/out/1'}
                                 )
    # execute with dates
    lisfloodexe(settings_a)
    
    settings_b = self.setoptions(self.settings_files['full'],
                                 opts_to_set=['repStateMaps', 'repEndMaps', 'repDischargeMaps',
                                              'repSnowMaps', 'repLZMaps', 'repUZMaps'],
                                 vars_to_set={'StepStart': 213, 'StepEnd': 215,
                                              'PathOut': '$(PathRoot)/out/2'})
    # execute with integer steps
    lisfloodexe(settings_b)

    assert settings_a.step_start_int == 213
    assert settings_a.step_end_int == 215
    assert settings_b.step_start_dt == datetime.datetime(2000, 7, 30, 6, 0)
    assert settings_b.step_end_dt == datetime.datetime(2000, 8, 1, 6, 0)

    maskinfo = MaskInfo.instance()
    comparator = NetCDFComparator(maskinfo.info.mask)
    out_a = settings_a.output_dir
    out_b = settings_b.output_dir
    # assert results are equal
    comparator.compare_dirs(out_a, out_b)
```

## Other LF tests included in repository

There are other tests included in [tests/](https://github.com/ec-jrc/lisflood-code/tree/master/tests) 
folder of repository that can't be defined as unit tests. 
These tests execute the development version of lisflood with some predefined XML settings, 
and asserts that results are equal to a reference dataset (test oracle data in black-box terminology). 

Comparison between values `a` from current results A and values `b` from reference dataset B is made by comparing numpy arrays `a` and `b`
 with `atol=0.0001` and `rtol=0.001`, giving *relative tolerance = `rtol * b`* and *absolute tolerance = `atol`.*

In order to reduce dataset size, we use a test catchment (same as [LF_ETRS89_UseCase](https://github.com/ec-jrc/lisflood-usecases/tree/master/LF_ETRS89_UseCase)) with static data and meteo netCDF 
inputs that are cut in domain and time (only year 2000 is included).

**Note:** this kind of tests fail when the hydrological model is changed between reference version and current version under test.

### Testing LF Results
These tests do short execution (6months) of lisflood on the test catchment clipped from the full setup (EFAS).	
Assert that results of version under test are equal to test oracle.

|Test case      | DtSec | Simulation period                  | Files to compare              |
|---------------|-------|------------------------------------|-------------------------------|
|INIT daily     | 86400 |31/12/1999 06:00 - 06/01/2001 06:00 | avgdis.nc, lzavin.nc          |
|INIT 6h        | 21600 |31/12/1999 06:00 - 06/01/2001 06:00 | avgdis.nc, lzavin.nc          |
|RUN daily      | 86400 |02/01/2000 06:00 - 02/07/2000 06:00 | dis.nc, dis.tss, chanQWin.tss |
|RUN 6h         | 21600 |02/01/2000 06:00 - 02/07/2000 06:00 | dis.nc, dis.tss, chanQWin.tss |

All test cases are executed with following modules activated:

| Activated modules         |
|---------------------------|
|SplitRouting               |
|simulateReservoirs         |
|groundwaterSmooth          |
|TransientWaterDemandChange |
|drainedIrrigation          |
|openwaterevapo             |
|useWaterDemandAveYear      |
|riceIrrigation             |
|indicator                  |

#### Implementation
[test_results.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_results.py)

* test_dis_daily - execute lisflood with base.xml settings and assert that dis.nc, dis.tss and chanqWin.tss are equal to the reference
* test_dis_6h - execute lisflood with base.xml settings and assert that dis.nc, dis.tss and chanqWin.tss are equal to the reference (6hourly run)
* test_init_daily - execute lisflood with prerun.xml settings and assert that avgdis.nc and lzavin.nc are equal to the reference
* test_init_6h - execute lisflood with prerun.xml settings and assert that avgdis.nc and lzavin.nc are equal to the reference (6hourly run)
* test_initvars - assert that end maps (i.e. init state maps for a warm start) are produced in folder specified by `PathOut` option as defined in XML settings file.

|Initial state files checked by **test_initvars**|
|------------------------------------------------|
|ch2cr.end.nc, chcro.end.nc, chside.end.nc, cseal.end.nc, cum.end.nc, cumf.end.nc, cumi.end.nc, dis.end.nc, dslf.end.nc, dsli.end.nc, dslr.end.nc, frost.end.nc, lz.end.nc, rsfil.end.nc, scova.end.nc, scovb.end.nc, scovc.end.nc, tha.end.nc, thb.end.nc, thc.end.nc, thfa.end.nc, thfb.end.nc, thfc.end.nc, thia.end.nc, thib.end.nc,thic.end.nc, uz.end.nc, uzf.end.nc, uzi.end.nc, wdept.end.nc|

### Testing Warm start
Test ensures that a long cold run is equivalent to an initial cold start + repeated warm starts.
It's a regression test as it was introduced along with warmstart fixes and checks that the inconsistency between cold and warm runs won't be reintroduced.

* run continuously for a long period (at least 6 months) and save output in a folder
* run on the same period but restarting LISFLOOD at every step (start and stop)
* Compare all state maps from continuous run with state maps from each warm start execution. Maps must be identical at the timestep of the warm run. 
* Test must be performed with daily and 6-hourly steps.

|Test case       | DtSec | Simulation period                  | Files to compare              |
|----------------|-------|------------------------------------|-------------------------------|
|warmstart daily | 86400 |02/01/2000 06:00 - 30/12/2000 06:00 | all produced files (.nc,.tss) |
|warmstart 6h    | 21600 |01/03/2000 06:00 - 31/07/2000 06:00 | all produced files (.nc,.tss) |

All test cases are executed with following modules activated:

| Activated modules         |
|---------------------------|
|SplitRouting               |
|groundwaterSmooth          |
|TransientWaterDemandChange |
|drainedIrrigation          |
|openwaterevapo             |
|riceIrrigation             |
|indicator                  |

**Note:** Due the current implementation of the reservoir module (and its calibration methods), this test fails on certain domains having reservoirs with particular attributes.   
**Note:** This test doesn't use a reference dataset so it's not a black-box test. It ensures that cold and warm runs are equivalent.

#### Implementation
[test_warmstart.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_warmstart.py)

To illustrate implementation of this test we take test_warmstart_daily as example. test_warmstart_6h is similar but with a shorter simulation period and DtSec=21600.
1. Execute an initialization run for year 2000 and save avgdis.nc and lzavin.nc outputs in a folder.
```python
settings_prerun = self.setoptions(self.settings_files['prerun'], opts_to_unset=modules_to_unset,
                                  vars_to_set={'DtSec': dt_sec,
                                               'PathOut': path_out_init,
                                               'StepStart': step_start,
                                               'StepEnd': step_end})
# ** execute
lisfloodexe(settings_prerun)
```

2. Execute a long run for year 2000 (with cold.xml), using avgdis.nc and lzavin.nc from step 1, and save output in a folder as reference data.
```python
lzavin_path = settings_prerun.binding['LZAvInflowMap']
avgdis_path = settings_prerun.binding['AvgDis']
settings_longrun = self.setoptions(self.settings_files['cold'], 
                                   opts_to_unset=modules_to_unset,
                                   vars_to_set={'StepStart': step_start,
                                                'StepEnd': step_end,
                                                'LZAvInflowMap': lzavin_path,
                                                'PathOut': path_out_reference,
                                                'AvgDis': avgdis_path,
                                                'DtSec': dt_sec})
# ** execute
lisfloodexe(settings_longrun)
```

3. Execute a cold run for the first day of simulation, using avgdis.nc and lzavin.nc from step 1.
```python
settings_coldstart = self.setoptions(self.settings_files['cold'], 
                                     opts_to_unset=modules_to_unset,
                                     vars_to_set={'StepStart': step_start,
                                                  'StepEnd': step_start,
                                                  'LZAvInflowMap': lzavin_path,
                                                  'PathOut': path_out,
                                                  'AvgDis': avgdis_path,
                                                  'DtSec': dt_sec})
# ** execute
lisfloodexe(settings_coldstart)
```

4. Execute a warm start for each subsequent day of the simulation period, using output of the previous run (the first cold run or the previous warm run) as init state variables.
```python
# warm run (2. single step warm start/stop with initial conditions from previous run)
prev_settings = settings_coldstart
warm_step_start = prev_settings.step_end_dt + timedelta(seconds=dt_sec)
warm_step_end = warm_step_start
timestep_init = prev_settings.step_end_dt.strftime('%d/%m/%Y %H:%M')
maskinfo = MaskInfo.instance()
nc_comparator = NetCDFComparator(maskinfo.info.mask)
tss_comparator = TSSComparator(array_equal=True)
while warm_step_start <= step_end_dt:
    path_init = prev_settings.output_dir

    settings_warmstart = self.setoptions(
                            self.settings_files['warm'], 
                            opts_to_unset=modules_to_unset,
                            vars_to_set={
                                'StepStart': warm_step_start.strftime('%d/%m/%Y %H:%M'),
                                'StepEnd': warm_step_end.strftime('%d/%m/%Y %H:%M'),
                                'LZAvInflowMap': lzavin_path,
                                'PathOut': path_out,
                                'PathInit': path_init,
                                'timestepInit': timestep_init,
                                'AvgDis': avgdis_path,
                                'ReportSteps': report_steps,
                                'DtSec': dt_sec}
                        )
    # ** execute
    lisfloodexe(settings_warmstart)
```

5. At the end of each warm run, compare current warm run output with values from long run, at the specific timestep. Values must be equal.
```python
# ****** compare *******
timestep_dt = settings_warmstart.step_end_dt  # NetCDFComparator takes datetime.datetime as timestep
timestep = settings_warmstart.step_end_int
nc_comparator.compare_dirs(path_out, path_out_reference, timestep=timestep_dt)
tss_comparator.compare_dirs(path_out, path_out_reference, timestep=timestep)
```

**Note**: test doesn't check results at each warm run output but only every <num> of steps in order to speed up a bit.

## Release test for EFAS and GloFAS

At each release, in addition to pass all tests described above, LISFLOOD is tested also with full domains of EFAS and GLOFAS.
These tests are executed by internal LF developers before a new release is officially published.


[🔝](#top)