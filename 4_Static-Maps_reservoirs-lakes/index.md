# Reservoirs and lakes 

Lakes and reservoirs can be defined as a significant volume of water, which occupies a depression of the land and has no direct connection with a sea. They can intensify winter snowstorms, increase precipitation or/and surface temperature, generate night convection and intensive thunderstorms. Lakes and reservoirs can influence the atmosphere regionally and globally.<br>
 + Lake mask map
In the LISFLOOD model lake mask map represents the area covered by lakes and is used for computing evaporation from open water surfaces.
 + Lakes & reservoirs maps
In the LISFLOOD model lakes and reservoirs maps represent only outflow location grid-cells (store lake/reservoir ID number in the morphological parameter look-up table) and are used for the lakes and reservoirs modelling.


## Lake mask map

### General map information and possible source data

| Map name | File name;type | Units; range | Description |
| :---| :--- | :--- | :--- |
| Laks mask| lakemask.nc; <br>Type: Float32 |  Units: -; <br>Range: 0 or 1 | Map of the footprint of lakes|


| Source data| Reference/preparation | Temporal coverage | Spatial information |
| :---| :--- | :--- | :--- |
|Global Lakes and Wetlands Database (GLWD): <br>Large Lake Polygons (Level 1) |[GLWD leve1](https://www.worldwildlife.org/publications/global-lakes-and-wetlands-database-large-lake-polygons-level-1)|2004|Global, 1:1 to 1:3 million resolution|
|Global Lakes and Wetlands Database (GLWD): <br>Small Lake Polygons (Level 3) |[GLWD leve1](https://www.worldwildlife.org/publications/global-lakes-and-wetlands-database-large-lake-polygons-level-2)|2004|Global, 1:1 to 1:3 million resolution|
|Fraction of inland water| It can be prepared by using<br> the methodology explained [here](../4_Static-Maps_land-cover)|NA|Global|

### Methodology

Fraction of inland water map is adjusted to the LISFLOOD model – all grid-cells fully covered with ocean water that are considered during computations are filled with inland water. <br>
If a grid-cell has any fraction of inland water and is inside the GLWD Level 1 and GLWD level 2 lake shapefiles, it is marked as ‘1’ (fully covered), otherwise it is marked as ‘0’.<br>


### Results (examples)


<p float="left">
  <img src="../media/Static-Maps/lakemask_European_01min.png" width="394" />
  <img src="../media/Static-Maps/lakemask_Global_03min.png" width="611" /> 
</p>

*Figure 53: Lakemask map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right) with coloured areas showing land pixel.*



## Lakes and reservoirs maps


### General map information and possible source data


| Map name | File name;type | Units; range | Description |
| :---| :--- | :--- | :--- |
|Lakes|lakes.nc; <br>Type: Float32|Units: -; <br>Range: integer  ID number to identify eanch lake |Lake outflow location <br> (stores lake ID number in the morphological parameter look-up table)|
|Reservoirs|res.nc; <br>Type: Float32|Units: -; <br>Range: integer  ID number to identify eanch reservoir |Reservoir outflow location<br> (stores reservoir ID number in the morphological parameter look-up table)|

| Source data| Reference/preparation | Temporal coverage | Spatial information |
| :---| :--- | :--- | :--- |
|Lakes datase|NA|NA|European/Global, ASCII table|
|Reservoirs dataset|NA|NA|European/Global, ASCII table|
|Local Drain Direction (LDD) map| It can be prepared by following the methodology explained [here](../4_Static-Maps-topography)|NA|Global|

### Methodology

Any ASCII tables with lakes and reservoirs geographical location should be mapped on the local drain direction (ldd) map.



