import express from 'express';
import multer from 'multer';
import path from 'path';
import { validateFile } from '../middleware/fileUpload';
import { DetectionController } from '../controllers/DetectionController';
import { DetectionService } from '../services/DetectionService';
import { PythonBridge } from '../python-bridge/bridge';
import { DatabaseService } from '../services/DatabaseService';

const router = express.Router();

const uploadDir = path.resolve(__dirname, process.env.UPLOAD_DIR || '../../../uploads');
const upload = multer({ dest: uploadDir });

const db = new DatabaseService();
const bridge = new PythonBridge();
const detectionService = new DetectionService(db, bridge);
const controller = new DetectionController(detectionService);

router.post('/image', upload.single('image'), validateFile, controller.detectImage);
router.post('/video', upload.single('video'), validateFile, controller.detectVideo);
router.get('/status/:jobId', controller.getJobStatus);
router.get('/results/:jobId', controller.getJobResults);

export default router;
