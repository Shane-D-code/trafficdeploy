import logging

import cv2
import numpy as np

from .base import BaseViolationDetector

logger = logging.getLogger(__name__)


class IllegalParkingDetector(BaseViolationDetector):
    name = "ILLEGAL PARKING"

    def __init__(self, config=None):
        super().__init__(config)
        self.parking_zone_threshold = self.config.get('parking_zone_threshold', 0.5)

    def detect(self, image, detections):
        violations = []
        try:
            no_parking_zones = self._detect_no_parking_zones(image)
            if not no_parking_zones:
                return violations

            for zone in no_parking_zones:
                for det in detections:
                    det_class = det.get("class_name", "")
                    if det_class in ("vehicle", "car", "truck", "bus", "motorcycle"):
                        is_parked = self._check_parked_vehicle(
                            det.get("box", det.get("bbox")), zone, image
                        )
                        if is_parked:
                            violation = self.create_violation(
                                self.name,
                                det["confidence"] * 0.8,
                                det.get("box", det.get("bbox"))
                            )
                            violations.append(violation)
            return violations
        except Exception as e:
            logger.error(f"Illegal parking detection error: {e}")
            return violations

    def _detect_no_parking_zones(self, image):
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            zones = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 1000:
                    x, y, w, h = cv2.boundingRect(contour)
                    zones.append([x, y, x+w, y+h])
            return zones
        except Exception as e:
            logger.error(f"No-parking zone detection error: {e}")
            return []

    def _check_parked_vehicle(self, vehicle_box, zone, image):
        if not vehicle_box or len(vehicle_box) < 4:
            return False
        try:
            vx1, vy1, vx2, vy2 = vehicle_box[:4]
            zx1, zy1, zx2, zy2 = zone[:4]
            overlap_x1 = max(vx1, zx1)
            overlap_y1 = max(vy1, zy1)
            overlap_x2 = min(vx2, zx2)
            overlap_y2 = min(vy2, zy2)
            if overlap_x2 > overlap_x1 and overlap_y2 > overlap_y1:
                overlap_area = (overlap_x2 - overlap_x1) * (overlap_y2 - overlap_y1)
                vehicle_area = (vx2 - vx1) * (vy2 - vy1)
                overlap_ratio = overlap_area / vehicle_area if vehicle_area > 0 else 0
                return overlap_ratio > self.parking_zone_threshold
            return False
        except Exception as e:
            logger.error(f"Parking check error: {e}")
            return False
