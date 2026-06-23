"""
traffic_sign_analyzer.py - Analyze traffic signs for violation detection
Uses StreetSignSense model detecting 63 classes of traffic signs
Real-time inference: 5.4ms, 185 FPS on modern GPUs
"""

from ultralytics import YOLO
from huggingface_hub import hf_hub_download
import logging

logger = logging.getLogger(__name__)


class TrafficSignAnalyzer:
    """
    Analyze traffic signs using StreetSignSense model
    Detects 63 classes of traffic signs in real-time (5.4ms, 185 FPS)
    """

    def __init__(self, model_path=None):
        if model_path:
            self.model = YOLO(model_path)
        else:
            model_path = hf_hub_download(
                repo_id="AlessandroFerrante/StreetSignSenseY12n",
                filename="streetsignsense-yolo12n.pt"
            )
            self.model = YOLO(model_path)

        self.sign_categories = {
            'speed_limit': ['speed', 'limit', 'km/h'],
            'warning': ['warning', 'caution', 'danger'],
            'prohibition': ['no', 'prohibited', 'restricted'],
            'mandatory': ['must', 'required', 'compulsory'],
            'information': ['info', 'guide', 'direction', 'parking'],
            'construction': ['work', 'construction', 'roadwork'],
            'traffic_light': ['traffic', 'signal', 'light'],
        }

    def detect_signs(self, image):
        """
        Detect and classify traffic signs

        Args:
            image: Path to image or numpy array

        Returns:
            List of dicts with 'class', 'bbox', 'confidence', 'category'
        """
        results = self.model(image, conf=0.3)
        signs = []

        for r in results:
            if r.boxes:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    class_name = self.model.names[cls]
                    signs.append({
                        'class': class_name,
                        'bbox': box.xyxy[0].tolist(),
                        'confidence': float(box.conf[0]),
                        'category': self.get_sign_category(class_name),
                    })

        return signs

    def get_sign_category(self, sign_class):
        """Categorize the sign based on class name"""
        for category, keywords in self.sign_categories.items():
            if any(kw in sign_class.lower() for kw in keywords):
                return category
        return 'other'

    def has_speed_limit(self, signs, limit_kmh=None):
        """Check if a specific speed limit sign is present"""
        for sign in signs:
            sclass = sign['class'].lower()
            if 'speed' in sclass or 'limit' in sclass:
                if limit_kmh is None:
                    return True
                try:
                    num = int(''.join(c for c in sclass if c.isdigit()))
                    return num == limit_kmh
                except ValueError:
                    return True
        return False

    def has_prohibition(self, signs, prohibited_action=None):
        """Check if a prohibition sign is present"""
        for sign in signs:
            sclass = sign['class'].lower()
            if 'no' in sclass or 'prohibited' in sclass:
                if prohibited_action is None:
                    return True
                if prohibited_action.lower() in sclass:
                    return True
        return False
