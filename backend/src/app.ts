import dotenv from 'dotenv';
dotenv.config();

import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import path from 'path';
import fs from 'fs';
import http from 'http';
import { errorHandler } from './middleware/errorHandler';
import { rateLimiter } from './middleware/rateLimiter';
import apiRoutes from './api';
import { getWebSocketServer } from './websocket/WebSocketServer';

const app = express();
const PORT = process.env.PORT || 5000;

const uploadDir = path.resolve(__dirname, process.env.UPLOAD_DIR || '../../uploads');
if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir, { recursive: true });

app.use(helmet());
const corsOrigin = process.env.CORS_ORIGIN
  ? process.env.CORS_ORIGIN.split(',').map(s => s.trim())
  : ['http://localhost:3000'];
app.use(cors({ origin: corsOrigin, credentials: true }));
app.use(morgan('dev'));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));
app.use(rateLimiter);

const evidenceDir = path.resolve(__dirname, '../../traffic_violation_project/evidence');
if (!fs.existsSync(evidenceDir)) fs.mkdirSync(evidenceDir, { recursive: true });
app.use('/evidence', express.static(evidenceDir));

app.use('/api', apiRoutes);

app.get('/', (_req, res) => {
  res.json({ service: 'Gridlock API', status: 'running', timestamp: new Date().toISOString() });
});

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.use(errorHandler);

const server = http.createServer(app);

getWebSocketServer(server);

server.listen(PORT, () => {
  console.log(`Gridlock API running on http://localhost:${PORT}`);
  console.log(`WebSocket running on ws://localhost:${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/api/health`);
});

export default app;