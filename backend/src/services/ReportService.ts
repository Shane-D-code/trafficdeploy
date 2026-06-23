import { DatabaseService } from './DatabaseService';

export class ReportService {
  private db: DatabaseService;

  constructor() {
    this.db = new DatabaseService();
  }

  async generateReport(params: { startDate?: string; endDate?: string; types?: string[] }): Promise<any> {
    const violations = await this.db.getAllViolations();
    const stats = await this.db.getStats();

    let filtered = violations;
    if (params.startDate) filtered = filtered.filter(v => v.timestamp && new Date(v.timestamp) >= new Date(params.startDate!));
    if (params.endDate) {
      const end = new Date(params.endDate!);
      end.setHours(23, 59, 59, 999);
      filtered = filtered.filter(v => v.timestamp && new Date(v.timestamp) <= end);
    }
    if (params.types && params.types.length > 0) filtered = filtered.filter(v => params.types!.includes(v.violation_type));

    return {
      generatedAt: new Date().toISOString(),
      totalViolations: filtered.length,
      stats: {
        total: stats.total,
        byType: stats.byType,
        totalVehicles: stats.totalVehicles,
        compliance: stats.compliance
      },
      violations: filtered.slice(0, 1000).map(v => ({
        id: v.id,
        type: v.violation_type,
        plateText: v.plate_text,
        confidence: v.confidence,
        timestamp: v.timestamp,
        location: v.location,
        evidence_path: v.evidence_path
      }))
    };
  }
}
