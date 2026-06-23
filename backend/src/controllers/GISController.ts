import { Request, Response } from 'express';
import { GISService } from '../services/GISService';

export class GISController {
  private gisService: GISService;

  constructor() {
    this.gisService = new GISService();
  }

  getHeatmap = async (req: Request, res: Response): Promise<void> => {
    try {
      const { days = 30 } = req.query;
      const data = await this.gisService.getHeatmapData(Number(days));

      res.json({
        success: true,
        data,
        total: data.length,
      });
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };

  getDangerousZones = async (req: Request, res: Response): Promise<void> => {
    try {
      const { threshold = 10 } = req.query;
      const zones = await this.gisService.getDangerousZones(Number(threshold));

      res.json({
        success: true,
        zones,
        total: zones.length,
      });
    } catch (error: any) {
      res.status(500).json({ success: false, error: error.message });
    }
  };
}
