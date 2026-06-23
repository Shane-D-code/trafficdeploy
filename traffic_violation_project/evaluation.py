import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np
from ultralytics import YOLO


class ModelEvaluator:
    def __init__(self, model_path="models/traffic_violation_best.pt"):
        self.model = YOLO(model_path)
        self.class_names = self.model.names
        self.metrics = {}

    def compute_iou(self, box1: List[float], box2: List[float]) -> float:
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection
        return intersection / union if union > 0 else 0

    def compute_precision_recall(
        self, predictions: List, ground_truths: List, iou_threshold: float = 0.5
    ) -> Tuple[float, float, float]:
        if not ground_truths:
            return 1.0, 0.0, 0.0
        if not predictions:
            return 0.0, 0.0, 0.0

        predictions = sorted(predictions, key=lambda x: x["confidence"], reverse=True)
        tp = 0
        fp = 0
        matched_gt = [False] * len(ground_truths)

        for pred in predictions:
            best_iou = 0
            best_idx = -1
            for idx, gt in enumerate(ground_truths):
                if matched_gt[idx]:
                    continue
                iou = self.compute_iou(pred["bbox"], gt["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_idx = idx

            if best_iou >= iou_threshold and best_idx != -1:
                tp += 1
                matched_gt[best_idx] = True
            else:
                fp += 1

        fn = len(ground_truths) - tp
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0
        )
        return precision, recall, f1

    def compute_ap(
        self, predictions: List, ground_truths: List, iou_threshold: float = 0.5
    ) -> float:
        if not ground_truths or not predictions:
            return 0.0

        predictions = sorted(predictions, key=lambda x: x["confidence"], reverse=True)
        matched_gt = [False] * len(ground_truths)
        tp_fp = []

        for pred in predictions:
            best_iou = 0
            best_idx = -1
            for idx, gt in enumerate(ground_truths):
                if matched_gt[idx]:
                    continue
                iou = self.compute_iou(pred["bbox"], gt["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_idx = idx

            if best_iou >= iou_threshold and best_idx != -1:
                tp_fp.append((1, pred["confidence"]))
                matched_gt[best_idx] = True
            else:
                tp_fp.append((0, pred["confidence"]))

        tp_fp.sort(key=lambda x: x[1], reverse=True)
        cum_tp = 0
        cum_fp = 0
        precisions = []
        recalls = []
        total_gt = len(ground_truths)

        for is_tp, _ in tp_fp:
            if is_tp:
                cum_tp += 1
            else:
                cum_fp += 1
            prec = cum_tp / (cum_tp + cum_fp) if (cum_tp + cum_fp) > 0 else 0
            rec = cum_tp / total_gt if total_gt > 0 else 0
            precisions.append(prec)
            recalls.append(rec)

        if len(precisions) <= 1:
            return precisions[0] if precisions else 0.0

        ap = 0
        for i in range(len(precisions) - 1):
            ap += precisions[i + 1] * (recalls[i + 1] - recalls[i])
        return ap

    def evaluate(
        self,
        test_images: List[str],
        annotations: Dict = None,
        iou_threshold: float = 0.5,
        conf_threshold: float = 0.25,
    ) -> Dict:
        all_predictions = defaultdict(list)
        all_ground_truths = defaultdict(list)

        for img_path in test_images:
            if not os.path.exists(img_path):
                continue

            results = self.model(img_path, conf=conf_threshold, verbose=False)
            if len(results) == 0:
                continue
            result = results[0]
            boxes = result.boxes
            if boxes is not None:
                for i in range(len(boxes)):
                    cls_id = int(boxes.cls[i].item())
                    class_name = self.class_names.get(cls_id, f"class_{cls_id}")
                    all_predictions[class_name].append(
                        {
                            "bbox": boxes.xyxy[i].tolist(),
                            "confidence": float(boxes.conf[i].item()),
                        }
                    )

        if annotations:
            for img_id, anns in annotations.items():
                for ann in anns:
                    class_name = self.class_names.get(
                        ann.get("category_id", 0), "unknown"
                    )
                    all_ground_truths[class_name].append(
                        {"bbox": ann["bbox"], "confidence": 1.0}
                    )

        per_class = {}
        total_precision = 0
        total_recall = 0
        total_f1 = 0
        total_ap = 0
        num_classes = 0

        for cls_name in self.class_names.values():
            preds = all_predictions[cls_name]
            gts = all_ground_truths[cls_name]

            precision, recall, f1 = self.compute_precision_recall(
                preds, gts, iou_threshold
            )
            ap = self.compute_ap(preds, gts, iou_threshold)

            per_class[cls_name] = {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "ap": round(ap, 4),
                "predictions": len(preds),
                "ground_truths": len(gts),
            }

            total_precision += precision
            total_recall += recall
            total_f1 += f1
            total_ap += ap
            num_classes += 1

        n = num_classes if num_classes > 0 else 1

        self.metrics = {
            "per_class": per_class,
            "macro_precision": round(total_precision / n, 4),
            "macro_recall": round(total_recall / n, 4),
            "macro_f1": round(total_f1 / n, 4),
            "mAP": round(total_ap / n, 4),
            "iou_threshold": iou_threshold,
            "conf_threshold": conf_threshold,
            "total_images": len(test_images),
            "timestamp": datetime.now().isoformat(),
        }
        return self.metrics

    def summary(self) -> Dict:
        return self.metrics

    def export_report(self, output_path="model_audit_report.md") -> str:
        m = self.metrics
        lines = [
            "# Model Audit Report",
            "",
            f"**Generated:** {m.get('timestamp', datetime.now().isoformat())}",
            f"**Model:** models/traffic_violation_best.pt",
            "",
            "## Summary",
            "",
            f"- **mAP**: {m.get('mAP', 'N/A')}",
            f"- **Macro Precision**: {m.get('macro_precision', 'N/A')}",
            f"- **Macro Recall**: {m.get('macro_recall', 'N/A')}",
            f"- **Macro F1-Score**: {m.get('macro_f1', 'N/A')}",
            f"- **IoU Threshold**: {m.get('iou_threshold', 0.5)}",
            f"- **Confidence Threshold**: {m.get('conf_threshold', 0.25)}",
            f"- **Total Images Evaluated**: {m.get('total_images', 0)}",
            "",
            "## Per-Class Metrics",
            "",
            "| Class | Precision | Recall | F1-Score | AP | Predictions | Ground Truths |",
            "|-------|-----------|--------|----------|----|-------------|---------------|",
        ]
        for cls_name, cm in sorted(m.get("per_class", {}).items()):
            lines.append(
                f"| {cls_name} | {cm['precision']} | {cm['recall']} | {cm['f1']} | {cm['ap']} | {cm['predictions']} | {cm['ground_truths']} |"
            )
        lines.extend(
            [
                "",
                "## Notes",
                "",
                "- **mAP > 0.8** is considered excellent",
                "- **Precision** = TP / (TP + FP) — lower false positives",
                "- **Recall** = TP / (TP + FN) — fewer missed detections",
                "- **F1-Score** = 2 * (P * R) / (P + R) — harmonic mean",
                "- **AP** = Average Precision per class (area under PR curve)",
                "",
            ]
        )
        with open(output_path, "w") as f:
            f.write("\n".join(lines))
        return output_path


if __name__ == "__main__":
    evaluator = ModelEvaluator()
    test_images = []
    for ext in ["*.jpg", "*.jpeg", "*.png"]:
        test_images.extend([str(p) for p in Path(".").glob(ext)])
    for ext in ["*.jpg", "*.jpeg", "*.png"]:
        test_images.extend([str(p) for p in Path(".").glob(f"**/{ext}")])
    if not test_images:
        print("No test images found. Creating a synthetic test image.")
        dummy = np.ones((640, 640, 3), dtype=np.uint8) * 128
        cv2.imwrite("_eval_test.jpg", dummy)
        test_images = ["_eval_test.jpg"]

    print(f"Evaluating on {len(test_images)} images...")
    metrics = evaluator.evaluate(test_images, conf_threshold=0.25)
    report_path = evaluator.export_report()
    print(f"Report saved to {report_path}")
    print(json.dumps(metrics, indent=2))

    if os.path.exists("_eval_test.jpg"):
        os.unlink("_eval_test.jpg")
