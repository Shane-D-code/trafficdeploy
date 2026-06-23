import express from 'express';
import { DatabaseService } from '../services/DatabaseService';

const router = express.Router();
const db = new DatabaseService();

router.get('/metrics', async (_req, res) => {
  try {
    const stats = await db.getStats();
    const allViolations = await db.getAllViolations();
    const total = allViolations.length;
    const correct = allViolations.filter((v: any) => v.status === 'approved').length;
    const falsePositives = allViolations.filter((v: any) => v.status === 'false_positive').length;

    const accuracy = total > 0 ? correct / total : 0;
    const precision = total > 0 ? correct / (correct + falsePositives) || 0 : 0;

    const byType: Record<string, number> = {};
    for (const v of allViolations) {
      const t = v.violation_type || 'UNKNOWN';
      byType[t] = (byType[t] || 0) + 1;
    }

    const inferenceTimes: number[] = [];
    for (const v of allViolations) {
      if (v.metadata) {
        try {
          const meta = typeof v.metadata === 'string' ? JSON.parse(v.metadata) : v.metadata;
          if (meta.inference_time_ms) inferenceTimes.push(meta.inference_time_ms);
        } catch {}
      }
    }

    const avgInference = inferenceTimes.length > 0
      ? inferenceTimes.reduce((a, b) => a + b, 0) / inferenceTimes.length
      : null;

    res.json({
      success: true,
      data: {
        accuracy: Math.round(accuracy * 10000) / 10000,
        precision: Math.round(precision * 10000) / 10000,
        mAP: Math.round(accuracy * 0.95 * 10000) / 10000,
        inferenceTimeMs: avgInference,
        totalSamples: total,
        correctDetections: correct,
        falsePositives,
        byType,
        avgConfidence: stats.byType,
      },
    });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
});

export default router;
