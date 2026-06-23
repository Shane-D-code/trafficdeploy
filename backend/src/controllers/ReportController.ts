import { Request, Response } from 'express';
import { ReportService } from '../services/ReportService';
import { v4 as uuidv4 } from 'uuid';

const reportService = new ReportService();

export const generateReport = async (req: Request, res: Response): Promise<void> => {
  try {
    const { startDate, endDate, types } = req.body;
    const reportId = uuidv4();
    const data = await reportService.generateReport({ startDate, endDate, types });

    res.json({
      success: true,
      reportId,
      message: 'Report generated',
      data
    });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
};
