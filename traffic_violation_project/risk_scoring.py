"""
risk_scoring.py - Driver Risk Score Calculator
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List

logger = logging.getLogger(__name__)


class RiskScorer:
    """
    Calculate driver risk scores and identify repeat offenders
    """

    def __init__(self, db_path: str = 'traffic_violations.db'):
        self.db_path = db_path
        self.severity_weights = {
            'NO_HELMET': 2,
            'NO_SEATBELT': 2,
            'TRIPLE_RIDING': 3,
            'WRONG_SIDE': 4,
            'STOP_LINE': 3,
            'RED_LIGHT': 5,
            'ILLEGAL_PARKING': 1
        }

    def get_driver_history(self, license_plate: str) -> List[Dict]:
        """
        Get all violations for a driver/plate
        """
        from utils import search_violations_by_plate
        return search_violations_by_plate(license_plate, self.db_path)

    def calculate_risk_score(self, license_plate: str) -> Dict:
        """
        Calculate risk score for a driver
        """
        history = self.get_driver_history(license_plate)

        if not history:
            return {
                'score': 0,
                'level': 'A',
                'total_violations': 0,
                'recent_violations': 0,
                'severity_score': 0,
                'recommendation': 'No violations on record.'
            }

        total = len(history)
        now = datetime.now()
        recent = len([
            v for v in history
            if datetime.fromisoformat(v['timestamp'].replace('Z', '+00:00')) > now - timedelta(days=30)
        ])

        severity_score = sum([
            self.severity_weights.get(v['violation_type'], 1)
            for v in history
        ])

        base_score = min(severity_score / 10, 50)
        recent_penalty = min(recent * 5, 30)
        total_penalty = min(total * 2, 20)

        final_score = base_score + recent_penalty + total_penalty
        final_score = min(100, final_score)

        if final_score < 20:
            level = 'A'
        elif final_score < 40:
            level = 'B'
        elif final_score < 60:
            level = 'C'
        elif final_score < 80:
            level = 'D'
        else:
            level = 'F'

        return {
            'score': final_score,
            'level': level,
            'total_violations': total,
            'recent_violations': recent,
            'severity_score': severity_score,
            'recommendation': self._get_recommendation(level, final_score)
        }

    def _get_recommendation(self, level: str, score: float) -> str:
        """Generate recommendation based on risk level"""
        recommendations = {
            'A': "Safe driver. Continue maintaining good driving habits.",
            'B': "Minor violations observed. Consider defensive driving course.",
            'C': "Moderate risk driver. Required to attend traffic safety workshop.",
            'D': "High risk driver. Consider license suspension review.",
            'F': "Extreme risk driver. Immediate license suspension recommended."
        }
        return recommendations.get(level, "Review required.")

    def identify_repeat_offenders(self, threshold: int = 5) -> List[Dict]:
        """
        Identify repeat offenders with violations above threshold
        """
        from utils import get_all_violations

        violations = get_all_violations(db_path=self.db_path)

        plate_counts = {}
        plate_details = {}

        for v in violations:
            plate = v.get('plate_text')
            if not plate:
                continue

            if plate not in plate_counts:
                plate_counts[plate] = 0
                plate_details[plate] = []

            plate_counts[plate] += 1
            plate_details[plate].append(v)

        repeat_offenders = []
        for plate, count in plate_counts.items():
            if count >= threshold:
                risk = self.calculate_risk_score(plate)
                last_v = max(plate_details[plate], key=lambda x: x.get('timestamp', ''))
                repeat_offenders.append({
                    'plate': plate,
                    'violation_count': count,
                    'risk_score': risk['score'],
                    'risk_level': risk['level'],
                    'recent_violations': risk['recent_violations'],
                    'last_violation': last_v.get('timestamp', '')
                })

        return sorted(repeat_offenders, key=lambda x: x['violation_count'], reverse=True)
