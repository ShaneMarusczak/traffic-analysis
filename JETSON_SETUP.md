# Jetson Setup

Installation for NVIDIA Jetson Orin Nano.

## Requirements

- JetPack 6.2
- Python 3.10
- Camera (DroidCam or USB)

## Install
```bash
# 1. PyTorch (Jetson build)
wget https://developer.download.nvidia.com/compute/redist/jp/v60/pytorch/torch-2.5.0a0+872d972e41.nv24.08.17622132-cp310-cp310-linux_aarch64.whl
pip install torch-*.whl --break-system-packages

# 2. NumPy (specific version for Jetson compatibility)
pip install numpy==1.26.4 --break-system-packages

# 3. Other dependencies
pip install opencv-python pyyaml --break-system-packages

# 4. Ultralytics (no deps to avoid conflicts)
pip install ultralytics --no-deps --break-system-packages

# 5. Clone repo
git clone git@github.com:ShaneMarusczak/traffic-analysis.git
cd traffic-analysis/v2

# 6. Download YOLO model
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# 7. Configure camera
nano config.yaml  # Set camera URL

# 8. Test
python run_traffic.py 0.1  # 6 minute test
```

## Camera Setup

**DroidCam (phone camera):**
1. Install [DroidCam](https://www.dev47apps.com/) on Android
2. Connect phone and Jetson to same WiFi
3. Set in config.yaml: `url: "http://PHONE_IP:4747/video"`

**USB webcam:**
```yaml
url: 0  # Device index
```

## Max Performance
```bash
sudo nvpmodel -m 0
sudo jetson_clocks
```

## Verify GPU
```bash
python3 -c "import torch; print(torch.cuda.is_available())"
# Should print: True
```

## Resources

- [YOLOv8 Docs](https://docs.ultralytics.com/)
- [ByteTrack Paper](https://arxiv.org/abs/2110.06864)
- [Jetson Downloads](https://developer.nvidia.com/embedded/downloads)
- [DroidCam](https://www.dev47apps.com/)
