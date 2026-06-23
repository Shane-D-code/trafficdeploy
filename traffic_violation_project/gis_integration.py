"""
gis_integration.py - GIS and Heatmap Integration
"""

import json
import math
import random
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class GISIntegration:
    """
    GIS and geospatial analysis for traffic violations
    """

    def __init__(self, db_path: str = 'traffic_violations.db'):
        self.db_path = db_path
        self.city_center = {'lat': 12.9716, 'lng': 77.5946}
        self.city_bounds = {
            'min_lat': 12.85, 'max_lat': 13.10,
            'min_lng': 77.45, 'max_lng': 77.80
        }
        self.hotspots = [
            {'name': 'MG Road', 'lat': 12.9716, 'lng': 77.5946},
            {'name': 'Brigade Road', 'lat': 12.9716, 'lng': 77.5946},
            {'name': 'Church Street', 'lat': 12.9716, 'lng': 77.5946},
            {'name': 'Indiranagar', 'lat': 12.9716, 'lng': 77.5946},
            {'name': 'Koramangala', 'lat': 12.9716, 'lng': 77.5946},
            {'name': 'Electronic City', 'lat': 12.8500, 'lng': 77.6600},
            {'name': 'Whitefield', 'lat': 12.9700, 'lng': 77.7500},
            {'name': 'Jayanagar', 'lat': 12.9300, 'lng': 77.5900},
            {'name': 'Marathahalli', 'lat': 12.9600, 'lng': 77.7000},
            {'name': 'Yeshwanthpur', 'lat': 13.0200, 'lng': 77.5500},
        ]
        self.violation_types = [
            'NO_HELMET', 'NO_SEATBELT', 'RED_LIGHT',
            'WRONG_SIDE', 'TRIPLE_RIDING', 'STOP_LINE', 'ILLEGAL_PARKING'
        ]

    def get_violation_locations(self, start_date: str = None,
                                end_date: str = None) -> List[Dict]:
        """
        Get violation locations from DB or generate sample data
        """
        try:
            from utils import get_all_violations
            violations = get_all_violations(db_path=self.db_path)
            locations = []
            for v in violations:
                base = self._get_nearest_hotspot(v)
                locations.append({
                    'lat': base['lat'] + (random.random() - 0.5) * 0.01,
                    'lng': base['lng'] + (random.random() - 0.5) * 0.01,
                    'type': v.get('violation_type', 'UNKNOWN'),
                    'confidence': v.get('confidence', 0.5),
                    'timestamp': v.get('timestamp', datetime.now().isoformat()),
                    'severity': self._compute_severity(v),
                })
            if not locations:
                return self._generate_sample_locations()
            return locations
        except Exception as e:
            logger.warning(f"Could not load locations from DB: {e}")
            return self._generate_sample_locations()

    def _generate_sample_locations(self) -> List[Dict]:
        locations = []
        for hotspot in self.hotspots:
            for _ in range(random.randint(5, 20)):
                locations.append({
                    'lat': hotspot['lat'] + (random.random() - 0.5) * 0.01,
                    'lng': hotspot['lng'] + (random.random() - 0.5) * 0.01,
                    'type': random.choice(self.violation_types),
                    'confidence': 0.7 + random.random() * 0.3,
                    'timestamp': datetime.now().isoformat(),
                    'severity': random.randint(1, 5),
                })
        return locations

    def _compute_severity(self, violation: Dict) -> int:
        vtype = violation.get('violation_type', '')
        confidence = violation.get('confidence', 0.5)
        base = {
            'RED_LIGHT': 5, 'WRONG_SIDE': 4,
            'TRIPLE_RIDING': 3, 'STOP_LINE': 3,
            'NO_HELMET': 2, 'NO_SEATBELT': 2,
            'ILLEGAL_PARKING': 1
        }.get(vtype, 1)
        conf_bonus = 2 if confidence > 0.85 else (1 if confidence > 0.65 else 0)
        return min(base + conf_bonus, 10)

    def _get_nearest_hotspot(self, violation: Dict) -> Dict:
        vtype = violation.get('violation_type', 'UNKNOWN')
        mapping = {
            'NO_HELMET': 0, 'NO_SEATBELT': 1, 'TRIPLE_RIDING': 2,
            'RED_LIGHT': 3, 'WRONG_SIDE': 4, 'STOP_LINE': 5, 'ILLEGAL_PARKING': 6
        }
        idx = mapping.get(vtype, random.randint(0, len(self.hotspots) - 1))
        return self.hotspots[idx % len(self.hotspots)]

    def generate_heatmap_data(self, violation_locations: List[Dict] = None) -> Dict:
        if violation_locations is None:
            violation_locations = self.get_violation_locations()
        heatmap_data = {}
        for loc in violation_locations:
            key = f"{loc['lat']:.4f}_{loc['lng']:.4f}"
            if key not in heatmap_data:
                heatmap_data[key] = {
                    'lat': loc['lat'], 'lng': loc['lng'],
                    'count': 0, 'types': {}, 'severity_sum': 0
                }
            heatmap_data[key]['count'] += 1
            vtype = loc['type']
            heatmap_data[key]['types'][vtype] = heatmap_data[key]['types'].get(vtype, 0) + 1
            heatmap_data[key]['severity_sum'] += loc.get('severity', 1)
        for key in heatmap_data:
            heatmap_data[key]['avg_severity'] = round(
                heatmap_data[key]['severity_sum'] / heatmap_data[key]['count'], 1
            )
        return {
            'points': list(heatmap_data.values()),
            'total_points': len(heatmap_data),
            'total_violations': len(violation_locations)
        }

    def get_hotspots(self, threshold: int = 10) -> List[Dict]:
        heatmap = self.generate_heatmap_data()
        hotspots = []
        for point in heatmap['points']:
            if point['count'] >= threshold:
                hotspots.append({
                    'lat': point['lat'], 'lng': point['lng'],
                    'count': point['count'],
                    'types': point['types'],
                    'severity': point['avg_severity'],
                })
        return sorted(hotspots, key=lambda x: x['count'], reverse=True)

    def generate_geojson(self, violations: List[Dict] = None) -> str:
        if violations is None:
            violations = self.get_violation_locations()
        features = []
        for v in violations:
            features.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [v.get('lng', 0), v.get('lat', 0)]
                },
                'properties': {
                    'type': v.get('type', 'unknown'),
                    'confidence': v.get('confidence', 0),
                    'timestamp': v.get('timestamp', ''),
                    'severity': v.get('severity', 0)
                }
            })
        return json.dumps({'type': 'FeatureCollection', 'features': features})

    def generate_route_recommendations(self, violations: List[Dict] = None) -> Dict:
        if violations is None:
            violations = self.get_violation_locations()
        areas = {}
        for v in violations:
            area = self._get_area(v.get('lat', 0), v.get('lng', 0))
            if area not in areas:
                areas[area] = {'violations': [], 'count': 0, 'types': {}}
            areas[area]['violations'].append(v)
            areas[area]['count'] += 1
            vtype = v.get('type', 'unknown')
            areas[area]['types'][vtype] = areas[area]['types'].get(vtype, 0) + 1
        recommendations = []
        for area, data in areas.items():
            if data['count'] > 3:
                top_vtype = max(data['types'].items(), key=lambda x: x[1])[0]
                recommendations.append({
                    'area': area,
                    'violation_count': data['count'],
                    'top_violations': sorted(data['types'].items(), key=lambda x: x[1], reverse=True)[:3],
                    'recommendation': self._generate_recommendation(area, top_vtype),
                })
        return {
            'areas': areas,
            'recommendations': sorted(recommendations, key=lambda x: x['violation_count'], reverse=True),
            'total_areas': len(areas)
        }

    def _get_area(self, lat: float, lng: float) -> str:
        min_dist = float('inf')
        nearest = 'Unknown'
        for hotspot in self.hotspots:
            dist = math.sqrt((lat - hotspot['lat'])**2 + (lng - hotspot['lng'])**2)
            if dist < min_dist:
                min_dist = dist
                nearest = hotspot['name']
        return nearest

    def _generate_recommendation(self, area: str, top_type: str) -> str:
        recs = {
            'NO_HELMET': f"Increased helmet enforcement needed in {area}",
            'NO_SEATBELT': f"Seatbelt checks recommended in {area}",
            'RED_LIGHT': f"Additional signal monitoring required in {area}",
            'WRONG_SIDE': f"Road marking and signage improvement needed in {area}",
            'TRIPLE_RIDING': f"Rider safety awareness campaign in {area}",
            'STOP_LINE': f"Stop line reinforcement needed in {area}",
            'ILLEGAL_PARKING': f"Parking enforcement patrols recommended in {area}",
        }
        return recs.get(top_type, f"General traffic monitoring recommended in {area}")
