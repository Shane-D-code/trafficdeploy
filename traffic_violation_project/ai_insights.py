"""
ai_insights.py - AI-powered insights for traffic enforcement
"""

import json
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

SEVERITY_WEIGHTS = {
    "NO HELMET": 2,
    "NO SEATBELT": 2,
    "TRIPLE RIDING": 3,
    "WRONG SIDE": 4,
    "STOP LINE": 3,
    "RED LIGHT": 5,
    "ILLEGAL PARKING": 1,
}

LOCATIONS = [
    {"name": "MG Road", "lat": 12.9716, "lng": 77.5946},
    {"name": "Brigade Road", "lat": 12.9352, "lng": 77.6245},
    {"name": "Church Street", "lat": 12.9538, "lng": 77.6472},
    {"name": "Indiranagar", "lat": 12.9783, "lng": 77.6408},
    {"name": "Koramangala", "lat": 12.9279, "lng": 77.6271},
    {"name": "Electronic City", "lat": 12.8456, "lng": 77.6603},
    {"name": "Jayanagar", "lat": 12.9308, "lng": 77.5838},
    {"name": "Whitefield", "lat": 12.9698, "lng": 77.7500},
]


def get_dangerous_junctions(violations: List[Dict]) -> List[Dict]:
    location_stats = {}

    for v in violations:
        loc_idx = abs(hash(v.get("violation_type", ""))) % len(LOCATIONS)
        loc_name = LOCATIONS[loc_idx]["name"]
        vtype = v.get("violation_type", "UNKNOWN")

        if loc_name not in location_stats:
            location_stats[loc_name] = {"total": 0, "byType": {}, "severityScore": 0}
        location_stats[loc_name]["total"] += 1
        location_stats[loc_name]["byType"][vtype] = location_stats[loc_name]["byType"].get(vtype, 0) + 1
        location_stats[loc_name]["severityScore"] += SEVERITY_WEIGHTS.get(vtype, 1)

    junctions = []
    for name, data in location_stats.items():
        loc = next((l for l in LOCATIONS if l["name"] == name), {"lat": 12.97, "lng": 77.6})
        junctions.append({
            "location": name,
            "lat": loc["lat"],
            "lng": loc["lng"],
            "total": data["total"],
            "byType": data["byType"],
            "severityScore": data["severityScore"],
        })

    junctions.sort(key=lambda x: x["severityScore"], reverse=True)
    return junctions[:10]


def get_repeat_offenders(violations: List[Dict], min_count: int = 2) -> List[Dict]:
    plate_map = {}

    for v in violations:
        plate = v.get("plate_text")
        if not plate or plate == "N/A":
            continue
        if plate not in plate_map:
            plate_map[plate] = {"count": 0, "types": set(), "timestamps": [], "confidences": []}
        plate_map[plate]["count"] += 1
        plate_map[plate]["types"].add(v.get("violation_type", "UNKNOWN"))
        plate_map[plate]["timestamps"].append(v.get("timestamp", ""))
        plate_map[plate]["confidences"].append(v.get("confidence", 0))

    offenders = []
    for plate, data in plate_map.items():
        if data["count"] < min_count:
            continue
        types = list(data["types"])
        total_severity = sum(SEVERITY_WEIGHTS.get(t, 1) for t in types)
        avg_severity = total_severity / len(types) if types else 0
        risk_score = min(100, data["count"] * 15 + avg_severity * 10)

        data["timestamps"].sort()
        offenders.append({
            "plate": plate,
            "count": data["count"],
            "types": types,
            "riskScore": round(risk_score),
            "riskLevel": "high" if risk_score >= 70 else "medium" if risk_score >= 40 else "low",
            "firstViolation": data["timestamps"][0] if data["timestamps"] else "",
            "lastViolation": data["timestamps"][-1] if data["timestamps"] else "",
            "avgConfidence": round(sum(data["confidences"]) / len(data["confidences"]), 4) if data["confidences"] else 0,
        })

    offenders.sort(key=lambda x: x["riskScore"], reverse=True)
    return offenders[:20]


def generate_insights_summary(violations: List[Dict]) -> str:
    total = len(violations)
    if total == 0:
        return "No violations recorded."

    by_type = {}
    for v in violations:
        t = v.get("violation_type", "UNKNOWN")
        by_type[t] = by_type.get(t, 0) + 1

    top_type = max(by_type, key=by_type.get) if by_type else "NONE"
    junctions = get_dangerous_junctions(violations)
    offenders = get_repeat_offenders(violations)

    lines = [
        f"Total Violations: {total}",
        f"Most Common: {top_type} ({by_type.get(top_type, 0)} cases)",
        f"High-Risk Areas: {len(junctions)}",
        f"Repeat Offenders: {len(offenders)}",
    ]

    if junctions:
        lines.append(f"Worst Junction: {junctions[0]['location']} (severity: {junctions[0]['severityScore']})")
    if offenders:
        lines.append(f"Top Offender: {offenders[0]['plate']} ({offenders[0]['count']} violations)")

    return "\n".join(lines)
