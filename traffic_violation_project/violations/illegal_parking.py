from .base import BaseViolationDetector


class IllegalParkingDetector(BaseViolationDetector):
    name = "ILLEGAL PARKING"

    def detect(self, image, detections):
        violations = []
        # Rule: detect vehicles parked in no-parking zones
        # Future integration: parking zone segmentation + stationary vehicle detection
        # Placeholder: requires no-parking zone model
        return violations
