[//]: # (LISFLOOD input maps and tables)

# Input maps

***Table:*** *LISFLOOD input maps.*

| **Map**         | **Default name**[^20]       | **Units, range**        | **Description** |
|-----------------|-----------------|-------------------|-------------------------------------|
| **GENERAL**     ||||
| MaskMap         | area.map        | U.: -   <br> R.: 0 or 1      | *Boolean* map that defines model boundaries |
| **TOPOGRAPHY**  ||||
| Ldd             | ldd.map         | U.: flow directions  <br> R.: 1 ≤ map ≤ 9 | local drain direction map (with value  1-9); this file contains flow directions  from each cell to its steepest  downslope neighbour. Ldd directions are  coded according  to the following  diagram:  ![ldd](media/media/image58.png)  {width="1.8229 166666666667in"  height="1.84375 in"}  This resembles the numeric key pad of  your PC's keyboard, except for the  value 5, which defines a cell without  local drain direction  (pit). The pit cell at  the end of the path is the outlet point  of a catchment. |
| Grad            | gradient.map    | U.: $\frac{m}{m}$ <br> R.: map \> 0  **!!!** | Slope gradient  |
| Elevation Stdev | elvstd.map      | U.: $m$  <br> R.: map ≥ 0 | Standard deviation of elevation       |
| **LAND USE -- fraction maps**   ||  ||
| Fraction of water    | fracwater.map   | U.: \[-\] <br> R.: 0 ≤ map ≤ 1       | Fraction of inland water for each cell.  Values range from 0 (no water at all)  to 1 (pixel is 100% water)   |
| Fraction of sealed surface | fracsealed.map  | U.: \[-]  <br> R.: 0 ≤ map ≤ 1 | Fraction of impermeable surface for  each cell. Values range from 0 (100%  permeable surface -- no urban at all)  to 1 (100% impermeable surface).    |
| Fraction of forest | fracforest.map  | U.:\[-\]  <br> R.: 0 ≤ map ≤ 1 | Forest fraction for each cell. Values  range from 0 (no forest at all) to 1  (pixel is 100% forest)|
| Fraction of other land cover | fracother.map   | U.: \[\]  <br> R.: 0 ≤ map ≤ 1 | Other (agricultural areas, non-forested  natural area, pervious surface of urban  areas) fraction for each cell.          |
| **LAND COVER depending  maps** | |       ||
| Crop coef. for forest  | cropcoef\_\forest.map     | U.: \[-\]  <br> R.: 0.8≤ map ≤ 1.2 | Crop coefficient for forest |
| Crop coef. for other | cropcoef\_\other.map     | U.: \[-\]  <br> R.: 0.8≤ map ≤ 1.2 | Crop coefficient for other |
| Crop group number  for forest| crgrnum\_\forest.map      | U.: \[-\]  <br> R.: 1 ≤ map ≤ 5      | Crop group number for forest|
| Crop group number  for forest | crgrnum\_\other.map      | U.: \[-\]  <br> R.: 1 ≤ map ≤ 5 | Crop group number for other |
| Manning for forest | mannings\_\forest.map     | U.: \[-\]  <br> R.: 0.2≤ map ≤ 0.4 | Manning's roughness for forest      |
| Manning for other | mannings\_\other.map     | U.: \[-\]  <br> R.: 0.01≤ map ≤0.3 | Manning's roughness for other |
| Soil depth for forest for layer1 | soildep1\_\forest.map | U.: $mm$  <br> R.: map ≥ 50 | Forest soil depth for soil layer 1  (rooting depth) |
| Soil depth for other for layer2 | soildep1\_\other.map     | U.: $mm$  <br> R.: map ≥ 50 | Other soil depth for soil layer 1  (rooting depth)     |
| Soil depth for forest for layer2 | Soildep2\_\forest.map     | U.: $mm$  <br> R.: map ≥ 50 | Forest soil depth for soil layer 2 |
| Soil depth for other for layer2 | Soildep2\_\other.map     | U.: $mm$  <br> R.: map ≥ 50 | Other soil depth for soil layer 2 |
| **SOIL HYDRAULIC PROPERTIES  (depending on soil texture)** ||||
| ThetaSat1 for forest  | thetas1\_\forest.map      | U.: \[-\]  <br> R.: 0 \< map \<1     | Saturated volumetric soil moisture  content layer 1 |
| ThetaSat1 for other  | thetas1\_\other.map      | U.: \[-\]  <br> R.: 0 \< map \<1 | Saturated volumetric soil moisture  content layer 1      |
| ThetaSat2 for forest and other | thetas2.map     | U.: \[-\]  <br> R.: 0 \< map \<1 | Saturated volumetric soil moisture  content layer 2  |
| ThetaRes1 for forest  | thetar1\_\forest.map | U.: \[-\]  <br> R.: 0 \< map \<1 | Residual volumetric soil moisture  content layer 1 |
| ThetaRes1 for other  | thetar1\_\other.map      | U.: \[-\]  <br> R.: 0 \< map \<1 | Residual volumetric soil moisture  content layer 1 |
| ThetaRes2 for forest and other | thetar2.map     | U.: \[-\]  <br> R.: 0 \< map \<1 | Residual volumetric soil moisture  content layer 2 |
| Lambda1 for forest | lambda1\_\forest.map | U.: \[-\]  <br> R.: 0 \< map \<1 | Pore size index (λ) layer 1 |
| Lambda1 for other | lambda1\_\other.map | U.: \[-\]  <br> R.: 0 \< map \<1 | Pore size index (λ) layer 1 |
| Lambda2 for forest and other | lambda2.map     | U.: \[-\]  <br> R.: 0 \< map \<1 | Pore size index (λ) layer 2 |
| GenuAlpha1 for forest | alpha1\_\forest.map | U.: \[-\]  <br> R.: 0 \< map \<1 | Van Genuchten parameter α layer 1 |
| GenuAlpha1 for other | alpha1\_\other.map | U.: \[-\]  <br> R.: 0 \< map \<1 | Van Genuchten parameter α layer 1 |
| GenuAlpha2 for forest and other| alpha2.map | U.: \[-\]  <br> R.: 0 \< map \<1 | Van Genuchten parameter α layer 2 |
| Sat1 for forest | ksat1\_\forest.map | U.: $\frac{cm}{day}$  <br> R.: 1 ≤ map ≤100 | Saturated conductivity layer 1 |
| Sat1 for other  | ksat1\_\other.map | U.:$\frac{cm}{day}$  <br> R.: 1 ≤ map ≤100 | Saturated conductivity layer 1 |
| Sat2 for forest and other | ksat2.map | U.: $\frac{cm}{day}$  <br> R.: 1 ≤ map ≤100 | Saturated conductivity layer 2 |
| **CHANNEL GEOMETRY**      ||||
| Channels        | chan.map        | U.: \[-\]  <br> R.: 0 or 1 | Map with Boolean 1 for all channel pixels, and Boolean 0 for all other pixels on MaskMap |
| ChanGrad        | changrad.map    | U.: $\frac{m}{m}$  <br> R.: map \> 0  **!!!** | Channel gradient |
| ChanMan         | chanman.map     | U.: \[-\]  <br> R.: map \> 0 | Manning's roughness coefficient for  channels |
| ChanLength      | chanleng.map    | U.: $m$  <br> R.: map \> 0 | Channel length (can exceed grid size, to account for  meandering rivers) |
| ChanBottomWidth | chanbw.map      | U.: $m$  <br> R.: map \> 0 | Channel bottom width |
| ChanSdXdY       | chans.map       | U.: $\frac{m}{m}$ <br> R.: map ≥ 0 | Channel side slope **Important:** defined as  horizontal divided by vertical distance  (dx/dy); this may be confusing because slope  is usually defined the other way round  (i.e. dy/dx)! |
| ChanDepth\Threshold | chanbnkf.map    | U.: $m$  <br> R.: map \> 0 | Bankfull channel depth |
| **DEFINITION OF INPUT/OUTPUT TIMESERIES**    ||||
| Gauges          | outlets.map     | U.: \[-\]  <br> R.: For each station an  individual number | Nominal map with locations at which discharge  timeseries are reported (usually correspond to  gauging stations) |
| Sites           | sites.map       | U.: \[-\]  <br> R.: For each station an  individual number | Nominal map with locations (individual pixels or  areas) at which timeseries of intermediate state and rate  variables are reported (soil moisture, infiltration,  snow, etcetera) |
| **METEOROLOGICAL VARIABLES**     ||||
| **Map**         | **Default prefix**       | **Units,range**        | **Description** |
|                 |         |          |                 |
| PrecipitationMaps  | pr              | U.: $\frac{mm}{day}$  <br> R.: map ≥ 0 | Precipitation rate  |
| TavgMaps        | ta              | U.: $°C$  <br> R.:-50 ≤ map ≤50 | Average *daily* temperature |
| E0Maps          | e               | U.: $\frac{mm}{day}$  <br> R.: map ≥ 0 | Daily potential evaporation rate, free  water surface |
| ES0Maps         | es              | U.: $\frac{mm}{day}$  <br> R.: map ≥ 0 | Daily potential evaporation rate, bare soil |
| ET0Maps         | et              | U.: $\frac{mm}{day}$  <br> R.: map ≥ 0 | Daily potential evapotranspiration rate, reference crop |
| **DEVELOPMENT OF VEGETATION OVER TIME**     ||||
| LAIMaps for forest | lai\_forest     | U.: $\frac{m^2}{m^2}$  <br> R.: map ≥ 0 | Pixel-average Leaf Area Index for forest  |
| LAIMaps for other | lai\_other  | U.: $\frac{m^2}{m^2}$  <br> R.: map ≥ 0 | Pixel-average Leaf Area Index for other  |


**Table:*** *Optional maps that define grid size.*     

| **Map**         | **Default name**       | **Units, range**        | **Description** |
|-----------------|-----------------|-----------------|-------------------------------------|
| PixelLengthUser | pixleng.map     | U.: $m$  <br> R.: map \> 0 | Map with pixel length |
| PixelAreaUser   | pixarea.map     | U.: $m$  <br> R.: map \> 0 | Map with pixel area |



# Input tables

In the previous version of LISFLOOD a number of model parameters are read through tables that are linked to the classes on the land use and soil (texture) maps. Those tables are replaced by maps (e.g. soil hydraulic property maps) in order to include the sub-grid variability of each parameter. Therefore only one default table is used in the standard LISFLOOD setting

The following table gives an overview:


```R
# Looks strange to me
```

**Table A12.3** LISFLOOD input table*                      
----------------------------------------- ------------------ -------------------------------------------
  **LAND USE**                                                 
  **Table**                                 **Default name**   **Description**
  Day of the year -\> LAI                   LaiOfDay.txt       Lookup table: Day of the year -\> LAI map

