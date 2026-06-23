import logging

import cv2
import numpy as np

from .base import BaseViolationDetector

logger = logging.getLogger(__name__)


class RedLightDetector(BaseViolationDetector):
    name = "RED LIGHT"

    def __init__(self, config=None):
        super().__init__(config)
        self.red_light_confidence = self.config.get('red_light_confidence', 0.7)

    def detect(self, image, detections):
        violations = []
        try:
            self._current_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            traffic_lights = self._detect_traffic_lights(image)
            if not traffic_lights:
                return violations

            red_lights = self._get_red_lights(traffic_lights)
            if not red_lights:
                return violations

            for red_light in red_lights:
                for det in detections:
                    det_class = det.get("class_name", "")
                    if det_class in ("vehicle", "car", "truck", "bus", "motorcycle"):
                        is_violating = self._check_red_light_violation(
                            det.get("box", det.get("bbox")), red_light, image
                        )
                        if is_violating:
                            violation = self.create_violation(
                                self.name,
                                det["confidence"] * 0.9,
                                det.get("box", det.get("bbox"))
                            )
                            violations.append(violation)
            return violations
        except Exception as e:
            logger.error(f"Red light detection error: {e}")
            return violations

    def _detect_traffic_lights(self, image):
        try:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            lower_red1 = np.array([0, 70, 50])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([170, 70, 50])
            upper_red2 = np.array([180, 255, 255])
            mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            red_mask = cv2.bitwise_or(mask1, mask2)

            lower_green = np.array([40, 70, 50])
            upper_green = np.array([90, 255, 255])
            green_mask = cv2.inRange(hsv, lower_green, upper_green)

            lower_yellow = np.array([15, 70, 50])
            upper_yellow = np.array([35, 255, 255])
            yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

            combined = cv2.bitwise_or(cv2.bitwise_or(red_mask, green_mask), yellow_mask)
            contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            lights = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if 50 < area < 5000:
                    x, y, w, h = cv2.boundingRect(contour)
                    if 0.3 < w / h < 3.0:
                        roi = combined[y:y+h, x:x+w]
                        red_pixels = cv2.countNonZero(cv2.bitwise_and(roi, cv2.bitwise_or(red_mask[y:y+h, x:x+w], cv2.bitwise_or(green_mask[y:y+h, x:x+w], yellow_mask[y:y+h, x:x+w]))))
                        lights.append({'bbox': [x, y, x+w, y+h], 'area': area})
            return lights
        except Exception as e:
            logger.error(f"Traffic light detection error: {e}")
            return []

    def _get_red_lights(self, traffic_lights):
        red_lights = []
        try:
            for tl in traffic_lights:
                bbox = tl.get("bbox", tl.get("box", []))
                if len(bbox) < 4:
                    continue
                x, y, w = bbox[0], bbox[1], bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                if w < 5 or h < 5:
                    continue
                roi = self._current_hsv[y:y+h, x:x+w] if hasattr(self, '_current_hsv') else None
                if roi is None or roi.size == 0:
                    red_lights.append(bbox)
                    continue
                lower_red1 = np.array([0, 70, 50])
                upper_red1 = np.array([10, 255, 255])
                lower_red2 = np.array([170, 70, 50])
                upper_red2 = np.array([180, 255, 255])
                mask1 = cv2.inRange(roi, lower_red1, upper_red1)
                mask2 = cv2.inRange(roi, lower_red2, upper_red2)
                red_mask = cv2.bitwise_or(mask1, mask2)
                red_pixels = cv2.countNonZero(red_mask)
                lower_green = np.array([40, 70, 50])
                upper_green = np.array([90, 255, 255])
                green_pixels = cv2.countNonZero(cv2.inRange(roi, lower_green, upper_green))
                total = red_pixels + green_pixels + 1
                if red_pixels / total > 0.4 and red_pixels > green_pixels:
                    red_lights.append(bbox)
            return red_lights
        except Exception as e:
            logger.error(f"Red light filtering error: {e}")
            return traffic_lights

    def _check_red_light_violation(self, vehicle_box, red_light, image):
        if not vehicle_box or len(vehicle_box) < 4:
            return False
        try:
            vx1, vy1, vx2, vy2 = vehicle_box[:4]
            sx1, sy1, sx2, sy2 = red_light[:4]
            signal_center_x = (sx1 + sx2) // 2
            vehicle_center_x = (vx1 + vx2) // 2
            is_below_signal = vy1 > sy2
            horizontal_distance = abs(vehicle_center_x - signal_center_x)
            signal_height = sy2 - sy1
            is_near_horizontally = horizontal_distance < max(signal_height * 3, 200)
            return is_below_signal and is_near_horizontally
        except Exception as e:
            logger.error(f"Red light violation check error: {e}")
            return False
