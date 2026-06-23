import logging
import os
from datetime import datetime

import torch
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelTrainer:
    def __init__(self, device=None):
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")
        self._create_directories()

    def _create_directories(self):
        dirs = ['models', 'logs', 'runs', 'checkpoints']
        for d in dirs:
            os.makedirs(d, exist_ok=True)

    def train_traffic_model(self, data_path='data/traffic_dataset.yaml', epochs=100):
        logger.info("Training Traffic Violation Detection Model")
        model = YOLO('yolov8m.pt')
        results = model.train(
            data=data_path,
            epochs=epochs,
            imgsz=640,
            batch=16,
            device=self.device,
            workers=8,
            patience=20,
            save=True,
            project='runs/traffic',
            name=f'traffic_violation_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            exist_ok=True,
            augment=True,
            hsv_h=0.015, hsv_s=0.7, hsv_v=0.4,
            translate=0.1, scale=0.5,
            fliplr=0.5, mosaic=1.0,
        )
        logger.info("Traffic model training completed")
        return results

    def train_plate_model(self, data_path='data/plate_dataset.yaml', epochs=50):
        logger.info("Training License Plate Detection Model")
        model = YOLO('yolov8n.pt')
        results = model.train(
            data=data_path,
            epochs=epochs,
            imgsz=416,
            batch=32,
            device=self.device,
            workers=8,
            patience=10,
            save=True,
            project='runs/plate',
            name=f'license_plate_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            exist_ok=True,
            augment=True,
        )
        logger.info("Plate model training completed")
        return results

    def evaluate_model(self, model_path, data_path):
        logger.info("Evaluating model")
        model = YOLO(model_path)
        results = model.val(data=data_path, device=self.device, conf=0.001, iou=0.6)
        logger.info("Model evaluation completed")
        return results

    def convert_to_onnx(self, model_path):
        logger.info("Converting model to ONNX")
        model = YOLO(model_path)
        output_path = model_path.replace('.pt', '.onnx')
        model.export(format='onnx', imgsz=640, simplify=True, opset=12)
        logger.info(f"ONNX model saved to: {output_path}")
        return output_path


def main():
    configs = [
        {
            "name": "traffic_violation",
            "pretrained": "yolov8m.pt",
            "data": "config/traffic_dataset.yaml",
            "epochs": 100,
            "imgsz": 640,
            "batch": 16,
        },
        {
            "name": "license_plate",
            "pretrained": "yolov8n.pt",
            "data": "config/plate_dataset.yaml",
            "epochs": 50,
            "imgsz": 416,
            "batch": 32,
        },
    ]

    for cfg in configs:
        print(f"Training {cfg['name']}...")
        model = YOLO(cfg["pretrained"])
        model.train(
            data=cfg["data"],
            epochs=cfg["epochs"],
            imgsz=cfg["imgsz"],
            batch=cfg["batch"],
            project=f"runs/{cfg['name']}",
            name="train",
            device="cpu",
        )
        print(f"{cfg['name']} training complete.")


if __name__ == "__main__":
    main()
