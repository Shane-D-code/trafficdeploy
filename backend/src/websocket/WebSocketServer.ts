import { WebSocketServer, WebSocket } from 'ws';
import { EventEmitter } from 'events';
import { Server as HttpServer } from 'http';

export class NotificationServer extends EventEmitter {
  private wss: WebSocketServer;
  private clients: Set<WebSocket> = new Set();
  private heartbeatInterval!: NodeJS.Timeout;

  constructor(server: HttpServer) {
    super();
    this.wss = new WebSocketServer({ server, path: '/ws' });
    this.setupWebSocket();
    this.startHeartbeat();
    console.log(`WebSocket server attached to HTTP server`);
  }

  private setupWebSocket(): void {
    this.wss.on('connection', (ws: WebSocket, req) => {
      const clientId = 'CLIENT_' + Date.now() + '_' + Math.random().toString(36).substring(7);
      console.log(`Client connected: ${clientId}`);

      (ws as any).clientId = clientId;
      (ws as any).isAlive = true;

      this.clients.add(ws);
      this.emit('clientConnected', { clientId });

      ws.on('message', (data: Buffer) => {
        try {
          const message = JSON.parse(data.toString());
          this.handleClientMessage(ws, message);
        } catch (error) {
          console.error('WebSocket message parse error:', error);
        }
      });

      ws.on('close', () => {
        console.log(`Client disconnected: ${clientId}`);
        this.clients.delete(ws);
        this.emit('clientDisconnected', { clientId });
      });

      ws.on('error', (error) => {
        console.error(`WebSocket error for client ${clientId}:`, error.message);
      });

      this.sendToClient(ws, {
        type: 'CONNECTED',
        clientId,
        timestamp: new Date().toISOString(),
        message: 'Connected to Gridlock Notification Server'
      });
    });
  }

  private handleClientMessage(ws: WebSocket, message: any): void {
    switch (message.type) {
      case 'PING':
        this.sendToClient(ws, { type: 'PONG', timestamp: new Date().toISOString() });
        break;
      case 'PONG':
        (ws as any).isAlive = true;
        break;
      case 'SUBSCRIBE':
        (ws as any).subscriptions = message.channels || ['all'];
        this.sendToClient(ws, {
          type: 'SUBSCRIBED',
          channels: (ws as any).subscriptions,
          timestamp: new Date().toISOString()
        });
        break;
      default:
        console.log('Unknown message type:', message.type);
    }
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      this.clients.forEach((ws) => {
        if (!(ws as any).isAlive) {
          this.clients.delete(ws);
          ws.terminate();
          return;
        }
        (ws as any).isAlive = false;
        this.sendToClient(ws, { type: 'PING' });
      });
    }, 30000);
  }

  private sendToClient(ws: WebSocket, message: any): void {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
    }
  }

  broadcast(message: any, channels?: string[]): void {
    this.clients.forEach((ws) => {
      const subscriptions = (ws as any).subscriptions || ['all'];
      const shouldReceive = !channels ||
        channels.some(ch => subscriptions.includes(ch) || subscriptions.includes('all'));

      if (shouldReceive) {
        this.sendToClient(ws, message);
      }
    });
  }

  broadcastViolation(violation: any): void {
    this.broadcast({
      type: 'NEW_VIOLATION',
      data: violation,
      timestamp: new Date().toISOString()
    }, ['violations']);
  }

  broadcastJobComplete(jobId: string, results: any): void {
    this.broadcast({
      type: 'JOB_COMPLETE',
      jobId,
      results,
      timestamp: new Date().toISOString()
    }, ['jobs']);
  }

  broadcastJobProgress(jobId: string, progress: number, status: string): void {
    this.broadcast({
      type: 'JOB_PROGRESS',
      jobId,
      progress,
      status,
      timestamp: new Date().toISOString()
    }, ['jobs']);
  }

  shutdown(): void {
    clearInterval(this.heartbeatInterval);
    this.wss.close();
    console.log('WebSocket server shut down');
  }
}

let wsInstance: NotificationServer | null = null;

export function getWebSocketServer(server?: HttpServer): NotificationServer | null {
  if (!wsInstance) {
    if (!server) {
      return null;
    }
    wsInstance = new NotificationServer(server);
  }
  return wsInstance;
}