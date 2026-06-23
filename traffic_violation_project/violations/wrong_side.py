import logging

import cv2
import numpy as np

from .base import BaseViolationDetector

logger = logging.getLogger(__name__)


class WrongSideDetector(BaseViolationDetector):
    name = "WRONG SIDE"

    def __init__(self, config=None):
        super().__init__(config)
        self.lane_confidence_threshold = self.config.get('lane_confidence', 0.5)
        self.direction_threshold = self.config.get('direction_threshold', 0.3)

    def detect(self, image, detections):
        violations = []
        try:
            lanes = self._detect_lanes(image)
            if not lanes:
                return violations

            direction = self._get_traffic_direction(lanes)

            for det in detections:
                det_class = det.get("class_name", "")
                if det_class in ("vehicle", "car", "truck", "bus", "motorcycle"):
                    is_wrong = self._check_vehicle_direction(det.get("box", det.get("bbox")), lanes, direction)
                    if is_wrong:
                        violation = self.create_violation(
                            self.name,
                            det["confidence"] * 0.9,
                            det.get("box", det.get("bbox"))
                        )
                        violations.append(violation)
            return violations
        except Exception as e:
            logger.error(f"Wrong-side detection error: {e}")
            return violations

    def _detect_lanes(self, image):
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi/180, threshold=50, minLineLength=100, maxLineGap=50)
            if lines is None:
                return []
            filtered = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                if 20 < abs(angle) < 80:
                    filtered.append(line[0])
            return filtered
        except Exception as e:
            logger.error(f"Lane detection error: {e}")
            return []

    def _get_traffic_direction(self, lanes):
        if not lanes:
            return None
        angles = []
        for lane in lanes:
            x1, y1, x2, y2 = lane
            angle = np.arctan2(y2 - y1, x2 - x1)
            angles.append(angle)
        return np.mean(angles)

    def _check_vehicle_direction(self, vehicle_box, lanes, direction):
        if not vehicle_box or len(vehicle_box) < 4:
            return False
        try:
            vx1, vy1, vx2, vy2 = vehicle_box[:4]
            center_x = (vx1 + vx2) // 2
            center_y = (vy1 + vy2) // 2
            vehicle_lane = None
            for lane in lanes:
                if len(lane) < 4:
                    continue
                lane_center_x = (lane[0] + lane[2]) // 2
                if abs(center_x - lane_center_x) < 150:
                    vehicle_lane = lane
                    break
            if vehicle_lane is None:
                return False
            if direction is not None:
                lane_angle = np.arctan2(
                    vehicle_lane[3] - vehicle_lane[1],
                    vehicle_lane[2] - vehicle_lane[0]
                )
                vehicle_angle = np.arctan2(vy2 - vy1, vx2 - vx1)
                angle_diff = abs(vehicle_angle - lane_angle)
                if angle_diff > np.pi / 2:
                    return True
            return False
        except Exception as e:
            logger.error(f"Wrong side check error: {e}")
            return False
