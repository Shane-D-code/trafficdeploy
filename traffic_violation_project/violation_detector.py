import cv2
import numpy as np
from ultralytics import YOLO
import easyocr
from datetime import datetime
from pathlib import Path

from preprocessing import preprocess_image
from violations import WrongSideDetector, StopLineDetector, RedLightDetector, IllegalParkingDetector


_model = None
_reader = None
_plate_model = None


def _load_model(model_path='models/traffic_violation_best.pt'):
    global _model
    if _model is None:
        _model = YOLO(model_path)
    return _model


def _load_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(['en'])
    return _reader


def _load_plate_model(model_path='models/license_plate_best.pt'):
    global _plate_model
    if _plate_model is None:
        _plate_model = YOLO(model_path)
    return _plate_model


def compute_iou(boxA, boxB):
    x_left   = max(boxA[0], boxB[0])
    y_top    = max(boxA[1], boxB[1])
    x_right  = min(boxA[2], boxB[2])
    y_bottom = min(boxA[3], boxB[3])
    if x_right < x_left or y_bottom < y_top:
        return 0.0
    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    boxA_area = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxB_area = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    union_area = boxA_area + boxB_area - intersection_area
    if union_area == 0:
        return 0.0
    return intersection_area / union_area


def _parse_detections(results):
    detections = []
    if results.boxes is None:
        return detections
    boxes = results.boxes
    names = results.names
    for i in range(len(boxes)):
        x1, y1, x2, y2 = boxes.xyxy[i].tolist()
        cls_id = int(boxes.cls[i].item())
        conf   = boxes.conf[i].item()
        detections.append({
            'class_name': names[cls_id],
            'class_id':   cls_id,
            'confidence': conf,
            'bbox':       [x1, y1, x2, y2],
        })
    return detections


def extract_plate_text(image, vehicle_bbox, plate_model_path='models/license_plate_best.pt'):
    h, w = image.shape[:2]
    vx1, vy1, vx2, vy2 = map(int, vehicle_bbox)
    pad_x = int((vx2 - vx1) * 0.1)
    pad_y = int((vy2 - vy1) * 0.1)
    vx1 = max(0, vx1 - pad_x)
    vy1 = max(0, vy1 - pad_y)
    vx2 = min(w, vx2 + pad_x)
    vy2 = min(h, vy2 + pad_y)
    vehicle_crop = image[vy1:vy2, vx1:vx2]
    if vehicle_crop.size == 0:
        return None
    plate_bbox = None
    try:
        plate_model = _load_plate_model(plate_model_path)
        plate_results = plate_model(vehicle_crop, verbose=False)[0]
        if plate_results.boxes is not None and len(plate_results.boxes) > 0:
            boxes = plate_results.boxes
            names = plate_results.names
            best_conf = 0.0
            for i in range(len(boxes)):
                conf = boxes.conf[i].item()
                cls_id = int(boxes.cls[i].item())
                name = names.get(cls_id, '')
                if 'plate' in name.lower() or 'license' in name.lower() or conf > 0.4:
                    if conf > best_conf:
                        best_conf = conf
                        plate_bbox = boxes.xyxy[i].tolist()
            if plate_bbox is None:
                best_idx = int(boxes.conf.argmax().item())
                plate_bbox = boxes.xyxy[best_idx].tolist()
    except Exception:
        pass
    if plate_bbox is not None:
        px1, py1, px2, py2 = map(int, plate_bbox)
        ph_, pw_ = vehicle_crop.shape[:2]
        ppad = 5
        px1 = max(0, px1 - ppad)
        py1 = max(0, py1 - ppad)
        px2 = min(pw_, px2 + ppad)
        py2 = min(ph_, py2 + ppad)
        plate_crop = vehicle_crop[py1:py2, px1:px2]
    else:
        plate_crop = vehicle_crop
    if plate_crop.size == 0:
        return None
    gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    denoised = cv2.fastNlMeansDenoising(thresh, h=30)
    upscaled = cv2.resize(denoised, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    reader = _load_reader()
    ocr_results = reader.readtext(upscaled)
    good_results = [r for r in ocr_results if r[2] > 0.5]
    if not good_results:
        return None
    best_text = str(max(good_results, key=lambda r: r[2])[1])
    best_text = best_text.upper().replace(' ', '')
    best_text = ''.join(c for c in best_text if c.isalnum())
    return best_text if best_text else None


def is_valid_plate(text):
    if not text:
        return False
    pattern = r'^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$'
    return bool(__import__('re').match(pattern, text))


def detect_violations(image_path, model_path='models/traffic_violation_best.pt', enable_preprocessing=False):
    model = _load_model(model_path)
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    results = model(image, conf=0.01)[0]
    detections = _parse_detections(results)

    riders    = [d for d in detections if d['class_name'] == 'person_rider']
    helmets   = [d for d in detections if d['class_name'] == 'helmet']
    vehicles  = [d for d in detections if d['class_name'] == 'vehicle']
    seatbelts = [d for d in detections if d['class_name'] == 'seatbelt']
    no_helmet_det = [d for d in detections if d['class_name'] == 'no_helmet']
    no_seatbelt_det = [d for d in detections if d['class_name'] == 'no_seatbelt']

    now = datetime.now().isoformat()
    violations = []

    rider_vehicle_map = {}
    for ri, rider in enumerate(riders):
        best_iou = 0.0
        best_vbox = None
        for veh in vehicles:
            iou = compute_iou(rider['bbox'], veh['bbox'])
            if iou > best_iou:
                best_iou = iou
                best_vbox = veh['bbox']
        if best_vbox is not None and best_iou > 0.05:
            rider_vehicle_map[ri] = best_vbox

    # --- NO HELMET: use direct no_helmet class first, fallback to IoU logic ---
    if no_helmet_det:
        for det in no_helmet_det:
            plate = None
            if vehicles:
                best_iou = 0.0
                best_vbox = None
                for veh in vehicles:
                    iou = compute_iou(det['bbox'], veh['bbox'])
                    if iou > best_iou:
                        best_iou = iou
                        best_vbox = veh['bbox']
                if best_vbox is not None and best_iou > 0.05:
                    plate = extract_plate_text(image, best_vbox)
            violations.append({
                'type': 'NO HELMET',
                'confidence': det['confidence'],
                'bbox': det['bbox'],
                'plate_text': plate,
                'timestamp': now,
            })
    else:
        for ri, rider in enumerate(riders):
            rx1, ry1, rx2, ry2 = rider['bbox']
            rider_h = ry2 - ry1
            upper_body_bbox = [rx1, ry1, rx2, ry1 + 0.4 * rider_h]
            has_helmet = any(compute_iou(upper_body_bbox, h['bbox']) > 0.3 for h in helmets)
            if not has_helmet:
                veh_bbox = rider_vehicle_map.get(ri, rider['bbox'])
                plate = extract_plate_text(image, veh_bbox)
                violations.append({
                    'type': 'NO HELMET',
                    'confidence': rider['confidence'],
                    'bbox': rider['bbox'],
                    'plate_text': plate,
                    'timestamp': now,
                })

    # --- NO SEATBELT: use direct no_seatbelt class first, fallback to IoU logic ---
    if no_seatbelt_det:
        for det in no_seatbelt_det:
            plate = extract_plate_text(image, det['bbox'])
            violations.append({
                'type': 'NO SEATBELT',
                'confidence': det['confidence'],
                'bbox': det['bbox'],
                'plate_text': plate,
                'timestamp': now,
            })
    else:
        for vehicle in vehicles:
            vx1, vy1, vx2, vy2 = vehicle['bbox']
            vw = vx2 - vx1
            driver_region = [vx1, vy1, vx1 + 0.5 * vw, vy2]
            has_seatbelt = any(compute_iou(driver_region, sb['bbox']) > 0.1 for sb in seatbelts)
            if not has_seatbelt:
                plate = extract_plate_text(image, vehicle['bbox'])
                violations.append({
                    'type': 'NO SEATBELT',
                    'confidence': vehicle['confidence'],
                    'bbox': vehicle['bbox'],
                    'plate_text': plate,
                    'timestamp': now,
                })

    # --- TRIPLE RIDING ---
    for vehicle in vehicles:
        vbox = vehicle['bbox']
        rider_count = sum(1 for r in riders if compute_iou(vbox, r['bbox']) > 0.1)
        if rider_count > 2:
            plate = extract_plate_text(image, vehicle['bbox'])
            violations.append({
                'type': 'TRIPLE RIDING',
                'confidence': vehicle['confidence'],
                'bbox': vehicle['bbox'],
                'plate_text': plate,
                'timestamp': now,
            })

    # --- Future violation detectors (rule-based placeholders) ---
    for DetectorClass in [WrongSideDetector, StopLineDetector, RedLightDetector, IllegalParkingDetector]:
        detector = DetectorClass()
        violations.extend(detector.detect(image, detections))

    return violations, detections


def draw_violations(image, violations):
    if isinstance(image, str):
        img = cv2.imread(image)
        if img is None:
            raise FileNotFoundError(f"Could not read image: {image}")
    else:
        img = image.copy()
    for v in violations:
        x1, y1, x2, y2 = map(int, v['bbox'])
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 3)
        label = f"{v['type']} ({v['confidence']:.2f})"
        cv2.putText(img, label, (x1, max(y1 - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        if v['plate_text']:
            plate_label = f"Plate: {v['plate_text']}"
            cv2.putText(img, plate_label, (x1, max(y1 - 35, 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    return img


def generate_evidence_image(image, violations, detections=None):
    annotated = draw_violations(image, violations)
    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    evidence_dir = Path('evidence')
    evidence_dir.mkdir(parents=True, exist_ok=True)
    filename = f"violation_{now}.jpg"
    path = str(evidence_dir / filename)
    cv2.imwrite(path, annotated)
    return path, filename


if __name__ == '__main__':
    import os
    TEST_IMAGES = {
        'case_1_no_helmet': 'test_no_helmet.jpg',
        'case_2_no_seatbelt': 'test_no_seatbelt.jpg',
        'case_3_triple_riding': 'test_triple_riding.jpg',
    }
    for case_name, img_path in TEST_IMAGES.items():
        print(f"\n{'=' * 60}")
        print(f"  TEST CASE: {case_name}")
        print(f"{'=' * 60}")
        if not os.path.exists(img_path):
            print(f"  Image not found: {img_path}  (skipping)")
            continue
        try:
            violations, detections = detect_violations(img_path)
            print(f"  Detections: {len(detections)}")
            for d in detections:
                print(f"    {d['class_name']}: {d['confidence']:.3f}")
            if not violations:
                print("  Result: No violations detected.")
            else:
                for v in violations:
                    plate = v['plate_text']
                    valid = is_valid_plate(plate) if plate else False
                    print(f"  Type:       {v['type']}")
                    print(f"  Confidence: {v['confidence']:.3f}")
                    print(f"  Plate:      {plate}  {'VALID' if valid else 'INVALID' if plate else 'N/A'}")
                    print()
            annotated = draw_violations(img_path, violations)
            out_path = f'output_{case_name}.jpg'
            cv2.imwrite(out_path, annotated)
            print(f"  -> Annotated image saved to {out_path}")
        except Exception as exc:
            print(f"  Error: {exc}")
