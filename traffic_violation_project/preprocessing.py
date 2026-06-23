import cv2


def enhance_low_light(image):
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    lightness, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    lightness = clahe.apply(lightness)
    enhanced = cv2.merge([lightness, a, b])
    return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)


def normalize_image(image):
    return cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)


def reduce_noise(image):
    return cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)


def preprocess_image(
    image, enable_clahe=True, enable_noise_reduction=True, enable_normalize=False
):
    result = image.copy()
    if enable_clahe:
        result = enhance_low_light(result)
    if enable_noise_reduction:
        result = reduce_noise(result)
    if enable_normalize:
        result = normalize_image(result)
    return result
