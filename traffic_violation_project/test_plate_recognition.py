import sys

import cv2
import numpy as np


def create_test_plate_image(plate_text, width=300, height=80):
    img = np.ones((height, width, 3), dtype=np.uint8) * 200
    cv2.rectangle(img, (3, 3), (width - 3, height - 3), (0, 0, 0), 2)
    cv2.rectangle(img, (5, 5), (width - 5, height - 5), (255, 255, 255), -1)
    noise = np.random.randint(0, 20, (height, width, 3), dtype=np.uint8)
    img = cv2.add(img, noise)
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.0
    thickness = 2
    text_size = cv2.getTextSize(plate_text, font, font_scale, thickness)[0]
    text_x = (width - text_size[0]) // 2
    text_y = (height + text_size[1]) // 2
    cv2.putText(
        img, plate_text, (text_x, text_y), font, font_scale, (0, 0, 0), thickness
    )
    return img


def test_is_valid_plate():
    from license_plate_recognition import is_valid_plate

    valid_cases = [
        ("KA01AB1234", True),
        ("DL02C5678", True),
        ("MH12AB3456", True),
        ("TN01A1234", True),
        ("", False),
        ("AB", False),
        ("ABCDEFGHIJ", False),
        ("1234567890", False),
    ]
    all_ok = True
    for text, expected in valid_cases:
        result = is_valid_plate(text)
        if result != expected:
            all_ok = False
    return all_ok


def test_ocr_pipeline():
    from license_plate_recognition import LicensePlateRecognizer, is_valid_plate

    recognizer = LicensePlateRecognizer(plate_model_path=None)
    test_cases = [
        ("KA01AB1234", True),
        ("DL02C5678", True),
        ("KA51F1234", True),
        ("MH12DE3456", True),
        ("TN01AB1234", True),
        ("GJ01CD5678", True),
    ]
    results = []
    for plate_text, expected_valid in test_cases:
        img = create_test_plate_image(plate_text)
        vehicle_bbox = [0, 0, img.shape[1], img.shape[0]]
        extracted = recognizer.extract_plate_text(img, vehicle_bbox)
        valid = is_valid_plate(extracted) if extracted else False
        results.append(
            {
                "original": plate_text,
                "extracted": extracted,
                "valid": valid,
                "expected_valid": expected_valid,
            }
        )
    return results


if __name__ == "__main__":
    print("=" * 60)
    print("LICENSE PLATE RECOGNITION TESTS")
    print("=" * 60)

    valid_ok = test_is_valid_plate()

    print("\n  is_valid_plate() direct tests: ", end="")
    print("PASS" if valid_ok else "FAIL")

    print("\n  OCR pipeline tests (informational):")
    print("  " + "-" * 40)
    ocr_results = test_ocr_pipeline()
    ocr_ok = 0
    for r in ocr_results:
        match = r["extracted"] == r["original"] if r["extracted"] else False
        if match:
            ocr_ok += 1
        print(
            f"    {'✓' if match else '✗'} {r['original']:<16} -> "
            f"{str(r['extracted']):<16} (valid={r['valid']})"
        )
    print(f"\n  OCR exact matches: {ocr_ok}/{len(ocr_results)}")

    print("\n" + "=" * 60)
    if valid_ok:
        print("ALL CRITICAL TESTS PASSED")
    else:
        print("SOME CRITICAL TESTS FAILED")
    print("=" * 60)

    sys.exit(0 if valid_ok else 1)
