# Scale/Offset Packing Values for LISFLOOD Output Variables

Based on actual GloFAS global run min/max values, with ~20-50% headroom above observed max.

Formula: `scale_factor = (vmax - vmin) / 65534`, `add_offset = vmin + scale_factor * 32767`

Only time-series outputs (Maps/All) are listed. State/End maps should NOT be packed.

| Variable | Unit | Obs Min | Obs Max | Design Min | Design Max | scale_factor | add_offset | Precision (±) |
|----------|------|---------|---------|------------|------------|--------------|------------|---------------|
| dis (DischargeMaps) | m3/s | 0 | 2.93e5 | 0 | 400000 | 6.1040 | 200000.0 | ±3.05 m3/s |
| chanq | m3/s | 0 | 2.93e5 | 0 | 400000 | 6.1040 | 200000.0 | ±3.05 m3/s |
| chanqavgdt | m3/s | 0 | 2.93e5 | 0 | 400000 | 6.1040 | 200000.0 | ±3.05 m3/s |
| chcro (CrossSectionArea) | m2 | 0 | 9.89e7 | 0 | 1.5e8 | 2288.4 | 75000000.0 | ±1144 m2 |
| tws (TotalWaterStorage) | mm | -2396 | 2.69e7 | -5000 | 3.5e7 | 534.4 | 17497500.0 | ±267 mm |
| lz (LowerZone) | mm | -2886 | 1415 | -4000 | 2000 | 0.09156 | -1000.0 | ±0.046 mm |
| uz, uzf, uzi | mm | 0 | 2486 | 0 | 3500 | 0.05341 | 1750.0 | ±0.027 mm |
| scov (SnowCover) | mm | 0 | 5359 | 0 | 8000 | 0.12207 | 4000.0 | ±0.061 mm |
| scova, scovb, scovc | mm | 0 | 6819 | 0 | 10000 | 0.15260 | 5000.0 | ±0.076 mm |
| rain | mm/day | 0 | 509 | 0 | 700 | 0.01068 | 350.0 | ±0.005 mm |
| snow | mm/day | 0 | 132 | 0 | 200 | 0.003052 | 100.0 | ±0.0015 mm |
| smelt (SnowMelt) | mm/day | 0 | 167 | 0 | 250 | 0.003815 | 125.0 | ±0.0019 mm |
| etact (ETactual) | mm/day | -6.3 | 828 | -10 | 1000 | 0.01541 | 495.0 | ±0.0077 mm |
| tact, tactF | mm/day | -6.4 | 7.7 | -10 | 15 | 3.815e-4 | 2.5 | ±0.00019 mm |
| Ta_other | mm/day | 0 | 7.4 | 0 | 15 | 2.289e-4 | 7.5 | ±0.00011 mm |
| esact, esactF | mm/day | 0 | 11.4 | 0 | 20 | 3.052e-4 | 10.0 | ±0.00015 mm |
| dirrun (DirectRunoff) | mm | 0 | 255 | 0 | 400 | 0.006104 | 200.0 | ±0.003 mm |
| srun (SurfaceRunoff) | mm | 0 | 330 | 0 | 500 | 0.007630 | 250.0 | ±0.0038 mm |
| trun (TotalRunoff) | mm | 0 | 331 | 0 | 500 | 0.007630 | 250.0 | ±0.0038 mm |
| inf, infF (Infiltration) | mm | 0 | 314 | 0 | 500 | 0.007630 | 250.0 | ±0.0038 mm |
| pflow, pflowF, pflowO, pflowi | mm | 0 | 293 | 0 | 400 | 0.006104 | 200.0 | ±0.003 mm |
| quz, quzF, quzI, quzO | mm | 0 | 209 | 0 | 300 | 0.004578 | 150.0 | ±0.0023 mm |
| qlz | mm | 0 | 2.0 | 0 | 3 | 4.578e-5 | 1.5 | ±2.3e-5 mm |
| uz2lz, uz2lzF | mm | 0 | 2.0 | 0 | 3 | 4.578e-5 | 1.5 | ±2.3e-5 mm |
| gwloss | mm | 0 | 1.0 | 0 | 2 | 3.052e-5 | 1.0 | ±1.5e-5 mm |
| sgwF, sgwIrrigation, sgwOther, sgwPixel | mm | 0 | 40 | 0 | 60 | 9.156e-4 | 30.0 | ±4.6e-4 mm |
| frost (FrostIndex) | - | 0 | 57 | 0 | 100 | 0.001526 | 50.0 | ±7.6e-4 |
| dslr, dslrf, dslri | days | 1 | 2558 | 0 | 4000 | 0.06104 | 2000.0 | ±0.031 days |
| cseal (CumInterSealed) | mm | 0 | 1.0 | 0 | 1.5 | 2.289e-5 | 0.75 | ±1.1e-5 mm |
| tha, thb, thc, thfa-thic (theta) | - | 0.04 | 0.70 | 0 | 1.0 | 1.526e-5 | 0.5 | ±7.6e-6 |
| ofdir (OFDirectM3) | m3 | 0 | 1.76e6 | 0 | 2.5e6 | 38.15 | 1250000.0 | ±19 m3 |
| offor (OFForestM3) | m3 | 0 | 5.08e6 | 0 | 7.0e6 | 106.8 | 3500000.0 | ±53 m3 |
| ofoth (OFOtherM3) | m3 | 0 | 2.90e6 | 0 | 4.0e6 | 61.04 | 2000000.0 | ±31 m3 |
| wdept (WaterDepth) | mm | 0 | 168 | 0 | 250 | 0.003815 | 125.0 | ±0.0019 mm |
| transloss | mm | 0 | 412 | 0 | 600 | 0.009156 | 300.0 | ±0.0046 mm |
| ttoc (ToChanRunoff) | mm | 0 | 235 | 0 | 350 | 0.005341 | 175.0 | ±0.0027 mm |
| lakeh | m | 0 | 39.5 | 0 | 60 | 9.156e-4 | 30.0 | ±4.6e-4 m |
| lakeprevinq, lakeprevoutq | m3/s | 0 | 1.06e5 | 0 | 150000 | 2.289 | 75000.0 | ±1.14 m3/s |
| rsfil (ReservoirFill) | - | 0 | 0.98 | 0 | 1.5 | 2.289e-5 | 0.75 | ±1.1e-5 |


## Notes

### Design range choices
- Headroom of 20-50% above observed max to accommodate extreme events not seen in the calibration run
- For variables with observed min = 0, design min is kept at 0 (physical lower bound)
- For lz (can go negative due to abstractions), design min set to -4000 based on observed -2886
- For tws (huge dynamic range 0 to 27M): precision is coarse (±267 mm) — consider whether this variable really needs map output or if TSS at gauges suffices

### Variables NOT recommended for packing
- `tws` (TotalWaterStorage): extreme dynamic range makes int16 precision poor. Use float32 instead.
- `chcro` (CrossSectionArea): same issue — range 0 to 1.5e8 gives ±1144 m2 precision
- All `.end` and `State` variables: used for warm start, need full precision

### How to use these values in `default_options.py`

```python
'DischargeMaps': ReportedMap(name='DischargeMaps', output_var='ChanQAvg',
                             unit='m3/s', end=[], steps=[],
                             all=['repDischargeMaps'], restrictoption=[],
                             monthly=False, yearly=False,
                             scale_factor=6.1040, add_offset=200000.0),
```

### Verification
After implementation, verify with:
```python
# For discharge: design range 0-400000
# packed = round((value - 200000) / 6.1040)
# At value=0:        packed = -32767  ✓ (min int16 usable)
# At value=400000:   packed = +32767  ✓ (max int16 usable)
# At value=200000:   packed = 0       ✓ (midpoint)
```
