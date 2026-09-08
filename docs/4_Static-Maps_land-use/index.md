# Land use

The LISFLOOD hydrological model can distinguish the following land cover types: forest, inland water, sealed surface (impervious urban area), irrigated land, rice, and other land cover type. Interception, evapotranspiration, infiltration, and overland (or surface) flow respond differently to each surface type.<br> 

+ **Fraction of inland water map** <br> 
Inland water map includes information on rivers, freshwater and saline lakes, ponds and other permanent water bodies over the continents. In the LISFLOOD model the inland water fraction map is used to identify the fraction of the pixel covered by open water bodies where the most prominent hydrological process is evaporation.
Considering that LISFLOOD does not distinguish oceans from inland water it is recommended to verify consistency between water fractions and computational area mask, especially in the coastal areas. Pixels included in the computational area mask cannot be fully covered with ocean. If this happens in coastal areas, then the fraction of inland water must be set to 1 and the [lake mask](../4_Static-Maps_reservoirs-lakes#lake-mask-map) should be changed accordingly. <br>

+ **Fraction of sealed surface map** <br> 
Here, the sealed surface map describes urban areas, characterizing the human impact on the environment. In the LISFLOOD model the sealed surface fraction map is used to identify impervious areas where there is no water infiltration into the soil, meaning water is accumulated in the surface depression, yet evaporates, but once depression is full - water is transported by a surface runoff.<br> 

+ **Fraction of forest map** <br> 
Forest map describes land use composed of evergreen and deciduous needle leaf and broad leaf trees. In the LISFLOOD model the forest fraction is used to identify forested areas where main hydrological processes are canopy interception, evapotranspiration from canopies, canopies drainage and evapotranspiration.<br/>

+ **Fraction of irrigated crops map** <br> 
Irrigated crops map includes all possible crops excluding rice (is modelled separately). In the LISFLOOD model the irrigated crops fraction map is used to identify part of the pixel which is used by agriculture - water is abstracted from ground water and surface water bodies to irrigate the fields; main hydrological process connected with the irrigated crops are canopy interception, evapotranspiration from canopies, canopies drainage and evapotranspiration. <br/>

+ **Fraction of other land cover type map** <br> 
Other land cover type map includes agricultural areas, non-forested natural area, pervious surface of urban areas. In the LISFLOOD model the other land cover type fraction map is used in the following hydrological processes: canopy interception, evaporation from the canopies, canopy drainage, plant evapotranspiration, evaporation from the soil. The relative importance of these processes depends on the Leaf Area Index.<br/>


## Fraction of inland water
### General map information and possible source data

| Map name | File name;type | Units; range | Description |
| :---| :--- | :--- | :--- |
|Fraction of inland water         | fracwater.nc; <br> Type: Float32          | Units: -;<br> Range: [0-1]         |Inland water fraction for each grid-cell;<br> values range from 0 (grid-cell has no inland water) to 1 (grid-cell is fully covered with inland water) |


| Source data| Reference/preparation | Temporal coverage | Spatial information |
| :---| :--- | :--- | :--- |
|Copernicus Global Land Cover Layers: CGLS-LC100 collection 2   |[CGLS-LC100](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_Landcover_100m_Proba-V-C3_Global#description)      |2015        |Global, 100 m|

### Methodology

To create the fraction of inland water, the 'water-permanent-coverfraction' layer can be used. It gives the percentage values of permanent inland water covering each grid-cell, ranging from 0 - grid-cell has no inland water - to 100% - grid-cell is fully covered with inland water. Values are translated into fractions per grid-cell, and then high initial resolution reduced to the needed resolution, e.g. 1 arc min, with mean() reducer.
Note: Inland water fraction field should be checked for consistency with all other fractions.

### Results (example)

<p float="left">
  <img src="../media/Static-Maps/fracwater_European_01min.png" width="329" />
  <img src="../media/Static-Maps/fracwater_Global_03min.png" width="513" /> 
</p>

*Figure 9: Fraction of inland water map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*

## Fraction of sealed surfaces
### General map information and possible source data


| Map name | File name;type | Units; range | Description |
| :---| :--- | :--- | :--- |
|Fraction of sealed surfaces | fracsealed.nc; <br> Type: Float32  | Units: -;<br> Range: [0-1]  |Urban surface fraction for each grid-cell;<br> values range from 0 (grid-cell has no urban surface) to 1 (grid-cell is fully covered with urban surface) |


| Source data| Reference/preparation | Temporal coverage | Spatial information |
| :---| :--- | :--- | :--- |
|Copernicus Global Land Cover Layers: CGLS-LC100 collection 2   |[CGLS-LC100](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_Landcover_100m_Proba-V-C3_Global#description)      |2015        |Global, 100 m|

### Methodology

To create the fraction of sealed surface map, the 'urban-coverfraction' layer can be used. It gives the percentage values of urban surface covering each grid-cell, ranging from 0 % - grid-cell has no urban surface to 100 % - grid-cell is fully covered with urban surface. Values are translated into fractions per grid-cell and multiplied by 0.75 to account for urban permeable part (it is assumed that in general all urban areas have part which allows water to infiltrate, e.g. trees along the road, bushes along the fence, grass or moss between concrete tiles or cobble stones, and on average it covers 25 % of the area at a kilometre scale), and then high native resolution is reduced to the needed resolution, e.g. 1 arc min, with mean() reducer.<br>
Note: Sealed surface fraction field should be checked for consistency with all other fractions.

### Results (example)

<p float="left">
  <img src="../media/Static-Maps/fracsealed_European_01min.png" width="329" />
  <img src="../media/Static-Maps/fracsealed_Global_03min.png" width="513" /> 
</p>

*Figure 10: Fraction of sealed surfaces map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*

## Fraction of forest 
### General map information and possible source data


| Map name | File name;type | Units; range | Description |
| :---| :--- | :--- | :--- |
|Fraction of forest       | fracforest.nc; <br> Type: Float32          | Units: -;<br> Range: [0-1]         |Forest fraction for each grid-cell; <br>values range from 0 (grid-cell has no forest) to 1 (grid-cell is fully covered with forest) |


| Source data| Reference/preparation | Temporal coverage | Spatial information |
| :---| :--- | :--- | :--- |
|Copernicus Global Land Cover Layers: CGLS-LC100 collection 2   |[CGLS-LC100](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_Landcover_100m_Proba-V-C3_Global#description)       |2015        |Global, 100 m|

### Methodology

To create the fraction of forest map, the 'tree-coverfraction' layer can be used. It gives the percentage values of forest covering each grid-cell, ranging from 0 % - grid-cell has no forest to 100 % - grid-cell is fully covered with forest. Values are translated into fractions per grid-cell, and then high native resolution is reduced to the needed resolution, e.g. 1 arc min, with mean() reducer.<br>
Note: Forest fraction field should be checked for consistency with all other fractions.

### Results (example)

<p float="left">
  <img src="../media/Static-Maps/fracforest_European_01min.png" width="329" />
  <img src="../media/Static-Maps/fracforest_Global_03min.png" width="513" /> 
</p>

*Figure 11: Fraction of forest map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*

## Fraction of irrigated crops
### General map information and possible source data


| Map name | File name;type | Units; range | Description |
| :---| :--- | :--- | :--- |
| Fraction of irrigated crops | fracirrigated.nc; <br> Type: Float32 | Units: -;<br> Range: [0-1] | Irrigated crop (except rice) fraction for each grid-cell; <br>values range from 0 (grid-cell has no irrigated crops) to 1 (grid-cell is fully covered with irrigated crops) |
 
| Source data | Reference/preparation | Temporal coverage | Spatial information |
| :---| :--- | :--- | :--- |
| European Irrigation Map 2010 (EIM2010) | [Zajac et al., 2022](https://www.sciencedirect.com/science/article/pii/S0378377422000749); data available from the [AGRI4CAST Resources Portal](https://agri4cast.jrc.ec.europa.eu/DataPortal/Index.aspx) | 2010 | European, 10 km |
| CORINE Land Cover 2018 CLC2018 | [CLC2018](https://land.copernicus.eu/pan-european/corine-land-cover) | 2018 | European, 100 m |
| FAO Global Map of Irrigation Areas v5.0 (GMIA) | [Siebert et al., 2013](https://openknowledge.fao.org/server/api/core/bitstreams/02e5f498-eb5d-4a08-b501-b3e05fdefc57/content) | 2005 | Global, 5 arcmin |
| Eurostat irrigated area statistics (validation only) | [ef_poirrig](https://ec.europa.eu/eurostat/databrowser/view/ef_poirrig/default/map?lang=en) | 2010 census | European, NUTS2 regions |

### Methodology
Note: this is an updated version of the irrigation fraction as described in [Choulga et al., 2024](https://hess.copernicus.org/articles/28/2991/2024/).

Multiple data sources can be used to create the fraction of irrigated crops map, giving priority to more accurate regional information where available over a global dataset. Two workflows are described here: a European workflow based on EIM2010 downscaled with CORINE land cover (used for the European 1 arcmin domain, e.g. EFAS), and a global workflow based on the FAO GMIA v5.0 (used for the global 3 arcmin domain, e.g. GloFAS).
 
In both workflows, the maximum extent available for irrigated crops in each grid-cell is defined as the sum of the current "other" and "irrigated" land-use fractions (i.e. forest, rice, water, and sealed fractions cannot be converted to irrigated land).
 
#### European domain (EIM2010 + CORINE downscaling)
 
EIM2010 (Zajac et al., 2022) provides irrigated areas at 10 km resolution for 14 crop classes, together with the total irrigable area (TIA) and the irrigated area (IA), derived from the 2010 EU agricultural census.
The crop-specific irrigated areas of the EIM2010 shapefile are summed per 10 km cell for the irrigated area (IA in the Zajac dataset) . Cells with IA = 0 are discarded.
The IA of each 10 km EIM2010 cell is distributed to the model grid-cells inside it using the CLC2018 agricultural classes as spatial proxy. For each cell, a priority list of CORINE classes is built: class 212 ("Permanently irrigated land") is used first; then the CORINE classes corresponding to the cell's irrigated crop composition, ordered by decreasing irrigated area (arable-land crops (211), grass (231), vineyards (221), fruit trees and citrus (222), olive groves (223)); finally the generic agricultural classes 241, 231, 242, 243 and 244. CORINE area is accumulated within the cell, class by class, until it equals or exceeds the cell's IA; the IA is then distributed over the selected pixels proportionally to their CORINE agricultural area.
The irrigated area assigned to each model grid-cell is capped at the maximum available extent (fraction of "other" + "irrigated" - as calculated in [Choulga et al., 2024](https://hess.copernicus.org/articles/28/2991/2024/)- and multiplied by the pixel area). Any excess area is redistributed to neighbouring pixels of the same 10 km EIM2010 cell that still have available capacity, so that the cell total is preserved wherever physically possible.
The resulting field is converted to a per-pixel fraction and merged with the current fracirrigated map by taking, for each grid-cell, the maximum of the two values. This preserves irrigated areas in countries not covered by EIM2010.
The "other" fraction is recomputed as the residual, fracother = 1 − (fracforest + fracrice + fracwater + fracsealed + fracirrigated). Where this residual would be negative (due to rounding of the new irrigated fraction), the irrigated fraction is reduced accordingly, ensuring that the sum of all fractions equals 1 in every grid-cell. 
The final data was evaluated against the Eurostat irrigated area statistics ([ef_poirrig](https://ec.europa.eu/eurostat/databrowser/view/ef_poirrig/default/map?lang=en), including irrigated greenhouse areas), by summing the mapped irrigated area (including rice) over NUTS regions and comparing country totals against the reported values.

#### Global Domamin
The global workflow (used for the global 3 arcmin domain, e.g. GloFAS) is based on the FAO Global Map of Irrigation Areas v5.0 (Siebert et al., 2013), provided at 5 arcmin resolution. Two GMIA layers are used: the area equipped for irrigation (AEI) in hectares per grid-cell (gmia_v5_aei_ha), and the area actually irrigated expressed as a percentage of the area equipped for irrigation (gmia_v5_aai_pct_aei).
The area actually irrigated in each 5 arcmin cell is obtained by scaling the equipped area by the actually-irrigated percentage, AAI [ha] = AEI × (AAI% / 100). This is divided by the grid-cell area (converted from m² to hectares) to give the fraction of the cell that is actually irrigated: fracirrigated = (AEI × AAI% / 100) / (cell_area / 10000). By construction this fraction lies in [0, 1]; cells with no equipped area are set to 0.
The resulting field is interpolated from the 5 arcmin FAO grid onto the model grid (3 arcmin) by bilinear interpolation, and any negative or missing values produced by the interpolation are set to 0.
As in the European workflow, the irrigated fraction assigned to each grid-cell is capped at the maximum available extent, defined as the sum of the current "other" and "irrigated" fractions (forest, rice, water and sealed fractions cannot be converted to irrigated land). Where the interpolated irrigated fraction exceeds this maximum, it is set to the maximum, and the new irrigated fraction is rounded to three decimals.
The "other" fraction is then recomputed as the residual, fracother = 1 − (fracsealed + fracwater + fracforest + fracrice + fracirrigated). Where this residual would be negative (because the sum of the fixed fractions plus the new irrigated fraction exceeds 1), the irrigated fraction is reduced by the amount of the overshoot so that the residual becomes zero and all fractions sum to 1. Any remaining negative values in the irrigated and other fractions are set to 0.

### Results (example)

<p float="left">
  <img src="../media/Static-Maps/fracirrigated_European_01min.png" width="329" />
  <img src="../media/Static-Maps/fracirrigated_Global_03min.png" width="513" /> 
</p>

*Figure 12: Fraction of irrigated crops map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*


## Fraction of rice crops
### General map information and possible source data


| Map name | File name;type | Units; range | Description |
| :---| :--- | :--- | :--- |
|Fraction of rice      | fracrice.nc; <br> Type: Float32          | Units: -;<br> Range: [0-1]         |Irrigated rice fraction for each grid-cell; <br>values range from 0 (grid-cell has no irrigated rice) to 1 (grid-cell is fully covered with irrigated rice)|


| Source data| Reference/preparation | Temporal coverage | Spatial information |
| :---| :--- | :--- | :--- |
|Spatial Production Allocation Model (SPAM) - Global Spatially-Disaggregated Crop Production Statistics Data for 2010 (V 1.0)  |[Spatial Production Allocation Model](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/PRFF8V)  |2018        |Global, 5 arcmin (approx 10 km)|
|CORINE Land Cover 2018 CLC2018   |[CLC2018](https://land.copernicus.eu/pan-european/corine-land-cover)      |2018        |European, 100 m|

### Methodology

To create the fraction of irrigated rice map, multiple data sources can be used, for example when more accurate information could be found regionally compared with a global dataset. We describe here the process when using two datasets.<br>
For a global coverage, the 'spam2010v1r0_global_physical-area_rice_i' file from the SPAM dataset is used. It describes the area (in hectares) where crop is grown, not considering how often its production is harvested, with 'i' denoting a portion of the crop is irrigated. The area of irrigated rice values translated from hectares to fractions per grid-cell, and the native resolution is changed to the highest resolution of all datasets used, here CORINE dataset 100 m resolution.<br>
For a regional coverage (here Europe), the '213' - ‘Rice field’ value from the CORINE dataset is used (discrete classification where each grid-cell is fully covered with a certain land cover), assigning grid-cells covered with irrigated rice fraction 1.<br>
Finally, the generated fields are merged, with priority given to the high quality dataset (here from CORINE) over its geographical domain (here over the European domain), and the merged field resolution is reduced to the needed resolution, e.g. 1 arc min, with mean() reducer.<br>
Note: Irrigated rice fraction field should be checked for consistency with all other fractions.<br>

### Results (example)

<p float="left">
  <img src="../media/Static-Maps/fracrice_European_01min.png" width="329" />
  <img src="../media/Static-Maps/fracrice_Global_03min.png" width="513" /> 
</p>

*Figure 13: Fraction of rice crops map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*



## Fraction of other land use type
### General map information and possible source data


| Map name | File name;type | Units; range | Description |
| :---| :--- | :--- | :--- |
|Fraction of other land use type     | fracother.nc; <br> Type: Float32          | Units: -;<br> Range: [0-1]         |Other (e.g. agricultural areas, non-forested natural areas, pervious surface of urban areas)<br> land cover type (not mentioned above) fraction for each grid-cell; <br>values range from 0 (grid-cell has no other land cover type) to 1 (grid-cell is fully covered with other land cover type); <br>computed in a following way: fraction_other = 1 - (fraction_inlandWater + fraction_urban + fraction_forest + fraction_irrigatedCrop + fraction_irrigatedRice + fraction_oceanWater)|


| Source data| Reference/preparation | Temporal coverage | Spatial information |
| :---| :--- | :--- | :--- |
|Fraction of inland water|It can be prepared by implementing [this methodology](../4_Static-Maps_land-use#fraction-of-inland-water)|NA|Global|
|Fraction of sealed surfaces|It can be prepared by implementing [this methodology](../4_Static-Maps_land-use#fraction-of-sealed-surfaces)|NA|Global|
|Fraction of forest|It can be prepared by implementing [this methodology](../4_Static-Maps_land-use#fraction-of-forest)|NA|Global|
|Fraction of irrigated crops|It can be prepared by implementing [this methodology](../4_Static-Maps_land-use#fraction-of-irrigated-crops)|NA|Global|
|Fraction of rice|It can be prepared by implementing [this methodology](../4_Static-Maps_land-use#fraction-of-rice-crops)|NA|Global|

### Methodology
Note: This map was updated using the new irrigated fraction map. Hence even if the following methodology is generally valid to calculate the "other fraction", the layer was updated using the formula: fracother = 1 − (fracforest + fracrice + fracwater + fracsealed + fracirrigated), as described in the "Fraction of irrigated" crops section

Here the other land cover type map is created based on all other fraction maps required by LISFLOOD model. It should be noted that: i) all fraction maps together (including fraction of other land cover type) should sum up to 1 in each grid-cell, and ii) consistency check for all fractions must be done because data come from different sources and it can happen that fractions summed can result to more than 1. <br>
The following procedures are recommended to check consistency between fraction maps. All fractions are summed up to compute the other land cover type fraction map. If the fraction sum is less than 1, then the other land cover type fraction is calculated as 1 minus all fraction sum, else other land cover type fraction is 0. For cases when the sum is greater than 1, a correction for forest, irrigated crops, rice, and sealed surface fractions is computed: <br>

$ \small fractionCorrectionFactor=\frac{fractionAllSum-1}{fractionForest+fractionIrrigated+fractionRice+fractionSealed}$

Finally, if data sources for forest, irrigated crops, rice, and sealed surfaces fractions have the same level of uncertainty, each of these fractions are corrected in the same way at the needed resolution (e.g. 1 and 3 arc min):<br>

$ \small fractionCorrectedX = fractionX - (fractionX \cdot fractionCorrectionFactor) $<br>
where X is Forest, Irrigated, Rice, Sealed.

### Results (example)

<p float="left">
  <img src="../media/Static-Maps/fracother_European_01min.png" width="329" />
  <img src="../media/Static-Maps/fracother_Global_03min.png" width="513" /> 
</p>

*Figure 14: Fraction of other land use type map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right).*
