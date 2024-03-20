# Testing OSLisflood developments

In this document we report details about all kind of tests we execute during development cycles.

## Introduction

In [tests/](https://github.com/ec-jrc/lisflood-code/tree/master/tests){:target="_blank"} folder of lisflood-code repository there are several unit 
tests ensuring that all *helper components* of Lisflood work as expected. 
These components are not strictly related to the hydrological model but are essential for the execution.

Most of unit tests are executed mocking I/O, to keep them reasonably fast.

Please note that in same folder there are other tests that actually test the model in a black-box fashion. 
These tests are much slower as they execute lisflood for longer periods and write results on disk (TSS and netCDF maps) which are then compared 

- to a *test oracle dataset*, 
- or to results from another simulation (executed in the same test) with different parameters but same expected values. 

See the dedicated paragraph on this page for more details.

Static data and fixtures (i.e. static maps and meteo forcings) comes from two catchments. 
They are netCDF files reduced in space (Po catchment area) and time (6 hourly data from 2015-12-10 12:00 to 2017-12-29 12:00) from original EFAS dataset.

In tests where values comparison are needed, we use [lisfloodutilities.compare](https://github.com/ec-jrc/lisflood-utilities/blob/master/src/lisfloodutilities/compare/__init__.py){:target="_blank"} 
helper classes (NetCDFComparator, TSSComparator).

These classes compare netCDF and TSSs values between two dataset of OSLisflood results, using `atol=0.0001` and `rtol=0.001` (defaults values in NetCDFComparator and TSSComparator). 
See [`numpy.allclose`](https://numpy.org/doc/stable/reference/generated/numpy.allclose.html){:target="_blank"} for more details. 

Some tests use `array_equal` option in order to compare values using [`numpy.array_equal`](https://numpy.org/doc/stable/reference/generated/numpy.array_equal.html){:target="_blank"} function.

Tests that are using Comparator classes are:

| Test name                |    File                  | Usage and tolerences                                                              |
|--------------------------|--------------------------|-----------------------------------------------------------------------------------|
| test_dates_steps_day     | test_dates_steps.py      | NetCDFComparator(array_equal=True)                                                |
| test_dates_steps_6h      | test_dates_steps.py      | NetCDFComparator(array_equal=True)                                                |
| test_end_state_reported  | test_state_end_maps.py   | NetCDFComparator(array_equal=True)                                                |
| test_dis_daily           | test_results.py          | NetCDFComparator(atol=0.0001, rtol=0.001), TSSComparator(atol=0.0001, rtol=0.001) |
| test_dis_6h              | test_results.py          | NetCDFComparator(atol=0.0001, rtol=0.001), TSSComparator(atol=0.0001, rtol=0.001) |
| test_init_daily          | test_results.py          | NetCDFComparator(atol=0.0001, rtol=0.001), TSSComparator(atol=0.0001, rtol=0.001) |
| test_init_6h             | test_results.py          | NetCDFComparator(atol=0.0001, rtol=0.001), TSSComparator(atol=0.0001, rtol=0.001) |
| test_warmstart_daily     | test_warmstart.py        | NetCDFComparator(atol=0.0001, rtol=0.001), TSSComparator(array_equal=True)        |
| test_warmstart_6h        | test_warmstart.py        | NetCDFComparator(atol=0.0001, rtol=0.001), TSSComparator(array_equal=True)        |
| test_subcacthment_daily  | test_subcatchments.py    | NetCDFComparator(array_equal=True)                                                |
| test_subcacthment_6h     | test_subcatchments.py    | NetCDFComparator(array_equal=True)                                                |
| test_reported_steps      | test_reported_steps.py   | NetCDFComparator(array_equal=True)                                                |
| test_waterabstraction_24h| test_water_abstraction.py| NetCDFComparator(array_equal=True)                                                |
| test_waterabstraction_6h | test_water_abstraction.py| NetCDFComparator(array_equal=True)                                                |


## How to execute tests

In order to execute tests decribed in this page, you need to download source code and create a conda environment for OSLisflood.

Then, from project folder, run

```bash
pytest tests/
```

As defined in pytest.ini, this is equivalent to

```bash
pytest tests/ -ra -x -l --cov=lisflood --cov-config=.coveragerc -m "not slow" -vv
```

This will skip all tests marked as slow (which can run for 30 mins/1 hour).
To execute slow tests simply run:

```bash
pytest tests/ -m "slow"
```

### Output sample of pytest execution

<details><summary>Toggle</summary>

<div markdown="1">

```text

(lisflood) [master]user@Enki:~/projects/lisflood-code $ pytest tests/
================================ test session starts ================================
platform linux -- Python 3.7.8, pytest-5.2.1, py-1.8.0, pluggy-0.13.0
cachedir: .pytest_cache
rootdir: /home/user/projects/lisflood-code, inifile: pytest.ini
plugins: env-0.6.2, cov-2.8.1, mock-2.0.0

tests/test_dates_steps.py::TestStepsDates::test_dates_steps_daily PASSED                 [  2%]
tests/test_dates_steps.py::TestStepsDates::test_dates_steps_6h PASSED                    [  4%]
tests/test_options.py::TestOptions::test_basic PASSED                                    [  6%]
tests/test_options.py::TestOptions::test_split_routing_only PASSED                       [  8%]
tests/test_options.py::TestOptions::test_reservoirs_only PASSED                          [ 11%]
tests/test_options.py::TestOptions::test_lakes_only PASSED                               [ 13%]
tests/test_options.py::TestOptions::test_rice_only PASSED                                [ 15%]
tests/test_options.py::TestOptions::test_pf_only PASSED                                  [ 17%]
tests/test_options.py::TestOptions::test_waterabstraction_only PASSED                    [ 20%]
tests/test_options.py::TestWrongTimestepInit::test_raisexc PASSED                        [ 22%]
tests/test_reported_maps.py::TestReportedMaps::test_prerun PASSED                        [ 24%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_dischargemaps PASSED             [ 26%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_dischargemaps_not_called PASSED  [ 28%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_lakes PASSED                     [ 31%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_lakes_not_called PASSED          [ 33%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_reservoirs PASSED                [ 35%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_reservoirs_not_called PASSED     [ 37%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_snowmaps PASSED                  [ 40%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_snowmaps_not_called PASSED       [ 42%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_pfmaps PASSED                    [ 44%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_pfmaps_not_called PASSED         [ 46%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_lzmaps PASSED                    [ 48%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_lzmaps_not_called PASSED         [ 51%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_uzmaps PASSED                    [ 53%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_uzmaps_not_called PASSED         [ 55%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_gwpercuzlzmaps PASSED            [ 57%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_gwpercuzlzmaps_not_called PASSED [ 60%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_totalabs PASSED                  [ 62%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_totalabs_not_called PASSED       [ 64%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_totalwuse PASSED                 [ 66%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_totalwuse_not_called PASSED      [ 68%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_windex PASSED                    [ 71%]
tests/test_reported_maps.py::TestReportedMaps::test_rep_windex_not_called PASSED         [ 73%]
tests/test_reported_tss.py::TestReportedTSS::test_rep_dischargetss PASSED                [ 75%]
tests/test_reported_tss.py::TestReportedTSS::test_rep_dischargetss_not_called PASSED     [ 77%]
tests/test_reported_tss.py::TestReportedTSS::test_rep_stateupgaugestss PASSED            [ 80%]
tests/test_reported_tss.py::TestReportedTSS::test_rep_stateupgaugestss_not_called PASSED [ 82%]
tests/test_reported_tss.py::TestReportedTSS::test_rep_rateupgaugestss PASSED             [ 84%]
tests/test_reported_tss.py::TestReportedTSS::test_rep_rateupgaugestss_not_called PASSED  [ 86%]
tests/test_reported_tss.py::TestReportedTSS::test_rep_meteoupgaugestss PASSED            [ 88%]
tests/test_reported_tss.py::TestReportedTSS::test_rep_meteoupgaugestss_not_called PASSED [ 91%]
tests/test_state_end_maps.py::TestRepMaps::test_no_reported PASSED                       [ 93%]
tests/test_state_end_maps.py::TestRepMaps::test_end_reported PASSED                      [ 95%]
tests/test_state_end_maps.py::TestRepMaps::test_state_reported PASSED                    [ 97%]
tests/test_state_end_maps.py::TestRepMaps::test_end_state_reported PASSED                [100%]

----------- coverage: platform linux, python 3.7.8-final-0 -----------
Name                                                           Stmts   Miss  Cover
----------------------------------------------------------------------------------
src/lisflood/Lisflood_EnKF.py                                     21     12    43%
src/lisflood/Lisflood_dynamic.py                                  89     16    82%
src/lisflood/Lisflood_initial.py                                 108      8    93%
src/lisflood/Lisflood_monteCarlo.py                               11      4    64%
src/lisflood/__init__.py                                          13      1    92%
src/lisflood/global_modules/__init__.py                            0      0   100%
src/lisflood/global_modules/add1.py                              634    261    59%
src/lisflood/global_modules/checkers.py                           36     21    42%
src/lisflood/global_modules/decorators.py                         16      9    44%
src/lisflood/global_modules/default_options.py                     4      0   100%
src/lisflood/global_modules/errors.py                             26      7    73%
src/lisflood/global_modules/output.py                            190     59    69%
src/lisflood/global_modules/settings.py                          395     64    84%
src/lisflood/global_modules/stateVar.py                           93     79    15%
src/lisflood/global_modules/zusatz.py                            237    172    27%
src/lisflood/hydrological_modules/__init__.py                     42     31    26%
src/lisflood/hydrological_modules/evapowater.py                   72     24    67%
src/lisflood/hydrological_modules/frost.py                        18      0   100%
src/lisflood/hydrological_modules/groundwater.py                  54      3    94%
src/lisflood/hydrological_modules/indicatorcalc.py               106      4    96%
src/lisflood/hydrological_modules/inflow.py                       58     28    52%
src/lisflood/hydrological_modules/kinematic_wave_parallel.py     105      9    91%
src/lisflood/hydrological_modules/lakes.py                       120     14    88%
src/lisflood/hydrological_modules/landusechange.py                28      7    75%
src/lisflood/hydrological_modules/leafarea.py                     35      0   100%
src/lisflood/hydrological_modules/miscInitial.py                  94     10    89%
src/lisflood/hydrological_modules/opensealed.py                   20      0   100%
src/lisflood/hydrological_modules/polder.py                       25      6    76%
src/lisflood/hydrological_modules/readmeteo.py                    30      5    83%
src/lisflood/hydrological_modules/reservoir.py                   128      5    96%
src/lisflood/hydrological_modules/riceirrigation.py               49      0   100%
src/lisflood/hydrological_modules/routing.py                     178      8    96%
src/lisflood/hydrological_modules/snow.py                         63      0   100%
src/lisflood/hydrological_modules/soil.py                        177      0   100%
src/lisflood/hydrological_modules/soilloop.py                    172      3    98%
src/lisflood/hydrological_modules/structures.py                   15      0   100%
src/lisflood/hydrological_modules/surface_routing.py              64      0   100%
src/lisflood/hydrological_modules/transmission.py                 29     11    62%
src/lisflood/hydrological_modules/waterabstraction.py            230     16    93%
src/lisflood/hydrological_modules/waterbalance.py                 77     62    19%
src/lisflood/hydrological_modules/waterlevel.py                   27      9    67%
src/lisflood/hydrological_modules/wateruse.py                      8      3    62%
src/lisflood/main.py                                              88     37    58%
----------------------------------------------------------------------------------
TOTAL                                                           3985   1008    75%


============ 45 passed, 10 deselected in 90.49s (0:01:30) ============

```

</div>
</details>

## Unit Tests

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

[test_options.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_options.py){:target="_blank"}

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
Make sure that OSLisflood prints state maps and end maps. Last step in state maps must be identical to the only step in end maps.

#### Implementation

[test_state_end_maps.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_state_end_maps.py){:target="_blank"}


|Test case                | Expected                                                                                                                                     |
|-------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| test_no_reported        | no .nc and .tss files are being written when no report options are setno .nc and .tss files are being written when no report options are set |
| test_end_reported       | only End Maps are reported when 'repEndMaps' is activated                                                                                    |
| test_state_reported     | only State Maps are reported when 'repStateMaps' is activated                                                                                |
| test_end_state_reported | State Maps and End Maps are reported and that last timestep values in State Maps are array equal to the values in End Maps                   |


### Testing reporting maps
Make sure that OSLisflood prints maps when reporting options are active.
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
[test_reported_maps.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_reported_maps.py){:target="_blank"}

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
Make sure that OSLisflood prints TSS files when reporting options are active.

| **setoption**     |
| ------------------|
| repDischargeTs    |
| repStateUpsGauges |
| repRateUpsGauges  |
| repMeteoUpsGauges |

#### Implementation
[test_reported_tss.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_reported_tss.py){:target="_blank"}

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

### Testing reporting steps 
Make sure that OSLisflood prints state files following reporting steps formula in ReportSteps xml option.

#### Implementation
[test_reported_steps.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_reported_steps.py){:target="_blank"}

In order to test that specific files are written when a step matches the ReportSteps formula, we use a test formula 'starttime+10..endtime'.
Then we geterate specific outputs for the desired steps and compare the two output using NetCDFComparator(array_equal=True)

**Example: test_reported_steps**

```python
    def test_reported_steps(self):

        strReportStepA = 'starttime+10..endtime'
        settings_a = setoptions(self.settings_file,
                                vars_to_set={'StepStart': '01/07/2016 00:00', 'StepEnd': '01/08/2016 00:00',
                                             'PathOut': '$(PathRoot)/out/a',
                                             'ReportSteps': strReportStepA, 
                                             })
        mk_path_out(self.out_dir_a)
        lisfloodexe(settings_a)

        int_start, _ = datetoint(settings_a.binding['StepStart'], settings_a.binding)
        int_end, _ = datetoint(settings_a.binding['StepEnd'], settings_a.binding)

        strReportStepB = ''
        for i in range(int_start,int_end,10):
            if strReportStepB != '':
                strReportStepB = strReportStepB + ',' 
            strReportStepB = strReportStepB + str(i)

        settings_b = setoptions(self.settings_file,
                                vars_to_set={'StepStart': '01/07/2016 00:00', 'StepEnd': '01/08/2016 00:00',
                                             'PathOut': '$(PathRoot)/out/b',
                                             'ReportSteps': strReportStepB,
                                             })
        mk_path_out(self.out_dir_b)
        lisfloodexe(settings_b)

        comparator = NetCDFComparator(settings_a.maskpath, array_equal=True)
        comparator.compare_dirs(self.out_dir_b, self.out_dir_a)
        assert not comparator.errors
```


### Testing Init run output maps
Make sure OSLisflood can run an initial run to generate AVGDIS and LZAVIN maps with proper extension (.nc or .map)

#### Implementation
[test_reported_maps.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_reported_maps.py){:target="_blank"}

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

Tests are done with daily and 6-hourly timesteps (i.e. DtSec=86400 and DtSec=21600).

#### Implementation
[test_dates_steps.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_dates_steps.py){:target="_blank"}

Execute lisflood with report options activated, using dates formats for StepStart and StepEnd and a daily timestep. 
Then execute lisflood with same setup, this time using integers for StepStart and StepEnd.
**Assert that results are identical.**

Test is repeated for 6-hourly timesteps. An additional test is done to check dates before year 1970.

**Example: test_dates_steps_daily**

```python
def test_dates_steps_daily(self):
    settings_a = self.setoptions(self.settings_files['full'],
                                 opts_to_set=['repStateMaps', 'repEndMaps', 'repDischargeMaps',
                                              'repSnowMaps', 'repLZMaps', 'repUZMaps'],
                                 vars_to_set={'StepStart': '30/07/2016 06:00', 'StepEnd': '01/08/2016 06:00',
                                              'PathOut': '$(PathRoot)/out/1'}
                                 )
    mk_path_out('data/LF_ETRS89_UseCase/out/1')
    lisfloodexe(settings_a)
    settings_b = self.setoptions(self.settings_files['full'],
                                 opts_to_set=['repStateMaps', 'repEndMaps', 'repDischargeMaps',
                                              'repSnowMaps', 'repLZMaps', 'repUZMaps'],
                                 vars_to_set={'StepStart': 6057, 'StepEnd': 6059,
                                              'PathOut': '$(PathRoot)/out/2'})
    mk_path_out('data/LF_ETRS89_UseCase/out/2')

    lisfloodexe(settings_b)

    assert settings_a.step_start_int == 6057
    assert settings_a.step_end_int == 6059
    assert settings_a.step_start == settings_a.step_start_dt.strftime('%d/%m/%Y %H:%M')
    assert settings_a.step_end == settings_a.step_end_dt.strftime('%d/%m/%Y %H:%M')
    assert settings_b.step_start_dt == datetime.datetime(2016, 7, 30, 6, 0)
    assert settings_b.step_end_dt == datetime.datetime(2016, 8, 1, 6, 0)

    comparator = NetCDFComparator(settings_a.maskpath)
    out_a = settings_a.output_dir
    out_b = settings_b.output_dir
    comparator.compare_dirs(out_a, out_b)
```

### Testing Water Abstraction
The test verifies the use of the correct (closest, antecedent timestamp, and closest, antecedent day of the year) water demand information, unsing the following options:
TransientWaterDemandChange = this option allows to read water demand information from a netcdf stack which includes simulation start and end dates. The water demand information for the closest, antecedent timestamp (dd/mm/yyyy) to the modelled time step is used in the computations.
UseWaterDemandAveYear = this option allows to read water demand information from a netcdf stack with a single year temporal coverage. The water demand information for the closest, antecedent day of the year (dd/mm) to the modelled time step is used in the computations.
For more information please refer to [Water use - LISFLOOD (ec-jrc.github.io)](https://ec-jrc.github.io/lisflood-model/2_18_stdLISFLOOD_water-use/)

#### Implementation
[test_water_abstraction.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_water_abstraction.py){:target="_blank"}
The test uses two datasets: waterdemand19902019, that includes daily data from 1990 to 2019, and waterdemand, that includes only one year used as reference for any year.
Test asserts that output generated using TransientWaterDemandChange with useWaterDemandAveYear flag active using the reference dataset included into the waterdemand folder is the same of the one generated disabling useWaterDemandAveYear flag and using the waterdemand19902019 folder.
 

```python
    def run_lisflood_waterabstraction(self, dt_sec):
        
        settings_a = setoptions(self.settings_file,
                                opts_to_set=('TransientWaterDemandChange', 'useWaterDemandAveYear'),
                                vars_to_set={'StepStart': '30/07/2016 00:00', 'StepEnd': '01/08/2016 00:00',
                                             'DtSec': dt_sec, 'PathOut': '$(PathRoot)/out/a',
                                             'PathWaterUse': '$(PathRoot)/maps/waterdemand'
                                             })
        mk_path_out(self.out_dir_a)
        lisfloodexe(settings_a)

        settings_b = setoptions(self.settings_file,
                                opts_to_set=('TransientWaterDemandChange'),
                                opts_to_unset=('useWaterDemandAveYear'),
                                vars_to_set={'StepStart': '30/07/2016 00:00', 'StepEnd': '01/08/2016 00:00',
                                             'DtSec': dt_sec, 'PathOut': '$(PathRoot)/out/b',
                                             'PathWaterUse': '$(PathRoot)/maps/waterdemand19902019'})
        mk_path_out(self.out_dir_b)
        lisfloodexe(settings_b)

        comparator = NetCDFComparator(settings_a.maskpath, array_equal=True)
        comparator.compare_dirs(self.out_dir_b, self.out_dir_a)

```

## Other LF tests included in repository

There are other tests included in [tests/](https://github.com/ec-jrc/lisflood-code/tree/master/tests){:target="_blank"}.
folder of repository that can't be defined as unit tests. 

These tests execute the development version of lisflood with some predefined XML settings, 
and asserts that results are equal to a reference dataset (test oracle data in black-box terminology). 

In order to reduce dataset size, we use a test catchment (same as [LF_ETRS89_UseCase](https://github.com/ec-jrc/lisflood-usecases/tree/master/LF_ETRS89_UseCase){:target="_blank"}) 
with static data clipped from EFAS domain. Meteo netCDF forcings are also cut from domain and contain 6 hourly data from 2015-12-10 12:00 to 2017-12-29 12:00. 

**Note:** These tests fail when hydrological model is changed between reference version and current version under test.

### Testing LF Results

These tests do short execution (max 1 year) of lisflood on the Po test catchment clipped from the full setup (EFAS) 
and assert that results are within defined tolerances if compared with test oracle.

All test cases are executed with following modules activated:

| Activated modules         |
|---------------------------|
|SplitRouting               |
|simulateReservoirs         |
|groundwaterSmooth          |
|drainedIrrigation          |
|openwaterevapo             |
|riceIrrigation             |
|indicator                  |

#### Implementation

[test_results.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_results.py){:target="_blank"}


|Test case            | DtSec | Simulation period                  | Expected                                                     |
|---------------------|-------|------------------------------------|--------------------------------------------------------------|
| test_init_daily     | 86400 |31/12/2015 06:00 - 06/01/2017 06:00 | avgdis.nc and lzavin.nc diffs are within tolerances          |
| test_init_6h        | 21600 |31/12/2015 06:00 - 06/01/2017 06:00 | avgdis.nc and lzavin.nc diffs are within tolerances          |
| test_dis_daily      | 86400 |02/01/2016 06:00 - 02/07/2016 06:00 | dis.nc, dis.tss and chanQWin.tss diffs are within tolerances |
| test_dis_6h         | 21600 |02/01/2016 06:00 - 02/07/2016 06:00 | dis.nc, dis.tss and chanQWin.tss diffs are within tolerances |
| test_initvars       | 86400 |02/01/2016 06:00 - 05/02/2016 06:00 | all init files *.end.nc are written in output folder         |


|Initial state files checked by **test_initvars** |
|-------------------------------------------------|
|ch2cr.end.nc, chanq.end.nc, chcro.end.nc, chside.end.nc, cseal.end.nc, cum.end.nc, cumf.end.nc, cumi.end.nc, dslf.end.nc, dsli.end.nc, dslr.end.nc, frost.end.nc, lakeh.end.nc, lakeprevinq.end.nc, lakeprevoutq.end.nc, lz.end.nc,  ofdir.end.nc, offor.end.nc, ofoth.end.nc, rsfil.end.nc, scova.end.nc, scovb.end.nc, scovc.end.nc, tha.end.nc, thb.end.nc, thc.end.nc, thfa.end.nc, thfb.end.nc, thfc.end.nc, thia.end.nc, thib.end.nc,thic.end.nc, uz.end.nc, uzf.end.nc, uzi.end.nc|

### Testing Warm start
Test ensures that a long cold run is equivalent to an initial cold start + repeated warm starts.
It's a regression test as it was introduced along with warmstart fixes and checks that the inconsistency between cold and warm runs won't be reintroduced.

* run continuously for a long period and save output in a folder `reference`
* run on the same period but restarting OSLisflood at every step (start and stop)
* Compare all state maps from `reference` with state maps of each warm start execution. Maps must be identical at the timestep of the warm run. 

|Test case             | DtSec | Simulation period                  | Expected                                       |
|----------------------|-------|------------------------------------|------------------------------------------------|
| test_warmstart_daily | 86400 |02/01/2016 06:00 - 30/12/2016 06:00 | nc diffs are within tolerances, TSSs identical |
| test_warmstart_6h    | 21600 |01/03/2016 06:00 - 31/07/2016 06:00 | nc diffs are within tolerances, TSSs identical |

All test cases are executed with following modules activated:

| Activated modules         |
|---------------------------|
|SplitRouting               |
|groundwaterSmooth          |
|drainedIrrigation          |
|openwaterevapo             |
|riceIrrigation             |
|indicator                  |

**Note:** Due the current implementation of the reservoir module (and its calibration methods), this test could fail on certain domains having reservoirs with particular attributes. In the current test basin (PO basin) the test must be successful with reservoir ON.   
**Note:** This test doesn't use a reference dataset so it's not a black-box test. It ensures that cold and warm runs are equivalent.

#### Implementation
[test_warmstart.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_warmstart.py){:target="_blank"}

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


### Testing Sub Catchments

Run a simulation on entire domain (e.g. Po basin), then run one subcatchment for the same period of time.
Compare all state maps. Results must be identical.

**Important note:** Since water abastraction modules are introducing incongruities in subcatchments, 
we've added a test that assert that values are different between the two identical runs when 
water demand modules are activated (e.g. `wateruse=1` and `groundwatersmooth=1`).  

This test demonstrates that wateruse module introduces incongruities between running the model on subcatchments and on the entire domain.


|Test case                                              | DtSec | Simulation period                  | Expected                       |
|-------------------------------------------------------|-------|------------------------------------|--------------------------------|
| test_subcacthment_daily                               | 86400 |02/01/2016 06:00 - 30/03/2016 06:00 | all netcdf are array equal     |
| test_subcacthment_6h                                  | 21600 |01/03/2016 06:00 - 30/03/2016 06:00 | all netcdf are array equal     |
| test_subcacthment_daily_wateruse_groundwatersmooth_OFF| 86400 |02/01/2016 06:00 - 30/01/2016 06:00 | all netcdf are array equal     |
| test_subcacthment_daily_wateruse_groundwatersmooth_ON | 86400 |02/01/2016 06:00 - 30/01/2016 06:00 | the results are not identical  |

**Note:** This test doesn't use a reference dataset so it's not a black-box test. It ensures that simulations on domain and its subdomains are equivalent.
 

#### Implementation
[test_subcatchments.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_subcatchments.py){:target="_blank"}

```python
settings_files = {
        'cold': os.path.join(os.path.dirname(__file__), 'data/LF_ETRS89_UseCase/settings/cold.xml'),
}
modules_to_unset = [
    'wateruse',
    'useWaterDemandAveYear',
    'wateruseRegion',
    'TransientWaterDemandChange',
]
modules_to_unsetGW= [
    'groundwaterSmooth',
]

def test_subcacthment_daily(self):
    step_start = '02/01/2016 06:00'
    step_end = '30/03/2016 06:00'
    dt_sec = 86400
    report_steps = '3650..4100'
    self.run_subcathmenttest_by_dtsec(dt_sec, step_end, step_start, report_steps=report_steps)

def test_subcacthment_daily_wateruse_groundwatersmooth_ON(self):
    step_start = '02/01/2016 06:00'
    step_end = '30/01/2016 06:00'
    dt_sec = 86400
    report_steps = '3650..4100'
    with pytest.raises(AssertionError) as excinfo:
        self.run_subcathmenttest_by_dtsec(dt_sec, step_end, step_start, report_steps=report_steps, wateruse_on=True, groundwatersmooth_off=False)
    assert 'Arrays are not equal' in str(excinfo.value)

```

The method `run_subcathmenttest_by_dtsec` executes two cold runs of lisflood: one on domain and one on subdomain, and then compare results using subdomain mask.

```python
def run_subcathmenttest_by_dtsec(self, dt_sec, step_end, step_start, report_steps='1..9999', wateruse_on=False):
    modules_to_unset = self.modules_to_unset if not wateruse_on else []
    modules_to_set = self.modules_to_unset if wateruse_on else []
    # long run entire domain
    
    path_out_domain = mk_path_out('data/LF_ETRS89_UseCase/out/longrun_domain{}'.format(dt_sec))
    settings_longrun = self.setoptions(self.settings_files['cold'], opts_to_unset=modules_to_unset,
                                       opts_to_set=modules_to_set,
                                       vars_to_set={'StepStart': step_start,
                                                    'StepEnd': step_end,
                                                    'PathOut': path_out_domain,
                                                    'ReportSteps': report_steps,
                                                    'DtSec': dt_sec})
    # ** execute
    lisfloodexe(settings_longrun)

    # long run entire on subdomain
    path_out_subdomain = mk_path_out('data/LF_ETRS89_UseCase/out/longrun_subdomain{}'.format(dt_sec))
    settings_longrun_subdomain = self.setoptions(self.settings_files['cold'], opts_to_unset=modules_to_unset,
                                                 vars_to_set={'StepStart': step_start,
                                                              'StepEnd': step_end,
                                                              'PathOut': path_out_subdomain,
                                                              'ReportSteps': report_steps,
                                                              'MaskMap': '$(PathRoot)/maps/subcatchment_mask.map',
                                                              'DtSec': dt_sec})
    # ** execute
    lisfloodexe(settings_longrun_subdomain)

    # ****** compare *******
    # compare using the last maskmap (subcatchment_mask.map)
    settings = LisSettings.instance()
    nc_comparator = NetCDFComparator(settings.maskpath, array_equal=True)
    nc_comparator.compare_dirs(path_out_subdomain, path_out_domain)
```

### Testing Inflow

This test verifies the correct functioning of the option inflow. Uses a catchment with a nested sub-catchment, i.e. a catchment with 2 output points, one upstream of the other. After completing a 1 year model run for the full catchment, the upstream output point is used as inflow point to model the sub-catchment. Only discharge files are compared, differences should be <0.001 m<sup>3</sup>/s.

#### Implementation

[test_inflow.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_inflow.py){:target="_blank"}


|Test case            | DtSec | Simulation period                  | Expected                                                     |
|---------------------|-------|------------------------------------|--------------------------------------------------------------|
| test_inflow_daily   | 86400 |02/01/2016 06:00 - 30/01/2016 06:00 | reference dis.tss and new dis.tss are within tolerances      |
| test_inflow_6h      | 21600 |01/03/2016 06:00 - 30/03/2016 06:00 | reference dis.tss and new dis.tss are within tolerances      |

### Testing Reference system

Verifies the correct functioning of the code for projected and geographic coordinate systems

#### Implementation

[test_latlon.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_latlon.py){:target="_blank"}


|Test case            | DtSec | Simulation period                  | Expected                                                     |
|---------------------|-------|------------------------------------|--------------------------------------------------------------|
| test_lat_lon_short  | 86400 |01/01/2016 00:00 - 01/02/2016 00:00 | dis_run.tss and reference dis_short.tss are within tolerances|
| test_lat_lon_long   | 21600 |02/01/1986 00:00 - 01/01/2018 00:00 | dis_run.tss and reference dis_long.tss are within tolerances |


### Testing Caching

Verifies the use of cached files. It compares the output generated and the number of cached files used.

#### Implementation

[test_caching.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_caching.py){:target="_blank"}


|Test case            | DtSec | Simulation period                  | Expected                                                     |
|---------------------|-------|------------------------------------|--------------------------------------------------------------|
| test_caching_24h    | 86400 |30/07/2016 06:00 - 01/08/2016 06:00 | compares output generated with and without cached files      |
| test_caching_6h     | 21600 |30/07/2016 06:00 - 01/08/2016 06:00 | compares output generated with and without cached files      |

### Testing Chunking

Verifies chunking files using NetCDFTimeChunks with values `1`, `10`, `auto` and `-1` 

#### Implementation

[test_chunking.py](https://github.com/ec-jrc/lisflood-code/blob/master/tests/test_chunking.py){:target="_blank"}


|Test case            | DtSec | Simulation period                  | Expected                                                     |
|---------------------|-------|------------------------------------|--------------------------------------------------------------|
| test_chunking_24h   | 86400 |30/07/2016 06:00 - 01/09/2016 06:00 | compares output chunking files with reference files             |
| test_chunking_6h    | 21600 |30/07/2016 06:00 - 01/09/2016 06:00 | compares output chunking files with reference files             |

## Release test for EFAS and GloFAS

At each release, in addition to pass all tests described above, OSLisflood is tested also with full domains of EFAS and GLOFAS.
These tests are executed by internal OSLisflood developers when hydrological model is not changed.


[🔝](#top)
