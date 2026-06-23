import express from 'express';
import { getStats, getViolations, getCompliance, getViolationLocations, updateReviewStatus, getIncidents, reviewIncident } from '../controllers/AnalyticsController';
import { DatabaseService } from '../services/DatabaseService';

const router = express.Router();
const db = new DatabaseService();

const fpUndoMap = new Map<string, { previousStatus: string; timeout: NodeJS.Timeout }>();

router.get('/stats', getStats);
router.get('/violations', getViolations);
router.get('/violations/locations', getViolationLocations);
router.get('/compliance', getCompliance);
router.post('/review', updateReviewStatus);

router.patch('/violations/:id/false-positive', async (req, res) => {
  try {
    const { id } = req.params;
    const { previousStatus } = await db.markFalsePositive(id);

    if (fpUndoMap.has(id)) {
      clearTimeout(fpUndoMap.get(id)!.timeout);
    }

    const timeout = setTimeout(async () => {
      fpUndoMap.delete(id);
    }, 60000);
    fpUndoMap.set(id, { previousStatus, timeout });

    res.json({ success: true, message: 'Marked as false positive', undoAvailable: true });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
});

router.delete('/violations/:id/false-positive', async (req, res) => {
  try {
    const { id } = req.params;
    const entry = fpUndoMap.get(id);
    if (!entry) {
      res.status(400).json({ success: false, error: 'Undo window expired (60s)' });
      return;
    }
    clearTimeout(entry.timeout);
    fpUndoMap.delete(id);
    await db.undoFalsePositive(id, entry.previousStatus);
    res.json({ success: true, message: 'False positive undone' });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
});

router.get('/incidents', getIncidents);
router.post('/incidents/:incidentId/review', reviewIncident);

router.get('/metrics', async (_req, res) => {
  try {
    const metrics = await db.getMetrics();
    res.json({ success: true, data: metrics });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
});

export default router;
