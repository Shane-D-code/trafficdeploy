import express from 'express';
import { DatabaseService } from '../services/DatabaseService';

const router = express.Router();
const db = new DatabaseService();

router.get('/', async (req, res) => {
  try {
    const settings = await db.getSettings();
    res.json({ success: true, data: settings });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
});

router.put('/', async (req, res) => {
  try {
    await db.saveSettings(req.body);
    res.json({ success: true });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
});

export default router;
