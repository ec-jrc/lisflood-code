# Step 6: Running LISFLOOD (warm start)

Once you have initiallized LISFLOOD you can launch a "warm start". That means you can use all internal state variables ('end maps') that you have received during the initialization (see Step 5) as the initial conditions for a succeeding simulation. 
This is particularly useful if you are simulating individual flood events on a small time interval (e.g. hourly). For instance, to estimate the initial conditions just before the flood event you can do an initialization also called 'pre-run' on a *daily* time interval for the year before the flood event. Then you  can use the resulting 'end maps' as the initial conditions for the hourly simulation of the flood event.

In any case, you should be aware that values of some **internal state variables of the model** (especially lower zone storage) **are very much dependent on the parameterisation used**. Hence, suppose we have 'end maps' that were created using some parameterisation of the model (let's say parameter set *A*), then these maps should **not** be used as initial conditions for a model run with another parameterisation (parameter set *B*). If you decide to do this anyway, you are likely to encounter serious initialisation problems (but these may not be immediately visible in the output!). If you do this while calibrating the model (i.e. parameter set *B* is the calibration set), this will render the calibration exercise pretty much useless (since the output is the result of a mix of different parameter sets). However, for *FrostIndexInitValue* and *DSLRInitValue* it is perfectly safe to use the 'end maps', since the values of these maps do not depend on any calibration parameters (that is, only if you do not calibrate on any of the frost-related parameters!). If you need to calibrate for individual events (i.e.hourly), you should apply *each* parameterisation on *both * the (daily) pre-run and the 'event' run! This may seem awkward, but there is no way of getting around this (except from avoiding event-based calibration at all, which may be a good idea anyway).

## What you need to do
1. Copy the output maps of the initialisation run (found in folder "out") into the folder "init"

2. Replace in the LISFLOOD settings file the 'bogus' values of -9999 for *LZAvInflowMap* and *AvgDis* with the actual map: 

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

3. Switch of the initialisation option in the LISFLOOD settings file

```xml
<setoption choice="0" name="InitLisflood"/>
```


4. launch LISFLOOD

To run the model, start up a command prompt (Windows) or a console window (Linux) and type 'lisflood' followed by the name of the settings file, e.g.:

```unix
lisflood settings.xml
```

If everything goes well you should see something like this:

```unix
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
