import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).parent.resolve()
_DEFAULT_MODEL_PATH = str(_BASE_DIR / "models" / "traffic_violation_best.pt")
_DEFAULT_PLATE_MODEL_PATH = str(_BASE_DIR / "models" / "license_plate_best.pt")

from license_plate_recognition import LicensePlateRecognizer
from preprocessing import preprocess_image
from preprocessing_pipeline import ImagePreprocessor
from explanation_engine import ExplanationEngine
from evidence_generator import EvidenceGenerator
from vehicle_classifier import VehicleClassifier
from violations import (
    IllegalParkingDetector,
    RedLightDetector,
    StopLineDetector,
    WrongSideDetector,
)

CLASS_NAME_MAP = {
    "person_rider": "rider",
    "person": "pedestrian",
    "rider": "rider",
    "vehicle": "vehicle",
    "car": "vehicle",
    "truck": "vehicle",
    "bus": "vehicle",
    "motorcycle": "vehicle",
    "helmet": "helmet",
    "seatbelt": "seatbelt",
    "no_helmet": "no_helmet",
    "without_helmet": "no_helmet",
    "no_seatbelt": "no_seatbelt",
    "without_seatbelt": "no_seatbelt",
}


def _standardize_class_name(class_name):
    return CLASS_NAME_MAP.get(class_name, class_name)


def calculate_overall_confidence(detection_conf, ocr_conf=None, plate_valid=False):
    overall_conf = detection_conf
    if ocr_conf is not None:
        overall_conf = (detection_conf * 0.6) + (ocr_conf * 0.4)
        if not plate_valid:
            overall_conf *= 0.5
    return min(overall_conf, 1.0)


class ViolationDetector:
    def __init__(
        self,
        model_path=None,
        plate_model_path=None,
        device="cpu",
    ):
        model_path = model_path or _DEFAULT_MODEL_PATH
        plate_model_path = plate_model_path or _DEFAULT_PLATE_MODEL_PATH
        model_path = str(Path(model_path)) if Path(model_path).is_absolute() else str(_BASE_DIR / model_path)
        plate_model_path = str(Path(plate_model_path)) if Path(plate_model_path).is_absolute() else str(_BASE_DIR / plate_model_path)

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at: {model_path}")

        self.model = YOLO(model_path)
        self.device = device
        if device == "cuda" and torch.cuda.is_available():
            self.model.to("cuda")
            logger.info("Traffic model loaded on GPU")
        else:
            logger.info("Traffic model loaded on CPU")

        self.plate_recognizer = LicensePlateRecognizer(
            plate_model_path if plate_model_path else None, device
        )

        self.class_names = self.model.names

        self.iou_threshold = 0.3

        self.preprocessor = ImagePreprocessor()
        self.explanation_engine = ExplanationEngine()
        self.evidence_generator = EvidenceGenerator()
        self.vehicle_classifier = VehicleClassifier(model_path)

    def compute_iou(self, box1, box2):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)

        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0

    def get_upper_body_box(self, person_box):
        x1, y1, x2, y2 = person_box
        height = y2 - y1
        upper_y2 = y1 + int(height * 0.4)
        return [x1, y1, x2, upper_y2]

    def get_driver_region(self, vehicle_box):
        x1, y1, x2, y2 = vehicle_box
        width = x2 - x1
        height = y2 - y1

        driver_x1 = x1 + int(width * 0.1)
        driver_x2 = x1 + int(width * 0.4)
        driver_y1 = y1 + int(height * 0.3)
        driver_y2 = y1 + int(height * 0.7)

        return [driver_x1, driver_y1, driver_x2, driver_y2]

    def extract_plate_text(self, image, vehicle_box):
        return self.plate_recognizer.extract_plate_text(image, vehicle_box)

    def detect_violations(
        self, image, confidence_threshold=0.01, enable_preprocessing=True
    ):
        if isinstance(image, str):
            original_image = cv2.imread(image)
            if original_image is None:
                raise ValueError(f"Could not read image from: {image}")
        else:
            original_image = image.copy()

        proc_image = original_image.copy()

        if enable_preprocessing:
            conditions = self.preprocessor.analyze_conditions(original_image)
            proc_image = self.preprocessor.preprocess(original_image, conditions)
        else:
            conditions = {}

        results = self.model(proc_image, conf=confidence_threshold, verbose=False)

        violations = []
        detections = []

        if len(results) > 0:
            result = results[0]
            boxes = result.boxes.xyxy.cpu().numpy()
            confs = result.boxes.conf.cpu().numpy()
            cls_ids = result.boxes.cls.cpu().numpy().astype(int)
            names = result.names

            for box, conf, cls_id in zip(boxes, confs, cls_ids):
                class_name = _standardize_class_name(
                    names.get(cls_id, f"class_{cls_id}")
                )
                detections.append(
                    {
                        "box": box.tolist(),
                        "bbox": box.tolist(),
                        "confidence": float(conf),
                        "class_id": int(cls_id),
                        "class_name": class_name,
                    }
                )

        riders = [
            d for d in detections if d["class_name"] == "rider"
        ]
        vehicles = [
            d
            for d in detections
            if d["class_name"] in ["vehicle", "car", "truck", "bus", "motorcycle"]
        ]
        helmets = [d for d in detections if d["class_name"] == "helmet"]
        seatbelts = [d for d in detections if d["class_name"] == "seatbelt"]
        no_helmets = [
            d for d in detections if d["class_name"] in ["no_helmet", "without_helmet"]
        ]
        no_seatbelts = [
            d
            for d in detections
            if d["class_name"] in ["no_seatbelt", "without_seatbelt"]
        ]

        now = datetime.now().isoformat()

        rider_vehicle_map = {}
        for ri, rider in enumerate(riders):
            best_iou = 0.0
            best_vbox = None
            for veh in vehicles:
                iou = self.compute_iou(rider["box"], veh["box"])
                if iou > best_iou:
                    best_iou = iou
                    best_vbox = veh["box"]
            if best_vbox is not None and best_iou > 0.05:
                rider_vehicle_map[ri] = best_vbox

        # NO HELMET
        if no_helmets:
            for det in no_helmets:
                plate = None
                if vehicles:
                    best_iou = 0.0
                    best_vbox = None
                    for veh in vehicles:
                        iou = self.compute_iou(det["box"], veh["box"])
                        if iou > best_iou:
                            best_iou = iou
                            best_vbox = veh["box"]
                    if best_vbox is not None and best_iou > 0.05:
                        plate = self.extract_plate_text(original_image, best_vbox)
                violations.append(
                    {
                        "type": "NO HELMET",
                        "violation_type": "NO HELMET",
                        "confidence": det["confidence"],
                        "bbox": det["box"],
                        "plate_text": plate,
                        "timestamp": now,
                    }
                )
        else:
            for ri, rider in enumerate(riders):
                rider_box = rider["box"]
                upper_body = self.get_upper_body_box(rider_box)
                has_helmet = any(
                    self.compute_iou(upper_body, h["bbox"]) > 0.3 for h in helmets
                )
                if not has_helmet:
                    veh_bbox = rider_vehicle_map.get(ri, rider_box)
                    plate = self.extract_plate_text(original_image, veh_bbox)
                    violations.append(
                        {
                            "type": "NO HELMET",
                            "violation_type": "NO HELMET",
                            "confidence": rider["confidence"],
                            "bbox": rider_box,
                            "plate_text": plate,
                            "timestamp": now,
                        }
                    )

        # NO SEATBELT
        if no_seatbelts:
            for det in no_seatbelts:
                plate = self.extract_plate_text(original_image, det["box"])
                violations.append(
                    {
                        "type": "NO SEATBELT",
                        "violation_type": "NO SEATBELT",
                        "confidence": det["confidence"],
                        "bbox": det["box"],
                        "plate_text": plate,
                        "timestamp": now,
                    }
                )
        else:
            for vehicle in vehicles:
                vbox = vehicle["box"]
                driver_region = self.get_driver_region(vbox)
                has_seatbelt = any(
                    self.compute_iou(driver_region, sb["bbox"]) > 0.1
                    for sb in seatbelts
                )
                if not has_seatbelt:
                    plate = self.extract_plate_text(original_image, vbox)
                    violations.append(
                        {
                            "type": "NO SEATBELT",
                            "violation_type": "NO SEATBELT",
                            "confidence": vehicle["confidence"],
                            "bbox": vbox,
                            "plate_text": plate,
                            "timestamp": now,
                        }
                    )

        # TRIPLE RIDING
        for vehicle in vehicles:
            vbox = vehicle["box"]
            vw = vbox[2] - vbox[0]
            vh = vbox[3] - vbox[1]

            # Skip wide vehicles (cars, buses) — likely not two-wheelers
            if vw > 0 and vw / vh > 0.65:
                continue

            # Expand vehicle box upward to catch riders sitting on top
            x1, y1, x2, y2 = vbox
            expanded_top = y1 - vh * 0.8
            expanded_bottom = y2 + vh * 0.1
            expanded_left = x1 - vw * 0.1
            expanded_right = x2 + vw * 0.1

            rider_count = 0
            for r in riders:
                rx1, ry1, rx2, ry2 = r["box"]
                ix1 = max(expanded_left, rx1)
                iy1 = max(expanded_top, ry1)
                ix2 = min(expanded_right, rx2)
                iy2 = min(expanded_bottom, ry2)
                if ix1 < ix2 and iy1 < iy2:
                    inter = (ix2 - ix1) * (iy2 - iy1)
                    rider_area = (rx2 - rx1) * (ry2 - ry1)
                    if rider_area > 0 and inter / rider_area > 0.1:
                        rider_count += 1

            if rider_count > 2:
                plate = self.extract_plate_text(original_image, vbox)
                violations.append(
                    {
                        "type": "TRIPLE RIDING",
                        "violation_type": "TRIPLE RIDING",
                        "confidence": vehicle["confidence"],
                        "bbox": vbox,
                        "plate_text": plate,
                        "timestamp": now,
                    }
                )

        # Rule-based violations
        for DetectorClass in [
            WrongSideDetector,
            StopLineDetector,
            RedLightDetector,
            IllegalParkingDetector,
        ]:
            detector = DetectorClass()
            for rv in detector.detect(original_image, detections):
                if "type" not in rv:
                    rv["type"] = rv.get("violation_type", detector.name)
                if "violation_type" not in rv:
                    rv["violation_type"] = rv["type"]
                violations.append(rv)

        violations = self.explanation_engine.generate_explanations_for_violations(violations)

        return violations, detections

    def preprocess_image(self, image):
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        lab_enhanced = cv2.merge((l_enhanced, a, b))
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        denoised = cv2.fastNlMeansDenoisingColored(enhanced, None, 10, 10, 7, 21)
        return denoised

    def draw_violations(self, image, violations):
        if isinstance(image, str):
            annotated = cv2.imread(image)
            if annotated is None:
                raise FileNotFoundError(f"Could not read image: {image}")
        else:
            annotated = image.copy()

        for violation in violations:
            bbox = violation.get("bbox") or violation.get("box")
            if not bbox or len(bbox) < 4:
                continue
            v_type = violation.get("type", "UNKNOWN")
            confidence = violation.get("confidence", 0.0)
            plate_text = violation.get("plate_text", None)

            x1, y1, x2, y2 = map(int, bbox[:4])

            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)

            label = f"{v_type}: {confidence:.2f}"

            (text_w, text_h), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )

            cv2.rectangle(
                annotated, (x1, y1 - text_h - 10), (x1 + text_w, y1), (0, 255, 0), -1
            )
            cv2.putText(
                annotated,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2,
            )

            if plate_text:
                plate_label = f"Plate: {plate_text}"
                cv2.putText(
                    annotated,
                    plate_label,
                    (x1, y2 + 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    2,
                )

        return annotated


_module_detector = None


def _get_detector(model_path=None):
    global _module_detector
    if _module_detector is None:
        _module_detector = ViolationDetector(model_path)
    return _module_detector


def detect_violations(
    image_path,
    model_path=None,
    enable_preprocessing=False,
):
    detector = _get_detector(model_path)
    return detector.detect_violations(
        image_path, enable_preprocessing=enable_preprocessing
    )


def draw_violations(image, violations):
    detector = _get_detector()
    return detector.draw_violations(image, violations)


def extract_plate_text(image, vehicle_bbox):
    from license_plate_recognition import extract_plate_text as _lpr_extract

    return _lpr_extract(image, vehicle_bbox)


def is_valid_plate(text):
    from license_plate_recognition import is_valid_plate as _lpr_valid

    return _lpr_valid(text)


def generate_evidence_image(image, violations, detections=None):
    annotated = draw_violations(image, violations)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    evidence_dir = Path("evidence")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    filename = f"violation_{now}.jpg"
    path = str(evidence_dir / filename)
    cv2.imwrite(path, annotated)
    return path, filename


class FrameTracker:
    def __init__(self, max_track_length=10, iou_threshold=0.5):
        self.tracks = {}
        self.max_track_length = max_track_length
        self.iou_threshold = iou_threshold
        self.next_id = 0

    def update(self, detections, frame=None):
        matched = set()
        for track_id, track in self.tracks.items():
            best_match = None
            best_iou = 0
            for det_idx, det in enumerate(detections):
                if det_idx in matched:
                    continue
                iou = self._compute_iou(track['bbox'], det.get('box', det.get('bbox')))
                if iou > self.iou_threshold and iou > best_iou:
                    best_iou = iou
                    best_match = det_idx
            if best_match is not None:
                matched.add(best_match)
                track['bbox'] = detections[best_match].get('box', detections[best_match].get('bbox'))
                track['confidence'] = detections[best_match]['confidence']
                track['class_name'] = detections[best_match]['class_name']
                track['frames_seen'] += 1
            else:
                track['lost'] = True

        for det_idx, det in enumerate(detections):
            if det_idx not in matched:
                self.tracks[self.next_id] = {
                    'id': self.next_id,
                    'bbox': det.get('box', det.get('bbox')),
                    'confidence': det['confidence'],
                    'class_name': det['class_name'],
                    'frames_seen': 1,
                    'lost': False,
                    'plate_text': None,
                    'plate_confidence': 0
                }
                self.next_id += 1

        to_remove = []
        for track_id, track in self.tracks.items():
            if track.get('lost', False) and track['frames_seen'] > self.max_track_length:
                to_remove.append(track_id)
        for track_id in to_remove:
            del self.tracks[track_id]
        return self.tracks

    def _compute_iou(self, box1, box2):
        if not box1 or not box2 or len(box1) < 4 or len(box2) < 4:
            return 0
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection
        return intersection / union if union > 0 else 0


class EventConsolidator:
    def __init__(self, iou_threshold=0.3, time_window=10):
        self.iou_threshold = iou_threshold
        self.time_window = time_window

    def consolidate_violations(self, violations, image=None):
        if not violations:
            return []
        grouped = {}
        for v in violations:
            key = f"{v['type']}_{v.get('plate_text', 'NOPLATE')}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(v)
        consolidated = []
        for key, group in grouped.items():
            if len(group) == 1:
                consolidated.append(group[0])
            else:
                group.sort(key=lambda x: x['confidence'], reverse=True)
                kept = []
                for v in group:
                    is_duplicate = False
                    for kept_v in kept:
                        iou = self._compute_iou(v.get('bbox', v.get('box')), kept_v.get('bbox', kept_v.get('box')))
                        if iou > self.iou_threshold:
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        kept.append(v)
                if kept:
                    consolidated.append(kept[0])
        return consolidated

    def _compute_iou(self, box1, box2):
        if not box1 or not box2 or len(box1) < 4 or len(box2) < 4:
            return 0
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection
        return intersection / union if union > 0 else 0


class VideoProcessor:
    def __init__(self, detector, frame_interval=30, max_frames=100):
        self.detector = detector
        self.frame_interval = frame_interval
        self.max_frames = max_frames

    def process_video(self, video_path, confidence_threshold=0.5, enable_preprocessing=True):
        results = []
        try:
            cap = cv2.VideoCapture(video_path)
            frame_count = 0
            processed_count = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                frame_count += 1
                if frame_count % self.frame_interval == 0:
                    processed_count += 1
                    violations, detections = self.detector.detect_violations(
                        frame, confidence_threshold, enable_preprocessing
                    )
                    if violations:
                        results.append({
                            'frame': frame_count,
                            'violations': violations,
                            'detections': detections
                        })
                if processed_count >= self.max_frames:
                    break
            cap.release()
            return results
        except Exception as e:
            logger.error(f"Video processing error: {e}")
            return results


def detect_violations_json(image_path, confidence_threshold=0.5, enable_preprocessing=True):
    try:
        detector = ViolationDetector()
        violations, detections = detector.detect_violations(
            image_path,
            confidence_threshold=confidence_threshold,
            enable_preprocessing=enable_preprocessing
        )
        result = {
            'violations': [],
            'stats': {
                'total': len(violations),
                'byType': {},
                'avgConfidence': 0,
                'totalPlates': 0,
                'validPlates': 0
            },
            'annotated_image_path': None
        }

        if violations:
            annotated_path, _ = generate_evidence_image(image_path, violations, detections)
            result['annotated_image_path'] = annotated_path

        plate_count = 0
        valid_plate_count = 0
        total_confidence = 0
        for v in violations:
            violation = {
                'id': str(datetime.now().timestamp()) + str(len(result['violations'])),
                'type': v.get('type', 'UNKNOWN'),
                'confidence': v.get('confidence', 0.0),
                'bbox': v.get('bbox', [0, 0, 0, 0]),
                'timestamp': v.get('timestamp', datetime.now().isoformat())
            }
            if v.get('plate_text'):
                violation['plateText'] = v['plate_text']
                violation['plateConfidence'] = v.get('plate_confidence', v.get('ocr_confidence', 0.0))
                violation['plateValid'] = v.get('plate_valid', False)
                plate_count += 1
                if v.get('plate_valid', False):
                    valid_plate_count += 1
            result['violations'].append(violation)
            vtype = v.get('type', 'UNKNOWN')
            result['stats']['byType'][vtype] = result['stats']['byType'].get(vtype, 0) + 1
            total_confidence += v.get('confidence', 0.0)
        if result['stats']['total'] > 0:
            result['stats']['avgConfidence'] = total_confidence / result['stats']['total']
        result['stats']['totalPlates'] = plate_count
        result['stats']['validPlates'] = valid_plate_count
        return result
    except Exception as e:
        return {
            'error': str(e),
            'violations': [],
            'stats': {'total': 0, 'byType': {}, 'avgConfidence': 0, 'totalPlates': 0, 'validPlates': 0},
            'annotated_image_path': None
        }


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', type=str)
    parser.add_argument('--video', type=str)
    parser.add_argument('--confidence', type=float, default=0.5)
    parser.add_argument('--preprocess', type=lambda x: x.lower() == 'true', default=True)
    parser.add_argument('--interval', type=int, default=30)
    parser.add_argument('--max-frames', type=int, default=100)
    parser.add_argument('--json', action='store_true', default=True)
    args = parser.parse_args()

    if args.image:
        print(f"Processing image: {args.image}", file=sys.stderr)
        result = detect_violations_json(args.image, args.confidence, args.preprocess)
        print(json.dumps(result))
        sys.exit(0)
    elif args.video:
        print(f"Processing video: {args.video}", file=sys.stderr)
        result_json = detect_violations_json(args.video, args.confidence, args.preprocess)
        print(json.dumps(result_json))
        sys.exit(0)

    MODEL_PATH = "models/traffic_violation_best.pt"
    TEST_IMAGE = "test_images/sample_traffic.jpg"
    OUTPUT_DIR = "test_outputs"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Initializing Violation Detector...", file=sys.stderr)
    detector = ViolationDetector(model_path=MODEL_PATH)

    if os.path.exists(TEST_IMAGE):
        print(f"Processing image: {TEST_IMAGE}", file=sys.stderr)

        try:
            violations, detections = detector.detect_violations(
                TEST_IMAGE, enable_preprocessing=True
            )

            print(f"\nFound {len(violations)} violation(s):", file=sys.stderr)
            for i, v in enumerate(violations, 1):
                print(f"{i}. {v['type']} (Confidence: {v['confidence']:.2f})", file=sys.stderr)
                if v.get("plate_text"):
                    print(f"   Plate: {v['plate_text']}", file=sys.stderr)

            image = cv2.imread(TEST_IMAGE)
            annotated = detector.draw_violations(image, violations)

            output_path = os.path.join(OUTPUT_DIR, "violation_detection_result.jpg")
            cv2.imwrite(output_path, annotated)
            print(f"\nAnnotated image saved to: {output_path}", file=sys.stderr)

        except Exception as e:
            print(f"Error processing image: {e}", file=sys.stderr)
    else:
        print(f"Test image not found: {TEST_IMAGE}", file=sys.stderr)
        print("Please update TEST_IMAGE path to a valid image file.", file=sys.stderr)

        print("\nCreating sample test image...", file=sys.stderr)
        sample_img = np.ones((720, 1280, 3), dtype=np.uint8) * 255
        cv2.putText(
            sample_img,
            "Traffic Violation Detection Test",
            (100, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            (0, 0, 255),
            2,
        )
        cv2.putText(
            sample_img,
            "Please place your test image at:",
            (100, 200),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 0),
            1,
        )
        cv2.putText(
            sample_img,
            f"'{TEST_IMAGE}'",
            (100, 250),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            1,
        )

        cv2.imwrite(TEST_IMAGE, sample_img)
        print(f"Sample image created at: {TEST_IMAGE}", file=sys.stderr)
        print("Run the script again after updating the model path and test image.", file=sys.stderr)
