"""
model_registry.py - Production-Ready Model Registry
Handles: VehicleNet UVH-26, StreetSignSense, EULPR with proper error handling
"""

import os
import torch
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Tuple
import logging
from ultralytics import YOLO
from huggingface_hub import hf_hub_download, snapshot_download, HfApi
import easyocr

logger = logging.getLogger(__name__)


class GridlockModelRegistry:
    """
    Production model registry with retry, fallback, and status tracking
    """

    def __init__(self, model_dir=None, use_gpu=True):
        if model_dir is None:
            model_dir = os.path.join(os.path.dirname(__file__), 'models')
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        self.device = 'cuda' if use_gpu and torch.cuda.is_available() else 'cpu'
        self.models = {}
        self.load_status = {}
        self.api = HfApi()

        logger.info(f"Model registry initialized on {self.device}")

    def _verify_file_size(self, path):
        return os.path.getsize(path) > 1000

    def _download_with_retry(self, repo_id, filename, max_retries=3):
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt+1}/{max_retries}: {repo_id}/{filename}")

                model_path = hf_hub_download(
                    repo_id=repo_id,
                    filename=filename,
                    cache_dir=str(self.model_dir / 'hub_cache'),
                    resume_download=True,
                    force_download=(attempt > 0),
                    local_files_only=(attempt == 0)
                )

                if self._verify_file_size(model_path):
                    size_kb = os.path.getsize(model_path) / 1024
                    logger.info(f"Downloaded {size_kb:.1f} KB")
                    return model_path

                logger.warning(f"File size {os.path.getsize(model_path)} bytes - retrying...")
                time.sleep(2 ** attempt)
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed: {e}")
                time.sleep(2 ** attempt)
        return None

    def load_vehicle_net(self, variant='nano'):
        logger.info("Loading VehicleNet UVH-26 (14 Indian vehicle classes)...")

        repo_map = {
            'nano': ('Perception365/VehicleNet-RFDETR-n', 'model.pt'),
            'medium': ('Perception365/VehicleNet-Y26m', 'model.pt')
        }
        repo_id, filename = repo_map.get(variant, repo_map['nano'])

        model_path = self._download_with_retry(repo_id, filename)

        if model_path:
            try:
                self.models['vehicle'] = YOLO(model_path)
                self.load_status['vehicle'] = 'success'
                logger.info("VehicleNet UVH-26 loaded successfully")
                return self.models['vehicle']
            except Exception as e:
                logger.error(f"Failed to load VehicleNet: {e}")

        logger.warning("VehicleNet load failed, falling back to traffic_violation_best.pt")
        fallback_path = self.model_dir / 'traffic_violation_best.pt'
        if fallback_path.exists():
            logger.warning("Using fallback traffic_violation_best.pt")
            self.models['vehicle'] = YOLO(str(fallback_path))
            self.load_status['vehicle'] = 'fallback'
            return self.models['vehicle']

        self.load_status['vehicle'] = 'failed'
        return None

    def load_street_sign_sense(self):
        logger.info("Loading StreetSignSense (63 traffic signs)...")

        model_path = self._download_with_retry(
            "AlessandroFerrante/StreetSignSenseY12n",
            "streetsignsense-yolo12n.pt"
        )

        if model_path:
            try:
                self.models['traffic_sign'] = YOLO(model_path)
                self.load_status['traffic_sign'] = 'success'
                logger.info("StreetSignSense loaded successfully")
                return self.models['traffic_sign']
            except Exception as e:
                logger.error(f"Failed to load StreetSignSense: {e}")

        self.load_status['traffic_sign'] = 'failed'
        return None

    def load_license_plate_eulpr(self):
        logger.info("Loading EULPR plate detection...")

        model_path = self._download_with_retry(
            "0xnu/european-license-plate-recognition",
            "model.onnx"
        )

        if model_path:
            try:
                self.models['plate_detector'] = YOLO(model_path, task='detect')
                self.models['plate_ocr'] = easyocr.Reader(
                    ['en', 'de', 'fr', 'es', 'it', 'nl'],
                    gpu=torch.cuda.is_available(),
                    verbose=False
                )
                self.load_status['plate'] = 'success'
                logger.info("EULPR loaded successfully")
                return self.models['plate_detector'], self.models['plate_ocr']
            except Exception as e:
                logger.error(f"Failed to load EULPR: {e}")

        logger.warning("EULPR load failed, using fallback plate model")
        fallback_path = self.model_dir / 'license_plate_best.pt'
        if fallback_path.exists():
            logger.warning("Using fallback license_plate_best.pt")
            self.models['plate_detector'] = YOLO(str(fallback_path))
            self.models['plate_ocr'] = easyocr.Reader(['en'], gpu=torch.cuda.is_available(), verbose=False)
            self.load_status['plate'] = 'fallback'
            return self.models['plate_detector'], self.models['plate_ocr']

        self.load_status['plate'] = 'failed'
        return None, None

    def load_all(self, use_enhanced=True):
        logger.info("=" * 60)
        logger.info("Loading all models...")
        logger.info("=" * 60)

        if use_enhanced:
            self.load_vehicle_net('nano')
            self.load_street_sign_sense()
            plate_detector, plate_ocr = self.load_license_plate_eulpr()
            if plate_detector and plate_ocr:
                self.models['plate_detector'] = plate_detector
                self.models['plate_ocr'] = plate_ocr

        if 'vehicle' not in self.models or self.load_status.get('vehicle') == 'failed':
            fallback_path = self.model_dir / 'traffic_violation_best.pt'
            if fallback_path.exists():
                self.models['vehicle'] = YOLO(str(fallback_path))
                self.load_status['vehicle'] = 'fallback'
                logger.info("Using fallback traffic model")

        logger.info("=" * 60)
        logger.info("Model Load Summary:")

        model_names = {
            'vehicle': 'VehicleNet UVH-26 (14 classes)',
            'traffic_sign': 'StreetSignSense (63 signs)',
            'plate': 'EULPR plates'
        }
        for key, name in model_names.items():
            status = self.load_status.get(key, 'not_loaded')
            icon = "OK" if status in ['success', 'fallback'] else "FAIL"
            logger.info("  %s %s: %s", icon, name, status)

        logger.info("=" * 60)
        return self.models

    def get_model_status(self):
        return {
            'status': self.load_status,
            'device': self.device,
            'loaded': len(self.models),
            'models': list(self.models.keys())
        }
