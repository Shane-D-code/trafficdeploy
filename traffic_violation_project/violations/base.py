from datetime import datetime


class BaseViolationDetector:
    name = "base"

    def __init__(self, config=None):
        self.config = config if config is not None else {}

    def detect(self, image, detections):
        return []

    def create_violation(self, v_type, confidence, bbox, plate_text=None):
        return {
            "type": v_type,
            "confidence": confidence,
            "bbox": bbox,
            "plate_text": plate_text,
            "timestamp": datetime.now().isoformat(),
        }
