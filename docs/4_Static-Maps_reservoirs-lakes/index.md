# Reservoirs and lakes 

Lakes and reservoirs can be defined as a significant volume of water, which occupies a depression of the land and has no direct connection with a sea. They can intensify winter snowstorms, increase precipitation or/and surface temperature, generate night convection and intensive thunderstorms. Lakes and reservoirs can influence the atmosphere regionally and globally.<br>

The modelling of lakes and reservoirs requires three maps and a set of txt files.

 
## Lake mask map

The lake mask map represents the area covered by lakes and reservoirs, it is used for computing evaporation from open water surfaces.

### General map information and possible source data

| Map name | File name;type | Units; range | Description |
| :---| :--- | :--- | :--- |
| Lake mask| lakemask.nc; <br>Type: Float32 |  Units: -; <br>Range: 0 or 1 | Map of the footprint of lakes|


| Source data| Reference/preparation | Temporal coverage | Spatial information |
| :---| :--- | :--- | :--- |
|Global Lakes and Wetlands Database (GLWD): <br>Large Lake Polygons (Level 1) |[GLWD leve1](https://www.worldwildlife.org/publications/global-lakes-and-wetlands-database-large-lake-polygons-level-1)|2004|Global, 1:1 to 1:3 million resolution|
|Global Lakes and Wetlands Database (GLWD): <br>Small Lake Polygons (Level 3) |[GLWD leve1](https://www.worldwildlife.org/publications/global-lakes-and-wetlands-database-large-lake-polygons-level-2)|2004|Global, 1:1 to 1:3 million resolution|
|Fraction of inland water| It can be prepared by using<br> the methodology explained [here](../4_Static-Maps_land-use#lend-use)|NA|Global|

### Methodology

Fraction of inland water map is adjusted to the LISFLOOD model – all grid-cells fully covered with ocean water that are considered during computations are filled with inland water. <br>
If a grid-cell has any fraction of inland water and is inside the GLWD Level 1 and GLWD level 2 lake shapefiles, it is marked as ‘1’ (fully covered), otherwise it is marked as ‘0’.<br>


### Results (examples)


<p float="left">
  <img src="../media/Static-Maps/lakemask_European_01min.png" width="329" />
  <img src="../media/Static-Maps/lakemask_Global_03min.png" width="513" /> 
</p>

*Figure 53: Lakemask map at 1 arc min horizontal resolution for European domain (left) and at 3 arc min horizontal resolution for Global domain (right) with coloured areas showing land pixel.*

## Reservoirs map and tables 

Reservoirs having degree of regulation below 0.08 are more accurately modelled as lakes.

## Lakes map and tables 

Lakes are identified using a unique integer number (ID).
The lakes map represent the outflow location of a lake: each outflow point has the ID of the relevant lake. Modelling of lakes within OS LISFLOOD then requires the following pieces of information: lake surface area, average inflow to the lake, width of the lake outlet. The latter information is provuided to the code in .txt format (these txt files are traditionally called OS LISFLOOD tables).


### General map and tables information and possible source data

| Map/table name | File name; type | Units; range | Description |
| :---| :--- | :--- | :--- |
|Lakes|lakes.nc; <br>Type: Float32|Units: -; <br>Range: integer  ID number to identify each lake |Lake outflow location <br> (stores lake ID number in the metadata file)|
|lakea| lakea.txt; <br>2 columms: ID VALUE; 1 row for each lake|Units: m|Width of the outltet of the lake|
|lakerea| lakearea.txt; <br>2 columms: ID VALUE; 1 row for each lake|Units: m2|Lake surface area|
|lakeavginflow| lakeavginflow.txt; <br>2 columms: ID VALUE; 1 row for each lake|Units: m3/s|Average inflow to the lake|

[HydroLAKES](https://www.hydrosheds.org/products/hydrolakes) is a relevant example of source of data for lakes map and tables.

### Methodology

As a first step, it is recommended to create a file including all lakes information required by OS LISFLOOD and some relevant metadata that can help with model analysis and results description.
Essential information are

1. Lake unique identifier, selected by the user or taken from external datasets;
2. Geographic oordinates of the lake outlet;
3. Coordinates of the lake outlet mapped on OS LISFLOOD local drainage direction map  ([ldd](https://ec-jrc.github.io/lisflood-code/4_Static-Maps_topography/));
4. Lake surface area;
5. Lake outlet width;
6. Average inflow to the lake.

Optional metadata are:
7. Lake catchment area [km2 or m2]
8. Lake name 
9. Lake country
10. Lake identifier in other dataset
11. Source of information 4,5,6

Lake unique identifier (1) and coordinates of the outlet mapped on the OS LISFLOOD local drainage direction map  ([ldd](https://ec-jrc.github.io/lisflood-code/4_Static-Maps_topography/)) (3) are required to generate the lake map. Geographic oordinates of the lake outlet (2) and OS LISFLOOD local drainage direction map  ([ldd](https://ec-jrc.github.io/lisflood-code/4_Static-Maps_topography/)) are essential to generate (3), for this step, the comparison between lake catchment area (7) and OS LISFLOOD [upstream area map](https://ec-jrc.github.io/lisflood-code/4_Static-Maps_topography/) is strongly recommended.

Lake surface area can be retrieved from local datasets or global datasets such as HydroLAKES](https://www.hydrosheds.org/products/hydrolakes), [GLWD](https://www.hydrosheds.org/products/glwd), [GRAND](https://www.globaldamwatch.org/grand).

Where lake outlet width cannot be retrieved from external datdaset, it can be measured with GIS tools.

Finally, lake average inflow can be retrieved from observed time series (where available) or numerical model results.

Lake maps and tables of the European 1arcmin domain and global 3arcmin domain are based on information from [HydroLAKES](https://www.hydrosheds.org/products/hydrolakes).
Lake outlet width was generally measured with GIS tools; lake average inflow was computed using OS LISFLOOD CEMS EFAS and CEMS GloFAS discharge reanalysis (GloFASv4 reanalysis for GloFASv5 tables; EFASv5 naturalized flow for EFASv6 tables).
