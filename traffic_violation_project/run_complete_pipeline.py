"""
run_complete_pipeline.py - End-to-End Pipeline for Traffic Violation Detection

Integrates all modules:
  - Detection (violation_detector)
  - Preprocessing (preprocessing_pipeline)
  - Review (review_system)
  - GIS Analytics (gis_integration)
  - AI Insights (ai_insights)
  - Risk Scoring (risk_scoring)
  - Evidence Generation (evidence_generator)
  - Evaluation (evaluation, evaluation_metrics)
  - Reporting (report_generator)
"""

import argparse
import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(f'pipeline_{datetime.now().strftime("%Y%m%d")}.log')
    ]
)
logger = logging.getLogger('pipeline')


class PipelineResult:
    def __init__(self):
        self.start_time = datetime.now()
        self.stages = {}
        self.errors = []
        self.output_dir = None

    def add_stage(self, name: str, status: str, data: any = None, duration: float = 0):
        self.stages[name] = {
            'status': status,
            'data': data,
            'duration': round(duration, 2),
        }

    def add_error(self, stage: str, message: str):
        self.errors.append({'stage': stage, 'message': str(message)})
        logger.error(f"[{stage}] {message}")

    def summary(self) -> Dict:
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return {
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'total_duration': round(elapsed, 2),
            'stages': self.stages,
            'errors': self.errors,
            'success': len(self.errors) == 0,
            'output_dir': self.output_dir,
        }


class TrafficPipeline:
    """
    End-to-end pipeline tying together all system modules
    """

    def __init__(self, db_path: str = 'traffic_violations.db', output_dir: str = 'pipeline_output'):
        self.db_path = db_path
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.result = PipelineResult()
        self.result.output_dir = output_dir

    def run_detection(self, image_path: str, conf_threshold: float = 0.25,
                      enable_preprocessing: bool = True) -> List[Dict]:
        start = datetime.now()
        try:
            from violation_detector import ViolationDetector
            detector = ViolationDetector()
            violations, detections = detector.detect_violations(
                image_path, confidence_threshold=conf_threshold,
                enable_preprocessing=enable_preprocessing
            )
            duration = (datetime.now() - start).total_seconds()
            self.result.add_stage('detection', 'ok', {
                'violations': len(violations),
                'detections': len(detections),
                'image': image_path,
            }, duration)
            logger.info(f"Detection: {len(violations)} violations, {len(detections)} detections in {duration:.2f}s")
            return violations
        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            self.result.add_error('detection', str(e))
            return []

    def save_violations(self, violations: List[Dict]) -> List[int]:
        start = datetime.now()
        saved_ids = []
        try:
            from utils import ensure_dirs, save_evidence, save_violation
            import cv2

            dirs = ensure_dirs()
            for v in violations:
                vtype = v.get('type', v.get('violation_type', 'UNKNOWN'))
                confidence = v.get('confidence', 0.0)
                plate = v.get('plate_text')
                vid = save_violation(
                    v_type=vtype,
                    plate=plate,
                    confidence=confidence,
                    location=v.get('location', 'Bangalore'),
                    db_path=self.db_path,
                )
                saved_ids.append(vid)

            duration = (datetime.now() - start).total_seconds()
            self.result.add_stage('save', 'ok', {'saved': len(saved_ids)}, duration)
            logger.info(f"Saved {len(saved_ids)} violations to database")
            return saved_ids
        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            self.result.add_error('save', str(e))
            return []

    def generate_evidence(self, violations: List[Dict], image_path: Optional[str] = None) -> List[str]:
        start = datetime.now()
        paths = []
        try:
            from evidence_generator import EvidenceGenerator
            import cv2

            eg = EvidenceGenerator(output_dir=os.path.join(self.output_dir, 'evidence'))

            for v in violations:
                if image_path and os.path.exists(image_path):
                    img = cv2.imread(image_path)
                    if img is not None:
                        card_path = eg.generate_evidence_card(img, v)
                        paths.append(card_path)

            challan_dir = os.path.join(self.output_dir, 'challans')
            for v in violations:
                challan_path = eg.generate_challan(v, output_dir=challan_dir)
                if challan_path:
                    paths.append(challan_path)

            duration = (datetime.now() - start).total_seconds()
            self.result.add_stage('evidence', 'ok', {'generated': len(paths)}, duration)
            logger.info(f"Generated {len(paths)} evidence items")
            return paths
        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            self.result.add_error('evidence', str(e))
            return []

    def run_review_workflow(self, officer_id: str = 'SYSTEM') -> Dict:
        start = datetime.now()
        try:
            from review_system import ReviewSystem
            rs = ReviewSystem(db_path=self.db_path)

            pending = rs.get_pending_reviews()
            stats = rs.get_review_stats()

            auto_approved = 0
            for review in pending:
                confidence = review.get('confidence', 0)
                if confidence > 0.85:
                    if rs.approve_violation(review['id'], officer_id,
                                            f"Auto-approved (confidence: {confidence:.2f})"):
                        auto_approved += 1

            updated_stats = rs.get_review_stats()

            duration = (datetime.now() - start).total_seconds()
            self.result.add_stage('review', 'ok', {
                'pending': len(pending),
                'auto_approved': auto_approved,
                'stats': updated_stats,
            }, duration)
            logger.info(f"Review: {len(pending)} pending, {auto_approved} auto-approved")
            return updated_stats
        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            self.result.add_error('review', str(e))
            return {}

    def run_gis_analysis(self) -> Dict:
        start = datetime.now()
        try:
            from gis_integration import GISIntegration
            gis = GISIntegration(db_path=self.db_path)

            heatmap = gis.generate_heatmap_data()
            hotspots = gis.get_hotspots(threshold=5)
            geojson = gis.generate_geojson()
            routes = gis.generate_route_recommendations()

            geojson_path = os.path.join(self.output_dir, 'violations.geojson')
            with open(geojson_path, 'w') as f:
                f.write(geojson)

            report = {
                'heatmap_points': heatmap.get('total_points', 0),
                'total_violations': heatmap.get('total_violations', 0),
                'hotspots': len(hotspots),
                'routes': routes.get('total_areas', 0),
                'geojson_path': geojson_path,
            }

            duration = (datetime.now() - start).total_seconds()
            self.result.add_stage('gis', 'ok', report, duration)
            logger.info(f"GIS: {report['heatmap_points']} heatmap points, {report['hotspots']} hotspots")
            return report
        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            self.result.add_error('gis', str(e))
            return {}

    def run_ai_insights(self) -> Dict:
        start = datetime.now()
        try:
            from ai_insights import AIInsights
            ai = AIInsights(db_path=self.db_path)

            trends = ai.predict_trends(days_ahead=7)
            anomalies = ai.detect_anomalies()
            peak = ai.peak_hour_analysis()
            report = ai.generate_insight_report()

            report_path = os.path.join(self.output_dir, 'insights_report.json')
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)

            summary = {
                'anomalies': len(anomalies),
                'peak_period': peak.get('peak_period', 'N/A') if 'error' not in peak else 'N/A',
                'trending_types': len(trends.get('predictions', {})) if 'error' not in trends else 0,
                'report_path': report_path,
            }

            duration = (datetime.now() - start).total_seconds()
            self.result.add_stage('ai_insights', 'ok', summary, duration)
            logger.info(f"AI Insights: {summary['anomalies']} anomalies, peak: {summary['peak_period']}")
            return summary
        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            self.result.add_error('ai_insights', str(e))
            return {}

    def run_risk_scoring(self) -> Dict:
        start = datetime.now()
        try:
            from risk_scoring import RiskScorer
            rs = RiskScorer(db_path=self.db_path)

            repeat_offenders = rs.identify_repeat_offenders(threshold=3)

            profiles = {}
            for offender in repeat_offenders[:10]:
                score = rs.calculate_risk_score(offender['plate'])
                profiles[offender['plate']] = score

            report = {
                'repeat_offenders': len(repeat_offenders),
                'top_offenders': repeat_offenders[:5] if repeat_offenders else [],
                'profiles': profiles,
            }

            duration = (datetime.now() - start).total_seconds()
            self.result.add_stage('risk_scoring', 'ok', report, duration)
            logger.info(f"Risk Scoring: {report['repeat_offenders']} repeat offenders")
            return report
        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            self.result.add_error('risk_scoring', str(e))
            return {}

    def run_evaluation(self) -> Dict:
        start = datetime.now()
        try:
            from evaluation import ModelEvaluator
            from pathlib import Path as PPath

            evaluator = ModelEvaluator()
            test_images = []
            for ext in ['*.jpg', '*.jpeg', '*.png']:
                test_images.extend([str(p) for p in PPath('.').glob(ext)])
                test_images.extend([str(p) for p in PPath('.').glob(f'**/{ext}')])

            metrics = {}
            if test_images:
                metrics = evaluator.evaluate(test_images, conf_threshold=0.25)
                report_path = evaluator.export_report(
                    os.path.join(self.output_dir, 'model_audit_report.md')
                )
                metrics['report_path'] = report_path

            duration = (datetime.now() - start).total_seconds()
            self.result.add_stage('evaluation', 'ok', {
                'test_images': len(test_images),
                'mAP': metrics.get('mAP', 'N/A'),
            }, duration)
            logger.info(f"Evaluation: {len(test_images)} images tested")
            return metrics
        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            self.result.add_error('evaluation', str(e))
            return {}

    def generate_summary_report(self) -> str:
        start = datetime.now()
        try:
            summary = self.result.summary()
            report_path = os.path.join(self.output_dir, 'pipeline_summary.json')
            with open(report_path, 'w') as f:
                json.dump(summary, f, indent=2)

            md_path = os.path.join(self.output_dir, 'pipeline_summary.md')
            with open(md_path, 'w') as f:
                f.write(f"# Pipeline Execution Summary\n\n")
                f.write(f"**Start:** {summary['start_time']}\n")
                f.write(f"**End:** {summary['end_time']}\n")
                f.write(f"**Duration:** {summary['total_duration']}s\n")
                f.write(f"**Status:** {'✅ Success' if summary['success'] else '❌ Failed'}\n\n")
                f.write(f"## Stages\n\n")
                f.write("| Stage | Status | Duration |\n")
                f.write("|-------|--------|----------|\n")
                for name, stage in summary['stages'].items():
                    f.write(f"| {name} | {stage['status']} | {stage['duration']}s |\n")

                if summary['errors']:
                    f.write(f"\n## Errors\n\n")
                    for err in summary['errors']:
                        f.write(f"- **{err['stage']}**: {err['message']}\n")

                f.write(f"\n## Output Directory\n\n")
                f.write(f"`{summary['output_dir']}`\n")

            self.result.add_stage('summary_report', 'ok', {'path': md_path},
                                   (datetime.now() - start).total_seconds())
            logger.info(f"Summary report: {md_path}")
            return md_path
        except Exception as e:
            self.result.add_error('summary_report', str(e))
            return ''

    def run_all(self, image_path: Optional[str] = None) -> PipelineResult:
        logger.info("=" * 60)
        logger.info("Starting Complete Pipeline")
        logger.info("=" * 60)

        if image_path and os.path.exists(image_path):
            violations = self.run_detection(image_path)
            if violations:
                self.save_violations(violations)
                self.generate_evidence(violations, image_path)

        self.run_review_workflow()
        self.run_gis_analysis()
        self.run_ai_insights()
        self.run_risk_scoring()
        self.run_evaluation()
        self.generate_summary_report()

        summary = self.result.summary()
        logger.info("=" * 60)
        logger.info(f"Pipeline Complete: {summary['total_duration']}s")
        logger.info(f"Output: {self.output_dir}")
        logger.info(f"Errors: {len(summary['errors'])}")
        logger.info("=" * 60)

        return self.result


def main():
    parser = argparse.ArgumentParser(
        description='Traffic Violation Detection - Complete Pipeline'
    )
    parser.add_argument('--image', type=str, help='Image file to process')
    parser.add_argument('--db', type=str, default='traffic_violations.db',
                        help='Database path')
    parser.add_argument('--output', type=str, default='pipeline_output',
                        help='Output directory')
    parser.add_argument('--conf-threshold', type=float, default=0.25,
                        help='Detection confidence threshold')
    parser.add_argument('--no-preprocess', action='store_true',
                        help='Disable image preprocessing')
    parser.add_argument('--skip-detection', action='store_true',
                        help='Skip detection stage')
    parser.add_argument('--stages', type=str, nargs='*',
                        choices=['detection', 'review', 'gis', 'insights', 'risk', 'evaluation'],
                        help='Run specific stages only')
    parser.add_argument('--json-output', action='store_true',
                        help='Output results as JSON')

    args = parser.parse_args()

    pipeline = TrafficPipeline(db_path=args.db, output_dir=args.output)

    if args.stages:
        if 'detection' in args.stages and args.image and os.path.exists(args.image):
            violations = pipeline.run_detection(
                args.image, args.conf_threshold, not args.no_preprocess
            )
            if violations:
                pipeline.save_violations(violations)
                pipeline.generate_evidence(violations, args.image)
        if 'review' in args.stages:
            pipeline.run_review_workflow()
        if 'gis' in args.stages:
            pipeline.run_gis_analysis()
        if 'insights' in args.stages:
            pipeline.run_ai_insights()
        if 'risk' in args.stages:
            pipeline.run_risk_scoring()
        if 'evaluation' in args.stages:
            pipeline.run_evaluation()
    else:
        pipeline.run_all(
            image_path=args.image if args.image and os.path.exists(args.image) else None
        )

    pipeline.generate_summary_report()
    result = pipeline.result.summary()

    if args.json_output:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
