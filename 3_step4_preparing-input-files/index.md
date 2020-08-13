## Step 3: Input files (maps and tables)

In the current version of LISFLOOD, all model input is provided as either maps (grid files in PCRaster format or NetCDF format) or tables. This chapter describes all the data that are required to run the model. Files that are specific to *optional* LISFLOOD features (e.g. inflow hydrographs, reservoirs) are not listed here; they are described in the documentation for each option.

### Input maps

LISFLOOD requires that all maps must have *identical* location attributes (number of rows, columns, cellsize, upper x and y coordinate.

All input maps roughly fall into any of the following six categories:

-   maps related to topography
-   maps related to land cover -- fraction of land cover
-   maps related to land cover and soil
-   maps related to soil texture (soil hydraulic properties)
-   maps related to channel geometry
-   maps related to the meteorological conditions
-   maps related to the development of vegetation over time
-   maps that define at which locations output is generated as time series

All maps that are needed to run the model are listed in the table of Annex 12.

#### Role of "mask" and "channels" maps 

The mask map (i.e. "area.map") defines the model domain. In order to avoid unexpected results, **it is vital that all maps that are related to topography, land use and soil are defined** (i.e. don't contain a missing value) for each pixel that is "true" (has a Boolean 1 value) on the mask map. The same applies for all meteorological input and the Leaf Area Index maps. Similarly, all pixels that are "true" on the channels map must have some valid (non-missing) value on each of the channel parameter maps. Undefined pixels can lead to unexpected behaviour of the model, output that is full of missing values, loss of mass balance and possibly even model crashes. Some maps needs to have values in a defined range e.g. the gradient map has to be greater than 0.

#### Map location attributes and distance units

LISFLOOD needs to know the size properties of each grid cell (length, area) in order to calculate water *volumes* from meteorological forcing variables that are all defined as water *depths*. By default, LISFLOOD obtains this information from the location attributes of the input maps. This will only work if all maps are in an "equal area" (equiareal) projection, and the map co-ordinates (and cell size) are defined in meters. For datasets that use, for example, a latitude-longitude system, neither of these conditions is met. In such cases you can still run LISFLOOD if you provide two additional maps that contain the length and area of each grid cell

##### Table x.x Optional maps that define grid size

| **Map**         |  **Default name**  | **Description**                                              |
| --------------- | ------------------ | ------------------------------------------------------------ |
| PixelLengthUser | pixleng.map/nc     | Map with pixel length<br><br> Unit: $[m]$,<br> *Range *of values: map \> 0* |
| PixelAreaUser   | pixarea.map/nc     | Map with pixel area<br><br>*Unit:* $[m^2]$,<br> *Range of values: map \> 0* |

Both maps should be stored in the same directory where all other input maps are. The values on both maps may vary in space. A limitation is that a pixel is always represented as a square, so length and width are considered equal (no rectangles). In order to tell LISFLOOD to ignore the default location attributes and use the maps instead, you need to activate the special option "*gridSizeUserDefined*", which involves adding the following line to the LISFLOOD settings file:

```xml
<setoption choice="1" name="gridSizeUserDefined" \>
```

LISFLOOD settings files and the use of options are explained in detail in a [dedicated chapter](https://ec-jrc.github.io/lisflood-code/3_step3_preparing-setting-file/) and [aanex](https://ec-jrc.github.io/lisflood-code/4_annex_settings_and_options/) of this document.

**#### Naming of meteorological variable maps .... SHOULD WE REFER TO THE NETCDF CHAPTER? IS THE NETCDF CHAPTER A COMPLEMENT OR A REPLACEMENT TO THIS SECTION??**

The meteorological forcing variables (and Leaf Area Index) are defined in *map stacks*. A *map stack* is simply a series of maps, where each map represents the value of a variable at an individual time step. The name of each map is made up of a total of 11 characters: 8 characters, a dot and a 3-character suffix. Each map name starts with a *prefix*, and ends with the time step number. All character positions in between are
filled with zeros ("0"). Take for example a stack of precipitation maps. Table 4.1 shows that the default prefix for precipitation is "pr", which produces the following file names:

```
pr000000.007   : at time step 7
...
pr000035.260   : at time step 35260
```

LISFLOOD can handle two types of stacks. First, there are **regular stacks**, in which a map is defined for each time step. For instance, the following 10-step stack is a regular stack:

```
  t        map name
  1        pr000000.001
  2        pr000000.002
  3        pr000000.003
  4        pr000000.004
  5        pr000000.005
  6        pr000000.006
  7        pr000000.007
  8        pr000000.008
  9        pr000000.009
  10       pr000000.010
```

In addition to regular stacks, it is also possible to define **sparse stacks**. A *sparse* stack is a stack in which maps are not defined for all time steps, for instance:

```
1        pr000000.001
2        -
3        -
4        pr000000.004
5        -
6        -
7        pr000000.007
8        -
9        -
10       -
```

Here, maps are defined only for time steps 1, 4 and 7. In this case, LISFLOOD will use the map values of *pr000000.001* during time steps 1, 2 and 3, those of *pr000000.004* during time steps 4, 5 and 6, and those of *pr000000.007* during time steps 7, 8, 9 and 10. 
Since both regular and sparse stacks can be combined within one single run, sparse stacks can be very useful to save disk space. For instance, LISFLOOD always needs the *average daily* temperature, even when the model is run on an hourly time step. So, instead of defining 24 identical maps for each hour, you can simply define 1 for the first hour of each day and leave out the rest, for instance:

```
1        ta000000.001
2        -
:        :
:        :
25       ta000000.025
:        :
:        :
49       ta000000.049
:        :
```

Similarly, potential evapo(transpi)ration is usually calculated on a daily basis. So for hourly model runs it is often convenient to define $E0, ES0$ and $ET0$ in sparse stacks as well. Leaf Area Index (*LAI*) is a variable that changes relatively slowly over time, and as a result it is usually advantageous to define *LAI* in a sparse map stack.



#### Leaf area index maps 

Because Leaf area index maps follow a yearly circle, only a map stack of one year is necessary which is then used again and again for the  following years (this approach can be used for all input maps following a yearly circle e.g. water use). LAI is therefore defined as sparse map stack with a map every 10 days or a month, for example for a monthly changing LAI:


```
 1       lai00000.001 
 2       lai00000.032 
 3       lai00000.060 
 4       lai00000.091 
 5       lai00000.121 
 6       lai00000.152 
 7       lai00000.182 
 8       lai00000.213 
 9       lai00000.244 
 10      lai00000.274 
 11      lai00000.305 
 12      lai00000.335 
```

After one year the first map is taken again for simulation. For example the simulation started on the $5^{th}$ March 2010 and the first LAI is lai00000.060. On the  $1^{th}$March 2011 the map lai00000.060 is taken again as LAI input. To let LISFLLOD know which map has to be used at which day a lookup table (LaiOfDay.txt) is necessary.

### Input tables

In the previous version of LISFLOOD a number of model parameters are read through tables that are linked to the classes on the land use and soil (texture) maps. Those tables are replaced by maps (e.g. soil hydraulic property maps) in order to include the sub-grid variability of each parameter. Therefore only one table is used in the standard LISFLOOD setting (without lake or reservoir option)

The following table gives an overview:

##### Table: LISFLOOD input tables

| **Table**             | **Default name**      | **Description**       |
|----------------------------|-----------------------|--------------------------|
| Day of the year -\> LAI    | LaiOfDay.txt          | Lookup table: Day of the year -\> LAI map |


### Organisation of input data

It is up to the user how the input data are organised. However, it is advised to keep the base maps, meteorological maps and tables separated (i.e. store them in separate directories). For practical reasons the **following input structure is suggested**:

-   all **base maps** are in one directory (e.g. 'maps')

    -   fraction maps in a subfolder (e.g. 'fraction')

    -   soil hydraulic properties in a subfolder (e.g.'soilhyd')

    -   land cover depending maps in a subfolder (e.g.'table2map')

-   all **tables** are in one directory (e.g. 'tables')

-   all **meteorological input** maps are in one directory (e.g. 'meteo')

-   a folder **Leaf Area Index** (e.g. 'lai')

    -   all Leaf Area Index for forest in a subfolder (e.g.'forest')

    -   all Leaf Area Index for other in a subfolder (e.g.'other')

-   all **output** goes to one directory (e.g. 'out')

The following Figure illustrates this:

![](https://github.com/StefaniaGrimaldi/lisflood-code/tree/gh-pages/media/image36.png){width="5.802083333333333in"
height="4.541666666666667in"}

***Figure:*** *Suggested file structure for LISFLOOD*

### Generating input base maps **CHECK THIS LAST SENTENCE**

At the time of writing this document, complete sets of LISFLOOD base maps covering the whole of Europe have been compiled at 1- and 5-km pixel resolution. A number of automated procedures have been written that allow you to generate sub-sets of these for pre-defined areas (using either existing mask maps or co-ordinates of catchment outlets).

[:top:](#top)
