## Step 3: Input files (maps and tables)

In the current version of OS LISFLOOD, all the model inputs are provided as either maps (NetCDF format) or text files (.txt extension). This chapter provides an overview of the data set that is required to run the model.

### INPUT MAPS

> Albeit OS LISFLOOD can still read maps in pcraster format, users are strongly recommended to prepare their own input maps in NetCDF format: pcraster format will be discarded in future versions of OS LISFLOOD (timeline not yet defined). Users interested in converting their existing pcraster maps into NetCDF format can refer to the [OS LISFLOOD untility pcr2nc](https://github.com/ec-jrc/lisflood-utilities#pcr2nc).

LISFLOOD requires that all maps must have *identical* location attributes (number of rows, columns, cellsize, upper x and y coordinates).

The input maps can be classified according to two main categories:<br>
+ **meteorological forcings**. These maps provide time series of values for each pixel of the computational domain. More specifically, the meteorological forcings provide the values of precipitation, temperature, reference values of evaporation from water surfaces, reference values of evaporation from open water bodies, reference values of evapotranspiration for each pixel of the modelled area. For each meteorological forcing, one map is required for each computational time step. <br>
+ **static maps**. These maps provide information of morphological, physical, soil, and land use properties for each pixel of the computational domain. 

### Meteorological forcings

The meteorological forcing variables are defined in *map stacks*. A *map stack* is simply a series of maps, where each map represents the value of a variable at an individual time step.<br>It is recommented to use the netcdf format. <br> LISFLOOD is capable of reading meteorological forcings split into multiple files (e.g. yearly chuncks). To use this functionality, it is enough to add the symbol '\*' after the file name (e.g. ET0_\*).

Generally used prefixes for the meteorological forcings maps are: <br>
+ tp : total precipitation; units: mm/day.<br>
+ ta : average temperature at 2m within the time computational step: degrees Celsius or Kelvin (the units must be specified in the [settings file](../3_step2_preparing-setting-file/index.md))<br>
+ EW0 : reference value of evaporation from open water bodies; units: mm/day; these data can be prepared using [LISVAP](https://ec-jrc.github.io/lisflood-lisvap/).<br>
+ ES0 : reference value of evaporation from bare soil; units: mm/day; these data can be prepared using [LISVAP](https://ec-jrc.github.io/lisflood-lisvap/).<br>
+ ET0 : reference value of evapotranspiration; units: mm/day; these data can be prepared using [LISVAP](https://ec-jrc.github.io/lisflood-lisvap/).<br>

> Cumulative quantities (total precipitation, reference values of evaporation and evapotranspiration) must always be provided in $mm/day$, also when performing a simulation with sub-daily (hourly) computational time step: OS LISFLOOD will internally convert values provided in $mm/day$ to the desidered temporal resolution. For example, total precipitation values for a simulation with 6h computational time step must be provided every 6 hours, but 6 hours cumulative values are multipied by 4 ($mm/day$).


*Note for pcraster users only:* File names of meteorological forcings maps in pcraster format must adhere to pre-defined rules. The name of each map is made up of a total of 11 characters: 8 characters, a dot and a 3-character suffix. Each map name starts with a *prefix*, and ends with the time step number. All character positions in between are filled with zeros ("0"). <br>


### Static maps
The section [Static Maps](../4_Static-Maps-introduction) provides detailed guidelines for the preparation of the static maps data set. The following paragraph provides an overview of the information provided by the static maps.
+   [general maps](../4_Static-Maps_general-maps/): area mask; landuse mask; grid-cell length; grid-cell area.
+   [topography](../4_Static-Maps_topography/): local drain direction; gradient; standard deviation of elevation; upstream area.
+   [land use maps](../4_Static-Maps_land-use/): fraction of forest; fraction of irrigated crops; fraction of rice crops; fraction of inland water; fraction of sealed surfaces; fraction of other land uses.
+   [land use depending](../4_Static-Maps_land-use-depending/):crop coefficient; crop group number; Manning/s's surface roughness; soil depth.
+   [soil hydraulic properties](../4_Static-Maps_soil-hydraulic-properties/): saturated hydraulic conductivity; soil water content at saturation; residual soil water content; parameters alpha and lambda of Van Genuchten's equations.
+   [channel geometry](../4_Static-Maps_channel-geometry/): channels mask; channels side slope; channels length; channels gradient; Manning's rougheness coefficient of the channels; channels bottom width; floodplain width; bankfull channels depth; MCT diffusive wave routing channels.
+   [leaf area index](../4_Static-Maps_leaf-area-index/): evolution of vegetation over time (leaf area index) for land covers forest, irrigated areas, others.
+   [reservoirs and lakes](../4_Static-Maps_reservoirs-lakes/): lake mask; lakes ID points; reservoirs ID points. These maps are required only upon activation of the [lakes module](https://ec-jrc.github.io/lisflood-model/3_02_optLISFLOOD_lakes/) and/or of the [reservoirs module](https://ec-jrc.github.io/lisflood-model/3_03_optLISFLOOD_reservoirs/).
+   [rice calendar](../4_Static-Maps_water-use/): rice calendar for planting and harvesting seasons. These maps are required only when activating the [rice irrigation module](https://ec-jrc.github.io/lisflood-model/2_17_stdLISFLOOD_irrigation/)
+   inflow points: locations and IDs of the points in which LISFLOOD adds an inflow hydrograph, as explained [here](https://ec-jrc.github.io/lisflood-model/3_09_optLISFLOOD_inflow-hydrograph/)
+   [sectoral water demand maps]: domestic, energetic, livestock, industrial water use. These maps represent the time series of spatially distributed values of water demand for domestic, energetic, livestock, and industrial water use. These maps  are required only when activating the [water use module](https://ec-jrc.github.io/lisflood-model/2_18_stdLISFLOOD_water-use/)
+ outlet points: locations and IDs of the points for which OS LISFLOOD provides the time series of discharge values.

#### Role of "mask", "channels" ans "channelsMCT" maps 

The mask map (i.e. domain.nc, also called area.nc) defines the model domain. In order to avoid unexpected results, **it is vital that all maps that are related to topography, land use and soil are defined** (i.e. don't contain a missing value) for each pixel that is "true" (has a Boolean 1 value) on the mask map. The same applies for all meteorological input and the Leaf Area Index maps. Similarly, all pixels that are "true" on the channels map must have some valid (non-missing) value on each of the channel parameter maps. At the same time, all pixels that have value "true" in the MCT rivers mask must also belong to the "channels" map. Undefined pixels can lead to unexpected behaviour of the model, output that is full of missing values, loss of mass balance and possibly even model crashes. Some maps needs to have values in a defined range e.g. the gradient map has to be greater than 0. When preparing their own input maps, users are recommended to refer to [these guidelines](../4_Static-Maps-introduction/).

#### Geometrical properties of the computational grid cell

LISFLOOD needs to know the size properties of each grid cell (length, area) in order to calculate water *volumes* from meteorological forcing variables that are all defined as water *depths*. By default, LISFLOOD obtains this information from the location attributes of the input maps. This will only work if all maps are in an "equal area" (equiareal) projection, and the map co-ordinates (and cell size) are defined in meters. For datasets that use a latitude-longitude system, neither of these conditions is met. In such cases it is imperative to provide two additional maps that contain the length and area of each grid cell. These maps are described in [this section](../4_Static-Maps_general-maps/) of the [guidelines](../4_Static-Maps-introduction/) for the generation of the static maps and tables.

##### Table: maps that define grid size, essential when using latitude-longitude system

| **Map**         |  **Default name**  | **Description**                                              |
| --------------- | ------------------ | ------------------------------------------------------------ |
| PixelLengthUser | pixleng.map/nc     | Map with pixel length<br><br> Unit: $[m]$,<br> *Range *of values: map \> 0* |
| PixelAreaUser   | pixarea.map/nc     | Map with pixel area<br><br>*Unit:* $[m^2]$,<br> *Range of values: map \> 0* |

The values on both maps may vary in space. A limitation is that a pixel is always represented as a square, so length and width are considered equal (no rectangles). In order to tell LISFLOOD to use the maps a, you need to activate the special option "*gridSboveizeUserDefined*", which involves adding the following line to the LISFLOOD settings file:

```xml
<setoption choice="1" name="gridSizeUserDefined" \>
```

LISFLOOD settings files and the use of options are explained in detail in a [dedicated chapter](../3_step2_preparing-setting-file/index.md) and [annex](../5_annex_settings_and_options/index.md) of this document.


#### Leaf area index maps 

Because Leaf area index maps follow a yearly circle, only a map stack of one year is necessary which is then used again and again for the  following years (this approach can be used for all input maps following a yearly circle e.g. water use). LAI is therefore defined as sparse map stack with a map every 10 days or a month. After one year the first map is taken again for simulation. 


#### Important technical note for the generation of the water regions map

Water demand and water abstraction are spatially distributed within each water region. As detailed [here](../2_18_stdLISFLOOD_water-use/), the water resources (surface water bodies and groundwater) are shared inside the water region in order to meet the cumulative requirements of the water region area. For this reason, it is strongly recommended to include the entire water region(s) in the modelled area. If a portion of the water region is not included in the modelled area, then LISFLOOD cannot adequately compute the water demand and abstraction. In other words, LISFLOOD will not be able to account for sources of water outside of the computational domain (it is important to notice that LISFLOOD will not crush but the results will be affected by this discrepancy).
The inclusion of the complete water region in the computational domain becomes compulsory under the specific circumstances of model calibration.
Calibrated parameters are optimised for a specific model set up. It is often required to calibrate the parameters of several subcatchments inside a basin. Each calibration subcatchment must include a finite number of water regions (each water region can belong to only one subctatchment). If this condition is met, the calibrated parameters can be correctly optimised. Conversely, when a water region belongs to one or more calibration sub-catchments, the water resources are allocated and abstracted in different quantities when modelling the calibration subcatchment only or the entire basin. Similarly, the option groundwater smooth leads to different  geometries of the cone of depression due to groundwater abstraction when modelling the subcatchment only or the entire basin. These two scenarios impede the correct calibration of the model parameters and must be avoided. The user is advised to switch off the groundwater smooth option and to ensure the consistency between water regions and calibration cacthments. The utility [waterregions](https://github.com/ec-jrc/lisflood-utilities/) can be used to 1) verify the consistency between calibration catchments and water regions or 2) create a water region map which is consistent with a set of calibration points.


### INPUT TABLES

The geographical location of lakes and reservoirs is identified by the two maps described [here](../4_Static-Maps_reservoirs-lakes/). These maps provide the location of lakes and reservoirs. Each lake and each reservoir is identified by its ID (an integer number). 
LISFLOOD requires additional information for the adequate modelling of [lakes](https://ec-jrc.github.io/lisflood-model/3_02_optLISFLOOD_lakes/) and [reservoirs](https://ec-jrc.github.io/lisflood-model/3_03_optLISFLOOD_reservoirs/). These additional pieces of information are supplied to the numerical code by using tables in *.txt* format. Each table has 2 columns: the first column is the ID of the lake or of the reservoir, the second column is the quantity required by OS LISFLOOD. For example, OS LISFLOOD requires the surface area of each lake, and the storage capacity of each reservoir. The dedicated section [Reservoirs and lakes, maps and table](../4_Static-Maps_reservoirs-lakes/) of the [guidelines](../4_Static-Maps-introduction/) for the generation of the static maps and tables.

### Organisation of input data

It is up to the user how the input data are organised. As an example, users might decide to organize base maps, meteorological maps, static maps, and tables in separate directories. It is strogly recommended to store output files in a separate directory.

For example:

-   all **base maps** are in one directory (e.g. 'maps')

    -   fraction maps in a subfolder (e.g. 'fraction')

    -   soil hydraulic properties in a subfolder (e.g.'soilhyd')

    -   water demand maps in a subfolder (e.g. 'waterdemand')
    -   ...etc

-   all **tables** are in one directory (e.g. 'tables')

-   all **meteorological input** maps are in one directory (e.g. 'meteo')

-   all **output** goes to one directory (e.g. 'out')


Users might consider the example of sub-folders organization provided in the public datasets: [OS LISLOOD static and parameter maps for GloFAS dataset](https://data.jrc.ec.europa.eu/dataset/68050d73-9c06-499c-a441-dc5053cb0c86) and [OS LISLOOD static and parameter maps for Europe](https://data.jrc.ec.europa.eu/dataset/f572c443-7466-4adf-87aa-c0847a169f23).



[:top:](#top)
