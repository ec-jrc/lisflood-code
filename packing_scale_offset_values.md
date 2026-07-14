# Scale/Offset Packing Values — Current Implementation

CF-convention int16 packing as implemented in `default_options.py`.
Formula: `unpacked = packed * scale_factor + add_offset`
Precision = scale_factor / 2

## Packed Variables (Maps outputs)

| Variable(s) | Unit | Design Range | scale_factor | add_offset | Precision (±) |
|-------------|------|--------------|--------------|------------|---------------|
| DischargeMaps | m3/s | 0 – 400,000 | 6.104 | 200000.0 | ±3.05 m3/s |
| DirectRunoffMaps | mm | 0 – 400 | 0.006104 | 200.0 | ±0.003 mm |
| ESActForestMaps, ESActMaps, ESRefMapsOut | mm | 0 – 20 | 3.052e-4 | 10.0 | ±1.5e-4 mm |
| ETActMaps, ETActBudykoMaps | mm | -10 – 1000 | 0.01541 | 495.0 | ±0.0077 mm |
| ETRefMapsOut | mm | 0 – 20 | 3.052e-4 | 10.0 | ±1.5e-4 mm |
| EWIntForestMaps, EWIntMaps | mm | 0 – 20 | 3.052e-4 | 10.0 | ±1.5e-4 mm |
| EWRefMapsOut, EWater | mm | 0 – 20 | 3.052e-4 | 10.0 | ±1.5e-4 mm |
| FastRunoffMaps | mm | 0 – 500 | 0.007630 | 250.0 | ±0.0038 mm |
| GwPercUZLZ (all variants) | mm | 0 – 3 | 4.578e-5 | 1.5 | ±2.3e-5 mm |
| InfiltrationForestMaps, InfiltrationMaps | mm | 0 – 500 | 0.007630 | 250.0 | ±0.0038 mm |
| InterceptionForestMaps, InterceptionMaps | mm | 0 – 15 | 2.289e-4 | 7.5 | ±1.1e-4 mm |
| MonthETactMM | mm | 0 – 300 | 0.004578 | 150.0 | ±0.0023 mm |
| MonthETdifMM | mm | -300 – 300 | 0.009156 | 0.0 | ±0.0046 mm |
| MonthETpotMM | mm | 0 – 300 | 0.004578 | 150.0 | ±0.0023 mm |
| PrecipitationMaps, RainMaps | mm | 0 – 1000 | 0.01526 | 500.0 | ±0.0076 mm |
| PrefFlow (all variants) | mm | 0 – 400 | 0.006104 | 200.0 | ±0.003 mm |
| SeepSubToGWMaps | mm | 0 – 60 | 9.156e-4 | 30.0 | ±4.6e-4 mm |
| SnowCoverMaps | mm | 0 – 10000 | 0.15260 | 5000.0 | ±0.076 mm |
| SnowMaps | mm | 0 – 200 | 0.003052 | 100.0 | ±0.0015 mm |
| SnowMeltMaps | mm | 0 – 250 | 0.003815 | 125.0 | ±0.0019 mm |
| SurfaceRunoffMaps | mm | 0 – 500 | 0.007630 | 250.0 | ±0.0038 mm |
| TaOtherMaps, TaForestMaps, TaIrrigationMaps, TaMaps | mm | -10 – 15 | 3.815e-4 | 2.5 | ±1.9e-4 mm |
| Theta (all Maps variants: 1/2/3, Other/Forest/Irrigation) | - | 0 – 1 | 1.526e-5 | 0.5 | ±7.6e-6 |
| TotalRunoffMaps, TotalToChanMaps | mm | 0 – 500 | 0.007630 | 250.0 | ±0.0038 mm |
| TransLossMaps | mm | 0 – 600 | 0.009156 | 300.0 | ±0.0046 mm |
| UZForestMaps, UZIrrigationMaps, UZMaps | mm | 0 – 3500 | 0.05341 | 1750.0 | ±0.027 mm |
| UZOutflow (all variants) | mm | 0 – 300 | 0.004578 | 150.0 | ±0.0023 mm |
| WaterDepthMaps | mm | 0 – 250 | 0.003815 | 125.0 | ±0.0019 mm |

## NOT Packed (scale_factor = None)

These variables have no packing defined and will always be written as float:

- All `*End` maps (End maps — warm start, full precision needed)
- All `*State` maps (State maps — warm start, full precision needed)
- TotalWaterStorageMaps (range too large for useful int16 precision)
- TavgMapsOut (temperature — no packing defined)
- All water use / indicator variables (monthly aggregations, various ranges)
- FalkenmarkM3Capita1, EFlowIndicator, etc. (specialized indicators)

## Notes

- Packing is only active when `OutputPacking = True` in settings XML
- All values derived from GloFAS global run observed min/max with 20-50% headroom
- Theta uses theoretical range 0–1 (physically bounded)
- Precision column shows maximum quantization error (half a scale_factor step)
- Clipping warning fires once per variable if values exceed design range
