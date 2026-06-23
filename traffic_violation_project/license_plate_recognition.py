import logging
import os
import re
from pathlib import Path

import cv2
import easyocr
import numpy as np
import torch
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).parent.resolve()


class LicensePlateRecognizer:
    def __init__(self, plate_model_path=None, device="cpu"):
        if plate_model_path is None:
            plate_model_path = _BASE_DIR / "models" / "license_plate_best.pt"
        else:
            plate_model_path = Path(plate_model_path)
            if not plate_model_path.is_absolute():
                plate_model_path = _BASE_DIR / plate_model_path
        plate_model_path = str(plate_model_path)
        self.device = device
        if os.path.exists(plate_model_path):
            self.plate_model = YOLO(plate_model_path)
            if device == "cuda" and torch.cuda.is_available():
                self.plate_model.to("cuda")
                logger.info("Using GPU for plate detection")
            else:
                logger.info("Using CPU for plate detection")
        else:
            if plate_model_path is None:
                logger.warning("No plate model path provided - using fallback")
            else:
                logger.warning(f"Plate model not found at: {plate_model_path} - using fallback")
            self.plate_model = None

        self.reader = easyocr.Reader(["en"], gpu=(device == "cuda"))

        self.indian_plate_pattern = re.compile(
            r"^([A-Z]{2})[- ]?([0-9]{1,2})[- ]?([A-Z]{1,3})[- ]?([0-9]{1,4})$"
        )

        self.indian_states = {
            "AN",
            "AP",
            "AR",
            "AS",
            "BR",
            "CH",
            "CT",
            "DL",
            "DN",
            "GA",
            "GJ",
            "HR",
            "HP",
            "JH",
            "JK",
            "KA",
            "KL",
            "LD",
            "MH",
            "ML",
            "MN",
            "MP",
            "MZ",
            "NL",
            "OD",
            "PB",
            "PY",
            "RJ",
            "SK",
            "TN",
            "TR",
            "UP",
            "UK",
            "WB",
        }

        logger.info("LicensePlateRecognizer initialized")

    def extract_plate_text(self, image, vehicle_bbox, confidence_threshold=0.5):
        try:
            vehicle_crop = self._crop_vehicle_region(image, vehicle_bbox)
            if vehicle_crop is None:
                return None

            plate_crop = self._detect_plate_region(vehicle_crop)
            if plate_crop is None:
                return None

            preprocessed = self._preprocess_for_ocr(plate_crop)
            if preprocessed is None:
                return None

            text = self._run_ocr(preprocessed, confidence_threshold)
            if text is None:
                return None

            cleaned_text = self._clean_plate_text(text)

            if self.is_valid_plate(cleaned_text):
                logger.info(f"Valid plate: {cleaned_text}")
                return cleaned_text
            else:
                logger.debug(f"Invalid plate format: {cleaned_text}")
                return None

        except Exception as e:
            logger.error(f"Plate extraction error: {e}")
            return None

    def _crop_vehicle_region(self, image, vehicle_bbox):
        try:
            x1, y1, x2, y2 = map(int, vehicle_bbox)
            h, w = image.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 <= x1 or y2 <= y1:
                return None
            crop = image[y1:y2, x1:x2]
            return None if crop.size == 0 else crop
        except Exception as e:
            logger.error(f"Crop vehicle error: {e}")
            return None

    def _detect_plate_region(self, vehicle_crop):
        try:
            if self.plate_model is not None:
                results = self.plate_model(vehicle_crop, conf=0.25, verbose=False)
                if len(results) > 0 and len(results[0].boxes) > 0:
                    boxes = results[0].boxes
                    confs = boxes.conf.cpu().numpy()
                    best_idx = np.argmax(confs)
                    plate_box = boxes.xyxy[best_idx].cpu().numpy()
                    px1, py1, px2, py2 = map(int, plate_box)
                    h, w = vehicle_crop.shape[:2]
                    pad_x = int((px2 - px1) * 0.2)
                    pad_y = int((py2 - py1) * 0.2)
                    px1 = max(0, px1 - pad_x)
                    py1 = max(0, py1 - pad_y)
                    px2 = min(w, px2 + pad_x)
                    py2 = min(h, py2 + pad_y)
                    if px2 > px1 and py2 > py1:
                        return vehicle_crop[py1:py2, px1:px2]

            h, w = vehicle_crop.shape[:2]
            roi = vehicle_crop[int(h * 0.6):h]
            return roi if roi.size >= 100 else vehicle_crop

        except Exception as e:
            logger.error(f"Detect plate error: {e}")
            return vehicle_crop

    def _preprocess_for_ocr(self, plate_crop):
        try:
            if plate_crop is None or plate_crop.size == 0:
                return None

            img = plate_crop.copy()
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

            try:
                thresh1 = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
                )
                thresh2 = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2
                )
                thresh = cv2.addWeighted(thresh1, 0.5, thresh2, 0.5, 0)
            except Exception:
                _, thresh = cv2.threshold(
                    gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                )

            denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
            h, w = denoised.shape[:2]
            upscaled = cv2.resize(
                denoised, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC
            )

            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            sharpened = cv2.filter2D(upscaled, -1, kernel)

            morph_kernel = np.ones((2, 2), np.uint8)
            morph = cv2.morphologyEx(sharpened, cv2.MORPH_CLOSE, morph_kernel)

            variants = [denoised, upscaled, sharpened, morph]
            return max(variants, key=lambda x: np.std(x))

        except Exception as e:
            logger.error(f"Preprocess error: {e}")
            return plate_crop

    def _run_ocr(self, image, confidence_threshold=0.5):
        try:
            results = self.reader.readtext(image, detail=1, paragraph=False)
            if not results:
                return None

            valid = [(t, c) for _, t, c in results if c > confidence_threshold]
            if not valid:
                return None

            valid.sort(key=lambda x: x[1], reverse=True)
            best_text = valid[0][0]

            if len(valid) > 1:
                combined = "".join(t for t, c in valid if c > 0.5)
                return combined if len(combined) > len(best_text) else best_text

            return best_text

        except Exception as e:
            logger.error(f"OCR error: {e}")
            return None

    def _clean_plate_text(self, text):
        if not text:
            return ""
        cleaned = "".join(c for c in text if c.isalnum())
        return cleaned.upper()

    def is_valid_plate(self, plate_text):
        if not plate_text or len(plate_text) < 4:
            return False

        match = self.indian_plate_pattern.match(plate_text)
        if match:
            state_code = match.group(1)
            if state_code in self.indian_states:
                return True
            return True

        if 8 <= len(plate_text) <= 12:
            if plate_text[:2].isalpha():
                digits = sum(1 for c in plate_text if c.isdigit())
                letters = sum(1 for c in plate_text if c.isalpha())
                if digits >= 2 and letters >= 2:
                    return True

        patterns = [
            r"^[A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4}$",
            r"^[A-Z]{2}[0-9]{2}[A-Z][0-9]{4}$",
            r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{1,4}$",
        ]
        return any(re.match(p, plate_text) for p in patterns)

    def batch_extract_plates(self, image, vehicle_bboxes, confidence_threshold=0.5):
        return [
            self.extract_plate_text(image, bbox, confidence_threshold)
            for bbox in vehicle_bboxes
        ]


_recognizer = None


def get_recognizer():
    global _recognizer
    if _recognizer is None:
        possible_paths = [
            _BASE_DIR / "models" / "license_plate_best.pt",
            _BASE_DIR / "models" / "plate_best.pt",
            _BASE_DIR / "models" / "license_plate.pt",
            _BASE_DIR / "models" / "plate.pt",
        ]
        model_path = next((p for p in possible_paths if p.exists()), None)
        _recognizer = LicensePlateRecognizer(
            plate_model_path=str(model_path) if model_path else None
        )
    return _recognizer


def extract_plate_text(image, vehicle_bbox, confidence_threshold=0.5):
    return get_recognizer().extract_plate_text(
        image, vehicle_bbox, confidence_threshold
    )


def is_valid_plate(text):
    return get_recognizer().is_valid_plate(text)


if __name__ == "__main__":
    print("=" * 60)
    print("LICENSE PLATE RECOGNITION TEST")
    print("=" * 60)

    def create_test_image(plate_text, position=(160, 120)):
        img = np.ones((300, 500, 3), dtype=np.uint8) * 128
        cv2.rectangle(img, (50, 50), (450, 250), (200, 200, 200), -1)
        cv2.rectangle(img, (50, 50), (450, 250), (100, 100, 100), 2)
        x, y = position
        cv2.rectangle(img, (x, y), (x + 180, y + 40), (50, 50, 50), -1)
        cv2.rectangle(img, (x, y), (x + 180, y + 40), (255, 255, 255), 1)
        cv2.putText(
            img,
            plate_text,
            (x + 10, y + 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )
        return img

    test_cases = [
        ("KA01AB1234", "Standard Indian format"),
        ("DL02C5678", "Delhi format with single letter"),
        ("INVALID123", "Invalid format"),
    ]

    recognizer = LicensePlateRecognizer(plate_model_path=None)
    vehicle_bbox = [50, 50, 450, 250]

    print(f"\n{'Test':<8} {'Original':<16} {'Extracted':<16} {'Valid':<8} {'Match':<8}")
    print("-" * 60)
    for idx, (plate_text, desc) in enumerate(test_cases, 1):
        img = create_test_image(plate_text)
        extracted = recognizer.extract_plate_text(img, vehicle_bbox)
        valid = recognizer.is_valid_plate(extracted) if extracted else False
        match = (extracted == plate_text) if extracted else False
        print(
            f"{idx:<8} {plate_text:<16} {str(extracted):<16} {str(valid):<8} {str(match):<8}"
        )

    print("\n" + "=" * 60)
