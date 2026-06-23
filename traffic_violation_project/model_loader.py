import os
import sys
import logging
from pathlib import Path
from huggingface_hub import hf_hub_download
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_REPO = "Shane30/gridlock-models"
MODELS_DIR = Path(__file__).parent / "models"

REQUIRED_MODELS = [
    "traffic_violation_best.pt",
    "helmet_final_best.pt",
    "seatbelt_best.pt",
    "license_plate_best.pt",
    "all_redsignal_wrongside_best.pt"
]


def ensure_models_downloaded():
    MODELS_DIR.mkdir(exist_ok=True, parents=True)

    missing_models = []
    for model in REQUIRED_MODELS:
        model_path = MODELS_DIR / model
        if not model_path.exists():
            missing_models.append(model)

    if not missing_models:
        logger.info("All models already present")
        return

    logger.info(f"Downloading {len(missing_models)} models from Hugging Face...")
    logger.info(f"Models: {', '.join(missing_models)}")

    for model in missing_models:
        try:
            logger.info(f"  Downloading {model}...")
            start_time = time.time()

            downloaded_path = hf_hub_download(
                repo_id=MODEL_REPO,
                filename=model,
                cache_dir=str(MODELS_DIR),
                local_dir=str(MODELS_DIR),
                local_dir_use_symlinks=False,
                resume_download=True
            )

            elapsed = time.time() - start_time
            file_size = os.path.getsize(downloaded_path) / (1024 * 1024)
            logger.info(f"  Downloaded {model} ({file_size:.1f} MB) in {elapsed:.1f}s")

        except Exception as e:
            logger.error(f"  Failed to download {model}: {e}")
            raise RuntimeError(f"Model download failed: {model}")

    logger.info("All models downloaded successfully")


try:
    ensure_models_downloaded()
except Exception as e:
    logger.error(f"Model download failed: {e}")
    logger.warning("System will run with limited functionality")
