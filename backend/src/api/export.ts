import express from 'express';
import { DatabaseService } from '../services/DatabaseService';

const router = express.Router();
const db = new DatabaseService();

// GET /api/export?format=csv|json&type=...&startDate=...&endDate=...
router.get('/', async (req, res) => {
  try {
    const format = (req.query.format as string) || 'csv';
    const { type, startDate, endDate, plate } = req.query as Record<string, string>;

    const { rows } = await db.searchViolations({ type, startDate, endDate, plate, limit: 10000 });

    const data = rows.map(v => ({
      id: v.id,
      evidence_id: v.evidence_id,
      timestamp: v.timestamp,
      violation_type: v.violation_type,
      plate_text: v.plate_text || '',
      confidence: v.confidence,
      status: v.status || 'pending',
    }));

    if (format === 'json') {
      res.setHeader('Content-Disposition', 'attachment; filename="violations.json"');
      res.setHeader('Content-Type', 'application/json');
      return res.send(JSON.stringify(data, null, 2));
    }

    // CSV
    const headers = Object.keys(data[0] || {});
    const csv = [
      headers.join(','),
      ...data.map(row => headers.map(h => JSON.stringify((row as any)[h] ?? '')).join(','))
    ].join('\n');

    res.setHeader('Content-Disposition', 'attachment; filename="violations.csv"');
    res.setHeader('Content-Type', 'text/csv');
    res.send(csv);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
});

export default router;
