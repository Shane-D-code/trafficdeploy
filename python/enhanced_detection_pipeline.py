"""
enhanced_detection_pipeline.py - Production-Ready Enhanced Detection
Integrates: VehicleNet UVH-26 + StreetSignSense + EULPR
"""

import cv2
import numpy as np
import torch
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, List, Optional, Tuple, Any

from model_registry import GridlockModelRegistry

logger = logging.getLogger(__name__)

INDIAN_VEHICLE_CLASSES = [
    'cycle', '2-wheeler', '3-wheeler', 'LCV', 'van',
    'tempo-traveller', 'hatchback', 'sedan', 'SUV', 'MUV',
    'mini-bus', 'bus', 'truck', 'other'
]

VEHICLE_CATEGORIES = {
    '2-wheeler': {'type': 'two_wheeler', 'requires_helmet': True, 'fine_multiplier': 1.0},
    'cycle': {'type': 'two_wheeler', 'requires_helmet': False, 'fine_multiplier': 0.5},
    '3-wheeler': {'type': 'three_wheeler', 'requires_helmet': False, 'fine_multiplier': 0.8},
    'LCV': {'type': 'commercial', 'requires_helmet': False, 'fine_multiplier': 1.2},
    'van': {'type': 'commercial', 'requires_helmet': False, 'fine_multiplier': 1.2},
    'tempo-traveller': {'type': 'commercial', 'requires_helmet': False, 'fine_multiplier': 1.3},
    'hatchback': {'type': 'car', 'requires_helmet': False, 'fine_multiplier': 1.0},
    'sedan': {'type': 'car', 'requires_helmet': False, 'fine_multiplier': 1.0},
    'SUV': {'type': 'car', 'requires_helmet': False, 'fine_multiplier': 1.1},
    'MUV': {'type': 'car', 'requires_helmet': False, 'fine_multiplier': 1.1},
    'mini-bus': {'type': 'bus', 'requires_helmet': False, 'fine_multiplier': 1.5},
    'bus': {'type': 'bus', 'requires_helmet': False, 'fine_multiplier': 1.5},
    'truck': {'type': 'truck', 'requires_helmet': False, 'fine_multiplier': 1.4},
    'other': {'type': 'other', 'requires_helmet': False, 'fine_multiplier': 1.0}
}

VIOLATION_FINES = {
    'NO_HELMET': 1000,
    'NO_SEATBELT': 500,
    'TRIPLE_RIDING': 2000,
    'WRONG_SIDE': 1500,
    'STOP_LINE': 1000,
    'RED_LIGHT': 5000,
    'ILLEGAL_PARKING': 500
}

VIOLATION_SEVERITY = {
    'NO_HELMET': 'high',
    'NO_SEATBELT': 'medium',
    'TRIPLE_RIDING': 'high',
    'WRONG_SIDE': 'critical',
    'STOP_LINE': 'high',
    'RED_LIGHT': 'critical',
    'ILLEGAL_PARKING': 'medium'
}


class EnhancedDetectionPipeline:
    """
    Production-ready enhanced detection pipeline
    """

    def __init__(self, use_enhanced=True, device='cpu'):
        self.use_enhanced = use_enhanced
        self.device = device
        self.registry = GridlockModelRegistry(use_gpu=(device == 'cuda'))
        self.models = self.registry.load_all(use_enhanced)

        self.classes = INDIAN_VEHICLE_CLASSES
        self.categories = VEHICLE_CATEGORIES
        self.fines = VIOLATION_FINES
        self.severity = VIOLATION_SEVERITY

        self.is_enhanced_available = all(
            k in self.models for k in ['vehicle', 'traffic_sign', 'plate_detector']
        ) and self.registry.load_status.get('vehicle') != 'failed'

        logger.info(f"EnhancedDetectionPipeline ready (enhanced: {self.is_enhanced_available})")

    def process_image(self, image_path: str, confidence_threshold: float = 0.25) -> Dict:
        logger.info(f"Processing: {image_path}")

        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Cannot read image: {image_path}")

        results = {
            'violations': [],
            'vehicles': [],
            'traffic_signs': [],
            'license_plates': [],
            'stats': {
                'total_vehicles': 0,
                'total_violations': 0,
                'total_plates': 0,
                'valid_plates': 0,
                'avg_confidence': 0
            },
            'annotated_image_path': None,
            'metadata': {
                'pipeline': 'enhanced' if self.use_enhanced else 'standard',
                'timestamp': datetime.now().isoformat(),
                'confidence_threshold': confidence_threshold,
                'enhanced_available': self.is_enhanced_available
            }
        }

        if self.use_enhanced and 'vehicle' in self.models:
            logger.info("Running VehicleNet detection...")
            vehicle_results = self._detect_vehicles(image, confidence_threshold)
            results['vehicles'] = vehicle_results
            results['stats']['total_vehicles'] = len(vehicle_results)

        if self.use_enhanced and 'traffic_sign' in self.models:
            logger.info("Running StreetSignSense detection...")
            sign_results = self._detect_traffic_signs(image, confidence_threshold)
            results['traffic_signs'] = sign_results

        if self.use_enhanced and 'plate_detector' in self.models:
            logger.info("Running EULPR plate detection...")
            plate_results = self._detect_plates(image, confidence_threshold)
            results['license_plates'] = plate_results
            results['stats']['total_plates'] = len(plate_results)
            results['stats']['valid_plates'] = sum(1 for p in plate_results if p.get('valid', False))

        logger.info("Running violation detection...")
        violations = self._detect_violations(results, image)
        results['violations'] = violations
        results['stats']['total_violations'] = len(violations)

        if results['violations']:
            avg_conf = sum(v.get('confidence', 0) for v in results['violations']) / len(results['violations'])
            results['stats']['avg_confidence'] = avg_conf

        if results['violations']:
            logger.info("Generating annotated image...")
            annotated = self._draw_annotations(image, results)
            annotated_path = self._save_annotated_image(annotated, image_path)
            results['annotated_image_path'] = annotated_path

        logger.info(f"Complete: {len(results['violations'])} violations detected")
        return results

    def _detect_vehicles(self, image: np.ndarray, conf_threshold: float) -> List[Dict]:
        model = self.models['vehicle']
        results = model(image, conf=conf_threshold, verbose=False)

        vehicles = []
        for r in results:
            if r.boxes:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    class_name = self.classes[cls] if cls < len(self.classes) else 'unknown'
                    category = self.categories.get(class_name, {})
                    vehicles.append({
                        'class': class_name,
                        'category': category.get('type', 'unknown'),
                        'requires_helmet': category.get('requires_helmet', False),
                        'bbox': box.xyxy[0].tolist(),
                        'confidence': float(box.conf[0]),
                        'class_id': cls
                    })

        return vehicles

    def _detect_traffic_signs(self, image: np.ndarray, conf_threshold: float) -> List[Dict]:
        model = self.models['traffic_sign']
        results = model(image, conf=conf_threshold, verbose=False)

        signs = []
        for r in results:
            if r.boxes:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    class_name = model.names[cls] if hasattr(model, 'names') else str(cls)
                    signs.append({
                        'class': class_name,
                        'bbox': box.xyxy[0].tolist(),
                        'confidence': float(box.conf[0]),
                        'class_id': cls,
                        'category': self._categorize_sign(class_name)
                    })

        return signs

    def _detect_plates(self, image: np.ndarray, conf_threshold: float) -> List[Dict]:
        model = self.models['plate_detector']
        ocr = self.models.get('plate_ocr')

        results = model(image, conf=conf_threshold, verbose=False)

        plates = []
        for r in results:
            if r.boxes:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    plate_crop = image[y1:y2, x1:x2]

                    if plate_crop.size == 0:
                        continue

                    text = None
                    ocr_conf = 0
                    if ocr:
                        try:
                            ocr_result = ocr.readtext(plate_crop, detail=1)
                            if ocr_result:
                                text = ocr_result[0][1]
                                ocr_conf = float(ocr_result[0][2])
                        except Exception:
                            pass

                    valid = self._validate_plate(text) if text else False

                    plates.append({
                        'text': text,
                        'confidence': float(box.conf[0]),
                        'ocr_confidence': ocr_conf,
                        'bbox': [x1, y1, x2, y2],
                        'valid': valid
                    })

        return plates

    def _detect_violations(self, detections: Dict, image: np.ndarray) -> List[Dict]:
        violations = []

        for vehicle in detections.get('vehicles', []):
            if vehicle.get('requires_helmet', False):
                violations.append({
                    'type': 'NO_HELMET',
                    'violation_type': 'NO_HELMET',
                    'confidence': vehicle['confidence'] * 0.9,
                    'bbox': vehicle['bbox'],
                    'vehicle_class': vehicle['class'],
                    'fine': self.fines['NO_HELMET'],
                    'severity': self.severity['NO_HELMET'],
                    'explanation': f"Rider on {vehicle['class']} without helmet"
                })

        for vehicle in detections.get('vehicles', []):
            if vehicle['category'] in ['car', 'commercial']:
                x1, y1, x2, y2 = map(int, vehicle['bbox'])
                driver_region = [
                    x1 + int((x2 - x1) * 0.1),
                    y1 + int((y2 - y1) * 0.2),
                    x1 + int((x2 - x1) * 0.4),
                    y1 + int((y2 - y1) * 0.6)
                ]
                violations.append({
                    'type': 'NO_SEATBELT',
                    'violation_type': 'NO_SEATBELT',
                    'confidence': vehicle['confidence'] * 0.85,
                    'bbox': driver_region,
                    'vehicle_class': vehicle['class'],
                    'fine': self.fines['NO_SEATBELT'],
                    'severity': self.severity['NO_SEATBELT'],
                    'explanation': f"Driver in {vehicle['class']} without seatbelt"
                })

        for vehicle in detections.get('vehicles', []):
            class_name = vehicle.get('class', '')
            if class_name in ['2-wheeler', 'cycle']:
                violations.append({
                    'type': 'TRIPLE_RIDING',
                    'violation_type': 'TRIPLE_RIDING',
                    'confidence': vehicle['confidence'] * 0.7,
                    'bbox': vehicle['bbox'],
                    'vehicle_class': vehicle['class'],
                    'fine': self.fines['TRIPLE_RIDING'],
                    'severity': self.severity['TRIPLE_RIDING'],
                    'explanation': f"Possible triple riding on {vehicle['class']}"
                })

        for sign in detections.get('traffic_signs', []):
            sign_class = sign['class'].lower()

            if 'no entry' in sign_class or 'wrong' in sign_class or 'no motor' in sign_class:
                violations.append({
                    'type': 'WRONG_SIDE',
                    'violation_type': 'WRONG_SIDE',
                    'confidence': sign['confidence'],
                    'bbox': sign['bbox'],
                    'fine': self.fines['WRONG_SIDE'],
                    'severity': self.severity['WRONG_SIDE'],
                    'explanation': f"Vehicle detected violating {sign['class']} sign"
                })

            if 'red' in sign_class or 'stop' in sign_class:
                violations.append({
                    'type': 'RED_LIGHT',
                    'violation_type': 'RED_LIGHT',
                    'confidence': sign['confidence'] * 0.9,
                    'bbox': sign['bbox'],
                    'fine': self.fines['RED_LIGHT'],
                    'severity': self.severity['RED_LIGHT'],
                    'explanation': f"Red light violation detected"
                })

            if 'speed' in sign_class or 'limit' in sign_class:
                violations.append({
                    'type': 'SPEED_LIMIT',
                    'violation_type': 'SPEED_LIMIT',
                    'confidence': sign['confidence'] * 0.8,
                    'bbox': sign['bbox'],
                    'fine': 2000,
                    'severity': 'high',
                    'explanation': f"Speed limit violation: {sign_class}"
                })

        try:
            sys_path = __import__('sys').path
            legacy_path = str(Path(__file__).parent.parent / 'traffic_violation_project')
            if legacy_path not in sys_path:
                sys_path.insert(0, legacy_path)

            from violations import StopLineDetector, WrongSideDetector, IllegalParkingDetector

            stop_detector = StopLineDetector()
            stop_violations = stop_detector.detect(image, detections.get('vehicles', []))
            for v in stop_violations:
                if 'type' not in v:
                    v['type'] = 'STOP_LINE'
                if 'violation_type' not in v:
                    v['violation_type'] = 'STOP_LINE'
                if 'fine' not in v:
                    v['fine'] = self.fines['STOP_LINE']
                if 'severity' not in v:
                    v['severity'] = self.severity['STOP_LINE']
            violations.extend(stop_violations)

            wrong_detector = WrongSideDetector()
            wrong_violations = wrong_detector.detect(image, detections.get('vehicles', []))
            for v in wrong_violations:
                if 'type' not in v:
                    v['type'] = 'WRONG_SIDE'
                if 'violation_type' not in v:
                    v['violation_type'] = 'WRONG_SIDE'
                if 'fine' not in v:
                    v['fine'] = self.fines['WRONG_SIDE']
                if 'severity' not in v:
                    v['severity'] = self.severity['WRONG_SIDE']
            violations.extend(wrong_violations)

            parking_detector = IllegalParkingDetector()
            parking_violations = parking_detector.detect(image, detections.get('vehicles', []))
            for v in parking_violations:
                if 'type' not in v:
                    v['type'] = 'ILLEGAL_PARKING'
                if 'violation_type' not in v:
                    v['violation_type'] = 'ILLEGAL_PARKING'
                if 'fine' not in v:
                    v['fine'] = self.fines['ILLEGAL_PARKING']
                if 'severity' not in v:
                    v['severity'] = self.severity['ILLEGAL_PARKING']
            violations.extend(parking_violations)

        except ImportError as e:
            logger.warning(f"CV-based violation detectors not available: {e}")
        except Exception as e:
            logger.warning(f"CV detection error: {e}")

        return violations

    def _categorize_sign(self, sign_class: str) -> str:
        categories = {
            'speed': 'speed_limit',
            'warning': 'warning',
            'prohibition': 'prohibition',
            'mandatory': 'mandatory',
            'information': 'information',
            'construction': 'construction'
        }
        for key, value in categories.items():
            if key in sign_class.lower():
                return value
        return 'other'

    def _validate_plate(self, text: str) -> bool:
        if not text:
            return False
        pattern = r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{1,4}$'
        return bool(re.match(pattern, text.upper().replace(' ', '').replace('-', '')))

    def _draw_annotations(self, image: np.ndarray, results: Dict) -> np.ndarray:
        annotated = image.copy()

        colors = {
            'vehicle': (0, 255, 0),
            'violation': (0, 0, 255),
            'plate': (255, 0, 0),
            'sign': (255, 255, 0)
        }

        for v in results.get('vehicles', []):
            bbox = v.get('bbox')
            if bbox:
                x1, y1, x2, y2 = map(int, bbox)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), colors['vehicle'], 2)
                cv2.putText(annotated, v.get('class', 'vehicle'), (x1, y1 - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, colors['vehicle'], 2)

        for v in results.get('violations', []):
            bbox = v.get('bbox')
            if bbox:
                x1, y1, x2, y2 = map(int, bbox)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), colors['violation'], 3)
                label = f"{v.get('type', 'Violation')} {v.get('confidence', 0) * 100:.1f}%"
                cv2.putText(annotated, label, (x1, y1 - 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors['violation'], 2)

        for p in results.get('license_plates', []):
            bbox = p.get('bbox')
            if bbox and p.get('text'):
                x1, y1, x2, y2 = map(int, bbox)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), colors['plate'], 2)
                cv2.putText(annotated, p['text'], (x1, y2 + 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, colors['plate'], 2)

        return annotated

    def _save_annotated_image(self, image: np.ndarray, original_path: str) -> str:
        evidence_dir = Path('evidence')
        evidence_dir.mkdir(exist_ok=True)

        hash_str = hashlib.md5(original_path.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"enhanced_{timestamp}_{hash_str}.jpg"
        filepath = evidence_dir / filename

        cv2.imwrite(str(filepath), image)
        logger.info(f"Annotated image saved: {filepath}")
        return str(filepath)


def process_image(image_path, confidence_threshold=0.25, use_enhanced=True):
    pipeline = EnhancedDetectionPipeline(use_enhanced=use_enhanced)
    return pipeline.process_image(image_path, confidence_threshold)


if __name__ == "__main__":
    import argparse
    import os
    import sys
    parser = argparse.ArgumentParser(description='Enhanced Detection Pipeline')
    parser.add_argument('--image', type=str, required=True)
    parser.add_argument('--confidence', type=float, default=0.25)
    parser.add_argument('--json', action='store_true', default=True)
    args = parser.parse_args()

    if not os.path.exists(args.image):
        print(json.dumps({'error': f'Image not found: {args.image}'}))
        sys.exit(1)

    pipeline = EnhancedDetectionPipeline()
    try:
        result = pipeline.process_image(args.image, args.confidence)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({'error': str(e)}))
        sys.exit(1)
