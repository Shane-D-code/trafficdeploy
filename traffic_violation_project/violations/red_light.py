from .base import BaseViolationDetector


class RedLightDetector(BaseViolationDetector):
    name = "RED LIGHT"

    def detect(self, image, detections):
        violations = []
        # Rule: detect vehicles crossing during red signal
        # Future integration: traffic light color detection + vehicle tracking
        # Placeholder: requires traffic light detection + tracking
        return violations
