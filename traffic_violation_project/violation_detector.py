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
_DEFAULT_HELMET_MODEL_PATH = str(_BASE_DIR / "models" / "helmet_final_best.pt")
_DEFAULT_SEATBELT_MODEL_PATH = str(_BASE_DIR / "models" / "seatbelt_best.pt")
_DEFAULT_REDSIGNAL_MODEL_PATH = str(_BASE_DIR / "models" / "all_redsignal_wrongside_best.pt")

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

HELMET_CLASS_MAP = {
    0: "helmet",        # driver_with_helmet → helmet
    1: "vehicle",       # bike → vehicle
    2: "rider",         # driver → rider
    3: "helmet",        # passenger_with_helmet → helmet
    4: "no_helmet",     # driver_without_helmet → no_helmet
    5: "no_helmet",     # passenger_without_helmet → no_helmet
}

SEATBELT_CLASS_MAP = {
    0: "seatbelt",      # Seat_Belt → seatbelt
    1: "no_seatbelt",   # WithoutSeat_Belt → no_seatbelt
}

REDSIGNAL_CLASS_MAP = {
    0: "correct_direction",
    1: "wrong_direction",
    2: "illegal_parking",
    3: "license_plate",
    4: "red_light_violation",
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
        helmet_model_path=None,
        seatbelt_model_path=None,
        redsignal_model_path=None,
        device="cpu",
        use_enhanced_models=False,
    ):
        model_path = model_path or _DEFAULT_MODEL_PATH
        plate_model_path = plate_model_path or _DEFAULT_PLATE_MODEL_PATH
        helmet_model_path = helmet_model_path or _DEFAULT_HELMET_MODEL_PATH
        seatbelt_model_path = seatbelt_model_path or _DEFAULT_SEATBELT_MODEL_PATH
        redsignal_model_path = redsignal_model_path or _DEFAULT_REDSIGNAL_MODEL_PATH
        model_path = str(Path(model_path)) if Path(model_path).is_absolute() else str(_BASE_DIR / model_path)
        plate_model_path = str(Path(plate_model_path)) if Path(plate_model_path).is_absolute() else str(_BASE_DIR / plate_model_path)
        helmet_model_path = str(Path(helmet_model_path)) if Path(helmet_model_path).is_absolute() else str(_BASE_DIR / helmet_model_path)
        seatbelt_model_path = str(Path(seatbelt_model_path)) if Path(seatbelt_model_path).is_absolute() else str(_BASE_DIR / seatbelt_model_path)
        redsignal_model_path = str(Path(redsignal_model_path)) if Path(redsignal_model_path).is_absolute() else str(_BASE_DIR / redsignal_model_path)

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at: {model_path}")

        self.model = YOLO(model_path)
        self.device = device
        if device == "cuda" and torch.cuda.is_available():
            self.model.to("cuda")
            logger.info("Traffic model loaded on GPU")
        else:
            logger.info("Traffic model loaded on CPU")

        # Load specialized ensemble models
        self.helmet_model = None
        self.seatbelt_model = None
        self.redsignal_model = None
        for name, path in [("helmet", helmet_model_path), ("seatbelt", seatbelt_model_path), ("redsignal", redsignal_model_path)]:
            if os.path.exists(path):
                try:
                    m = YOLO(path)
                    if self.device == "cuda" and torch.cuda.is_available():
                        m.to("cuda")
                    setattr(self, f"{name}_model", m)
                    logger.info("%s model loaded: %s", name, os.path.basename(path))
                except Exception as e:
                    logger.warning("Failed to load %s model at %s: %s", name, path, e)
            else:
                logger.warning("%s model not found at %s, skipping", name, path)

        self.person_model = YOLO('models/yolov8n.pt')
        print("DEBUG: Person model loaded successfully", file=sys.stderr)
        if self.device == "cuda" and torch.cuda.is_available():
            self.person_model.to("cuda")

        self.plate_recognizer = LicensePlateRecognizer(
            plate_model_path if plate_model_path else None, device
        )

        self.class_names = self.model.names

        self.iou_threshold = 0.3

        self.preprocessor = ImagePreprocessor()
        self.explanation_engine = ExplanationEngine()
        self.evidence_generator = EvidenceGenerator()
        self.vehicle_classifier = VehicleClassifier(model_path)
        # Per-model confidence thresholds (tuned for optimal detection)
        self.conf_thresholds = {
            "base": 0.25,        # Lower threshold — catch everything, let specialized models refine
            "helmet": 0.35,      # Specialized helmet model — high precision
            "seatbelt": 0.30,    # Seatbelts are small — moderate threshold
            "redsignal": 0.30,   # ML violations — moderate threshold
            "plate": 0.40,       # License plate detection — high precision
        }
        self.use_enhanced_models = use_enhanced_models
        self.enhanced_pipeline = None

        if use_enhanced_models:
            self._init_enhanced_models()

    def _init_enhanced_models(self):
        """Initialize enhanced models (VehicleNet, StreetSignSense, EULPR)"""
        try:
            import sys as _sys
            _enhanced_path = str(_BASE_DIR.parent / "python")
            if _enhanced_path not in _sys.path:
                _sys.path.insert(0, _enhanced_path)

            from enhanced_detection_pipeline import EnhancedDetectionPipeline
            self.enhanced_pipeline = EnhancedDetectionPipeline(use_enhanced=True)
            logger.info("Enhanced models (UVH-26, StreetSignSense, EULPR) loaded")
        except ImportError as e:
            logger.warning("Enhanced models not available: %s. Install with: pip install huggingface_hub", e)
            self.use_enhanced_models = False
        except Exception as e:
            logger.warning("Failed to load enhanced models: %s", e)
            self.use_enhanced_models = False

    def _run_helmet_model(self, image, confidence_threshold):
        """Run the specialized helmet model. Returns helmet_model_detections (driver/passenger
        with/without labels), and a set of no_helmet, helmet, rider, vehicle detections mapped
        to standard class names."""
        if self.helmet_model is None:
            return [], [], [], [], []

        helmet_raw = []
        no_helmet_raw = []
        riders_extra = []
        vehicles_extra = []

        try:
            hr = self.helmet_model(image, conf=confidence_threshold, verbose=False)
            if hr and len(hr) > 0:
                hb = hr[0].boxes
                if hb is not None and len(hb) > 0:
                    for box, conf, cls_id in zip(
                        hb.xyxy.cpu().numpy(),
                        hb.conf.cpu().numpy(),
                        hb.cls.cpu().numpy().astype(int),
                    ):
                        entry = {
                            "box": box.tolist(),
                            "bbox": box.tolist(),
                            "confidence": float(conf),
                            "class_id": int(cls_id),
                            "source": "helmet_model",
                        }
                        if cls_id in (0, 3):  # driver_with_helmet, passenger_with_helmet
                            entry["class_name"] = "helmet"
                            helmet_raw.append(entry)
                        elif cls_id in (4, 5):  # driver_without_helmet, passenger_without_helmet
                            entry["class_name"] = "no_helmet"
                            no_helmet_raw.append(entry)
                        elif cls_id == 1:  # bike
                            entry["class_name"] = "vehicle"
                            vehicles_extra.append(entry)
                        elif cls_id == 2:  # driver
                            entry["class_name"] = "rider"
                            riders_extra.append(entry)
        except Exception as e:
            logger.warning("Helmet model inference error: %s", e)

        return helmet_raw, no_helmet_raw, riders_extra, vehicles_extra

    def _run_seatbelt_model(self, image, confidence_threshold):
        """Run the specialized seatbelt model. Returns seatbelt and no_seatbelt detections
        as primary authority for seatbelt-related classes."""
        seatbelt_raw = []
        no_seatbelt_raw = []

        if self.seatbelt_model is None:
            return seatbelt_raw, no_seatbelt_raw

        try:
            sr = self.seatbelt_model(image, conf=confidence_threshold, verbose=False)
            if sr and len(sr) > 0:
                sb = sr[0].boxes
                if sb is not None and len(sb) > 0:
                    for box, conf, cls_id in zip(
                        sb.xyxy.cpu().numpy(),
                        sb.conf.cpu().numpy(),
                        sb.cls.cpu().numpy().astype(int),
                    ):
                        entry = {
                            "box": box.tolist(),
                            "bbox": box.tolist(),
                            "confidence": float(conf),
                            "class_id": int(cls_id),
                            "source": "seatbelt_model",
                        }
                        mapped = SEATBELT_CLASS_MAP.get(int(cls_id))
                        if mapped == "seatbelt":
                            entry["class_name"] = "seatbelt"
                            seatbelt_raw.append(entry)
                        elif mapped == "no_seatbelt":
                            entry["class_name"] = "no_seatbelt"
                            no_seatbelt_raw.append(entry)
        except Exception as e:
            logger.warning("Seatbelt model inference error: %s", e)

        return seatbelt_raw, no_seatbelt_raw

    def _run_redsignal_model(self, image, confidence_threshold):
        """Run the specialized red signal / wrong side model. Returns ML violation
        detections and license plate region hints."""
        ml_violations = []
        plate_hints = []

        if self.redsignal_model is None:
            return ml_violations, plate_hints

        try:
            rr = self.redsignal_model(image, conf=confidence_threshold, verbose=False)
            if rr and len(rr) > 0:
                rb = rr[0].boxes
                if rb is not None and len(rb) > 0:
                    for box, conf, cls_id in zip(
                        rb.xyxy.cpu().numpy(),
                        rb.conf.cpu().numpy(),
                        rb.cls.cpu().numpy().astype(int),
                    ):
                        mapped = REDSIGNAL_CLASS_MAP.get(int(cls_id))
                        if mapped == "license_plate":
                            plate_hints.append({
                                "box": box.tolist(),
                                "bbox": box.tolist(),
                                "confidence": float(conf),
                                "class_name": "license_plate",
                                "source": "redsignal_model",
                            })
                        elif mapped in ("wrong_direction", "red_light_violation", "illegal_parking"):
                            ml_violations.append({
                                "box": box.tolist(),
                                "bbox": box.tolist(),
                                "confidence": float(conf),
                                "class_name": mapped,
                                "source": "redsignal_model",
                            })
        except Exception as e:
            logger.warning("Red signal model inference error: %s", e)

        return ml_violations, plate_hints

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

    def _is_head_region(self, nh_box, riders, img_h):
        """
        Returns True only if nh_box overlaps with the upper 35% (head zone)
        of at least one rider, AND passes size + aspect ratio sanity checks.
        When no riders are available, relies on size + aspect checks alone.
        """
        nx1, ny1, nx2, ny2 = nh_box
        nw = nx2 - nx1
        nh_h = ny2 - ny1

        # Sanity 1: aspect ratio — heads are roughly square
        aspect = nw / nh_h if nh_h > 0 else 0
        if aspect < 0.4 or aspect > 2.5:
            return False

        # Sanity 2: absolute size — a head can't be tiny or gigantic
        area = nw * nh_h
        min_area = (img_h * 0.02) ** 2
        max_area = (img_h * 0.35) ** 2
        if area < min_area or area > max_area:
            return False

        # Sanity 3: if riders are available, require overlap with upper 35%
        if riders:
            for rider in riders:
                rx1, ry1, rx2, ry2 = rider["box"]
                rider_h = ry2 - ry1
                head_zone_bottom = ry1 + rider_h * 0.35

                ix1 = max(nx1, rx1)
                iy1 = max(ny1, ry1)
                ix2 = min(nx2, rx2)
                iy2 = min(ny2, head_zone_bottom)

                if ix2 > ix1 and iy2 > iy1:
                    inter = (ix2 - ix1) * (iy2 - iy1)
                    nh_area = nw * nh_h
                    if nh_area > 0 and inter / nh_area > 0.25:
                        return True
            return False

        # No riders to cross-check — pass based on size + aspect
        return True

    def extract_plate_text(self, image, vehicle_box):
        return self.plate_recognizer.extract_plate_text(image, vehicle_box)

    def _extract_plate_with_hints(self, image, vehicle_box, plate_hints, overlap_threshold=0.2):
        """Try vehicle-based plate extraction first, then fall back to
        redsignal model's license plate region hints."""
        plate = self.extract_plate_text(image, vehicle_box)
        if plate:
            return plate
        # Fallback: try the closest plate hint overlapping with vehicle box
        if plate_hints:
            for ph in plate_hints:
                iou = self.compute_iou(vehicle_box, ph["box"])
                if iou > overlap_threshold:
                    plate = self.extract_plate_text(image, ph["box"])
                    if plate:
                        return plate
        return None

    def detect_violations(
        self, image, confidence_threshold=None, enable_preprocessing=True
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

        # Use per-model tuned confidence thresholds for maximum coverage
        base_conf = confidence_threshold if confidence_threshold is not None else self.conf_thresholds["base"]
        helmet_conf = self.conf_thresholds["helmet"]
        seatbelt_conf = self.conf_thresholds["seatbelt"]
        redsignal_conf = self.conf_thresholds["redsignal"]

        results = self.model(proc_image, conf=base_conf, verbose=False)

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

        # --- SPECIALIZED MODEL INFERENCE (each at its own tuned threshold) ---

        # 1. Helmet model — PRIMARY authority for helmet/no_helmet
        h_helmet, h_no_helmet, h_riders, h_vehicles = self._run_helmet_model(proc_image, helmet_conf)

        # 2. Seatbelt model — PRIMARY authority for seatbelt/no_seatbelt
        s_seatbelt, s_no_seatbelt = self._run_seatbelt_model(proc_image, seatbelt_conf)

        # 3. Red signal / wrong side model — ML violation detection + plate hints
        ml_violations, plate_hints = self._run_redsignal_model(proc_image, redsignal_conf)

        # 4. Person detection model (COCO yolov8n) — for triple riding clustering fallback
        person_results = self.person_model(proc_image, conf=base_conf, verbose=False)
        person_detections = []
        if len(person_results) > 0 and person_results[0].boxes is not None:
            for box in person_results[0].boxes:
                cls = int(box.cls.item())
                if cls == 0:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = box.conf.item()
                    person_detections.append({
                        'bbox': [x1, y1, x2, y2],
                        'confidence': conf
                    })
        print(f"DEBUG: Raw person detections = {len(person_detections)}", file=sys.stderr)
        for i, p in enumerate(person_detections[:5]):
            print(f"DEBUG: Person {i}: bbox={p['bbox']}, conf={p['confidence']:.3f}", file=sys.stderr)

        # --- STRIP OVERLAPPING BASE MODEL DETECTIONS (specialized models win) ---
        helmet_model_boxes = [d["box"] for d in h_helmet + h_no_helmet]
        seatbelt_model_boxes = [d["box"] for d in s_seatbelt + s_no_seatbelt]

        filtered = []
        for d in detections:
            cls = d["class_name"]
            # Strip base model helmet/no_helmet where helmet model has a prediction
            if cls in ("helmet", "no_helmet"):
                if any(self.compute_iou(d["box"], hb) > self.iou_threshold for hb in helmet_model_boxes):
                    continue
            # Strip base model seatbelt/no_seatbelt where seatbelt model has a prediction
            if cls in ("seatbelt", "no_seatbelt", "without_seatbelt"):
                if any(self.compute_iou(d["box"], sb) > self.iou_threshold for sb in seatbelt_model_boxes):
                    continue
            filtered.append(d)
        detections = filtered

        # Add specialized model detections to pool
        for d in h_riders + h_vehicles:
            detections.append(d)
        for d in plate_hints:
            detections.append(d)

        # --- CATEGORIZE DETECTIONS (specialized models as primary) ---
        riders = [d for d in detections if d["class_name"] == "rider"]
        vehicles = [
            d for d in detections
            if d["class_name"] in ["vehicle", "car", "truck", "bus", "motorcycle"]
        ]

        # Helmet/no_helmet: helmet model first, then remaining base model
        helmets = list(h_helmet)
        no_helmets = list(h_no_helmet)
        for d in filtered:
            cls = d["class_name"]
            if cls == "helmet":
                helmets.append(d)
            elif cls in ("no_helmet", "without_helmet"):
                no_helmets.append(d)

        # Seatbelt/no_seatbelt: seatbelt model first, then remaining base model
        seatbelts = list(s_seatbelt)
        no_seatbelts = list(s_no_seatbelt)
        for d in filtered:
            cls = d["class_name"]
            if cls == "seatbelt":
                seatbelts.append(d)
            elif cls in ("no_seatbelt", "without_seatbelt"):
                no_seatbelts.append(d)

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

        # NO HELMET — with head-region validation to reject bags/objects
        # Helmet model detections (driver_without_helmet, passenger_without_helmet)
        # already validate actual people — skip head-region filter for them
        if no_helmets:
            img_h_px = original_image.shape[0]
            for det in no_helmets:
                is_helmet_model = det.get("source") == "helmet_model"
                if not is_helmet_model and not self._is_head_region(det["box"], riders, img_h_px):
                    logger.warning(
                        "[FILTER] Rejected no_helmet at %s (conf=%.2f) — not a head region",
                        det["box"], det["confidence"],
                    )
                    continue

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
                        plate = self._extract_plate_with_hints(original_image, best_vbox, plate_hints)
                violations.append(
                    {
                        "type": "NO HELMET",
                        "violation_type": "NO HELMET",
                        "confidence": det["confidence"],
                        "bbox": det["box"],
                        "plate_text": plate,
                        "timestamp": now,
                        "source": det.get("source", "base_model"),
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
                    plate = self._extract_plate_with_hints(original_image, veh_bbox, plate_hints)
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
                plate = self._extract_plate_with_hints(original_image, det["box"], plate_hints)
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
                    plate = self._extract_plate_with_hints(original_image, vbox, plate_hints)
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
        def count_overlapping(bbox_list, expanded_box):
            ex1, ey1, ex2, ey2 = expanded_box
            count = 0
            for item in bbox_list:
                ibox = item["box"] if "box" in item else item.get("bbox", [])
                if not ibox or len(ibox) < 4:
                    continue
                rx1, ry1, rx2, ry2 = ibox[:4]
                ix1 = max(ex1, rx1)
                iy1 = max(ey1, ry1)
                ix2 = min(ex2, rx2)
                iy2 = min(ey2, ry2)
                if ix1 < ix2 and iy1 < iy2:
                    inter = (ix2 - ix1) * (iy2 - iy1)
                    item_area = (rx2 - rx1) * (ry2 - ry1)
                    if item_area > 0 and inter / item_area > 0.1:
                        count += 1
            return count

        # Path A: Vehicle boxes exist — use expanded overlap counting
        triple_riding_flagged = False
        motos = [
            v for v in vehicles
            if any(k in v.get("class_name", "") for k in ["vehicle", "motorcycle", "motorbike", "bike"])
        ]
        for vehicle in motos:
            vbox = vehicle["box"]
            vw = vbox[2] - vbox[0]
            vh = vbox[3] - vbox[1]

            x1, y1, x2, y2 = vbox
            expanded = [
                x1 - vw * 0.1,
                y1 - vh * 0.8,
                x2 + vw * 0.1,
                y2 + vh * 0.1,
            ]

            rider_count = count_overlapping(riders, expanded)
            people_count = rider_count
            if rider_count == 0 and no_helmets:
                people_count = count_overlapping(no_helmets, expanded)

            if people_count > 2:
                plate = self._extract_plate_with_hints(original_image, vbox, plate_hints)
                violations.append({
                    "type": "TRIPLE RIDING",
                    "violation_type": "TRIPLE RIDING",
                    "confidence": vehicle["confidence"],
                    "bbox": vbox,
                    "plate_text": plate,
                    "timestamp": now,
                    "rider_count": people_count,
                    "source": "rider" if rider_count > 0 else "no_helmet_proxy",
                })
                triple_riding_flagged = True

        # Path B: No vehicle class fired — cluster person/rider/no_helmet/no_seatbelt boxes
        #          using horizontal + vertical geometry gates
        if not triple_riding_flagged:
            candidates = list(riders)
            if not candidates:
                candidates = [
                    d for d in (no_helmets + no_seatbelts)
                    if d.get("box") and len(d["box"]) >= 4
                ]

            if len(candidates) >= 3:
                candidates.sort(key=lambda d: d["box"][0])
                for i in range(len(candidates) - 2):
                    window = [candidates[i]]
                    ref_x2 = candidates[i]["box"][2]

                    for j in range(i + 1, len(candidates)):
                        if candidates[j]["box"][0] < ref_x2 + 300:
                            window.append(candidates[j])
                        else:
                            break

                    if len(window) >= 3:
                        bottoms = [d["box"][3] for d in window]
                        if max(bottoms) - min(bottoms) < 200:
                            all_x = [c for d in window for c in (d["box"][0], d["box"][2])]
                            all_y = [c for d in window for c in (d["box"][1], d["box"][3])]
                            cluster_box = [min(all_x), min(all_y), max(all_x), max(all_y)]
                            plate = self._extract_plate_with_hints(original_image, cluster_box, plate_hints)
                            avg_conf = sum(d["confidence"] for d in window) / len(window)
                            violations.append({
                                "type": "TRIPLE RIDING",
                                "violation_type": "TRIPLE RIDING",
                                "confidence": avg_conf,
                                "bbox": cluster_box,
                                "plate_text": plate,
                                "timestamp": now,
                                "rider_count": len(window),
                                "source": "cluster_proxy",
                            })
                            triple_riding_flagged = True
                            break

        # Path C: Person-model-based center-distance clustering fallback
        print("DEBUG: Entering triple-riding clustering block", file=sys.stderr)
        person_bboxes = [p['bbox'] for p in person_detections if p.get('bbox') is not None]
        if not triple_riding_flagged and len(person_bboxes) >= 3:
            centers = [
                ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
                for b in person_bboxes
            ]
            threshold_distance = 250

            groups = []
            for i, bbox in enumerate(person_bboxes):
                assigned = False
                for group in groups:
                    for idx in group:
                        dist = ((centers[i][0] - centers[idx][0]) ** 2 +
                                (centers[i][1] - centers[idx][1]) ** 2) ** 0.5
                        if dist < threshold_distance:
                            group.append(i)
                            assigned = True
                            break
                    if assigned:
                        break
                if not assigned:
                    groups.append([i])

            print(f"DEBUG: Groups formed = {len(groups)}", file=sys.stderr)
            for gi, g in enumerate(groups):
                print(f"DEBUG: Group {gi} has {len(g)} persons", file=sys.stderr)

            for group in groups:
                if len(group) >= 3:
                    bboxes = [person_bboxes[idx] for idx in group]
                    x1 = min(b[0] for b in bboxes)
                    y1 = min(b[1] for b in bboxes)
                    x2 = max(b[2] for b in bboxes)
                    y2 = max(b[3] for b in bboxes)
                    avg_conf = sum(person_detections[idx]['confidence'] for idx in group) / len(group)
                    violations.append({
                        "type": "TRIPLE RIDING",
                        "violation_type": "TRIPLE RIDING",
                        "confidence": avg_conf,
                        "bbox": [x1, y1, x2, y2],
                        "timestamp": now,
                        "rider_count": len(group),
                        "source": "person_cluster",
                    })
                    triple_riding_flagged = True

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

        # ML-based violations from all_redsignal_wrongside_best.pt ensemble model
        for mv in ml_violations:
            violation_type_map = {
                "wrong_direction": "WRONG SIDE",
                "red_light_violation": "RED LIGHT",
                "illegal_parking": "ILLEGAL PARKING",
            }
            vtype = violation_type_map.get(mv["class_name"])
            if vtype:
                # Only add if there isn't already a same-type violation nearby (IoU > 0.3)
                is_duplicate = any(
                    v["type"] == vtype and self.compute_iou(mv["box"], v.get("bbox", v.get("box", [0,0,0,0]))) > 0.3
                    for v in violations
                )
                if not is_duplicate:
                    violations.append({
                        "type": vtype,
                        "violation_type": vtype,
                        "confidence": mv["confidence"],
                        "bbox": mv["box"],
                        "timestamp": now,
                        "source": mv["source"],
                    })

        violations = self.explanation_engine.generate_explanations_for_violations(violations)

        if self.use_enhanced_models and self.enhanced_pipeline is not None:
            try:
                enhanced = self.enhanced_pipeline.process_image(
                    original_image if isinstance(image, str) else image,
                    confidence_threshold
                )

                # Enrich NO HELMET with UVH-26 vehicle classification
                vehicle_classes = {v['class'] for v in enhanced.get('vehicles', [])}
                if '2-wheeler' in vehicle_classes:
                    # Ensure 2-wheelers without helmet are flagged
                    has_no_helmet = any(
                        v['type'] == 'NO HELMET' for v in violations
                    )
                    if not has_no_helmet:
                        for veh in enhanced['vehicles']:
                            if veh['class'] == '2-wheeler' and veh.get('requires_helmet'):
                                plate = self.extract_plate_text(
                                    original_image, veh['bbox']
                                )
                                violations.append({
                                    'type': 'NO HELMET',
                                    'violation_type': 'NO HELMET',
                                    'confidence': veh['confidence'],
                                    'bbox': veh['bbox'],
                                    'plate_text': plate,
                                    'timestamp': now,
                                    'source': 'uvh26_enhanced',
                                })

                # Traffic sign violations from StreetSignSense
                sign_classes = {s['class'].lower() for s in enhanced.get('traffic_signs', [])}
                for sign_class in sign_classes:
                    if 'no entry' in sign_class or 'wrong' in sign_class or 'no motor' in sign_class:
                        violations.append({
                            'type': 'WRONG SIDE',
                            'violation_type': 'WRONG SIDE',
                            'confidence': 0.9,
                            'bbox': [0, 0, 0, 0],
                            'timestamp': now,
                            'source': 'streetsignsense_enhanced',
                        })

                # EULPR plate results - enrich existing violations
                if enhanced.get('license_plates'):
                    for plate_result in enhanced['license_plates']:
                        if plate_result.get('text'):
                            text = plate_result['text']
                            for v in violations:
                                if not v.get('plate_text') and v.get('type') != 'WRONG SIDE':
                                    v['plate_text'] = text
                                    v['ocr_confidence'] = plate_result.get('confidence', 0)

                logger.info(
                    "Enhanced pipeline: %d vehicles, %d signs, %d plates",
                    len(enhanced.get('vehicles', [])),
                    len(enhanced.get('traffic_signs', [])),
                    len(enhanced.get('license_plates', [])),
                )
            except Exception as e:
                logger.error("Enhanced pipeline error: %s", e)

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
        return draw_annotations(annotated, violations)

    def draw_annotations(self, image, violations, detections=None):
        if isinstance(image, str):
            annotated = cv2.imread(image)
            if annotated is None:
                raise FileNotFoundError(f"Could not read image: {image}")
        else:
            annotated = image.copy()
        return draw_annotations(annotated, violations, detections)


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


def draw_annotations(image, violations, detections=None):
    """
    Draw rich bounding boxes and annotations on image with per-type colors,
    confidence bars, labels, plate text, fine amounts, and watermark.
    """
    if isinstance(image, str):
        annotated = cv2.imread(image)
        if annotated is None:
            raise FileNotFoundError(f"Could not read image: {image}")
    else:
        annotated = image.copy()

    height, width = annotated.shape[:2]

    VIOLATION_COLORS = {
        'NO_HELMET': (0, 0, 255),
        'NO_SEATBELT': (0, 165, 255),
        'TRIPLE_RIDING': (255, 0, 255),
        'WRONG_SIDE': (255, 0, 0),
        'STOP_LINE': (0, 255, 0),
        'RED_LIGHT': (0, 0, 255),
        'ILLEGAL_PARKING': (0, 255, 255),
        'NO HELMET': (0, 0, 255),
        'NO SEATBELT': (0, 165, 255),
        'TRIPLE RIDING': (255, 0, 255),
        'WRONG SIDE': (255, 0, 0),
        'STOP LINE': (0, 255, 0),
        'RED LIGHT': (0, 0, 255),
        'ILLEGAL PARKING': (0, 255, 255),
    }

    DETECTION_COLORS = {
        'vehicle': (0, 255, 255),
        'car': (0, 255, 255),
        'truck': (0, 255, 255),
        'bus': (0, 255, 255),
        'motorcycle': (0, 255, 255),
        'person_rider': (0, 255, 0),
        'rider': (0, 255, 0),
        'person': (0, 255, 0),
        'helmet': (255, 255, 0),
        'seatbelt': (255, 0, 255),
        'pedestrian': (255, 200, 0),
    }

    if detections:
        for det in detections:
            bbox = det.get('box', det.get('bbox', []))
            if not bbox or len(bbox) < 4:
                continue
            x1, y1, x2, y2 = map(int, bbox[:4])
            class_name = det.get('class_name', 'object')
            conf = det.get('confidence', 0)
            color = DETECTION_COLORS.get(class_name, (128, 128, 128))
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 1)
            label = f"{class_name}: {conf:.2f}"
            cv2.putText(annotated, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    for violation in violations:
        bbox = violation.get('bbox', violation.get('box', []))
        if not bbox or len(bbox) < 4:
            continue

        x1, y1, x2, y2 = map(int, bbox[:4])
        vtype = violation.get('type', violation.get('violation_type', 'UNKNOWN'))
        confidence = violation.get('confidence', 0)
        plate_text = violation.get('plate_text', '')
        fine = violation.get('fine', 0)

        color = VIOLATION_COLORS.get(vtype, (255, 255, 255))

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)

        bar_width = int((x2 - x1) * min(confidence, 1.0))
        if bar_width > 0:
            cv2.rectangle(annotated, (x1, y1 - 8), (x1 + bar_width, y1), color, -1)

        label_parts = [f"{vtype.replace('_', ' ')}"]
        if confidence > 0:
            label_parts.append(f"{confidence*100:.1f}%")
        label = ' | '.join(label_parts)

        (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
        label_y = y1 - 32
        if label_y < 10:
            label_y = y2 + 10

        cv2.rectangle(annotated, (x1, label_y - text_h - 6),
                      (x1 + text_w + 12, label_y + 4), color, -1)
        cv2.putText(annotated, label, (x1 + 6, label_y + 4),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        if plate_text:
            plate_label = f"Plate: {plate_text}"
            plate_y = y2 + 22
            (pw, ph), _ = cv2.getTextSize(plate_label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(annotated, (x1, plate_y - ph - 4),
                          (x1 + pw + 10, plate_y + 4), (0, 0, 0), -1)
            cv2.putText(annotated, plate_label, (x1 + 5, plate_y + 4),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        if fine > 0:
            fine_label = f"Fine: Rs.{fine}"
            fine_y = y2 + 46
            (fw, fh), _ = cv2.getTextSize(fine_label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(annotated, (x1, fine_y - fh - 4),
                          (x1 + fw + 10, fine_y + 4), (0, 0, 0), -1)
            cv2.putText(annotated, fine_label, (x1 + 5, fine_y + 4),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cv2.putText(annotated, f"Gridlock AI | {timestamp}", (10, height - 10),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    count_label = f"{len(violations)} violation(s) detected"
    cv2.putText(annotated, count_label, (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255) if violations else (0, 255, 0), 2)

    return annotated


def extract_plate_text(image, vehicle_bbox):
    from license_plate_recognition import extract_plate_text as _lpr_extract
    return _lpr_extract(image, vehicle_bbox)


def is_valid_plate(text):
    from license_plate_recognition import is_valid_plate as _lpr_valid
    return _lpr_valid(text)


def generate_evidence_image(image, violations, detections=None):
    annotated = draw_annotations(image, violations, detections)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    evidence_dir = Path("evidence")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    filename = f"violation_{now}.jpg"
    path = str(evidence_dir / filename)
    cv2.imwrite(path, annotated)
    logger.info("Annotated image saved: %s", path)
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


def detect_violations_json(image_path, confidence_threshold=0.5, enable_preprocessing=True, use_enhanced_models=False):
    try:
        detector = ViolationDetector(use_enhanced_models=use_enhanced_models)
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
    parser.add_argument('--enhanced', action='store_true', default=False,
                        help='Use enhanced models (VehicleNet UVH-26, StreetSignSense, EULPR)')
    args = parser.parse_args()

    if args.image:
        print(f"Processing image: {args.image}", file=sys.stderr)
        if args.enhanced:
            print("Using enhanced models (UVH-26 + StreetSignSense + EULPR)", file=sys.stderr)
        result = detect_violations_json(args.image, args.confidence, args.preprocess, args.enhanced)
        print(json.dumps(result))
        sys.exit(0)
    elif args.video:
        print(f"Processing video: {args.video}", file=sys.stderr)
        if args.enhanced:
            print("Using enhanced models (UVH-26 + StreetSignSense + EULPR)", file=sys.stderr)
        result_json = detect_violations_json(args.video, args.confidence, args.preprocess, args.enhanced)
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
