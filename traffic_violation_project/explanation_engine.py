"""
explanation_engine.py - AI Explainability Module
"""

import logging
import random
from typing import Dict, List

logger = logging.getLogger(__name__)


class ExplanationEngine:
    """
    Generate human-readable explanations for AI decisions
    """

    def __init__(self):
        self.templates = {
            'NO_HELMET': [
                "Helmet was not detected on the rider with {conf:.1f}% confidence.",
                "The system could not find a helmet in the upper body region of the rider.",
                "Rider's head area showed no helmet with {conf:.1f}% certainty."
            ],
            'NO_SEATBELT': [
                "No seatbelt detected in the driver region with {conf:.1f}% confidence.",
                "The driver area of the vehicle showed no seatbelt presence.",
                "Seatbelt was not visible in the driver's region with {conf:.1f}% certainty."
            ],
            'TRIPLE_RIDING': [
                "{count} riders detected on a single vehicle, exceeding the legal limit of 2.",
                "Multiple riders ({count}) found on the same vehicle, indicating triple riding.",
                "The vehicle has {count} riders, which violates the maximum of 2 riders per vehicle."
            ],
            'RED_LIGHT': [
                "Vehicle crossed the stop line while the signal was red with {conf:.1f}% confidence.",
                "The vehicle proceeded through the intersection despite a red signal.",
                "Red light violation detected - vehicle crossed during red phase."
            ],
            'WRONG_SIDE': [
                "Vehicle detected driving on the wrong side of the road with {conf:.1f}% confidence.",
                "The vehicle is traveling against the designated traffic flow direction.",
                "Wrong-way driving detected in the opposite lane."
            ],
            'STOP_LINE': [
                "Vehicle crossed the stop line without stopping with {conf:.1f}% confidence.",
                "The vehicle failed to stop at the designated stop line.",
                "Stop line violation - vehicle continued past the stop line."
            ],
            'ILLEGAL_PARKING': [
                "Vehicle parked in a no-parking zone with {conf:.1f}% confidence.",
                "The vehicle is illegally parked in a restricted area.",
                "No-parking zone violation detected."
            ]
        }

    def generate_explanation(self, violation_type: str, confidence: float,
                             extra_data: Dict = None) -> str:
        """
        Generate human-readable explanation for a violation
        """
        normalized_type = violation_type.upper().replace(' ', '_')
        templates = self.templates.get(normalized_type, [
            f"Violation detected with {confidence * 100:.1f}% confidence."
        ])

        template = random.choice(templates)

        explanation = template.format(
            conf=confidence * 100,
            count=extra_data.get('count', 'multiple') if extra_data else 'multiple'
        )

        if confidence > 0.85:
            reasoning = "This is a high-confidence detection with strong evidence."
        elif confidence > 0.65:
            reasoning = "This detection has moderate confidence and may benefit from review."
        else:
            reasoning = "This is a low-confidence detection that requires human verification."

        return f"{explanation} {reasoning}"

    def generate_summary(self, violations: List[Dict]) -> str:
        """
        Generate summary of all violations
        """
        if not violations:
            return "No violations detected in this image."

        total = len(violations)
        types = {}
        for v in violations:
            vtype = v.get('type', v.get('violation_type', 'unknown'))
            types[vtype] = types.get(vtype, 0) + 1

        summary = f"Today, {total} violations were detected. "
        type_summary_parts = []
        for name, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
            type_summary_parts.append(
                f"{name.replace('_', ' ').title()} violations were highest ({count})"
            )
        summary += ". ".join(type_summary_parts[:3])

        return summary + "."

    def generate_explanations_for_violations(self, violations: List[Dict]) -> List[Dict]:
        """
        Generate explanations for a list of violations
        """
        results = []
        for v in violations:
            vtype = v.get('type', v.get('violation_type', 'unknown'))
            confidence = v.get('confidence', 0.0)

            explanation = self.generate_explanation(vtype, confidence, v)
            v['explanation'] = explanation
            results.append(v)

        return results
