import { Request, Response, NextFunction } from 'express';
import path from 'path';

const ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png'];
const ALLOWED_VIDEO_EXTENSIONS = ['.mp4'];
const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'video/mp4'];
const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB

export function validateFile(req: Request, res: Response, next: NextFunction): void {
  const file = req.file;

  if (!file) {
    res.status(400).json({ success: false, error: 'No file provided' });
    return;
  }

  if (file.size > MAX_FILE_SIZE) {
    res.status(400).json({ success: false, error: 'File too large (max 100MB)' });
    return;
  }

  const ext = path.extname(file.originalname).toLowerCase();
  const allowed = [...ALLOWED_IMAGE_EXTENSIONS, ...ALLOWED_VIDEO_EXTENSIONS];

  if (!allowed.includes(ext)) {
    res.status(400).json({
      success: false,
      error: `Invalid file type. Allowed: ${allowed.join(', ')}`
    });
    return;
  }

  next();
}
