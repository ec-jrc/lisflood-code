# General maps

+ Area mask & land use mask maps 
The mask maps in the hydrological model are used to detect where model should perform computations and where it shouldn't (skip the grid-cell). Area and land use masks are both Boolean maps which define model boundaries and land use calculation domain respectively.<br>
+ Grid-cell length & grid-cell area maps 
The grid-cell length and grid-cell area maps are used in LISFLOOD model to accurately compute the areal sums over grid-cells (e.g. the upstream area of the river when areas of all connected grid-cells are summed together or the rainfall amount over a certain grid-cell). If projection properties are in meters these maps become optional.<br>


## Area mask and land use mask maps

### General map information and possible source data

| Map name | File name;type | Units; range | Description |
| :---| :--- | :--- | :--- |


| Source data| Reference/preparation | Temporal coverage | Spatial information |
| :---| :--- | :--- | :--- |


### Methodology

To create a mask field (mask map or land use mask), source data (e.g. elevation or flow direction) values are changed to ‘1’ and the variable type is forced to be Byte for the mask map (area.nc), and Float32 for the land use mask (lusemask.nc).<br>
If the source data is at a higher resolution and/or is larger than the required model domain, it needs to be re-scaled to the required grid-cell resolution and/or clipped to the required model domain. <br>


### Results (examples)


<p float="left">
  <img src="../media/Static-Maps/area_European_01min.png" width="394" />
  <img src="../media/Static-Maps/area_Global_03min.png" width="611" /> 
</p>

*Figure 1: Mask map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right) with coloured areas showing land pixel.*



<p float="left">
  <img src="../media/Static-Maps/lusemask_European_01min.png" width="394" />
  <img src="../media/Static-Maps/lusemask_Global_03min.png" width="611" /> 
</p>

*Figure 2: Landuse mask map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right) with coloured areas showing land pixel.*

## Grid-cell length and grid-cell area maps


### General map information and possible source data


| Map name | File name;type | Units; range | Description |
| :---| :--- | :--- | :--- |


| Source data| Reference/preparation | Temporal coverage | Spatial information |
| :---| :--- | :--- | :--- |


### Methodology

To create the grid-cell area, the ee.Image.pixelArea() function in Google Earth Engine can be used, that computes the value of each grid-cell in square meters considering all curves of the Globe, and specify the needed grids resolution (e.g. 1 and 3 arc min) along the longitude in meters.<br>
Grid-cell length is computed dividing grid-cell area by its resolution along the longitude in meters.<br>
*Note: The pixel area and pixel length maps are given to the whole domain (i.e. not applying the ocean mask map).*<br>


### Results (examples)

<p float="centre">
  <img src="../media/Static-Maps/pixleng_European_01min.png" width="394" />
  <img src="../media/Static-Maps/pixleng_Global_03min.png" width="611" /> 
</p>

*Figure 3: Pixel length map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*



<p float="centre">
  <img src="../media/Static-Maps/pixarea_European_01min.png" width="394" />
  <img src="../media/Static-Maps/pixarea_Global_03min.png" width="611" /> 
</p>

*Figure 4: Pixel area map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*



