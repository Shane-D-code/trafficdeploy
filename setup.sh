#!/bin/zsh
set -euo pipefail

# Traffic Violation Detection System bootstrap

PROJECT_DIR="traffic_violation_project"

echo "==> Creating folder structure in: ${PROJECT_DIR}"
mkdir -p "${PROJECT_DIR}/datasets/violation_data/images"
mkdir -p "${PROJECT_DIR}/datasets/violation_data/labels"
mkdir -p "${PROJECT_DIR}/datasets/plate_data/images"
mkdir -p "${PROJECT_DIR}/datasets/plate_data/labels"
mkdir -p "${PROJECT_DIR}/models"

echo "==> Creating placeholder Python files"
touch "${PROJECT_DIR}/app.py" "${PROJECT_DIR}/violation_detector.py" "${PROJECT_DIR}/utils.py"

echo "==> Creating requirements.txt"
cat > "${PROJECT_DIR}/requirements.txt" <<'EOF'
ultralytics==8.2.40
opencv-python==4.10.0.84
Pillow==10.4.0
numpy==1.26.4
easyocr==1.7.1
streamlit==1.36.0
pandas==2.2.2
torch==2.3.1
torchvision==0.18.1
setuptools==69.5.1
wheel==0.43.0
EOF

echo "==> Creating virtual environment"
python3 -m venv "${PROJECT_DIR}/venv"

echo "==> Installing dependencies (this takes ~10 min)"
source "${PROJECT_DIR}/venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "${PROJECT_DIR}/requirements.txt"

echo "==> Done! Activate with: source ${PROJECT_DIR}/venv/bin/activate"