import glob, os
from ultralytics import YOLO

# --- auto find your .pt file ---
pts = glob.glob("**/*.pt", recursive=True)
print("Models found:", pts)
model = YOLO(pts[0])  # picks first one, change index if wrong

# --- check classes ---
print("\nClass names:", model.names)

# --- run on a test image ---
# drop any image in your project folder and it'll pick it up
imgs = glob.glob("**/*.jpg", recursive=True) + glob.glob("**/*.png", recursive=True)
print("Test image:", imgs[0])

results = model(imgs[0], conf=0.25)  # low conf to catch everything

for r in results:
    for box in r.boxes:
        cls_id = int(box.cls)
        conf = float(box.conf)
        label = model.names[cls_id]
        print(f"  Detected: {label} (class {cls_id}) — conf: {conf:.2f}")