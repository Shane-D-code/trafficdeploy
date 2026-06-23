<<<<<<< HEAD
# Trafficviolation
=======
# Gridlock - AI Traffic Violation Detection System

AI-powered traffic violation detection system using YOLOv8 and EasyOCR for Indian traffic conditions.

## Features

### Detection Capabilities
- **Vehicles & Riders**: YOLOv8 object detection
- **Helmet Detection**: Identifies riders without helmets
- **Seatbelt Detection**: Detects drivers without seatbelts
- **Triple Riding**: Identifies >2 riders on a vehicle
- **License Plate Recognition**: OCR with Indian plate validation (formats like KA01AB1234)
- **Wrong Side Driving**: Lane detection based
- **Stop Line Violation**: Stop line crossing detection
- **Red Light Violation**: Traffic light color detection
- **Illegal Parking**: No-parking zone detection

### Technical Features
- GPU Acceleration (Apple MPS, CUDA)
- Real-time Image Processing
- Video Processing (every 30th frame)
- Evidence Generation with Annotations
- SQLite Database Storage
- Analytics Dashboard
- PDF Report Generation
- Event Deduplication
- Frame Tracking

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.9+ |
| ML Framework | PyTorch, Ultralytics YOLOv8 |
| OCR | EasyOCR |
| Frontend | React / Vite |
| Database | SQLite |
| Visualization | Plotly, Matplotlib |
| Processing | OpenCV, NumPy |

## Quick Start

```bash
cd traffic_violation_project
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Project Structure

```
traffic_violation_project/
├── violation_detector.py           # Core violation detection engine
├── license_plate_recognition.py    # License plate OCR pipeline
├── preprocessing.py                # Image enhancement (CLAHE, denoise)
├── utils.py                        # SQLite DB and file utilities
├── evaluation.py                   # Model evaluation tooling
├── report_generator.py             # PDF report generation
├── test_plate_recognition.py       # OCR test suite
├── train.py                        # Model training pipeline
├── models/                         # YOLO model weights
│   ├── traffic_violation_best.pt   # 6-class detection model
│   └── license_plate_best.pt       # Plate detection model
├── evidence/                       # Generated evidence images
├── reports/                        # Generated PDF reports
└── violations/                     # Rule-based violation detectors
    ├── __init__.py
    ├── base.py                     # Base class for all detectors
    ├── wrong_side.py               # Wrong-side driving detection
    ├── stop_line.py                # Stop line violation detection
    ├── red_light.py                # Red light violation detection
    └── illegal_parking.py          # Illegal parking detection
```

## Usage

### 1. Upload Image
1. Navigate to **Detection** page
2. Upload JPG/PNG image
3. Adjust confidence threshold (default: 0.05)
4. Enable/disable preprocessing
5. Click **Detect Violations**

### 2. Process Video
1. Upload MP4 video
2. System processes every 30th frame
3. Results displayed with timestamps

### 3. View Analytics
1. Go to **Analytics** page
2. View violation statistics
3. Filter by date/type/plate

### 4. Generate Reports
1. Go to **Reports** page
2. Click **Generate PDF Report**

## Configuration

### Confidence Thresholds
| Parameter | Default | Range |
|-----------|---------|-------|
| Detection Confidence | 0.05 | 0.01-0.9 |
| IoU Threshold | 0.3 | 0.0-1.0 |

## Testing

```bash
# Test plate recognition
python test_plate_recognition.py

# Run with pytest
pytest tests/ -v
```

## License

This project is for academic and research purposes.
>>>>>>> 09740f1 (Add full project structure: backend, frontend, Docker config, ML models, pipeline, and evaluation modules)
# trafficdeploy
