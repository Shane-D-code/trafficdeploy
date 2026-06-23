import express from 'express';
import { cameraStreamService } from '../services/CameraStreamService';

const router = express.Router();

const cameras = [
  { id: 1, name: 'MG Road Junction', location: 'MG Road', status: 'online' as const, lat: 12.9716, lng: 77.5946 },
  { id: 2, name: 'Brigade Road', location: 'Brigade Road', status: 'online' as const, lat: 12.9352, lng: 77.6245 },
  { id: 3, name: 'Church Street', location: 'Church Street', status: 'offline' as const, lat: 12.9538, lng: 77.6472 },
  { id: 4, name: 'Indiranagar', location: 'Indiranagar', status: 'online' as const, lat: 12.9783, lng: 77.6408 },
  { id: 5, name: 'Koramangala', location: 'Koramangala', status: 'warning' as const, lat: 12.9279, lng: 77.6271 },
  { id: 6, name: 'Electronic City', location: 'Electronic City', status: 'online' as const, lat: 12.8456, lng: 77.6603 },
];

router.get('/cameras', (_req, res) => {
  const streamingStatus = cameras.map(c => ({
    ...c,
    isStreaming: cameraStreamService.isStreaming(c.id),
  }));
  res.json({ success: true, data: streamingStatus });
});

router.post('/camera/:cameraId/start', async (req, res) => {
  const cameraId = parseInt(req.params.cameraId);
  try {
    await cameraStreamService.startStream(cameraId);
    res.json({ success: true, cameraId, message: 'Camera stream started' });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
});

router.post('/camera/:cameraId/stop', (req, res) => {
  const cameraId = parseInt(req.params.cameraId);
  cameraStreamService.stopStream(cameraId);
  res.json({ success: true, cameraId, message: 'Camera stream stopped' });
});

router.get('/camera/:cameraId/status', (req, res) => {
  const cameraId = parseInt(req.params.cameraId);
  res.json({
    success: true,
    cameraId,
    isStreaming: cameraStreamService.isStreaming(cameraId),
  });
});

export default router;
