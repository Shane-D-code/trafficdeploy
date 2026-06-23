import dotenv from 'dotenv';
dotenv.config();

import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import path from 'path';
import fs from 'fs';
import http from 'http';
import compression from 'compression';
import { errorHandler } from './middleware/errorHandler';
import { rateLimiter } from './middleware/rateLimiter';
import apiRoutes from './api';
import { getWebSocketServer } from './websocket/WebSocketServer';

const app = express();
const PORT = parseInt(process.env.PORT || '5000', 10);

const uploadDir = path.resolve(__dirname, process.env.UPLOAD_DIR || '../../uploads');
if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir, { recursive: true });

app.use(compression());
app.use(helmet({
  crossOriginResourcePolicy: { policy: "cross-origin" },
  contentSecurityPolicy: false
}));
const corsOrigin = process.env.CORS_ORIGIN
  ? process.env.CORS_ORIGIN.split(',').map(s => s.trim())
  : ['http://localhost:3000', 'https://*.onrender.com'];
app.use(cors({ origin: corsOrigin, credentials: true }));
app.use(morgan('combined'));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));
app.use('/api', rateLimiter);

const evidenceDir = path.resolve(__dirname, '../../traffic_violation_project/evidence');
if (!fs.existsSync(evidenceDir)) fs.mkdirSync(evidenceDir, { recursive: true });
app.use('/evidence', express.static(evidenceDir));

const annotatedDir = path.resolve(__dirname, '../annotated');
if (!fs.existsSync(annotatedDir)) fs.mkdirSync(annotatedDir, { recursive: true });
app.use('/annotated', express.static(annotatedDir));

app.use('/uploads', express.static(uploadDir));

app.use('/api', apiRoutes);

app.get('/api/health', (_req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV,
    uptime: process.uptime(),
    memory: process.memoryUsage()
  });
});

const frontendPath = path.resolve(__dirname, '../../frontend/dist');
if (fs.existsSync(frontendPath)) {
  console.log('Serving frontend from:', frontendPath);
  app.use(express.static(frontendPath));
  app.get('*', (req, res, next) => {
    if (req.path.startsWith('/api')) return next();
    res.sendFile(path.join(frontendPath, 'index.html'));
  });
} else {
  console.log('Frontend build not found, API only mode');
  app.get('/', (_req, res) => {
    res.json({ service: 'Gridlock API', status: 'running', timestamp: new Date().toISOString() });
  });
}

app.use(errorHandler);

const server = http.createServer(app);

getWebSocketServer(server);

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Gridlock API running on port ${PORT}`);
  console.log(`Health check: http://0.0.0.0:${PORT}/api/health`);
});

export default app;