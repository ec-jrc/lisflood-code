## Leaf Area Index

The Leaf Area Index (LAI) is defined as half the total area of green elements of the canopy per unit horizontal ground area m<sup>2</sup>/m<sup>2</sup>. <br/>
The LAI quantifies the thickness of the vegetation cover. The Global Climate Observing System ([GCOS](https://public.wmo.int/en/programmes/global-climate-observing-system)) recognises LAI as an Essential Climate Variable ([ECV](https://public.wmo.int/en/programmes/global-climate-observing-system/essential-climate-variables)). 

Here, forest includes evergreen and deciduous needle leaf and broad leaf trees, irrigated crops - all possible crops excluding rice (is modelled separately), and other land cover type - agricultural areas, non-forested natural area, pervious surface of urban areas.
In LISFLOOD LAI has an important role in water interception and evapotranspiration processes.
 
### Leaf Area Index for land covers forest, irrigated crops, and other

#### General map information and possible source data

| Map name | File name;type | Units; range | Description |
| :---| :--- | :--- | :--- |
| LAI for forest        |  laif.nc; Float32          | Units: -; Range: 0 ..7         |10-day average (36 maps in total) Leaf Area Index for closed forested areas (forest fraction per grid-cell ≥ 0.7)|
| LAI for irrigated crops  | laii.nc; Float32    | Units: -; Range: 0 ..7     |10-day average (36 maps in total) Leaf Area Index for irrigated crop areas (irrigated crop fraction per grid-cell ≥ 0.7)|
| LAI for other     | laio.nc; Float32       | Units: -; Range: 0 ..7     |10-day average (36 maps in total) Leaf Area Index for mainly other land cover type areas (other land cover type fraction per grid-cell ≥ 0.7)|


| Source data| Reference/preparation | Temporal coverage | Spatial information |
| :---| :--- | :--- | :--- |
| Copernicus Global Land Service LAI Collection Version 2 | https://land.copernicus.eu/global/products/lai | 1 January 2010 - 31 December 2019 | Global, 1 km|
| Fraction of forest | It can be prepared by using [this methodology](../4_Static-Maps_land-use#fraction-of-forest)| NA | Global, 1' and 3'|
| Fraction of irrigated crops | It can be prepared by using [this methodology](../4_Static-Maps_land-use#fraction-of-irrigated-crops)| NA | Global, 1' and 3'|
| Fraction of other land cover type | It can be prepared by using [this methodology](../4_Static-Maps_land-use#fraction-of-other-land-use-type)|NA | Global, 1' and 3'|

#### Methodology

To create LAI for forest, irrigated crops and other land cover type, maps [Copernicus Global Land Service LAI Collection](https://land.copernicus.eu/global/products/lai) Version 2 can be used.<br/> The dataset provides a 10-day average LAI information, 36 maps each year. Here, to normalise the climate over different regions of the globe, the 10-day average LAI maps are aggregated over a 10-year period (i.e. first 10-day average of years 2010-2019 are aggregated to compute a first 10-day climatological average). As a result 36 climatological LAI maps are calculated. 
Then, fraction maps for forest, irrigated crops, and other land cover type are used to mask non-dense areas of the land cover type in question (i.e. fraction is less than 0.7) over the climatological LAI maps. <br/>
The LAI map resolution of the resulting field is reduced from native to the required one (e.g. from 1 km to 1 arc min) as follows. Firstly, the resolution is reduced to 1, 3, 15 arc min and 1, 3, 15, 60 degrees with mean.unweighted() reducer, and then all different resolutions are assembled to create a field with no missing values. For each resolution (going from the highest to the coarsest), grid-cells with missing values are identified and filled with the value of the corresponding grid-cell with non-missing value from the next resolution down map (e.g. using 3 arc min to fill in 1 arc min missing values). If the corresponding grid-cell is masked (has a missing value), then the value of the corresponding non-masked grid-cell from the next resolution down map is used, until all resolution maps are explored. If the corresponding grid-cell value of the coarsest resolution (here 60 degree) is still missing, a zero value is given.

#### Results (examples)



<p float="left">
  <img src="../media/Static-Maps/laif_0105_European_01min.png" width="329" />
  <img src="../media/Static-Maps/laif_0105_Global_03min.png" width="513" /> 
</p>

*Figure 51: Leaf area index for forest 5th January map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*


<p float="centre">
  <img src="../media/Static-Maps/laif_0805_European_01min.png" width="329" />
  <img src="../media/Static-Maps/laif_0805_Global_03min.png" width="513" /> 
</p>

*Figure 52: Leaf area index for forest 5th August map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*
