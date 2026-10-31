import { useEffect, useRef } from 'react';
import api from '../services/api';

export interface ExecutiveEvent {
  event: string;
  resource?: Record<string, unknown>;
  occurred_at?: string;
  actor?: Record<string, unknown>;
  [key: string]: unknown;
}

const RECONNECT_BASE_DELAY_MS = 1000;
const RECONNECT_MAX_DELAY_MS = 30000;

const buildSocketUrl = (): string | null => {
  if (typeof window === 'undefined') return null;
  const token = window.localStorage.getItem('token');
  if (!token) return null;

  const url = new URL('/ws', api.defaults.baseURL || window.location.origin);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.searchParams.set('token', token);
  return url.toString();
};

/**
 * Subscribes to the backend's native WebSocket endpoint and invokes the handler
 * for raw broadcast payloads whose `event` matches one of `eventNames`.
 */
export function useExecutiveEventStream(eventNames: string[], onEvent: (event: ExecutiveEvent) => void) {
  const handlerRef = useRef(onEvent);
  const eventKey = eventNames.join('|');

  useEffect(() => {
    handlerRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof WebSocket === 'undefined') return undefined;

    const wanted = new Set(eventKey.split('|').filter(Boolean));
    if (!wanted.size) return undefined;

    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;
    let disposed = false;

    const scheduleReconnect = () => {
      if (disposed) return;
      const delay = Math.min(RECONNECT_BASE_DELAY_MS * 2 ** attempt, RECONNECT_MAX_DELAY_MS);
      attempt += 1;
      reconnectTimer = setTimeout(connect, delay);
    };

    function connect() {
      if (disposed) return;
      const socketUrl = buildSocketUrl();
      if (!socketUrl) {
        scheduleReconnect();
        return;
      }

      try {
        socket = new WebSocket(socketUrl);
      } catch {
        scheduleReconnect();
        return;
      }

      socket.onopen = () => {
        attempt = 0;
      };

      socket.onmessage = (message) => {
        let payload: ExecutiveEvent;
        try {
          payload = JSON.parse(String(message.data));
        } catch {
          return;
        }
        if (payload && typeof payload.event === 'string' && wanted.has(payload.event)) {
          handlerRef.current(payload);
        }
      };

      socket.onclose = () => {
        socket = null;
        scheduleReconnect();
      };

      socket.onerror = () => {
        socket?.close();
      };
    }

    connect();

    return () => {
      disposed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (socket) {
        socket.onclose = null;
        socket.onerror = null;
        socket.close();
      }
    };
  }, [eventKey]);
}

export default useExecutiveEventStream;
