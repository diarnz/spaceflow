import { applyLayoutFromPlan } from './furnishing.js';

function resolveBridgeUrl() {
  const params = new URLSearchParams(window.location.search);
  const apiHost = params.get('apiHost') || 'localhost:8082';
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${apiHost}/ws/3d-bridge`;
}

class SpaceFlowBridge {
  constructor() {
    this.ws = null;
    this.connected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 25;
    this.reconnectDelayMs = 3000;
    this.url = resolveBridgeUrl();
    this.listeners = new Map();
  }

  on(type, handler) {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type).add(handler);
    return () => this.listeners.get(type)?.delete(handler);
  }

  emit(type, payload = {}) {
    const handlers = this.listeners.get(type);
    if (!handlers) return;
    handlers.forEach((handler) => {
      try {
        handler(payload);
      } catch (error) {
        console.warn('[SpaceFlow Bridge] Listener failed', error);
      }
    });
  }

  connect(url = this.url) {
    this.url = url;
    try {
      this.ws = new WebSocket(url);
      this.ws.addEventListener('open', () => {
        this.connected = true;
        this.reconnectAttempts = 0;
        console.log('[SpaceFlow Bridge] Connected to backend');
        this.emit('CONNECTED', {});
      });

      this.ws.addEventListener('message', (event) => {
        try {
          const message = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.warn('[SpaceFlow Bridge] Failed to parse incoming message', error);
        }
      });

      this.ws.addEventListener('close', () => {
        if (this.connected) {
          console.log('[SpaceFlow Bridge] Disconnected from backend');
        }
        this.connected = false;
        this.scheduleReconnect();
      });

      this.ws.addEventListener('error', () => {
        this.connected = false;
      });
    } catch (error) {
      this.connected = false;
      this.scheduleReconnect();
    }
  }

  scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;
    this.reconnectAttempts += 1;
    setTimeout(() => this.connect(this.url), this.reconnectDelayMs);
  }

  send(type, payload = {}) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify({ type, payload }));
  }

  handleMessage(message) {
    const { type, payload = {} } = message;
    if (type === 'CONNECTED') {
      const roomId = window._currentRoomId;
      if (roomId && !window._aiDesignInProgress) {
        this.send('REQUEST_LAYOUT', { roomId });
      }
      this.emit('CONNECTED', payload);
      return;
    }

    if (type === 'APPLY_LAYOUT') {
      if (window._currentRoomId === payload.roomId && Array.isArray(payload.items)) {
        if (payload.source === 'ai_agent') {
          window.dispatchEvent(new CustomEvent('spaceflow:ai-layout', { detail: payload }));
        }
        applyLayoutFromPlan(payload.items, { relocate: true, source: payload.source });
      } else {
        window._pendingBridgeLayouts = window._pendingBridgeLayouts || {};
        window._pendingBridgeLayouts[payload.roomId] = payload.items;
      }
      this.emit('APPLY_LAYOUT', payload);
      return;
    }

    if (type === 'AI_DESIGN_STARTED' || type === 'AI_DESIGN_DONE' || type === 'AI_DESIGN_ERROR') {
      this.emit(type, payload);
      return;
    }
  }

  applyPendingLayout(roomId) {
    const pending = window._pendingBridgeLayouts?.[roomId];
    if (roomId && Array.isArray(pending)) {
      applyLayoutFromPlan(pending, { relocate: true });
      delete window._pendingBridgeLayouts[roomId];
    }
  }
}

export const bridge = new SpaceFlowBridge();
window.spaceFlowBridge = bridge;
