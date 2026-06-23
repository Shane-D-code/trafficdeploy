"""
vehicle_classifier.py - Enhanced Vehicle Classification
"""

import cv2
import numpy as np
from ultralytics import YOLO
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class VehicleClassifier:
    """
    Enhanced vehicle classification with 10+ classes
    """

    def __init__(self, model_path=None):
        if model_path is None:
            model_path = str(Path(__file__).parent / "models" / "traffic_violation_best.pt")
        self.model = YOLO(model_path) if model_path and Path(model_path).exists() else None
        self.classes = [
            'car', 'suv', 'mini_truck', 'bus', 'truck',
            'taxi', 'auto_rickshaw', 'motorcycle', 'bicycle',
            'emergency_vehicle', 'electric_vehicle'
        ]

    def classify_vehicle(self, vehicle_crop):
        """
        Classify vehicle from crop
        """
        if self.model is None:
            return 'unknown', 0.0

        results = self.model(vehicle_crop, conf=0.5, verbose=False)

        if len(results) > 0 and len(results[0].boxes) > 0:
            box = results[0].boxes[0]
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            class_name = self.model.names.get(cls, 'unknown')
            return class_name, conf

        return 'unknown', 0.0

    def get_vehicle_details(self, vehicle_crop):
        """
        Get comprehensive vehicle details
        """
        class_name, conf = self.classify_vehicle(vehicle_crop)

        return {
            'type': class_name,
            'confidence': conf,
            'category': self._get_category(class_name),
            'color': self._get_color(vehicle_crop),
            'size': self._get_size(vehicle_crop)
        }

    def _get_category(self, class_name):
        """Map class to category"""
        categories = {
            'car': '4_wheeler',
            'suv': '4_wheeler',
            'taxi': '4_wheeler',
            'mini_truck': 'commercial',
            'bus': 'commercial',
            'truck': 'commercial',
            'auto_rickshaw': '3_wheeler',
            'motorcycle': '2_wheeler',
            'bicycle': '2_wheeler',
            'emergency_vehicle': 'emergency',
            'electric_vehicle': 'electric_vehicle'
        }
        return categories.get(class_name.lower(), 'unknown')

    def _get_color(self, crop):
        """Estimate vehicle color from HSV histogram"""
        try:
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)

            mask = v > 40
            h_vals = h[mask]

            if len(h_vals) == 0:
                return 'unknown'

            dominant_hue = np.median(h_vals)

            if dominant_hue < 10 or dominant_hue > 170:
                return 'red'
            elif dominant_hue < 25:
                return 'orange'
            elif dominant_hue < 35:
                return 'yellow'
            elif dominant_hue < 85:
                return 'green'
            elif dominant_hue < 130:
                return 'blue'
            elif dominant_hue < 160:
                return 'purple'
            else:
                return 'red'
        except Exception:
            return 'unknown'

    def _get_size(self, crop):
        """Get vehicle size category from crop dimensions"""
        h, w = crop.shape[:2]
        area = h * w
        if area < 10000:
            return 'small'
        elif area < 30000:
            return 'medium'
        return 'large'
