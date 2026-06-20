from .base import BaseViolationDetector


class StopLineDetector(BaseViolationDetector):
    name = "STOP LINE"

    def detect(self, image, detections):
        violations = []
        # Rule: detect vehicles crossing stop line
        # Future integration: use segmentation model for stop line + vehicle tracking
        # Placeholder: requires stop line segmentation model
        return violations
