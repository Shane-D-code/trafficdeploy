"""
ai_summary.py - AI-powered Summary Generator
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List

logger = logging.getLogger(__name__)


class AISummaryGenerator:
    """
    Generate AI-powered summaries and insights
    """

    def __init__(self, db_path: str = 'traffic_violations.db'):
        self.db_path = db_path

    def generate_daily_summary(self, date: str = None) -> Dict:
        """
        Generate a daily summary report
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        from utils import get_all_violations
        violations = get_all_violations(db_path=self.db_path)

        daily = [
            v for v in violations
            if v['timestamp'].startswith(date)
        ]

        return self._generate_summary(daily, f"Daily Summary - {date}")

    def generate_weekly_summary(self) -> Dict:
        """
        Generate a weekly summary report
        """
        week_ago = datetime.now() - timedelta(days=7)

        from utils import get_all_violations
        violations = get_all_violations(db_path=self.db_path)

        weekly = [
            v for v in violations
            if datetime.fromisoformat(v['timestamp'].replace('Z', '+00:00')) > week_ago
        ]

        return self._generate_summary(weekly, f"Weekly Summary - {datetime.now().strftime('%b %d')}")

    def _generate_summary(self, violations: List[Dict], title: str) -> Dict:
        """
        Generate summary from violations list
        """
        total = len(violations)

        by_type = {}
        for v in violations:
            vtype = v.get('violation_type', 'unknown')
            by_type[vtype] = by_type.get(vtype, 0) + 1

        most_common = max(by_type.items(), key=lambda x: x[1]) if by_type else ('None', 0)

        plates = set([v.get('plate_text') for v in violations if v.get('plate_text')])

        confidences = [v.get('confidence', 0) for v in violations]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        summary_text = f"{title}. "
        summary_text += f"Total vehicles processed: {total}. "

        if total > 0:
            summary_text += f"Violations detected: {total}. "
            summary_text += f"{most_common[0].replace('_', ' ').title()} violations were the most common ({most_common[1]}). "
            summary_text += f"Average detection confidence: {avg_confidence * 100:.1f}%. "
            summary_text += f"Unique license plates identified: {len(plates)}."
        else:
            summary_text += "No violations detected."

        insights = self._generate_insights(violations)

        return {
            'title': title,
            'summary': summary_text,
            'total': total,
            'by_type': by_type,
            'most_common': most_common,
            'unique_plates': len(plates),
            'avg_confidence': avg_confidence,
            'insights': insights
        }

    def _generate_insights(self, violations: List[Dict]) -> List[str]:
        """
        Generate actionable insights
        """
        insights = []

        if not violations:
            return ["No violations to analyze."]

        hours = {}
        for v in violations:
            try:
                hour = datetime.fromisoformat(v['timestamp'].replace('Z', '+00:00')).hour
                hours[hour] = hours.get(hour, 0) + 1
            except Exception:
                continue

        if hours:
            peak_hour = max(hours.items(), key=lambda x: x[1])
            insights.append(
                f"Peak violation hour: {peak_hour[0]}:00-{peak_hour[0] + 1}:00 ({peak_hour[1]} violations)"
            )

        by_type = {}
        for v in violations:
            vtype = v.get('violation_type', 'unknown')
            by_type[vtype] = by_type.get(vtype, 0) + 1

        if by_type.get('NO_HELMET', 0) > 10:
            insights.append("Recommendation: Increased helmet enforcement at high-risk areas")

        if by_type.get('NO_SEATBELT', 0) > 5:
            insights.append("Recommendation: Seatbelt awareness campaign needed")

        if by_type.get('RED_LIGHT', 0) > 5:
            insights.append("Recommendation: Additional signal monitoring at peak hours")

        if by_type.get('TRIPLE_RIDING', 0) > 5:
            insights.append("Recommendation: Targeted enforcement against triple riding")

        return insights[:5]

    def generate_ai_report(self) -> str:
        """
        Generate a complete AI report in markdown
        """
        daily = self.generate_daily_summary()
        weekly = self.generate_weekly_summary()

        report = f"""
# AI Traffic Violation Report

## {daily['title']}
{daily['summary']}

### Breakdown by Type
"""
        for vtype, count in sorted(daily['by_type'].items(), key=lambda x: x[1], reverse=True):
            report += f"- {vtype.replace('_', ' ').title()}: {count}\n"

        report += f"\n## {weekly['title']}\n{weekly['summary']}\n"

        report += "\n### Insights\n"
        for insight in weekly['insights']:
            report += f"- {insight}\n"

        return report
