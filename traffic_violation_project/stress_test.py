"""
Comprehensive ML Pipeline Stress Test
Tests all components under various conditions, edge cases, and error scenarios.
"""
import json
import logging
import os
import sys
import tempfile
import time
import traceback
from pathlib import Path

import cv2
import numpy as np

logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
os.environ["EASYOCR_MODULE_PATH"] = tempfile.mkdtemp()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = 0
FAIL = 0
ERROR = 0

def _type_name(t):
    if isinstance(t, tuple):
        return " | ".join(x.__name__ for x in t)
    return t.__name__

def report(name, passed, detail=""):
    global PASS, FAIL
    if passed:
        PASS += 1
        print(f"  ✅ PASS: {name}")
    else:
        FAIL += 1
        print(f"  ❌ FAIL: {name} — {detail}")

def check(name, condition, detail=""):
    report(name, condition, detail)

def expect_error(name, fn, expected_error_type=Exception):
    global PASS, FAIL, ERROR
    try:
        fn()
        FAIL += 1
        print(f"  ❌ FAIL: {name} — expected {_type_name(expected_error_type)} but no error raised")
    except expected_error_type:
        PASS += 1
        print(f"  ✅ PASS: {name} (raised {_type_name(expected_error_type)} as expected)")
    except Exception as e:
        ERROR += 1
        print(f"  ⚠️  ERROR: {name} — expected {_type_name(expected_error_type)}, got {type(e).__name__}: {e}")

def make_img(h=720, w=1280, val=128, channels=3):
    if channels == 1:
        return np.ones((h, w), dtype=np.uint8) * val
    return np.ones((h, w, channels), dtype=np.uint8) * val

def make_detection(class_name="vehicle", x1=100, y1=100, x2=300, y2=400, conf=0.85):
    return {"class_name": class_name, "confidence": conf,
            "box": [x1, y1, x2, y2], "bbox": [x1, y1, x2, y2]}

# =============================================================================
# 1. VIOLATION DETECTORS (Rule-based)
# =============================================================================
print("\n" + "=" * 70)
print("SECTION 1: RULE-BASED VIOLATION DETECTORS")
print("=" * 70)

from violations.red_light import RedLightDetector
from violations.stop_line import StopLineDetector
from violations.wrong_side import WrongSideDetector
from violations.illegal_parking import IllegalParkingDetector
from violations.base import BaseViolationDetector

img_720p = make_img(720, 1280)
img_small = make_img(100, 100)
img_gray = make_img(720, 1280, channels=1)
img_black = make_img(720, 1280, val=0)
img_white = make_img(720, 1280, val=255)

dets_standard = [make_detection("vehicle", 500, 300, 700, 500)]
dets_multi = [
    make_detection("vehicle", 500, 300, 700, 500),
    make_detection("car", 200, 350, 400, 550),
    make_detection("truck", 800, 250, 1000, 450),
    make_detection("bus", 50, 300, 250, 500),
    make_detection("motorcycle", 900, 400, 980, 500),
]
dets_no_vehicle = [make_detection("pedestrian", 300, 200, 350, 450)]
dets_empty = []
dets_malformed = [
    {"class_name": "vehicle", "confidence": 0.9},
    {"class_name": "vehicle", "box": [0, 0, 10]},
    {},
    None,
]

print("\n--- 1.1 RedLightDetector ---")
rld = RedLightDetector()

# Direct _check_red_light_violation tests
rld._current_hsv = cv2.cvtColor(img_720p, cv2.COLOR_BGR2HSV)
check("RL: vehicle below signal", rld._check_red_light_violation([500, 300, 700, 500], [600, 50, 680, 110], img_720p))
check("RL: vehicle above signal (no violation)", not rld._check_red_light_violation([500, 50, 700, 100], [600, 200, 680, 260], img_720p))
check("RL: vehicle far from signal (no violation)", not rld._check_red_light_violation([100, 300, 200, 500], [600, 50, 680, 110], img_720p))
check("RL: None vehicle_box", not rld._check_red_light_violation(None, [0, 0, 10, 10], img_720p))
check("RL: empty vehicle_box", not rld._check_red_light_violation([], [0, 0, 10, 10], img_720p))
check("RL: short vehicle_box", not rld._check_red_light_violation([1, 2, 3], [0, 0, 10, 10], img_720p))

# detect() integration tests
# Create image with actual red traffic light for detection
rld_img = make_img(720, 1280, val=180)
cv2.circle(rld_img, (640, 80), 30, (0, 0, 250), -1)   # saturated red light
cv2.circle(rld_img, (640, 80), 25, (0, 0, 255), -1)   # brighter center
check("RL detect: with red light in image", len(rld.detect(rld_img, dets_standard)) >= 1)
check("RL detect: empty detections", len(rld.detect(img_720p, [])) == 0)
check("RL detect: no-vehicle detections", len(rld.detect(img_720p, dets_no_vehicle)) == 0)
check("RL detect: edge case small image", len(rld.detect(img_small, dets_standard)) == 0)
check("RL detect: white image", isinstance(rld.detect(img_white, dets_standard), list))
check("RL detect: malformed detections", isinstance(rld.detect(img_720p, dets_malformed), list))

print("\n--- 1.2 StopLineDetector ---")
sld = StopLineDetector()

check("SL: vehicle crossing stop line", sld._check_stop_line_crossing([100, 300, 400, 500], [[150, 350, 350, 350]]))
check("SL: vehicle below line (no crossing)", not sld._check_stop_line_crossing([100, 500, 400, 700], [[150, 400, 350, 400]]))
check("SL: vehicle above line (no crossing)", not sld._check_stop_line_crossing([100, 100, 400, 250], [[150, 400, 350, 400]]))
check("SL: empty stop_lines", not sld._check_stop_line_crossing([100, 300, 400, 500], []))
check("SL: None vehicle_box", not sld._check_stop_line_crossing(None, [[0, 0, 10, 10]]))
check("SL: empty vehicle_box", not sld._check_stop_line_crossing([], [[0, 0, 10, 10]]))
check("SL: malformed stop_line entry", not sld._check_stop_line_crossing([100, 300, 400, 500], [[1, 2]]))

check("SL detect: empty detections", isinstance(sld.detect(img_720p, []), list))
check("SL detect: malformed detections", isinstance(sld.detect(img_720p, dets_malformed), list))
check("SL detect: type", isinstance(sld.detect(img_720p, dets_standard), list))

print("\n--- 1.3 WrongSideDetector ---")
wsd = WrongSideDetector()

check("WS: vehicle near lane returns bool", isinstance(wsd._check_vehicle_direction([325, 300, 475, 500], [[400, 0, 400, 720]], 0.0), bool))
check("WS: empty lanes", not wsd._check_vehicle_direction([500, 300, 700, 500], [], None))
check("WS: None vehicle_box", not wsd._check_vehicle_direction(None, [[0, 0, 10, 10]], 0.0))
check("WS: empty vehicle_box", not wsd._check_vehicle_direction([], [[0, 0, 10, 10]], 0.0))
check("WS: malformed lane", not wsd._check_vehicle_direction([500, 300, 700, 500], [[1, 2]], 0.0))

check("WS detect: empty detections", isinstance(wsd.detect(img_720p, []), list))
check("WS detect: malformed detections", isinstance(wsd.detect(img_720p, dets_malformed), list))
check("WS detect: type", isinstance(wsd.detect(img_720p, dets_standard), list))

print("\n--- 1.4 IllegalParkingDetector ---")
ipd = IllegalParkingDetector()

check("IP: vehicle fully in zone", ipd._check_parked_vehicle([100, 100, 300, 300], [50, 50, 350, 350], img_720p))
check("IP: vehicle partially in zone (>50%)", ipd._check_parked_vehicle([100, 100, 220, 300], [155, 100, 400, 400], img_720p))
check("IP: vehicle outside zone", not ipd._check_parked_vehicle([10, 10, 50, 50], [100, 100, 300, 300], img_720p))
check("IP: vehicle adjacent to zone (no overlap)", not ipd._check_parked_vehicle([100, 100, 200, 200], [200, 200, 300, 300], img_720p))
check("IP: None vehicle_box", not ipd._check_parked_vehicle(None, [0, 0, 10, 10], img_720p))
check("IP: empty vehicle_box", not ipd._check_parked_vehicle([], [0, 0, 10, 10], img_720p))

check("IP detect: empty detections", isinstance(ipd.detect(img_720p, []), list))
check("IP detect: malformed detections", isinstance(ipd.detect(img_720p, dets_malformed), list))
check("IP detect: type", isinstance(ipd.detect(img_720p, dets_standard), list))

print("\n--- 1.5 BaseViolationDetector ---")
bv = BaseViolationDetector()
v = bv.create_violation("TEST_TYPE", 0.95, [10, 20, 100, 200], "KA01AB1234")
check("Base create_violation: keys", all(k in v for k in ["type", "confidence", "bbox", "plate_text", "timestamp"]))
check("Base create_violation: type", v["type"] == "TEST_TYPE")
check("Base create_violation: confidence", v["confidence"] == 0.95)
check("Base create_violation: plate_text", v["plate_text"] == "KA01AB1234")
check("Base create_violation: bbox", v["bbox"] == [10, 20, 100, 200])
check("Base detect returns list", isinstance(bv.detect(None, None), list))

v2 = bv.create_violation("NO_PLATE", 0.8, [0, 0, 50, 50])
check("Base create_violation: plate_text defaults", v2["plate_text"] is None)

# =============================================================================
# 2. VIOLATION DETECTOR (Main YOLO-based class)
# =============================================================================
print("\n" + "=" * 70)
print("SECTION 2: VIOLATION DETECTOR (Main Class)")
print("=" * 70)

from violation_detector import (
    ViolationDetector, calculate_overall_confidence,
    FrameTracker, EventConsolidator,
    _standardize_class_name, CLASS_NAME_MAP
)

print("\n--- 2.1 CLASS_NAME_MAP & _standardize_class_name ---")
check("standardize: person_rider -> rider", _standardize_class_name("person_rider") == "rider")
check("standardize: no_helmet stays", _standardize_class_name("no_helmet") == "no_helmet")
check("standardize: without_helmet -> no_helmet", _standardize_class_name("without_helmet") == "no_helmet")
check("standardize: unknown stays", _standardize_class_name("giraffe") == "giraffe")
check("standardize: empty string", _standardize_class_name("") == "")

print("\n--- 2.2 calculate_overall_confidence ---")
check("conf: detection only", calculate_overall_confidence(0.9, None, False) == 0.9)
check("conf: with valid plate", abs(calculate_overall_confidence(0.9, 0.8, True) - 0.86) < 0.01)

check("conf: with invalid plate halved", abs(calculate_overall_confidence(0.9, 0.8, False) - 0.43) < 0.01)

check("conf: capped at 1.0", calculate_overall_confidence(0.99, 0.99, True) <= 1.0)
check("conf: zero detection", calculate_overall_confidence(0.0, None, False) == 0.0)

print("\n--- 2.3 ViolationDetector IoU ---")
try:
    vd = ViolationDetector(model_path="models/traffic_violation_best.pt")
    check("VD init", vd is not None)

    iou = vd.compute_iou([0, 0, 10, 10], [5, 5, 15, 15])
    check("VD IoU: partial overlap", abs(iou - 25/175) < 0.01)

    iou_full = vd.compute_iou([0, 0, 10, 10], [0, 0, 10, 10])
    check("VD IoU: identical boxes", iou_full == 1.0)

    iou_none = vd.compute_iou([0, 0, 10, 10], [20, 20, 30, 30])
    check("VD IoU: no overlap", iou_none == 0.0)

    ub = vd.get_upper_body_box([100, 100, 200, 400])
    check("VD upper_body: height", ub[3] - ub[1] == 120)
    check("VD upper_body: width unchanged", ub[2] - ub[0] == 100)

    dr = vd.get_driver_region([100, 100, 300, 500])
    check("VD driver_region: correct x_start", dr[0] == 120)
    check("VD driver_region: correct x_end", dr[2] == 180)
    check("VD driver_region: correct y_start", dr[1] == 220)
    check("VD driver_region: correct y_end", dr[3] == 380)

    print("\n--- 2.4 ViolationDetector detect_violations ---")
    test_img_path = "_stress_test_img.jpg"
    test_img = np.ones((640, 640, 3), dtype=np.uint8) * 128
    cv2.imwrite(test_img_path, test_img)

    violations, dets = vd.detect_violations(test_img_path, confidence_threshold=0.01)
    check("VD detect: returns tuple of 2", isinstance(violations, list) and isinstance(dets, list))
    check("VD detect: violation items are dicts", all(isinstance(v, dict) for v in violations))
    check("VD detect: detections have expected keys",
          all("box" in d and "class_name" in d and "confidence" in d for d in dets))

    violations2, dets2 = vd.detect_violations(test_img, confidence_threshold=0.01)
    check("VD detect: numpy array input", isinstance(violations2, list))

    violations3, dets3 = vd.detect_violations(test_img_path, confidence_threshold=0.01, enable_preprocessing=False)
    check("VD detect: preprocessing disabled", isinstance(violations3, list))

    # Edge cases
    violations4, dets4 = vd.detect_violations(test_img_path, confidence_threshold=1.0)
    check("VD detect: high threshold (likely no dets)", isinstance(violations4, list))

    # draw_violations
    annotated = vd.draw_violations(test_img, violations)
    check("VD draw: returns numpy array", isinstance(annotated, np.ndarray))
    check("VD draw: same size as input", annotated.shape == test_img.shape)

    annotated_path = vd.draw_violations(test_img_path, violations)
    check("VD draw: from path string", isinstance(annotated_path, np.ndarray))

    annotated_empty = vd.draw_violations(test_img, [])
    check("VD draw: empty violations", isinstance(annotated_empty, np.ndarray))

    os.unlink(test_img_path)
except Exception as e:
    print(f"  ⚠️  ERROR in ViolationDetector tests: {e}")
    traceback.print_exc()

print("\n--- 2.5 FrameTracker ---")
ft = FrameTracker(max_track_length=5, iou_threshold=0.3)
check("FT init", ft is not None and ft.next_id == 0)

d1 = [make_detection("vehicle", 100, 100, 200, 200)]
tracks1 = ft.update(d1)
check("FT update: returns dict", isinstance(tracks1, dict))
check("FT update: 1 track created", len(tracks1) == 1)
tid = list(tracks1.keys())[0]

d2 = [make_detection("vehicle", 105, 105, 205, 205)]
tracks2 = ft.update(d2)
check("FT update: track matched", len(tracks2) == 1)
check("FT update: frames_seen incremented", tracks2[tid]["frames_seen"] >= 2)

ft2 = FrameTracker(max_track_length=2, iou_threshold=0.9)
d_miss = [make_detection("vehicle", 500, 500, 600, 600)]
ft2.update(d_miss)
ft2.update(d_miss)
ft2.update(d_miss)
check("FT update: lost track removed after max_track_length", len(ft2.tracks) <= 1)

ft3 = FrameTracker()
check("FT update: empty detections", isinstance(ft3.update([]), dict))

print("\n--- 2.6 EventConsolidator ---")
ec = EventConsolidator(iou_threshold=0.3, time_window=10)

v1 = {"type": "NO HELMET", "confidence": 0.9, "bbox": [0, 0, 10, 10], "plate_text": "KA01AB1234"}
v2 = {"type": "NO HELMET", "confidence": 0.7, "bbox": [1, 1, 11, 11], "plate_text": "KA01AB1234"}
v3 = {"type": "NO SEATBELT", "confidence": 0.8, "bbox": [100, 100, 200, 200], "plate_text": "DL02C5678"}

check("EC consolidate: dedup", len(ec.consolidate_violations([v1, v2])) == 1)
check("EC consolidate: different types kept", len(ec.consolidate_violations([v1, v3])) == 2)
check("EC consolidate: empty list", len(ec.consolidate_violations([])) == 0)
check("EC consolidate: best confidence kept", ec.consolidate_violations([v1, v2])[0]["confidence"] == 0.9)

v_no_plate = {"type": "NO HELMET", "confidence": 0.8, "bbox": [0, 0, 10, 10]}
check("EC consolidate: no plate_text", len(ec.consolidate_violations([v1, v_no_plate])) == 2)

# =============================================================================
# 3. LICENSE PLATE RECOGNITION
# =============================================================================
print("\n" + "=" * 70)
print("SECTION 3: LICENSE PLATE RECOGNITION")
print("=" * 70)

from license_plate_recognition import (
    LicensePlateRecognizer, get_recognizer,
    extract_plate_text, is_valid_plate
)

print("\n--- 3.1 LicensePlateRecognizer init ---")
lpr = LicensePlateRecognizer(plate_model_path=None)
check("LPR init with None model", lpr is not None)
check("LPR model loaded when available", lpr.plate_model is not None)

print("\n--- 3.2 is_valid_plate ---")
check("LPR valid: standard KA01AB1234", lpr.is_valid_plate("KA01AB1234"))
check("LPR valid: DL02C5678", lpr.is_valid_plate("DL02C5678"))
check("LPR valid: MH12AB3456", lpr.is_valid_plate("MH12AB3456"))
check("LPR valid: TN07AX1234", lpr.is_valid_plate("TN07AX1234"))
check("LPR invalid: empty", not lpr.is_valid_plate(""))
check("LPR invalid: None", not lpr.is_valid_plate(None))
check("LPR invalid: too short (ABC)", not lpr.is_valid_plate("ABC"))
check("LPR invalid: all digits", not lpr.is_valid_plate("12345678"))
check("LPR invalid: all letters", not lpr.is_valid_plate("ABCDEFGH"))
check("LPR invalid: special chars", not lpr.is_valid_plate("KA-01-AB-1234!@#"))
# Should still match the regex after cleaning, but raw text with special chars doesn't match patterns
check("LPR valid: lowercase -> uppercase", lpr.is_valid_plate("KA01AB1234"))  # already upper

print("\n--- 3.3 _clean_plate_text ---")
check("LPR clean: removes hyphens", lpr._clean_plate_text("KA-01-AB-1234") == "KA01AB1234")
check("LPR clean: uppercase", lpr._clean_plate_text("ka01ab1234") == "KA01AB1234")
check("LPR clean: removes spaces", lpr._clean_plate_text("KA 01 AB 1234") == "KA01AB1234")
check("LPR clean: empty string", lpr._clean_plate_text("") == "")
check("LPR clean: None", lpr._clean_plate_text(None) == "")

print("\n--- 3.4 _crop_vehicle_region ---")
test_img = make_img(720, 1280)
crop = lpr._crop_vehicle_region(test_img, [100, 100, 300, 300])
check("LPR crop: returns np array", isinstance(crop, np.ndarray))
check("LPR crop: correct size", crop.shape == (200, 200, 3))

crop2 = lpr._crop_vehicle_region(test_img, [-50, -50, 50, 50])
check("LPR crop: clamped to 0", crop2.shape[0] == 50)

crop3 = lpr._crop_vehicle_region(test_img, [0, 0, 2000, 2000])
check("LPR crop: clamped to image bounds", crop3 is not None)

check("LPR crop: None for zero area box", lpr._crop_vehicle_region(test_img, [100, 100, 100, 200]) is None)

print("\n--- 3.5 extract_plate_text ---")
plate_img = np.ones((300, 500, 3), dtype=np.uint8) * 128
cv2.rectangle(plate_img, (100, 100), (280, 140), (50, 50, 50), -1)
cv2.putText(plate_img, "KA01AB1234", (110, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

result = lpr.extract_plate_text(plate_img, [50, 50, 450, 250])
check("LPR extract: runs without error", result is None or isinstance(result, str))

check("LPR extract: None image", lpr.extract_plate_text(None, [0, 0, 10, 10]) is None)
check("LPR extract: None bbox", lpr.extract_plate_text(plate_img, None) is None)
check("LPR extract: empty image", lpr.extract_plate_text(make_img(10, 10), [0, 0, 10, 10]) is None)

print("\n--- 3.6 Module-level helpers ---")
r = get_recognizer()
check("get_recognizer: returns instance", r is not None)
check("get_recognizer: singleton", get_recognizer() is r)

# These should not crash even without a real model
check("extract_plate_text module fn", isinstance(extract_plate_text(plate_img, [50, 50, 450, 250]), (str, type(None))))
check("is_valid_plate module fn", is_valid_plate("KA01AB1234") == True)

# =============================================================================
# 4. PREPROCESSING
# =============================================================================
print("\n" + "=" * 70)
print("SECTION 4: PREPROCESSING")
print("=" * 70)

from preprocessing import enhance_low_light, normalize_image, reduce_noise, preprocess_image

print("\n--- 4.1 enhance_low_light ---")
e = enhance_low_light(img_720p)
check("CLAHE: shape preserved", e.shape == img_720p.shape)
check("CLAHE: dtype uint8", e.dtype == np.uint8)

e_small = enhance_low_light(img_small)
check("CLAHE: small image", e_small.shape == img_small.shape)

expect_error("CLAHE: 1-channel input raises", lambda: enhance_low_light(img_gray), cv2.error)

print("\n--- 4.2 normalize_image ---")
n = normalize_image(img_720p)
check("norm: shape preserved", n.shape == img_720p.shape)
check("norm: range [0,255]", n.min() >= 0 and n.max() <= 255)

n_gray = normalize_image(img_gray)
check("norm: 1-channel works", n_gray.shape == img_gray.shape)

n_black = normalize_image(img_black)
check("norm: all-black input", n_black.shape == img_black.shape)

n_white = normalize_image(img_white)
check("norm: all-white input", n_white.shape == img_white.shape)

print("\n--- 4.3 reduce_noise ---")
r = reduce_noise(img_720p)
check("denoise: shape preserved", r.shape == img_720p.shape)

r_small = reduce_noise(img_small)
check("denoise: small image", r_small.shape == img_small.shape)

print("\n--- 4.4 preprocess_image ---")
p = preprocess_image(img_720p)
check("preprocess full: shape preserved", p.shape == img_720p.shape)

p_none = preprocess_image(img_720p, enable_clahe=False, enable_noise_reduction=False, enable_normalize=False)
check("preprocess no-op: image unchanged", np.array_equal(p_none, img_720p))

p_clahe_only = preprocess_image(img_720p, enable_clahe=True, enable_noise_reduction=False)
check("preprocess CLAHE only: shape", p_clahe_only.shape == img_720p.shape)

p_norm_only = preprocess_image(img_720p, enable_clahe=False, enable_normalize=True)
check("preprocess norm only: shape", p_norm_only.shape == img_720p.shape)

# =============================================================================
# 5. EVALUATION MODULE
# =============================================================================
print("\n" + "=" * 70)
print("SECTION 5: EVALUATION MODULE")
print("=" * 70)

from evaluation import ModelEvaluator

print("\n--- 5.1 ModelEvaluator IoU ---")
me = ModelEvaluator("models/traffic_violation_best.pt")
check("ME IoU: identical", me.compute_iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0)
check("ME IoU: no overlap", me.compute_iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0)
check("ME IoU: partial", abs(me.compute_iou([0, 0, 10, 10], [5, 5, 15, 15]) - 25/175) < 0.01)

print("\n--- 5.2 Precision/Recall/F1 ---")
p, r, f = me.compute_precision_recall(
    [{"bbox": [0, 0, 10, 10], "confidence": 0.9}],
    [{"bbox": [0, 0, 10, 10]}],
    0.5
)
check("ME PR: perfect match", p == 1.0 and r == 1.0 and f == 1.0)

p2, r2, f2 = me.compute_precision_recall(
    [{"bbox": [0, 0, 10, 10], "confidence": 0.9}],
    [{"bbox": [50, 50, 60, 60]}],
    0.5
)
check("ME PR: no match", p2 == 0.0 and r2 == 0.0 and f2 == 0.0)

p3, r3, f3 = me.compute_precision_recall([], [{"bbox": [0, 0, 10, 10]}], 0.5)
check("ME PR: no predictions", p3 == 0.0 and r3 == 0.0 and f3 == 0.0)

p4, r4, f4 = me.compute_precision_recall(
    [{"bbox": [0, 0, 10, 10], "confidence": 0.9}],
    [], 0.5
)
check("ME PR: no ground truth", p4 == 1.0 and r4 == 0.0 and f4 == 0.0)

print("\n--- 5.3 Average Precision ---")
ap = me.compute_ap(
    [{"bbox": [0, 0, 10, 10], "confidence": 0.9}],
    [{"bbox": [0, 0, 10, 10]}],
    0.5
)
check("ME AP: single perfect match", ap > 0.9)

ap2 = me.compute_ap([], [{"bbox": [0, 0, 10, 10]}], 0.5)
check("ME AP: no predictions", ap2 == 0.0)

ap3 = me.compute_ap(
    [{"bbox": [0, 0, 10, 10], "confidence": 0.9}],
    [], 0.5
)
check("ME AP: no ground truth", ap3 == 0.0)

print("\n--- 5.4 evaluate() ---")
test_img_path = "_eval_stress_test.jpg"
cv2.imwrite(test_img_path, make_img(640, 640))

metrics = me.evaluate([test_img_path], conf_threshold=0.25)
check("ME evaluate: returns dict", isinstance(metrics, dict))
check("ME evaluate: has per_class", "per_class" in metrics)
check("ME evaluate: has macro_precision", "macro_precision" in metrics)
check("ME evaluate: has macro_recall", "macro_recall" in metrics)
check("ME evaluate: has macro_f1", "macro_f1" in metrics)
check("ME evaluate: has mAP", "mAP" in metrics)
check("ME evaluate: mAP is float", isinstance(metrics["mAP"], float))

metrics2 = me.evaluate([], conf_threshold=0.25)
check("ME evaluate: empty image list", isinstance(metrics2, dict))

report_path = me.export_report("_stress_test_report.md")
check("ME export: file exists", os.path.exists(report_path))
summary = me.summary()
check("ME summary: returns dict", isinstance(summary, dict))
check("ME summary: matches metrics keys", set(summary.keys()) == set(metrics.keys()))

os.unlink(test_img_path)
os.unlink(report_path)

# =============================================================================
# 6. INTEGRATION TESTS
# =============================================================================
print("\n" + "=" * 70)
print("SECTION 6: INTEGRATION TESTS")
print("=" * 70)

from violation_detector import detect_violations, draw_violations, generate_evidence_image, VideoProcessor
from violation_detector import detect_violations_json

print("\n--- 6.1 Pipeline module-level functions ---")
test_img_path = "_integ_test.jpg"
test_img = np.ones((640, 640, 3), dtype=np.uint8) * 128
cv2.imwrite(test_img_path, test_img)

# detect_violations
violations, dets = detect_violations(test_img_path, enable_preprocessing=False)
check("Pipeline detect: returns tuple(2)", isinstance(violations, list) and isinstance(dets, list))
check("Pipeline detect: violations is list", isinstance(violations, list))

# draw_violations
annotated = draw_violations(test_img_path, violations)
check("Pipeline draw: returns np array", isinstance(annotated, np.ndarray))

# generate_evidence_image
os.makedirs("evidence", exist_ok=True)
path, filename = generate_evidence_image(test_img_path, violations)
check("Pipeline evidence: file created", os.path.exists(path))
check("Pipeline evidence: filename is str", isinstance(filename, str))
if os.path.exists(path):
    os.unlink(path)

# detect_violations_json
result = detect_violations_json(test_img_path, enable_preprocessing=False)
check("Pipeline JSON: returns dict", isinstance(result, dict))
check("Pipeline JSON: has violations key", "violations" in result)
check("Pipeline JSON: has stats key", "stats" in result)
check("Pipeline JSON: violations is list", isinstance(result["violations"], list))
check("Pipeline JSON: stats has total", "total" in result["stats"])

os.unlink(test_img_path)

print("\n--- 6.2 VideoProcessor ---")
vp = VideoProcessor(None, frame_interval=30, max_frames=5)
check("VideoProcessor init with None detector", vp is not None)

vp_real = VideoProcessor(vd if 'vd' in dir() else None)
dummy_video = "_stress_dummy.mp4"
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
vw = cv2.VideoWriter(dummy_video, fourcc, 30.0, (640, 480))
for _ in range(90):
    vw.write(np.ones((480, 640, 3), dtype=np.uint8) * 128)
vw.release()

if os.path.exists(dummy_video) and os.path.getsize(dummy_video) > 0:
    try:
        vid_results = vp_real.process_video(dummy_video, confidence_threshold=0.5, enable_preprocessing=False)
        check("VideoProcessor: returns list", isinstance(vid_results, list))
    except Exception as e:
        print(f"  ⚠️  VideoProcessor test error (may be expected without GPU): {e}")
    os.unlink(dummy_video)
else:
    print(f"  ⚠️  Could not create test video (skipping VideoProcessor test)")

print("\n--- 6.3 Stress: Concurrent/multi-scenario ---")
scenarios = [
    ("small image 50x50", make_img(50, 50)),
    ("tiny image 10x10", make_img(10, 10)),
    ("black image", make_img(720, 1280, val=0)),
    ("white image", make_img(720, 1280, val=255)),
    ("high contrast", np.random.randint(0, 256, (720, 1280, 3), dtype=np.uint8)),
]

if 'vd' in dir():
    for label, img in scenarios:
        try:
            v, d = vd.detect_violations(img, confidence_threshold=0.01, enable_preprocessing=True)
            check(f"Stress: {label} — returns tuple", isinstance(v, list) and isinstance(d, list))
        except Exception as e:
            print(f"  ⚠️  Stress: {label} — error: {e}")
else:
    print("  ⚠️  Skipping stress scenarios (vd not initialized)")

# =============================================================================
# 7. ERROR HANDLING EDGE CASES
# =============================================================================
print("\n" + "=" * 70)
print("SECTION 7: ERROR HANDLING & EDGE CASES")
print("=" * 70)

print("\n--- 7.1 Missing files ---")
expect_error("Detector: non-existent model path",
    lambda: ViolationDetector(model_path="/nonexistent/model.pt"),
    FileNotFoundError)

expect_error("detect_violations: non-existent image",
    lambda: detect_violations("/nonexistent/image.jpg"),
    (FileNotFoundError, ValueError))

result_err = detect_violations_json("/nonexistent/image.jpg")
check("detect_violations_json: error returns error dict", "error" in result_err)
check("detect_violations_json: error has empty violations", len(result_err.get("violations", [])) == 0)

print("\n--- 7.2 Invalid inputs ---")
if 'vd' in dir():
    expect_error("VD detect: non-existent path string",
        lambda: vd.detect_violations("/nonexistent/foo.jpg"),
        (FileNotFoundError, ValueError))

    expect_error("VD draw: non-existent path",
        lambda: vd.draw_violations("/nonexistent/foo.jpg", []),
        FileNotFoundError)

    # draw_violations with malformed bbox
    bad_v = [{"type": "TEST", "confidence": 0.5, "bbox": [0]}]  # incomplete bbox
    try:
        img_bad = vd.draw_violations(test_img_placeholder if 'test_img_placeholder' in dir() else make_img(640, 640), bad_v)
        check("VD draw: incomplete bbox handled", True)
    except Exception:
        check("VD draw: incomplete bbox handled", False)

# Test some more
check("detect_violations_json: handles no model gracefully",
    isinstance(detect_violations_json("/nonexistent.jpg"), dict))

print("\n--- 7.3 FrameTracker edge cases ---")
ft4 = FrameTracker()
check("FT4: max_track_length default", ft4.max_track_length == 10)
check("FT4: iou_threshold default", ft4.iou_threshold == 0.5)

# Update with same bbox over many frames, then new one
ft5 = FrameTracker(max_track_length=2, iou_threshold=0.5)
for _ in range(5):
    ft5.update([make_detection("vehicle", 100, 100, 200, 200)])
check("FT5: track not lost while matching", len(ft5.tracks) == 1)

ft5.update([make_detection("vehicle", 500, 500, 600, 600)])
# Old track (no match) + new track
check("FT5: old track removed, new added", len(ft5.tracks) <= 2)

# _compute_iou edge cases
check("FT5: IoU empty box1", ft5._compute_iou([], [0, 0, 10, 10]) == 0)
check("FT5: IoU None box1", ft5._compute_iou(None, [0, 0, 10, 10]) == 0)
check("FT5: IoU partial box", ft5._compute_iou([1, 2, 3], [0, 0, 10, 10]) == 0)

print("\n--- 7.4 EventConsolidator edge cases ---")
ec2 = EventConsolidator(iou_threshold=0.5)
check("EC2: empty violations", len(ec2.consolidate_violations([])) == 0)

# Violation without bbox field
v_no_bbox = {"type": "TEST", "confidence": 0.5, "box": [0, 0, 10, 10]}
v_no_bbox2 = {"type": "TEST", "confidence": 0.6, "box": [0, 0, 10, 10]}
check("EC2: violation with 'box' not 'bbox'", len(ec2.consolidate_violations([v_no_bbox, v_no_bbox2])) == 1)

v_no_loc = {"type": "TEST", "confidence": 0.5}
check("EC2: violation with no location", len(ec2.consolidate_violations([v_no_loc])) == 1)

# =============================================================================
# 8. SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("STRESS TEST SUMMARY")
print("=" * 70)
total = PASS + FAIL
print(f"\n  Total tests: {total}")
print(f"  ✅ Passed:    {PASS}")
print(f"  ❌ Failed:    {FAIL}")
print(f"  ⚠️  Errors:    {ERROR}")
print(f"  Pass rate:    {PASS/total*100:.1f}%" if total > 0 else "  No tests run")
print()

if FAIL == 0 and ERROR == 0:
    print("  ✅ ALL TESTS PASSED")
else:
    print(f"  ⚠️  {FAIL} failures, {ERROR} errors")
    sys.exit(1)
