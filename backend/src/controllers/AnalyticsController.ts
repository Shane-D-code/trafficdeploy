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
