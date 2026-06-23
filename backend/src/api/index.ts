import express from 'express';
import detectionRoutes from './detection';
import analyticsRoutes from './analytics';
import reportsRoutes from './reports';
import liveRoutes from './live';
import evidenceRoutes from './evidence';
import evaluationRoutes from './evaluation';
import insightsRoutes from './insights';
import settingsRoutes from './settings';
import exportRoutes from './export';

const router = express.Router();

router.use('/detection', detectionRoutes);
router.use('/analytics', analyticsRoutes);
router.use('/reports', reportsRoutes);
router.use('/live', liveRoutes);
router.use('/evidence', evidenceRoutes);
router.use('/evaluation', evaluationRoutes);
router.use('/insights', insightsRoutes);
router.use('/settings', settingsRoutes);
router.use('/export', exportRoutes);

export default router;
