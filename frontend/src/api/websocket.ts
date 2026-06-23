type MessageHandler = (message: any) => void;

let socket: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let handlers = new Set<MessageHandler>();
let reconnectAttempts = 0;
let intentionallyClosed = false;
const MAX_RECONNECT_ATTEMPTS = 20;

function getUrl(): string {
  const wsUrl = import.meta.env.VITE_WS_URL;
  if (wsUrl) return wsUrl;
  return 'ws://127.0.0.1:5000/ws';
}

function sendRaw(data: any) {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(data));
  }
}

function scheduleReconnect() {
  reconnectAttempts++;
  const delay = Math.min(1000 * 2 ** reconnectAttempts, 30000);
  console.log(`WebSocket reconnecting in ${delay}ms (attempt ${reconnectAttempts})`);
  reconnectTimer = setTimeout(connect, delay);
}

function connect() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  intentionallyClosed = false;
  const url = getUrl();
  console.log('WebSocket connecting to:', url);
  socket = new WebSocket(url);

  socket.onopen = () => {
    console.log('WebSocket connected');
    reconnectAttempts = 0;
    sendRaw({ type: 'SUBSCRIBE', channels: ['all', 'violations', 'jobs'] });
  };

  socket.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data);
      if (msg.type === 'PING') {
        sendRaw({ type: 'PONG' });
        return;
      }
      handlers.forEach(h => h(msg));
    } catch (err) {
      console.error('WebSocket message error:', err);
    }
  };

  socket.onclose = () => {
    console.log('WebSocket disconnected');
    socket = null;
    if (!intentionallyClosed && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
      scheduleReconnect();
    }
  };

  socket.onerror = () => {
    socket?.close();
  };
}

function disconnect() {
  intentionallyClosed = true;
  if (reconnectTimer) clearTimeout(reconnectTimer);
  socket?.close();
  socket = null;
  handlers.clear();
  reconnectAttempts = 0;
}

export function onMessage(handler: MessageHandler): () => void {
  handlers.add(handler);
  connect();
  return () => { handlers.delete(handler); };
}

export function sendMessage(data: any) {
  sendRaw(data);
}

export class WebSocketClient {
  private unsubs: (() => void)[] = [];

  connect() {
    connect();
  }

  onMessage(handler: MessageHandler): () => void {
    const unsub = onMessage(handler);
    this.unsubs.push(unsub);
    return unsub;
  }

  sendMessage(data: any) {
    sendRaw(data);
  }

  disconnect() {
    this.unsubs.forEach(fn => fn());
    this.unsubs = [];
  }

  isConnected() {
    return socket?.readyState === WebSocket.OPEN;
  }
}

export function getWebSocketClient(): WebSocketClient {
  return new WebSocketClient();
}

export const wsClient = new WebSocketClient();
