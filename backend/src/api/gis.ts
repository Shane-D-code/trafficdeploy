import express from 'express';
import { GISController } from '../controllers/GISController';

const router = express.Router();
const controller = new GISController();

router.get('/heatmap', controller.getHeatmap);
router.get('/dangerous-zones', controller.getDangerousZones);

export default router;
