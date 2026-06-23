import logging

import cv2
import numpy as np

from .base import BaseViolationDetector

logger = logging.getLogger(__name__)


class StopLineDetector(BaseViolationDetector):
    name = "STOP LINE"

    def __init__(self, config=None):
        super().__init__(config)
        self.stop_line_threshold = self.config.get('stop_line_threshold', 0.5)

    def detect(self, image, detections):
        violations = []
        try:
            stop_lines = self._detect_stop_lines(image)
            if not stop_lines:
                return violations

            for det in detections:
                det_class = det.get("class_name", "")
                if det_class in ("vehicle", "car", "truck", "bus", "motorcycle"):
                    crossed = self._check_stop_line_crossing(det.get("box", det.get("bbox")), stop_lines)
                    if crossed:
                        violation = self.create_violation(
                            self.name,
                            det["confidence"] * 0.85,
                            det.get("box", det.get("bbox"))
                        )
                        violations.append(violation)
            return violations
        except Exception as e:
            logger.error(f"Stop line detection error: {e}")
            return violations

    def _detect_stop_lines(self, image):
        try:
            h, w = image.shape[:2]
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blur, 150, 300)
            min_len = int(w * 0.25)
            lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi/180, threshold=100, minLineLength=min_len, maxLineGap=20)
            if lines is None:
                return []
            stop_lines = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                if abs(angle) < 10 or abs(abs(angle) - 180) < 10:
                    line_len = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                    if line_len < w * 0.3:
                        continue
                    if abs(y1 - h * 0.7) < h * 0.1:
                        stop_lines.append(line[0])
            return stop_lines
        except Exception as e:
            logger.error(f"Stop line detection error: {e}")
            return []

    def _check_stop_line_crossing(self, vehicle_box, stop_lines):
        if not vehicle_box or len(vehicle_box) < 4:
            return False
        try:
            vx1, vy1, vx2, vy2 = vehicle_box[:4]
            for line in stop_lines:
                if len(line) < 4:
                    continue
                lx1, ly1, lx2, ly2 = line[:4]
                line_y = (ly1 + ly2) // 2
                if vy1 < line_y < vy2:
                    return True
            return False
        except Exception as e:
            logger.error(f"Stop line crossing check error: {e}")
            return False
