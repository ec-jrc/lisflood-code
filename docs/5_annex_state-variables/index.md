**Table:** *State variables, required for warm start of model simulations.*

| Key                            | LISFLOOD file name | LISFLOOD variable     | Unit | Description                                                                                       |
|--------------------------------|--------------------|-----------------------| ---- |---------------------------------------------------------------------------------------------------|
| OFDirectState                  | ofdir              | OFM3Direct            | m3   | Water volume on catchment surface for direct fraction                                             |
| OFOtherState                   | ofoth              | OFM3Other             | m3   | Water volume on catchment surface for other fraction                                              |
| OFForestState                  | offor              | OFM3Forest            | m3   | Water volume on catchment surface for forest fraction                                             |
| ChanCrossSectionState          | chcro              | TotalCrossSectionArea | m2   | Total cross-section area of channel                                                               |
| DSLRState                      | dslr               | DSLR[0]               | day  | Reported days since last rain                                                                     |
| DSLRForestState                | dslf               | DSLR[1]               | day  | Reported days since last rain for forest                                                          |
| DSLRIrrigationState            | dsli               | DSLR[2]               | day  | Reported days since last rain irrigation                                                          |
| SnowCoverAState                | scova              | SnowCoverS[0]         | mm   | Reported snow cover in snow zone A                                                                |
| SnowCoverBState                | scovb              | SnowCoverS[1]         | mm   | Reported snow cover in snow zone B                                                                |
| SnowCoverCState                | scovc              | SnowCoverS[2]         | mm   | Reported snow cover in snow zone C                                                                |
| FrostIndexState                | frost              | FrostIndex            | C/day| Reported frost index                                                                              |
| CumInterceptionState           | cum                | CumInterception[0]    | mm   | Reported interception storage                                                                     |
| CumInterceptionForestState     | cumf               | CumInterception[1]    | mm   | Reported interception storage for forest                                                          |
| CumInterceptionIrrigationState | cumi               | CumInterception[2]    | mm   | Reported interception storage for irrigation                                                      |
| CumIntSealedState              | cseal              | CumInterSealed        | mm   | Reported cumulative depressions storage                                                           |
| Theta1State                    | th1                | Theta1a[0]            | -    | Reported volumetric soil water content for superficial soil layer (1), other fraction [V/V]      |
| Theta1ForestState              | thf1               | Theta1a[1]            | -    | Reported volumetric soil water content for superficial soil layer (1), forest fraction [V/V]     |
| Theta1IrrigationState          | thi1               | Theta1a[2]            | -    | Reported volumetric soil water content for superficial soil layer (1), irrigation fraction [V/V] |
| Theta2State                    | th2                | Theta1b[0]            | -    | Reported volumetric soil water content for upper soil layer (2), other fraction [V/V]            |
| Theta2ForestState              | thf2               | Theta1b[1]            | -    | Reported volumetric soil water content for upper soil layer (2), forest fraction [V/V]           |
| Theta2IrrigationState          | thi2               | Theta1b[2]            | -    | Reported volumetric soil water content upper soil layer (2), irrigation fraction [V/V]           |
| Theta3State                    | th3                | Theta2[0]             | -    | Reported volumetric soil water content for lower soil layer (3), other fraction [V/V]             |
| Theta3ForestState              | thf3               | Theta2[1]             | -    | Reported volumetric soil water content for lower soil layer (3), forest   fraction [V/V]          |
| Theta3IrrigationState          | thi3               | Theta2[2]             | -    | Reported volumetric soil water content for for lower soil layer (3), irrigation  fraction [V/V]   |
| UZState                        | uz                 | UZ[0]                 | mm   | Reported storage in upper groundwater zone, other fraction                                        |
| UZForestState                  | uzf                | UZ[1]                 | mm   | Reported storage in upper groundwater zone, forest fraction                                       |
| UZIrrigationState              | uzi                | UZ[2]                 | mm   | Reported storage in upper groundwater zone, irrigation fraction                                   |
| LZState                        | lz                 | LZ                    | mm   | Reported storage in lower groundwater zone                                                        |
| ChanQState                     | chanq              | ChanQ                 | m3/s | Reported instantaneous discharge at end of the model time step                                      |
| ChanQAvgDtState *L             | chanqavgdt         | ChanQAvgDt            | m3/s | Reported average discharge for the last routing sub-step                                           |
| LakeLevelState *L              | lakeh              | LakeLevel             | m    | Output map(s) with lake level                                                                     |
| LakePrevInflowState *L         | lakeprevinq        | LakeInflowOld         | m3/s | Output map with lake average inflow at previous routing sub-step (ChanQ(t-1))                     |
| LakePrevOutflowState *L        | lakeprevoutq       | LakeOutflow           | m3/s | Output map with lake average outflow at previous routing sub-step (ChanQ(t-1))                    |
| ReservoirFillState *R          | rsfil              | ReservoirFill         | -    | Output map(s) with Reservoir Filling [V/V]                                                        |
| CrossSection2State *SR         | ch2cr              | CrossSection2Area     | m2   | Cross section area for split routing                                                              |
| ChSideState *SR                | chside             | Sideflow1Chan         | m2/s | Sideflow to channel  for 1st line   of routing                                                    |
| PrevCmMCTState *MCT            | prevcm             | PrevCmMCT             | -    | Courant number at previous step for MCT routing                                                   |
| PrevDmMCTState *MCT            | prevdm             | PrevDmMCT             | -    | Reynolds number at previous step for MCT routing                                                  |

*L = this state variable is required when lakes are included in the modelling domain

*R = this state variable is required when reservoirs are included in the modelling domain

*SR = this state variable is required when using the split routing module

*MCT = this state variable is required when using diffusive routing (MCT)

A detailed description of OS LISFLOOD standard and optional modules is available from the [Model Documentation](https://ec-jrc.github.io/lisflood-model/)