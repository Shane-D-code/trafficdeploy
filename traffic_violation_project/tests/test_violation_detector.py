import cv2
import numpy as np
import pytest

from license_plate_recognition import LicensePlateRecognizer, is_valid_plate


class TestLicensePlateRecognizer:
    @pytest.fixture
    def recognizer(self):
        return LicensePlateRecognizer(plate_model_path=None)

    def test_init(self, recognizer):
        assert recognizer is not None
        assert hasattr(recognizer, 'reader')

    def test_is_valid_plate(self, recognizer):
        valid_plates = ['KA01AB1234', 'DL02C5678', 'MH12AB3456']
        invalid_plates = ['INVALID', '123', 'ABC']
        for plate in valid_plates:
            assert recognizer.is_valid_plate(plate) is True
        for plate in invalid_plates:
            assert recognizer.is_valid_plate(plate) is False

    def test_clean_plate_text(self, recognizer):
        assert recognizer._clean_plate_text("KA-01-AB-1234") == "KA01AB1234"
        assert recognizer._clean_plate_text("ka01ab1234") == "KA01AB1234"
        assert recognizer._clean_plate_text("") == ""


class TestViolationDetectorIntegration:
    def test_imports(self):
        from violation_detector import (
            ViolationDetector,
            calculate_overall_confidence,
            detect_violations,
            draw_violations,
        )
        assert ViolationDetector is not None
        assert calculate_overall_confidence is not None

    def test_calculate_overall_confidence(self):
        from violation_detector import calculate_overall_confidence

        assert calculate_overall_confidence(0.9, None, False) == 0.9
        assert calculate_overall_confidence(0.9, 0.8, True) == pytest.approx(0.86, rel=0.01)
        result = calculate_overall_confidence(0.9, 0.8, False)
        expected = (0.9 * 0.6 + 0.8 * 0.4) * 0.5
        assert result == pytest.approx(expected, rel=0.01)

    def test_frame_tracker(self):
        from violation_detector import FrameTracker

        tracker = FrameTracker(max_track_length=5, iou_threshold=0.5)
        detections = [
            {'box': [0, 0, 10, 10], 'confidence': 0.9, 'class_name': 'vehicle'},
            {'box': [20, 20, 30, 30], 'confidence': 0.8, 'class_name': 'rider'},
        ]
        tracks = tracker.update(detections)
        assert len(tracks) == 2

    def test_event_consolidator(self):
        from violation_detector import EventConsolidator

        consolidator = EventConsolidator(iou_threshold=0.3)
        violations = [
            {'type': 'NO HELMET', 'confidence': 0.9, 'bbox': [0, 0, 10, 10], 'plate_text': 'KA01AB1234'},
            {'type': 'NO HELMET', 'confidence': 0.7, 'bbox': [1, 1, 11, 11], 'plate_text': 'KA01AB1234'},
        ]
        result = consolidator.consolidate_violations(violations)
        assert len(result) == 1
        assert result[0]['confidence'] == 0.9
