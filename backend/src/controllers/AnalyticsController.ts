import { Request, Response } from 'express';
import { DatabaseService } from '../services/DatabaseService';

const db = new DatabaseService();

export const getStats = async (_req: Request, res: Response): Promise<void> => {
  try {
    const stats = await db.getStats();
    res.json({ success: true, data: stats });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const getViolations = async (req: Request, res: Response): Promise<void> => {
  try {
    const { type, plate, startDate, endDate, page, limit } = req.query;
    const result = await db.searchViolations({
      type: type as string,
      plate: plate as string,
      startDate: startDate as string,
      endDate: endDate as string,
      page: page ? parseInt(page as string) : 1,
      limit: limit ? parseInt(limit as string) : 50
    });
    res.json({ success: true, data: result });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const getCompliance = async (_req: Request, res: Response): Promise<void> => {
  try {
    const stats = await db.getStats();
    res.json({ success: true, data: stats.compliance });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const getViolationLocations = async (_req: Request, res: Response): Promise<void> => {
  try {
    const violations = await db.searchViolations({ limit: 200 });
    const locations = violations.rows.map((v: any) => {
      const baseLocs: Record<string, { lat: number; lng: number }> = {
        'NO HELMET': { lat: 12.9716, lng: 77.5946 },
        'NO SEATBELT': { lat: 12.9352, lng: 77.6245 },
        'TRIPLE RIDING': { lat: 12.9538, lng: 77.6472 },
        'RED LIGHT': { lat: 12.9822, lng: 77.5899 },
        'WRONG SIDE': { lat: 12.9279, lng: 77.6271 },
        'STOP LINE': { lat: 12.9719, lng: 77.6412 },
        'ILLEGAL PARKING': { lat: 12.9900, lng: 77.5700 },
      };
      const base = baseLocs[v.violation_type] || { lat: 12.97, lng: 77.60 };
      return {
        lat: base.lat + (Math.random() - 0.5) * 0.02,
        lng: base.lng + (Math.random() - 0.5) * 0.02,
        count: Math.floor(Math.random() * 10) + 1,
        type: v.violation_type,
        severity: v.confidence > 0.85 ? 8 : v.confidence > 0.65 ? 6 : 4,
      };
    });
    res.json({ success: true, data: locations });
  } catch (error: any) {
    res.json({ success: true, data: [] });
  }
};

export const updateReviewStatus = async (req: Request, res: Response): Promise<void> => {
  try {
    const { id, status, notes } = req.body;
    if (!id || !status) {
      res.status(400).json({ success: false, error: 'id and status are required' });
      return;
    }
    const validStatuses = ['approved', 'rejected', 'false_positive'];
    if (!validStatuses.includes(status)) {
      res.status(400).json({ success: false, error: `Invalid status. Must be one of: ${validStatuses.join(', ')}` });
      return;
    }
    await db.updateViolationStatus(id, status, notes);
    res.json({ success: true, message: `Violation ${id} ${status}` });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
};

const FINE_AMOUNTS: Record<string, number> = {
  'NO HELMET': 1000,
  'NO_HELMET': 1000,
  'NO SEATBELT': 1000,
  'NO_SEATBELT': 1000,
  'TRIPLE RIDING': 1500,
  'TRIPLE_RIDING': 1500,
  'RED LIGHT': 5000,
  'RED_LIGHT': 5000,
  'WRONG SIDE': 2000,
  'WRONG_SIDE': 2000,
  'STOP LINE': 1000,
  'STOP_LINE': 1000,
  'ILLEGAL PARKING': 500,
  'ILLEGAL_PARKING': 500,
};

export const getIncidents = async (req: Request, res: Response): Promise<void> => {
  try {
    const { status, page, limit } = req.query;
    const allViolations = await db.getAllViolations();

    const grouped = new Map<string, {
      incidentId: string;
      summary: {
        total_violations: number;
        total_fine: number;
        max_confidence: number;
        timestamp: string;
        license_plate: string;
        image_path: string;
        evidence_path: string;
        status: string;
      };
      violations: any[];
      fineBreakdown: { total: number; breakdown: Array<{ violation_type: string; confidence: number; fine: number; status: string }> };
      totalFine: number;
      canApprove: boolean;
    }>();

    for (const v of allViolations) {
      const jobId = (v as any).job_id || `single-${v.id}`;
      if (!grouped.has(jobId)) {
        grouped.set(jobId, {
          incidentId: jobId,
          summary: {
            total_violations: 0,
            total_fine: 0,
            max_confidence: 0,
            timestamp: v.timestamp || '',
            license_plate: v.plate_text || '',
            image_path: v.image_path || '',
            evidence_path: v.annotated_image_path || v.evidence_path || '',
            status: v.status || 'pending',
          },
          violations: [],
          fineBreakdown: { total: 0, breakdown: [] },
          totalFine: 0,
          canApprove: true,
        });
      }
      const incident = grouped.get(jobId)!;
      incident.violations.push(v);
      incident.summary.total_violations++;
      incident.summary.max_confidence = Math.max(incident.summary.max_confidence, v.confidence || 0);
      if (v.timestamp && v.timestamp > incident.summary.timestamp) {
        incident.summary.timestamp = v.timestamp;
      }
      if (v.plate_text) incident.summary.license_plate = v.plate_text;
      if (v.image_path) incident.summary.image_path = v.image_path;
      if (v.annotated_image_path || v.evidence_path) {
        incident.summary.evidence_path = (v.annotated_image_path || v.evidence_path) || '';
      }
      if (v.status) {
        if (v.status === 'rejected' || v.status === 'false_positive') incident.canApprove = false;
        if (incident.summary.status === 'pending') incident.summary.status = v.status;
      }
    }

    const incidents = Array.from(grouped.values()).filter(inc => {
      if (status && status !== 'all') {
        const filterStatus = status as string;
        if (filterStatus === 'pending') return inc.summary.status === 'pending';
        return inc.summary.status === filterStatus;
      }
      return true;
    });

    for (const inc of incidents) {
      const breakdown: Array<{ violation_type: string; confidence: number; fine: number; status: string }> = [];
      let totalFine = 0;
      for (const v of inc.violations) {
        const fine = FINE_AMOUNTS[v.violation_type] || 500;
        totalFine += fine;
        breakdown.push({
          violation_type: v.violation_type,
          confidence: v.confidence || 0,
          fine,
          status: v.status || 'pending',
        });
      }
      inc.fineBreakdown = { total: totalFine, breakdown };
      inc.totalFine = totalFine;
      inc.summary.total_fine = totalFine;
    }

    const pageNum = page ? parseInt(page as string) : 1;
    const pageSize = limit ? parseInt(limit as string) : 50;
    const startIdx = (pageNum - 1) * pageSize;
    const paged = incidents.slice(startIdx, startIdx + pageSize);

    res.json({ success: true, incidents: paged, total: incidents.length });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const reviewIncident = async (req: Request, res: Response): Promise<void> => {
  try {
    const { incidentId } = req.params;
    const { status, officerId, notes, reason } = req.body;
    if (!incidentId || !status) {
      res.status(400).json({ success: false, error: 'incidentId and status are required' });
      return;
    }
    const validStatuses = ['approved', 'rejected', 'false_positive'];
    if (!validStatuses.includes(status)) {
      res.status(400).json({ success: false, error: `Invalid status. Must be one of: ${validStatuses.join(', ')}` });
      return;
    }

    const allViolations = await db.getAllViolations();
    const incidentViolations = allViolations.filter((v: any) => {
      if (incidentId.startsWith('single-')) {
        return String(v.id) === incidentId.replace('single-', '');
      }
      return v.job_id === incidentId;
    });

    let updatedCount = 0;
    for (const v of incidentViolations) {
      try {
        await db.updateViolationStatus(String(v.id), status, notes || reason || '');
        updatedCount++;
      } catch (err) {
        console.error(`Failed to update violation ${v.id}:`, err);
      }
    }

    res.json({
      success: true,
      message: `Incident ${incidentId} ${status} (${updatedCount} violations updated)`,
      updatedCount,
    });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
};
