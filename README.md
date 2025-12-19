# Traffic Analysis System

Real-time vehicle detection and speed analysis on NVIDIA Jetson Orin Nano.

## What It Does

- Counts vehicles by direction
- Measures relative speeds  
- Generates statistical reports
- ~40 FPS with GPU acceleration

## Quick Start
```bash
# See JETSON_SETUP.md for installation

cd v2
nano config.yaml  # Set camera URL
python run_traffic.py 1  # Run for 1 hour
```

## Output
```
data/traffic_data_YYYYMMDD_HHMMSS.csv
reports/traffic_analysis_YYYYMMDD_HHMMSS.txt
```

## Example Report
```
Bin 0 [<  268]:    2 vehicles ( 0.6%)  Slow outliers
Bin 1 [ 268-423]: 112 vehicles (34.4%) 
Bin 2 [ 423-578]: 156 vehicles (47.9%) ← Most traffic
Bin 3 [ 578-734]:  42 vehicles (12.9%) 
Bin 4 [ 734-889]:  11 vehicles ( 3.4%) 
Bin 5 [>  889]:    3 vehicles ( 0.9%)  Fast outliers
```

## Tech Stack

- YOLOv8n + ByteTrack
- Multi-process architecture (detector/analyzer)
- Config-driven (config.yaml)

## Hardware

- Jetson Orin Nano 8GB
- JetPack 6.2
- iPhone 12 mini camera via DroidCam
