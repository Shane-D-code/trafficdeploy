import express from 'express';
import { generateReport } from '../controllers/ReportController';

const router = express.Router();

router.post('/generate', generateReport);

export default router;
