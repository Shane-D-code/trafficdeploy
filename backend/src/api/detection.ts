import express from 'express';
import multer from 'multer';
import path from 'path';
import { validateFile } from '../middleware/fileUpload';
import { detectImage, detectVideo, getJobStatus } from '../controllers/DetectionController';

const router = express.Router();

const uploadDir = path.resolve(__dirname, process.env.UPLOAD_DIR || '../../../uploads');
const upload = multer({ dest: uploadDir });

router.post('/image', upload.single('image'), validateFile, detectImage);
router.post('/video', upload.single('video'), validateFile, detectVideo);
router.get('/status/:jobId', getJobStatus);

export default router;
