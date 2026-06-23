"""
vehicle_classifier.py - Enhanced vehicle classification using UVH-26 models
Fine-tuned on IISc Bangalore's UVH-26-MV dataset with 14 India-specific classes
"""

from ultralytics import YOLO
from huggingface_hub import hf_hub_download
import logging

logger = logging.getLogger(__name__)


class VehicleClassifier:
    """
    Fine-grained vehicle classification using IISc UVH-26 models
    Trained on 14 India-specific vehicle classes

    Variants:
      - 'nano': RFDETRNano, 30.5M params, mAP@50: 0.667
      - 'm': YOLO26m, 20.36M params, mAP@50: 0.749
    """

    def __init__(self, variant='nano'):
        if variant == 'nano':
            repo_id = "Perception365/VehicleNet-RFDETR-n"
        else:
            repo_id = "Perception365/VehicleNet-Y26m"

        model_path = hf_hub_download(
            repo_id=repo_id,
            filename="model.pt"
        )

        self.model = YOLO(model_path)

        self.classes = [
            'cycle', '2-wheeler', '3-wheeler', 'LCV', 'van',
            'tempo-traveller', 'hatchback', 'sedan', 'SUV', 'MUV',
            'mini-bus', 'bus', 'truck', 'other'
        ]

        self.categories = {
            '2-wheeler': {'type': 'two_wheeler', 'requires_helmet': True},
            'cycle': {'type': 'two_wheeler', 'requires_helmet': False},
            '3-wheeler': {'type': 'three_wheeler', 'requires_helmet': False},
            'LCV': {'type': 'commercial', 'requires_helmet': False},
            'van': {'type': 'commercial', 'requires_helmet': False},
            'tempo-traveller': {'type': 'commercial', 'requires_helmet': False},
            'hatchback': {'type': 'car', 'requires_helmet': False},
            'sedan': {'type': 'car', 'requires_helmet': False},
            'SUV': {'type': 'car', 'requires_helmet': False},
            'MUV': {'type': 'car', 'requires_helmet': False},
            'mini-bus': {'type': 'bus', 'requires_helmet': False},
            'bus': {'type': 'bus', 'requires_helmet': False},
            'truck': {'type': 'truck', 'requires_helmet': False},
            'other': {'type': 'other', 'requires_helmet': False},
        }

    def classify(self, image):
        """
        Classify vehicles in image

        Args:
            image: Path to image or numpy array

        Returns:
            List of dicts with 'class', 'category', 'requires_helmet',
            'bbox', and 'confidence' for each detected vehicle
        """
        results = self.model(image, conf=0.3)
        vehicles = []

        for r in results:
            if r.boxes:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    class_name = self.classes[cls]
                    cat_info = self.categories.get(class_name, {})
                    vehicle = {
                        'class': class_name,
                        'category': cat_info.get('type', 'other'),
                        'requires_helmet': cat_info.get('requires_helmet', False),
                        'bbox': box.xyxy[0].tolist(),
                        'confidence': float(box.conf[0]),
                    }
                    vehicles.append(vehicle)

        return vehicles
