# Water use maps and water use related information

This chapter describes the main features of time variant (transient) sectoral water demand maps for domestic, livestock, industrial, energy (cooling) sectors. 
This chapter then focuses on the description of the ancillary maps required by OS LISFLOOD for the modelling of water abstraction from groundwater, surface water (channels, lakes, reservoirs), and non-conventional sources (e.g. desalination plants). 
In this documentation, water demand is the amount of water required to meet the needs of the vaious uses. Water abstraction or water withdrawal (considered synonyms) is the amount of water to be abstracted from surface of groundwater resources to meet water demand requirements. Water abstraction/withdrawal is generally larger than water demand to account for leakages and other losses in the water supply system. Consumptive use is the water volume used and removed from the hydrological cycle.

## Sectoral water demand maps

Sectoral water demand maps indicate, for each pixel, the time-varying water demand value to supply for domestic, livestock, industrial, and thermoelectric water consumption. The segregation of the total water demand for anthropogenic use into four main sectors, namely domestic, energy, industrial and livestock water demand, enables a more accurate representation of the processes and follows the Food and Agriculture Organisation of the United Nations (FAO) terminology ([Kohli et al., 2012](https://openknowledge.fao.org/server/api/core/bitstreams/f18d9669-c967-4e37-b466-b7dc7ab78f8d/content)).
Domestic water demand represents indoor and outdoor household water use as well as other uses (e.g. industrial and urban agriculture) connected to the municipal system (e.g. water use by shops, schools and public buildings). Electricity (energy) water demand is the water use for the cooling of thermoelectric and nuclear power plants. Water demand for industry is the water used for fabricating, processing, washing, cooling or transporting products and also includes water within the final products and water used for sanitation within the manufacturing facility. Livestock demand is the water used for drinking and cleaning purposes of livestock ([Choulga et al. 2024](https://hess.copernicus.org/articles/28/2991/2024/)).

The temporal discretization of these maps (e.g. daily, monthly, yearly update frequency) can be chosen by the modeller, mainly depending on the modelling purposes and on the available input data. The time convention is described in [this section](https://ec-jrc.github.io/lisflood-model/2_18_stdLISFLOOD_water-use/) of the OS LISFLOOD model documentation.

European 1arcmin and global 3arcmin sectoral water demand maps were generated using the OS LISFLOOD utility [water-demand-historical](https://github.com/ec-jrc/lisflood-utilities/tree/master/src/lisfloodutilities/water-demand-historic). 
This user guide provides an overview of the protocol implemented to produce domestic and energy demand maps with values updated monthly, industrial and livestock demand maps with values updated yearly. The generation of the maps relies on a number of external datasets: the complete list of external datasets and step-wise instructions are provided in the readme of the OS LISFLOOD utility [water-demand-historcal](https://github.com/ec-jrc/lisflood-utilities/tree/master/src/lisfloodutilities/water-demand-historic).
[FAO AQUASTAT](https://www.fao.org/aquastat/en/) constitues the main source of information: specifically, country level data of water withdrawal. Therefore, it must be noted that, strictly speaking, these maps represent water withdrawal rather than water demand. As explained in this page, this discrepancy can be accounted for by adequately setting ancillary OS LISFLOOD inputs such as $leakage fraction$.

Domestic water withdrawal estimates rely on FAO AQUASTAT municipal water withdrawal estimate per country and per year. Spatial disaggregation is achieved based on population data ([Global Human Settlement Layer](https://human-settlement.emergency.copernicus.eu/index_op.php)). Temporal downscaling to monthly frequency relies on monthly air temperature grids (e.g. [MSWX, Beck et al., 2022](https://journals.ametsoc.org/view/journals/bams/103/3/BAMS-D-21-0145.1.xml)) and literature parameters ([Hunag et al., 2018](https://hess.copernicus.org/articles/22/2117/2018/))

Industrial and energy water withdrawal estimates are based on country-scale FAO AQUASTAT industrial withdrawal data, country-scale [World Bank](https://data.worldbank.org/) manufacturing value added (MVA) data, [Global Change Analysis Model, GCAM](https://github.com/JGCRI/gcam-core/releases) regional industry and thermoelectric withdrawals, datasets avaible in the literature (e.g. Global-scale gridded estimates of thermoelectric power and manufacturing water use by [Vassolo & Doll, 2005](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2004WR003360)). Spatial downscaling is based on population grids (due to the lack of more precise data sources). Temporal downscaling of energy water withdrawal estimates rely on temperature information.

Country-scale livestock withdrawals estimates leverage on the difference between the FAO AQUASTAT data of agriculture and irrigation withdrawals, and on GCAM regional livestock withdrawals. Spatial downscaling is performed based on [Gridded Livestock of the World](https://www.nature.com/articles/sdata2018227).

The protocol for the generation of water withdrawal maps relied on a number of assumptions due to the lack of homogenous and granular data at the continental and global scale. Even at the country scale, information is not available for all countries, and for all years. Gaps in space and time were filled using nearest-neighbor interpolation and linear interpolation, respectively.


### Groundwater bodies 

The map of groundwater bodies is a boolean map indicating the spatial distribution of groundwater exploitable resources: OS LISFLOOD allows abstraction from the lower groundwater zone only in pixels with value equal 1.

This map can be generated using local, regional, continental, or global scale source data, depending on the specific OS LISFLOOD application.

Examples of continental scale source data are  (BGR & UNESCO) and [Africa Groundwater Atlas](https://www.bgs.ac.uk/geology-projects/africa-groundwater-atlas/) ([BGS](https://www.bgs.ac.uk/)).

The [Groundwater Resources of the World](https://www.whymap.org/whymap/EN/Maps_Data/Gwr/gwr_node_en.html) of the World-wide Hydrogeological Mapping and Assessment Programme (WHYMAP) is an example of source data for the global domain.

Global 3 arcmin groundwater bodies map was produced leveraging on two datasets: [Groundwater Resources of the World](https://www.whymap.org/whymap/EN/Maps_Data/Gwr/gwr_node_en.html) and the global map of bedrock elevation [GDEMM2024](https://www.nature.com/articles/s41597-024-03920-x). Albeit the first dataset was specifcally derived to highlight exploitable groundwater resources, the use of GDEMM2024 was considered useful to ensure the consistency between the global map of groudwater bodies and the available information on country-level groundwater abstraction (more details in the section **Sectoral water demand maps**). It was decided to ensure the presence of at least one groundwater pixel in all countries that reported some groundwater abstraction. According to this approach, exploitable groudwater bodies in the global 3arcmin map have larger extent than the data shown in the Groundwater Resources of the World. It is of parmount importance to acknowledge the uncertainty of the source data for the generation of water withdrawal and releated maps: the first version of the global 3arcmin map prioritized the consistency with country level data of water withdrawal (**Sectoral water demand maps**). 

European 1 arcmin groundwater bodies map was generated using the [International Hydrogeological Map of Europe, IHME1500](https://www.bgr.bund.de/EN/Themen/Grundwasser/Projekte/Flaechen-Rauminformationen/Ihme1500/ihme1500.html) v 1.2 as main data source. Specifically, groundwater resources were deemed available for the areas belonging to the following classes: *I. Predominally porous rocks; II. Predominnally fissured rocks, including karstified rocks; IIIa. Locally acquiferous rocks*. This approach satisfied the cross-check with available information on country level water abstraction from groundwater (for details, please see **Sectoral water demand maps**).
Groundwater bodies of areas of the European extended domain (as defined in the [introduction to the static maps](https://ec-jrc.github.io/lisflood-code/4_Static-Maps-introduction/)) not covered by IHME1500 were derived from the global map of groundwater bodies. To avoid abrupt discontinuities, the two datasets were merged at the country level. 

### Fraction of water abstraction from groundwater, surface water, non-conventional resources
OS LISFLOOD allows water abstraction from groundwater, surface water, non-conventional sources (e.g. desalinization plants). The maps fraction of water abstraction from groundwater (fracgroundwateruse) and fraction of water abstraction from non-conventional sources (fracnonconventionalwateruse) provide information on the proportion of the total water demand that must be provided by groundwater resources and non-conventional water sources, respectively. 

Information is provided to the OS LISFLOOD code at the pixel level. However, the actual granularity of the map depends on the spatial resolution of the model exercise and on the available data. Generally speaking, spatial allocation of water demand to the three sources should be defined at the water region level. 

The fraction of water to be abstracted from groundwater, $fracgroundwateruse$, is computed in two subsequent steps.  

The first step requires the computation of fracgroundwateruse of the ratio of water withdrawal from groundwater and total water widthdrawal, both quantities are aggreagated values over the same spatial domain (e.g. water region, country).

$$
fracgroundwateruse_1 = \frac{water withdrawal from groundwater}{total water withdrawal}
$$

$fracgroundwateruse_1$ represents then the average value for chosen spatial domain.
Pixel values of $fracgroundwateruse$ must account for the proportion of exploitable groundwater resources within the spatial domain: $fracgroundwateruse$ must be zero in pixels with no exploitable groundwater resources, and fraction values in the remaining pixels must be adjusted accordingly. The second step is then defined as follows:

$$
fracgroundwateruse = min(( fracgroundwateruse_1 * \frac{area_T}{area_G} * groundwaterbodies), 1-fracnonconventionalwateruse)
$$

$groundwaterbodies$ is the boolean with 1 values where groundwater is available. $area_T$ and $area_G$ are the total area of the spatial domain and the area with available groundwater within the spatial domain, respectively.

$fracnonconventionalwateruse$ is the fraction of water derived from non-conventional water sources (e.g. desalination) within the spatial domain. It is computed as the ratio of water withdrawal from groundwater and total water widthdrawal, as before, both quantities are aggreagated values over the same spatial domain (e.g. water region, country).

$$
fracnonconventionalwateruse =  \frac{water withdrawal from non conventional sources}{total water withdrawal}
$$

Finally, the proportion of water demand to be satisfied by surface water resources is computed internally by OS LISFLOOD as:

$$
fracsurfacewateruse = 1 - (fracgroundwateruse + fracnonconventionalwateruse)
$$

Information of water withdrawal from the three sources must be retrieved from external datasets.

European 1arcmin and global 3arcmin maps were generated levaraging on country level information made available from [FAO AQUASTAT](https://www.fao.org/aquastat/en/). Data were retrieved in 2024: the most recent information referred to the year 2021. 
The database provides information at the country level, nevertheless, information is not available for all countries, and different variables are available for different countries.
The implementented methdology aimed to maximize the exploitation of available information.
Total water withdrawal was either directly provided or defined as the sum of the other available infomration (surface water abstraction, groundwater abstraction, desalinated water, treated waste water, reuse of drained waeter from agricoluture, https://www.fao.org/aquastat/en/databases/glossary/). Groundwater withdrawal was either directly provided or computed as the complementary of the sum of the other variables.
Despite the attempt to maximize the exploitation of FAO AQUASTAT information, fraction of groundwater use could not be computed for some countries. The filling was done based on nearest neighbour approach. To avoid enforcing "extreme" scenarios to countries with no info, only values in the interval [0.15, 0.85] were transferred from the closest neighbors. If the three closest countries did not have information or had values outside of the interval [0.15, 0.85], the fill value was 0.5.
When using FAO AQUASTAT database, water withdrawal from non conventional sources was defined equal to the variable 'desalinated water produced'. Conutries were the latter variable was not availeble were allocated 0 value of $fractionofnonconventional$ water use. It is here noted that this water source is "outside" of the hydrological cycle modelled by LISFLOOD (oceans are not modelled!). Desalination plants processing water of lakes in landlocked countries are, on the contrary, retrieving water from the hydrological cycle modelled by LISFLOOD: to be consistent with the model implementation, the latter quantied did not contribute to the computation of $fractionofnonconventional$ water use, but were added to the abstraction from surface water bodies.

Clearly, leveraging on country level information leads to changes along the country borders which are generally not consistent with the physical groundwater and surface water basins. Where possible, it is recommmeded to use information at the basin or water region scale. 

### Fraction of consumptive water use
The fraction of consumptive water use defines the portion of water abstraction which is consumed and leaves the hydrological cycle. It applies to domestic, livestock, energy (cooling), and industrial uses; each fraction can be set independently as a constant for the entire modelling domain (by introducing the desired values in the OS LISFLOOD settings file) or as a map including more granular information, ideally segregated according to water regions.

Fractions of consumptive water use maps are currently not available for the European 1arcmin and global 3arcmin domains. Constant value were retrieved from the report of [Bisselink et al, 2018](https://publications.jrc.ec.europa.eu/repository/handle/JRC110927): 0.2 domestic consumptive use, 0.15 livestock consumptive use, 0.17 energy consumptive use, 0.15 industrial consumptive use.

### Irrigation efficiency, irrigation conveyance efficiency, irrigation multiplier
Water demand for irrigation is computed internally by the code according to soil mosture decific and crop type.
Irrigation efficiency, irrigation conveyance efficiency, irrigation multiplier are used to adjust the water demand to compute the volume to be abstracted for irrigation.
This value, included between 0 and 1, can be a constant over the entire modelling domain (by introducing the desired values in the OS LISFLOOD settings file) or a map.
The European 1arcmin domain makes use of a map with data at the level of NUTS2 regions and information retreived from [De Roo et al, 2020](https://publications.jrc.ec.europa.eu/repository/handle/JRC120388) (Figure 3, Benitez et al, 2018). 
The global 3arcmin domain currently makes use of 0.75 constant value, as indicated in [Bisselink et al, 2018](https://publications.jrc.ec.europa.eu/repository/handle/JRC110927).
Conveyance efficiency depends on how water is delivered to the fields, it is always included between 0 and 1, the lower the value, the larger the water abstraction for irrigation. It can be a constant value or a map. European 1 arcmin and global 3arcmin domains curretly use 0.8 constant value, as indicated in [Bisselink et al, 2018](https://publications.jrc.ec.europa.eu/repository/handle/JRC110927).
Irrigation multiplier is a factor larger than 1 applied to increase water demand for irrigation, to mimic the additioanl water abstraction required to prevent soil salinitization. The currently implemented value is 1.2. 

### Domestic leakage fraction and domestic water saving fraction
Domestic leakage fraction is used to account for  the leakages from pipes in urban water supply systems: this value must be lower than 1, 0 indicates absence of leakages. Within the code, domestic leakage fraction values larger than 0 are used to compute a multiplier (>1) of water demand for domestic use to compute water abstraction for domestic use.
Conversely, domestic water saving fraction reduces water demand, and, consequently, water abstraction.
For both inputs, OS LISFLOOD accepts a constant value or a map. The reports [Bisselink et al, 2018](https://publications.jrc.ec.europa.eu/repository/handle/JRC110927) and [De Roo et al, 2020](https://publications.jrc.ec.europa.eu/repository/handle/JRC120388) provide information on domestic leakage and water saving fraction, respectively.
In the current European 1arcmin and global 3arcmin set-ups,domestic leakage fraction is set to 0: water demnad maps are computed leveraging on water withdrawal values reported by FAO AQUASTAT[https://www.fao.org/aquastat/en/], which should, by definition, already account for leakages.

### Water regions map
As the spatial resolution of the model increases, the assumption of coincidence between demand and abstraction locations within the same model grid cell becomes increasingly invalid. To address this limitation, the concept of water regions is introduced. A water region is defined as a subcatchment where demand and abstraction activities occur, allowing for a more accurate representation of the spatial relationships between these processes. 
*Water regions* are generally defined by sub-river-basins within a Country. In order to mimick reality, it is advisable to avoid cross-Country-border abstractions. Whenever information is available, it is strongly recommended to align the *water regions* with the actual areas managed by water management authorities, such as regional water boards. In Europe, the River Basin Districts, as defined in the Water Framework Directive and subdivided by country, can be used.

#### Consistency between water region map and model calibration protocol

Water resourses (surface water bodies and groundwater) are shared inside the water region in order to meet the cumulative requirements of the entire water region area. For this reason, it is strongly recommended to include the entire water region(s) in the modelled area. If a portion of the water region is not included in the modelled area, then LISFLOOD cannot adequately compute the water demand and abstraction (it is important to notice that LISFLOOD will not crush but the results will be affected by this discrepancy).

**The inclusion of the complete water region in the computational domain becomes compulsory when performing catchment-based calibration, where parameters are optimized separately for each catchment inside the larger computational domain**. In this case, calibrated parameters are optmised for a specific model model domain. Each calibration domain must include a finite number of water regions (and each water region must be entirely included in one catchment). If and only if this condition is not met, the calibrated parameters can be correctly optimised. Conversely, when a water region belongs to one or more calibration catchments, the water resources are allocated and abstracted in different quantities during calibration as opposed to the modelling of the entire basin. 

The utility [waterregions](https://github.com/ec-jrc/lisflood-utilities) can be used to 1) verify the consistency between calibration catchments and water regions or 2) create a water region map which is consistent with a set of calibration points.

Current European 1arcmin and global 3arcmin water regions map were generated to meet the requirement explained above. The list of calibration points, a basemap of the major surface water basins, and the map of country borders were used as input to the OS LISFLOOD utility in the case of the European 1arcmin domain. The list of calibration points and the map of country borders were used as input in the case of the global 3arcmin domain.