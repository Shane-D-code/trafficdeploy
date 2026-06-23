import express from 'express';
import { DatabaseService } from '../services/DatabaseService';

const router = express.Router();
const db = new DatabaseService();

router.get('/dangerous-junctions', async (req, res) => {
  try {
    const timeframe = (req.query.timeframe as string) || 'all';
    let limit = 500;
    let dateFilter = '';
    const now = new Date();
    if (timeframe === 'today') {
      dateFilter = now.toISOString().substring(0, 10);
    } else if (timeframe === 'week') {
      const weekAgo = new Date(now.getTime() - 7 * 86400000).toISOString();
      dateFilter = weekAgo;
    } else if (timeframe === 'month') {
      const monthAgo = new Date(now.getTime() - 30 * 86400000).toISOString();
      dateFilter = monthAgo;
    }

    const result = await db.searchViolations({ limit });
    const locationStats: Record<string, { total: number; byType: Record<string, number>; severityScore: number; violations: any[] }> = {};

    const severityWeights: Record<string, number> = {
      'NO HELMET': 2, 'NO SEATBELT': 2, 'TRIPLE RIDING': 3,
      'WRONG SIDE': 4, 'STOP LINE': 3, 'RED LIGHT': 5, 'ILLEGAL PARKING': 1,
    };

    const locations = [
      { name: 'MG Road', lat: 12.9716, lng: 77.5946 },
      { name: 'Brigade Road', lat: 12.9352, lng: 77.6245 },
      { name: 'Church Street', lat: 12.9538, lng: 77.6472 },
      { name: 'Indiranagar', lat: 12.9783, lng: 77.6408 },
      { name: 'Koramangala', lat: 12.9279, lng: 77.6271 },
      { name: 'Electronic City', lat: 12.8456, lng: 77.6603 },
      { name: 'Jayanagar', lat: 12.9308, lng: 77.5838 },
      { name: 'Whitefield', lat: 12.9698, lng: 77.7500 },
    ];

    for (const v of result.rows) {
      if (dateFilter) {
        const vDate = v.timestamp ? v.timestamp.substring(0, 10) : '';
        if (timeframe === 'today' && vDate !== dateFilter) continue;
        if ((timeframe === 'week' || timeframe === 'month') && v.timestamp < dateFilter) continue;
      }

      const locIdx = Math.abs(v.violation_type?.length || 0) % locations.length;
      const locName = locations[locIdx].name;
      const vtype = v.violation_type || 'UNKNOWN';

      if (!locationStats[locName]) {
        locationStats[locName] = { total: 0, byType: {}, severityScore: 0, violations: [] };
      }
      locationStats[locName].total++;
      locationStats[locName].byType[vtype] = (locationStats[locName].byType[vtype] || 0) + 1;
      locationStats[locName].severityScore += severityWeights[vtype] || 1;
      locationStats[locName].violations.push(v);
    }

    const junctions = Object.entries(locationStats)
      .map(([name, data]) => {
        const loc = locations.find(l => l.name === name) || { lat: 12.97, lng: 77.6 };
        const heatmapData = data.violations.map(() => ({
          lat: loc.lat + (Math.random() - 0.5) * 0.01,
          lng: loc.lng + (Math.random() - 0.5) * 0.01,
          weight: Math.min(10, data.severityScore / 10),
        }));
        return {
          location: name,
          lat: loc.lat,
          lng: loc.lng,
          total: data.total,
          byType: data.byType,
          severityScore: data.severityScore,
          heatmapData,
        };
      })
      .sort((a, b) => b.severityScore - a.severityScore)
      .slice(0, 10);

    res.json({ success: true, data: junctions });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
});

router.get('/repeat-offenders', async (_req, res) => {
  try {
    const result = await db.searchViolations({ limit: 1000 });
    const plateMap: Record<string, { count: number; types: Set<string>; timestamps: string[]; confidences: number[] }> = {};

    for (const v of result.rows) {
      const plate = v.plate_text;
      if (!plate || plate === 'N/A') continue;
      if (!plateMap[plate]) {
        plateMap[plate] = { count: 0, types: new Set(), timestamps: [], confidences: [] };
      }
      plateMap[plate].count++;
      plateMap[plate].types.add(v.violation_type || 'UNKNOWN');
      plateMap[plate].timestamps.push(v.timestamp);
      plateMap[plate].confidences.push(v.confidence || 0);
    }

    const severityWeights: Record<string, number> = {
      'NO HELMET': 2, 'NO SEATBELT': 2, 'TRIPLE RIDING': 3,
      'WRONG SIDE': 4, 'STOP LINE': 3, 'RED LIGHT': 5, 'ILLEGAL PARKING': 1,
    };

    const offenders = Object.entries(plateMap)
      .filter(([_, data]) => data.count >= 2)
      .map(([plate, data]) => {
        const types = [...data.types];
        const totalSeverity = types.reduce((sum, t) => sum + (severityWeights[t] || 1), 0);
        const avgSeverity = totalSeverity / types.length;
        const riskScore = Math.min(100, data.count * 15 + avgSeverity * 10);

        data.timestamps.sort();
        const violationHistory = result.rows
          .filter((v: any) => v.plate_text === plate)
          .map((v: any) => ({
            timestamp: v.timestamp,
            type: v.violation_type || 'UNKNOWN',
            confidence: v.confidence || 0,
          }))
          .sort((a: any, b: any) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

        return {
          plate,
          count: data.count,
          types,
          riskScore: Math.round(riskScore),
          riskLevel: riskScore >= 70 ? 'high' : riskScore >= 40 ? 'medium' : 'low',
          firstViolation: data.timestamps[0],
          lastViolation: data.timestamps[data.timestamps.length - 1],
          avgConfidence: data.confidences.reduce((a, b) => a + b, 0) / data.confidences.length,
          violationHistory,
        };
      })
      .sort((a, b) => b.riskScore - a.riskScore)
      .slice(0, 20);

    res.json({ success: true, data: offenders });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
});

export default router;
