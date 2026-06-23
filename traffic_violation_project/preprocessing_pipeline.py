"""
preprocessing_pipeline.py - Advanced Image Preprocessing

Implements:
- Histogram Equalization (CLAHE)
- Motion Blur Reduction
- Shadow Removal
- Rain Reduction
- Night Enhancement
- Gamma Correction
- AdvancedImagePreprocessor with Hugging Face transformer support
"""

import cv2
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from transformers import pipeline as hf_pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False


class ImagePreprocessor:
    """
    Advanced image preprocessing pipeline for traffic images
    """

    def __init__(self, config=None):
        self.config = config or {}
        self.clip_limit = self.config.get('clahe_clip', 2.0)
        self.tile_grid = self.config.get('tile_grid', (8, 8))
        self.gamma = self.config.get('gamma', 1.2)
        self.denoise_strength = self.config.get('denoise_strength', 10)

    def preprocess(self, image: np.ndarray, conditions: dict = None) -> np.ndarray:
        """
        Full preprocessing pipeline

        Args:
            image: Input image (BGR)
            conditions: Dict with keys 'low_light', 'rain', 'shadow', 'motion_blur'

        Returns:
            Preprocessed image
        """
        if conditions is None:
            conditions = {}

        result = image.copy()

        # 1. Denoise
        result = self.reduce_noise(result)

        # 2. CLAHE (Low light enhancement)
        if conditions.get('low_light', True):
            result = self.enhance_low_light(result)

        # 3. Gamma correction
        if conditions.get('dark', False):
            result = self.apply_gamma(result)

        # 4. Shadow removal
        if conditions.get('shadow', False):
            result = self.remove_shadows(result)

        # 5. Motion blur reduction
        if conditions.get('motion_blur', False):
            result = self.reduce_motion_blur(result)

        # 6. Rain reduction
        if conditions.get('rain', False):
            result = self.reduce_rain(result)

        # 7. Sharpen
        result = self.sharpen(result)

        return result

    def enhance_low_light(self, image: np.ndarray) -> np.ndarray:
        """
        Apply CLAHE for low light enhancement
        """
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        clahe = cv2.createCLAHE(
            clipLimit=self.clip_limit,
            tileGridSize=self.tile_grid
        )
        l_enhanced = clahe.apply(l)

        lab_enhanced = cv2.merge((l_enhanced, a, b))
        return cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

    def reduce_noise(self, image: np.ndarray) -> np.ndarray:
        """
        Apply fast non-local means denoising
        """
        return cv2.fastNlMeansDenoisingColored(
            image, None,
            h=self.denoise_strength,
            hColor=self.denoise_strength,
            templateWindowSize=7,
            searchWindowSize=21
        )

    def apply_gamma(self, image: np.ndarray, gamma: float = None) -> np.ndarray:
        """
        Apply gamma correction
        """
        if gamma is None:
            gamma = self.gamma

        inv_gamma = 1.0 / gamma
        table = np.array([
            ((i / 255.0) ** inv_gamma) * 255
            for i in np.arange(0, 256)
        ]).astype("uint8")

        return cv2.LUT(image, table)

    def remove_shadows(self, image: np.ndarray) -> np.ndarray:
        """
        Remove shadows using morphology and inpainting
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        _, shadow_mask = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)

        kernel = np.ones((5, 5), np.uint8)
        shadow_mask = cv2.dilate(shadow_mask, kernel, iterations=2)

        result = cv2.inpaint(image, shadow_mask, 3, cv2.INPAINT_TELEA)

        return result

    def reduce_motion_blur(self, image: np.ndarray) -> np.ndarray:
        """
        Reduce motion blur using deconvolution
        """
        kernel_size = 5
        kernel = np.zeros((kernel_size, kernel_size))
        kernel[int((kernel_size - 1) / 2), :] = np.ones(kernel_size)
        kernel = kernel / kernel_size

        restored = cv2.filter2D(image, -1, kernel)

        return restored

    def reduce_rain(self, image: np.ndarray) -> np.ndarray:
        """
        Reduce rain streaks using median filtering
        """
        filtered = cv2.medianBlur(image, 3)

        alpha = 0.7
        return cv2.addWeighted(filtered, alpha, image, 1 - alpha, 0)

    def sharpen(self, image: np.ndarray) -> np.ndarray:
        """
        Apply sharpening kernel
        """
        kernel = np.array([
            [-1, -1, -1],
            [-1, 9, -1],
            [-1, -1, -1]
        ])
        return cv2.filter2D(image, -1, kernel)

    def analyze_conditions(self, image: np.ndarray) -> dict:
        """
        Auto-detect image conditions
        """
        conditions = {}

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Detect low light
        brightness = np.mean(gray)
        conditions['low_light'] = brightness < 100

        # Detect dark
        conditions['dark'] = brightness < 60

        # Detect shadows
        _, shadow_mask = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)
        shadow_ratio = np.sum(shadow_mask == 0) / gray.size
        conditions['shadow'] = shadow_ratio > 0.2

        # Detect motion blur
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        conditions['motion_blur'] = laplacian_var < 100

        # Detect rain/noise (simplified)
        median_var = cv2.medianBlur(gray, 3).var()
        conditions['rain'] = abs(median_var - gray.var()) > 50

        return conditions


class AdvancedImagePreprocessor:
    """
    Enhanced preprocessor with Hugging Face transformer support
    Falls back to OpenCV methods if transformers unavailable
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.base_preprocessor = ImagePreprocessor(config)
        self._init_hf_models()

    def _init_hf_models(self):
        self.depth_estimator = None
        self.image_enhancer = None
        if HAS_TRANSFORMERS:
            try:
                self.depth_estimator = hf_pipeline(
                    'depth-estimation',
                    model='Intel/dpt-hybrid-midas',
                    device=-1
                )
                logger.info("Hugging Face depth estimation model loaded")
            except Exception as e:
                logger.warning(f"Could not load depth model: {e}")
            try:
                self.image_enhancer = hf_pipeline(
                    'image-to-image',
                    model='keras-io/upernet-swin-model',
                    device=-1
                )
                logger.info("Hugging Face image enhancement model loaded")
            except Exception as e:
                logger.warning(f"Could not load enhancement model: {e}")
        else:
            logger.info("transformers not available, using OpenCV-only preprocessing")

    def preprocess(self, image: np.ndarray, conditions: Optional[Dict] = None) -> np.ndarray:
        if conditions is None:
            conditions = {}
        result = self.base_preprocessor.preprocess(image, conditions)
        if HAS_TRANSFORMERS and conditions.get('low_light', False):
            result = self._enhance_with_hf(result)
        return result

    def _enhance_with_hf(self, image: np.ndarray) -> np.ndarray:
        if self.image_enhancer is None:
            return image
        try:
            from PIL import Image as PILImage
            pil_img = PILImage.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            enhanced = self.image_enhancer(pil_img)
            if isinstance(enhanced, dict) and 'image' in enhanced:
                result = np.array(enhanced['image'])
                return cv2.cvtColor(result, cv2.COLOR_RGB2BGR)
            return image
        except Exception as e:
            logger.warning(f"HF enhancement failed: {e}")
            return image

    def estimate_depth(self, image: np.ndarray) -> Optional[np.ndarray]:
        if self.depth_estimator is None:
            return None
        try:
            from PIL import Image as PILImage
            pil_img = PILImage.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            depth = self.depth_estimator(pil_img)
            if isinstance(depth, dict) and 'depth' in depth:
                depth_np = np.array(depth['depth'])
                return depth_np
            return None
        except Exception as e:
            logger.warning(f"Depth estimation failed: {e}")
            return None

    def analyze_with_depth(self, image: np.ndarray) -> Dict:
        depth = self.estimate_depth(image)
        if depth is None:
            return self.base_preprocessor.analyze_conditions(image)
        conditions = self.base_preprocessor.analyze_conditions(image)
        mean_depth = np.mean(depth)
        conditions['depth_low'] = mean_depth < 100
        conditions['depth_high'] = mean_depth > 200
        return conditions

    def preprocess_adaptive(self, image: np.ndarray) -> np.ndarray:
        conditions = self.analyze_with_depth(image)
        return self.preprocess(image, conditions)
