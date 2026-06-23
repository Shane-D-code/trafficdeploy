import express from 'express';
import path from 'path';
import fs from 'fs';
import { DatabaseService } from '../services/DatabaseService';

const router = express.Router();
const db = new DatabaseService();

router.get('/', async (_req, res) => {
  try {
    const result = await db.searchViolations({ limit: 200 });
    const items = result.rows.map((v: any) => {
      let annotatedUrl = '';
      if (v.annotated_image_path) {
        const filename = path.basename(v.annotated_image_path);
        annotatedUrl = `/evidence/${filename}`;
      }
      let imgUrl = '';
      if (v.image_path) {
        imgUrl = v.image_path.startsWith('/') ? v.image_path : `/uploads/${path.basename(v.image_path)}`;
      } else if (v.evidence_path) {
        imgUrl = v.evidence_path.startsWith('/') ? v.evidence_path : `/evidence/${path.basename(v.evidence_path)}`;
      }
      return {
        id: String(v.id),
        evidenceId: v.evidence_id,
        violationType: v.violation_type,
        plateText: v.plate_text || 'N/A',
        confidence: v.confidence,
        timestamp: v.timestamp,
        imageUrl: imgUrl,
        annotatedImageUrl: annotatedUrl,
        status: v.status || 'pending',
        location: v.location || null,
      };
    });
    res.json({ success: true, data: items });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
});

router.get('/:id', async (req, res) => {
  try {
    const item = await db.getViolationById(req.params.id);
    if (!item) {
      res.status(404).json({ success: false, error: 'Evidence not found' });
      return;
    }
    let annotatedUrl = '';
    if (item.annotated_image_path) {
      const filename = path.basename(item.annotated_image_path);
      annotatedUrl = `/evidence/${filename}`;
    }
    let imgUrl = '';
    if (item.image_path) {
      imgUrl = item.image_path.startsWith('/') ? item.image_path : `/uploads/${path.basename(item.image_path)}`;
    } else if (item.evidence_path) {
      imgUrl = item.evidence_path.startsWith('/') ? item.evidence_path : `/evidence/${path.basename(item.evidence_path)}`;
    }
    res.json({
      success: true,
      data: {
        id: String(item.id),
        evidenceId: item.evidence_id,
        violationType: item.violation_type,
        plateText: item.plate_text || 'N/A',
        confidence: item.confidence,
        timestamp: item.timestamp,
        imageUrl: imgUrl,
        annotatedImageUrl: annotatedUrl,
        status: item.status || 'pending',
        bbox: item.bbox,
        metadata: item.metadata,
        location: item.location,
      },
    });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
});

router.delete('/:id', async (req, res) => {
  try {
    const violation = await db.getViolationById(req.params.id);
    if (!violation) {
      res.status(404).json({ success: false, error: 'Evidence not found' });
      return;
    }
    // Delete files from disk
    for (const p of [violation.evidence_path, violation.image_path, (violation as any).annotated_image_path]) {
      if (p && fs.existsSync(p)) fs.unlinkSync(p);
    }
    await db.deleteViolation(req.params.id);
    res.json({ success: true, message: `Evidence ${req.params.id} deleted` });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
});

export default router;
