from .base import BaseViolationDetector


class WrongSideDetector(BaseViolationDetector):
    name = "WRONG SIDE"

    def detect(self, image, detections):
        violations = []
        # Rule: detect vehicles moving in wrong direction
        # Future integration: use lane line detection + vehicle trajectory
        # Placeholder: requires video sequence or lane orientation model
        return violations
