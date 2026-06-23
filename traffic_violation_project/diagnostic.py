#!/usr/bin/env python3
import sys
import os
import json
import cv2
import torch
import numpy as np
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

print("=" * 60)
print("GRIDLOCK DIAGNOSTIC")
print("=" * 60)

print(f"\nPython: {sys.version}")
print(f"  CWD: {os.getcwd()}")

print("\nChecking imports...")
errors = []
try:
    import ultralytics; print(f"  ultralytics: {ultralytics.__version__}")
except Exception as e: errors.append(f"ultralytics: {e}")
try:
    import torch; print(f"  torch: {torch.__version__}, MPS: {torch.backends.mps.is_available()}")
except Exception as e: errors.append(f"torch: {e}")
try:
    import cv2; print(f"  opencv: {cv2.__version__}")
except Exception as e: errors.append(f"opencv: {e}")
try:
    import easyocr; print(f"  easyocr: {easyocr.__version__}")
except Exception as e: errors.append(f"easyocr: {e}")
try:
    from ultralytics import YOLO; print(f"  YOLO import: OK")
except Exception as e: errors.append(f"YOLO: {e}")

if errors:
    for e in errors:
        print(f"  ERROR: {e}")
    sys.exit(1)

print("\nChecking model files...")
models = ['models/traffic_violation_best.pt', 'models/license_plate_best.pt',
          'models/helmet_final_best.pt', 'models/seatbelt_best.pt',
          'models/all_redsignal_wrongside_best.pt']
for m in models:
    if os.path.exists(m):
        print(f"  {m}: {os.path.getsize(m)/1024/1024:.1f}MB")
    else:
        print(f"  {m}: MISSING")

print("\nLoading YOLO model...")
try:
    model = YOLO('models/traffic_violation_best.pt')
    print(f"  Model loaded: {len(model.names)} classes")
    print(f"  Classes: {model.names}")
except Exception as e:
    print(f"  FAILED: {e}")
    sys.exit(1)

print("\nTesting detection on sample image...")
img = np.ones((720, 1280, 3), dtype=np.uint8) * 200
cv2.rectangle(img, (300, 200), (500, 400), (0, 0, 255), -1)
test_path = '/tmp/diag_test.jpg'
cv2.imwrite(test_path, img)

try:
    results = model(test_path, conf=0.25, verbose=False)
    print(f"  Detection ran OK")
    for r in results:
        boxes = r.boxes
        if boxes is not None:
            print(f"  Found {len(boxes)} detections")
            for b in boxes:
                cls = int(b.cls[0])
                conf = float(b.conf[0])
                print(f"    - {model.names[cls]}: {conf:.2f}")
        else:
            print(f"  No detections (expected - random image)")
except Exception as e:
    print(f"  FAILED: {e}")
    import traceback; traceback.print_exc()

print("\nTesting violation_detector module...")
try:
    from violation_detector import detect_violations_json, generate_evidence_image
    result = detect_violations_json(test_path, confidence_threshold=0.25, enable_preprocessing=True)
    print(f"  detect_violations_json: OK")
    print(f"  Violations: {len(result.get('violations', []))}")
    print(f"  Stats: {json.dumps(result.get('stats', {}))}")
    print(f"  original_image_path: {result.get('original_image_path')}")
    
    if result.get('original_image_path') and os.path.exists(result['original_image_path']):
        print(f"  Original file exists: {os.path.getsize(result['original_image_path'])} bytes")
except Exception as e:
    print(f"  FAILED: {e}")
    import traceback; traceback.print_exc()

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
