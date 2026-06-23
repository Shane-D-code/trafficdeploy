import { DatabaseService } from './DatabaseService';

export class GISService {
  private db: DatabaseService;

  constructor() {
    this.db = new DatabaseService();
  }

  async getHeatmapData(days: number = 30): Promise<any[]> {
    const violations = await this.db.getAllViolations();
    const now = new Date();
    const cutoff = new Date(now.getTime() - days * 86400000);

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

    return (violations || [])
      .filter((v: any) => {
        const ts = v.timestamp ? new Date(v.timestamp) : now;
        return ts >= cutoff;
      })
      .map((v: any, idx: number) => {
        const loc = locations[idx % locations.length];
        return {
          id: v.id,
          violation_type: v.violation_type || 'UNKNOWN',
          confidence: v.confidence || 0,
          timestamp: v.timestamp,
          location: loc.name,
          lat: loc.lat + (Math.random() - 0.5) * 0.01,
          lng: loc.lng + (Math.random() - 0.5) * 0.01,
        };
      });
  }

  async getDangerousZones(threshold: number = 10): Promise<any[]> {
    const data = await this.getHeatmapData(365);

    const grouped: Record<string, { count: number; types: Set<string>; confidences: number[] }> = {};
    for (const v of data) {
      const loc = v.location || 'Unknown';
      if (!grouped[loc]) {
        grouped[loc] = { count: 0, types: new Set(), confidences: [] };
      }
      grouped[loc].count++;
      grouped[loc].types.add(v.violation_type);
      grouped[loc].confidences.push(v.confidence);
    }

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

    return Object.entries(grouped)
      .filter(([_, data]) => data.count >= threshold)
      .map(([name, data]) => {
        const loc = locations.find(l => l.name === name) || { lat: 12.97, lng: 77.6 };
        const avgConf = data.confidences.reduce((a, b) => a + b, 0) / data.confidences.length;
        return {
          location: name,
          lat: loc.lat,
          lng: loc.lng,
          count: data.count,
          types: [...data.types],
          avgConfidence: avgConf,
          severity: this._calculateSeverity(data.count),
        };
      })
      .sort((a, b) => b.count - a.count);
  }

  private _calculateSeverity(count: number): string {
    if (count > 50) return 'critical';
    if (count > 20) return 'high';
    if (count > 10) return 'medium';
    return 'low';
  }
}
