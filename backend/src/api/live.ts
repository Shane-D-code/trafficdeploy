import express from 'express';
import { getWebSocketServer } from '../websocket/WebSocketServer';

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
  res.json({ success: true, data: cameras });
});

router.post('/camera/:cameraId/start', (req, res) => {
  const { cameraId } = req.params;
  const ws = getWebSocketServer();
  if (ws) {
    ws.broadcast({
      type: 'CAMERA_DETECTION_STARTED',
      cameraId: parseInt(cameraId),
      timestamp: new Date().toISOString(),
    });
  }
  res.json({ success: true, cameraId: parseInt(cameraId) });
});

router.post('/camera/:cameraId/stop', (req, res) => {
  const { cameraId } = req.params;
  const ws = getWebSocketServer();
  if (ws) {
    ws.broadcast({
      type: 'CAMERA_DETECTION_STOPPED',
      cameraId: parseInt(cameraId),
      timestamp: new Date().toISOString(),
    });
  }
  res.json({ success: true, cameraId: parseInt(cameraId) });
});

export default router;
