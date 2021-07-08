# Topography maps

+ **Local drain direction map**
The local drain direction (ldd) in a distributed hydrological model is the essential component to connect the grid cells to express the flow direction from one cell to another and forming a river network from springs to mouth. Currently LISFLOOD hydrological model needs ldd in PCRaster file format. Following links provide examples how local drain direction map can be generated with [ArcGIS](https://desktop.arcgis.com/en/arcmap/10.3/tools/spatial-analyst-toolbox/flow-accumulation.htm) or [PCRaster](https://pcraster.geo.uu.nl/pcraster/4.3.0/documentation/pcraster_manual/sphinx/op_upstream.html). <br>
+ **Slope gradient map**
Elevation data and its derivate (e.g. slope) are used in hydrological models for snow processes and for routing of surface runoff. In the LISFLOOD model the slope gradient map is used for surface routing.<br>
+ **Standard deviation of elevation map**
Elevation data and its derivate (e.g. standard deviation of elevation) are used in hydrological models (e.g. the LISFLOOD model) for snow processes and for routing of surface runoff.<br>
+ **Map with upstream area**
The upstream area in a distributed hydrological model is the accumulated area of all connected water pixels that in a river network starts at the springs and goes to the river mouth. Springs grid-cells have lowest values, and river mouth grid-cells have the highest values on the map. Following links provide examples how upstream area map can be generated with [ArcGIS](https://desktop.arcgis.com/en/arcmap/10.3/tools/spatial-analyst-toolbox/flow-accumulation.htm) or [PCRaster](https://pcraster.geo.uu.nl/pcraster/4.3.0/documentation/pcraster_manual/sphinx/op_upstream.html). <br>

## Local drain direction map
### General map information and possible source data

| Map name | File name;type | Units; range | Description |
| :---| :--- | :--- | :--- |
|Local drain direction (ldd) map        | ldd.nc/ldd.map; <br> Type: Byte         | Units: -;<br> Values: 1,2,3,4,5,6,7,8,9         |Local drain direction map - flow directions from each grid-cell to its steepest downslope neighbour; geographical directions are coded n a following way: N=8, NE=9, E=6, SE=3, S=2, SW=1, W=4, NW=7, and grid-cells with only inflow of water (pits) equal 5; the pit grid-cell at the end of the path is the outlet point of a catchment; NoData=255 |


| Source data| Reference/preparation | Temporal coverage | Spatial information |
| :---| :--- | :--- | :--- |
|Flow direction map    |http://hydro.iis.u-tokyo.ac.jp/~yamadai/cama-flood/index.html          |2018         |Global, 1' and 3'|


### Methodology

It is suggested to use cautiously any file transforming commands as they might change file structure. Here it is suggested to use only CDO, GDAL and Python commands to preserve initial file structure as much as possible (especially latitude and longitude values) and be able to use it later as a Template for all other static maps.<br>
To create a local drain direction (ldd) field from a flow direction map, initial file values in a NetCDF format are changed in the following way for different geographical directions. Mouth: ‘-1’=>’5’, Inland: ‘0’=>’5’, North: ‘1’=>’8’, NE: ‘2’=>’9’, East: ‘3’=>’6’, SE: ‘4’=>’3’, South: ‘5’=>’2’, SW: ‘6’=>’1’, West: ‘7’=>’4’, NW: ‘8’=>’7’.<br>
Note: Obtaining a flow direction map from a digital elevation model is a complex process and is not described here. A good example of how to create a flow direction map can be found in [Yamazaki et al. (WRR, 2019)](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2019WR024873). Note also that the created ldd file must be checked and corrected if needed, so that water is not flowing out of the region of interest. Finally, after all manipulations of the NetCDF file, latitude and longitude values from the native files must be copied to the newly generated file to insure identical structure of all static map files. <br>

### Results (example)

<p float="left">
  <img src="../media/Static-Maps/ldd_European_01min.png" width="394" />
  <img src="../media/Static-Maps/ldd_Global_03min.png" width="611" /> 
</p>

*Figure 5: Local drain direction map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*


## Gradient map
### General map information and possible source data

| Map name | File name;type | Units; range | Description |
| :---| :--- | :--- | :--- |
|Gradient map        | gradient.nc; <br> Type: Float32         | Units: -;<br> Range: >0        |Slope gradient |


| Source data| Reference/preparation | Temporal coverage | Spatial information |
| :---| :--- | :--- | :--- |
| MERIT DEM: Multi-Error-Removed Improved-Terrain DEM| http://hydro.iis.u-tokyo.ac.jp/~yamadai/MERIT_DEM/index.html | 2018 | Global, 3" (~90 m) |
|Local drain direction (ldd) map    |It can be created using the methodology explained [here](../4_Static-Maps_topography#local-drain-direction-map)         |NA         |Global, 1' and 3'|

### Methodology
The local drain direction (ldd) file can be used to extract the connectivity between grid-cells. The distance (in meters) between two connected grid-cells is calculated together with the absolute difference (in meters) of elevation between the two grid-cells.<br>
Gradient is assigned to the upstream grid-cell, and computed according to the following formula:<br>

$$
gradient=\frac{elevation difference}{distance}
$$

$gradient$ is set equal 0 where $ldd$ is 5.

### Results (examples)

<p float="left">
  <img src="../media/Static-Maps/gradient_European_01min.png" width="394" />
  <img src="../media/Static-Maps/gradient_Global_03min.png" width="611" /> 
</p>

*Figure 6: Slope gradient map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*


## Standard deviation of elevation map
### General map information and possible source data

| Map name | File name;type | Units; range | Description |
| :---| :--- | :--- | :--- |
|Elevation standard deviation       | elvstd.nc; <br> Type: Float32         | Units: -;<br> Range: >=0        |Standard deviation of elevation (altitude difference elevation within a grid-cell) |


| Source data| Reference/preparation | Temporal coverage | Spatial information |
| :---| :--- | :--- | :--- |
| MERIT DEM: Multi-Error-Removed Improved-Terrain DEM| http://hydro.iis.u-tokyo.ac.jp/~yamadai/MERIT_DEM/index.html | 2018 | Global, 3" (~90 m) |

### Methodology

High resolution of initial elevation data is to be reduced to the needed coarser resolution i) by averaging elevation data with mean.unweighted() reducer to compute elevation field at required resolution, and ii) by computing standard deviation of all 90-meter grid-cells on the elevation field included into one e.g. 1 arc min grid-cell with stDev.unweighted() reducer.

### Results (examples)

<p float="left">
  <img src="../media/Static-Maps/elvstd_European_01min.png" width="394" />
  <img src="../media/Static-Maps/elvstd_Global_03min.png" width="611" /> 
</p>

*Figure 7: Standard deviation of elevation map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*

## Upstream area

| Map name | File name;type | Units; range | Description |
| :---| :--- | :--- | :--- |
|Upstream area       | upArea.nc; <br> Type: Float32         | Units: $m^2$;<br> Range: >0        |Map with upstream area (based on ldd and pixarea maps) - the accumulated area of all connected water pixels that in a river network starts at the springs and goes to the river mouth|


| Source data| Reference/preparation | Temporal coverage | Spatial information |
| :---| :--- | :--- | :--- |
|Pixel area map    |It can be created using the methodology explained XXXXXXXXXX          |NA         |Global, 1' and 3'|
|Local drain direction (ldd) map    |It can be created using the methodology explained [here](../4_Static-Maps_topography#local-drain-direction-map)         |NA         |Global, 1' and 3'|

### Methodology

To create an upstream area, pixel area and ldd maps are used with the PCRaster function accuflux. 

### Results (examples)

<p float="left">
  <img src="../media/Static-Maps/upArea_European_01min.png" width="394" />
  <img src="../media/Static-Maps/upArea_Global_03min.png" width="611" /> 
</p>
<p float="centre">
  <img src="../media/Static-Maps/upArea_European_01min_PoValley.png" width="800" />
</p>

*Figure 8: Map with upstream area at 1 arc min horizontal resolution for European domain (top left) and for the Po River Valley (bottom), and at 3 arc min horizontal resolution for Global domain (top right).*


