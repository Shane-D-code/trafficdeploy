import cv2
import numpy as np
import pytest

from preprocessing import enhance_low_light, normalize_image, preprocess_image, reduce_noise


class TestPreprocessing:
    @pytest.fixture
    def test_image(self):
        return np.ones((100, 100, 3), dtype=np.uint8) * 128

    def test_enhance_low_light(self, test_image):
        result = enhance_low_light(test_image)
        assert result is not None
        assert result.shape == test_image.shape

    def test_normalize_image(self, test_image):
        result = normalize_image(test_image)
        assert result is not None
        assert result.shape == test_image.shape

    def test_reduce_noise(self, test_image):
        result = reduce_noise(test_image)
        assert result is not None
        assert result.shape == test_image.shape

    def test_preprocess_image(self, test_image):
        result = preprocess_image(test_image)
        assert result is not None
        assert result.shape == test_image.shape
