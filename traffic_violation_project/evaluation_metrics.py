"""
evaluation_metrics.py - Model evaluation metrics computation

Computes accuracy, precision, recall, F1, per-class mAP, and inference time
statistics from the violations database using review-status ground truth.
"""

import time
import json
import sys
import logging
from collections import defaultdict
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core metric helpers
# ---------------------------------------------------------------------------

def compute_accuracy(violations: List[Dict]) -> Dict:
    """
    Compute accuracy / precision / recall / F1 from a list of violation dicts.

    Each violation dict is expected to have a 'status' field that can be:
      - 'approved'       → True Positive
      - 'false_positive' → False Positive
      - 'rejected'       → False Negative (missed / wrong detection)
      - 'pending' / None → ignored (not yet reviewed)

    Args:
        violations: list of violation record dicts from the DB

    Returns:
        Dict with accuracy, precision, recall, f1, mAP, per-class metrics,
        and confusion matrix counts.
    """
    reviewed = [v for v in violations if v.get('status') in ('approved', 'false_positive', 'rejected')]
    total_reviewed = len(reviewed)

    if total_reviewed == 0:
        return {
            'accuracy': 0.0,
            'precision': 0.0,
            'recall': 0.0,
            'f1': 0.0,
            'mAP': 0.0,
            'totalSamples': len(violations),
            'totalReviewed': 0,
            'truePositives': 0,
            'falsePositives': 0,
            'falseNegatives': 0,
            'byType': {},
            'mapPerClass': {},
        }

    tp = sum(1 for v in reviewed if v.get('status') == 'approved')
    fp = sum(1 for v in reviewed if v.get('status') == 'false_positive')
    fn = sum(1 for v in reviewed if v.get('status') == 'rejected')

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    accuracy  = tp / total_reviewed if total_reviewed > 0 else 0.0

    # Per-class metrics
    by_type: Dict[str, Dict] = defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0})
    for v in reviewed:
        vtype = v.get('violation_type', 'UNKNOWN')
        status = v.get('status')
        if status == 'approved':
            by_type[vtype]['tp'] += 1
        elif status == 'false_positive':
            by_type[vtype]['fp'] += 1
        elif status == 'rejected':
            by_type[vtype]['fn'] += 1

    map_per_class: Dict[str, float] = {}
    for vtype, counts in by_type.items():
        c_tp = counts['tp']
        c_fp = counts['fp']
        c_fn = counts['fn']
        c_prec = c_tp / (c_tp + c_fp) if (c_tp + c_fp) > 0 else 0.0
        c_rec  = c_tp / (c_tp + c_fn) if (c_tp + c_fn) > 0 else 0.0
        # AP approximation: precision * recall (single-point)
        map_per_class[vtype] = round(c_prec * c_rec * 100, 2)

    overall_map = round(sum(map_per_class.values()) / len(map_per_class), 4) if map_per_class else 0.0

    # Violation count by type across ALL (not just reviewed)
    type_counts: Dict[str, int] = defaultdict(int)
    for v in violations:
        type_counts[v.get('violation_type', 'UNKNOWN')] += 1

    return {
        'accuracy':      round(accuracy, 4),
        'precision':     round(precision, 4),
        'recall':        round(recall, 4),
        'f1':            round(f1, 4),
        'mAP':           round(overall_map, 4),
        'totalSamples':  len(violations),
        'totalReviewed': total_reviewed,
        'truePositives': tp,
        'falsePositives': fp,
        'falseNegatives': fn,
        'byType':        dict(type_counts),
        'mapPerClass':   map_per_class,
    }


def compute_inference_stats(violations: List[Dict]) -> Dict:
    """
    Compute inference time statistics from stored metadata.

    Args:
        violations: list of violation dicts; each may have a 'metadata' field
                    containing JSON with an 'inference_time_ms' key.

    Returns:
        Dict with avgMs, p50Ms, p95Ms, p99Ms, fps, sampleCount.
    """
    times: List[float] = []
    for v in violations:
        meta = v.get('metadata')
        if not meta:
            continue
        try:
            if isinstance(meta, str):
                meta = json.loads(meta)
            t = meta.get('inference_time_ms')
            if t is not None and t > 0:
                times.append(float(t))
        except (json.JSONDecodeError, TypeError):
            continue

    if not times:
        return {
            'avgMs': 0.0,
            'p50Ms': 0.0,
            'p95Ms': 0.0,
            'p99Ms': 0.0,
            'fps': 0.0,
            'sampleCount': 0,
        }

    sorted_t = sorted(times)
    n = len(sorted_t)

    def _percentile(arr, pct):
        idx = min(int(len(arr) * pct / 100), len(arr) - 1)
        return arr[idx]

    avg   = sum(sorted_t) / n
    p50   = _percentile(sorted_t, 50)
    p95   = _percentile(sorted_t, 95)
    p99   = _percentile(sorted_t, 99)
    fps   = round(1000 / avg, 2) if avg > 0 else 0.0

    return {
        'avgMs':       round(avg, 2),
        'p50Ms':       round(p50, 2),
        'p95Ms':       round(p95, 2),
        'p99Ms':       round(p99, 2),
        'fps':         fps,
        'sampleCount': n,
    }


def measure_inference_time(model, image, iterations: int = 10) -> Dict:
    """
    Directly benchmark a model on a single image.

    Args:
        model:      callable that accepts an image and returns predictions
        image:      input to pass to model (numpy array or path)
        iterations: number of timed runs

    Returns:
        Dict with avgMs, minMs, maxMs, stdMs, fps, samples.
    """
    import numpy as np

    # Warm-up run (not timed)
    try:
        model(image)
    except Exception:
        pass

    times: List[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        try:
            model(image)
        except Exception:
            pass
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        times.append(elapsed_ms)

    avg = float(np.mean(times))
    return {
        'avgMs':    round(avg, 2),
        'minMs':    round(float(np.min(times)), 2),
        'maxMs':    round(float(np.max(times)), 2),
        'stdMs':    round(float(np.std(times)), 2),
        'fps':      round(1000 / avg, 2) if avg > 0 else 0.0,
        'samples':  iterations,
    }


# ---------------------------------------------------------------------------
# Convenience wrapper: compute everything from a DB path
# ---------------------------------------------------------------------------

def compute_full_metrics(db_path: str = 'traffic_violations.db') -> Dict:
    """
    Load all violations from the SQLite DB and return combined metrics.

    Returns:
        Dict combining accuracy/mAP metrics and inference time stats.
    """
    import sqlite3

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            'SELECT violation_type, confidence, status, metadata FROM violations'
        )
        violations = [dict(row) for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        logger.error(f"DB read error: {e}")
        violations = []

    acc_metrics  = compute_accuracy(violations)
    time_metrics = compute_inference_stats(violations)

    return {**acc_metrics, 'inferenceTime': time_metrics}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Compute model evaluation metrics')
    parser.add_argument('--db', default='traffic_violations.db', help='Path to SQLite DB')
    args = parser.parse_args()

    metrics = compute_full_metrics(args.db)
    print(json.dumps(metrics, indent=2))
