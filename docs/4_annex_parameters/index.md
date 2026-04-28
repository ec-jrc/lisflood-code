**Table:** *Parameters range and default values.*

| ParameterName                  | MinValue           | MaxValue           | DefaultValue       | 
| :----------------------------- | -----------------: | -----------------: | -----------------: | 
| UpperZoneTimeConstant | 0.01 | 40 | 10 | 
| LowerZoneTimeConstant | 40 | 730 | 100 | 
| GwPercValue | 0.01 | 2 | 0.8 | 
| LZThreshold | 0 | 30 | 10 | 
| b_Xinanjiang | 0.01 | 5 | 0.5 | 
| PowerPrefFlow | 0.5 | 8 | 4 | 
| SnowMeltCoef | 2.5 | 6.5 | 4 | 
| CalChanMan1 | 0.5 | 2 | 1 | 
| GwLoss | 0 | 1.0 | 0 | 
| CalChanMan2 *SR  | 0.5 | 5 | 1 | 
| CalChanMan3 *MCT  | 0.5 | 5 | 1 | 
| LakeMultiplier *L | 0.5 | 2 | 1 | 
| ReservoirFloodStorage *R| 0.5 | 0.99 | 0.75 |
| ReservoirFloodOutflowFactor *R | 0.1 | 0.5 | 0.3 |
| QSplitMult *SR | 0 | 20 | 2 | 
| TransSub *TL | 0 | 0.15 | 0 | 

*L = this parameter is required when lakes are included in the modelling domain

*R = this parameter is required when reservoirs are included in the modelling domain

*SR = this parameter is required when using the split routing module

*MCT = this parameter is required when using diffusive routing (MCT)

*TL = this parameter is required when the transmission loss module is active

A detailed description of OS LISFLOOD standard and optional modules is available from the [Model Documentation](https://ec-jrc.github.io/lisflood-model/)



*The reservoir modelling routine was updated with OS LISFLOOD v5: the updated methodology is described in [this page](https://ec-jrc.github.io/lisflood-model/3_03_optLISFLOOD_reservoirs/). Former versions of OS LISFLOOD code required the following parameters for reservoir modelling:*
| ParameterName                  | MinValue           | MaxValue           | DefaultValue       | 
| :----------------------------- | -----------------: | -----------------: | -----------------: | 
| adjust_Normal_Flood | 0.01 | 0.99 | 0.8 | 
| ReservoirRnormqMult | 0.25 | 2 | 1 | 