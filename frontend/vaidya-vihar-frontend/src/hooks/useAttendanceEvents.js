import { useEffect, useRef } from 'react';
import { authenticatedSocketUrl } from '../services/domainSocketUrl';

export default function useAttendanceEvents(refresh) {
  const refreshRef = useRef(refresh);
  useEffect(() => { refreshRef.current = refresh; }, [refresh]);

  useEffect(() => {
    let socket = null;
    let timer = null;
    let disposed = false;
    let attempt = 0;

    function connect() {
      const url = authenticatedSocketUrl('/api/ws/outlet-events');
      if (!url || disposed) return;
      socket = new WebSocket(url);
      socket.onopen = () => { attempt = 0; };
      socket.onmessage = (message) => {
        try {
          const event = JSON.parse(String(message.data));
          if (typeof event?.type === 'string' && event.type.startsWith('attendance.')) void refreshRef.current();
        } catch {
          // The socket also carries non-event keep-alive messages.
        }
      };
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        socket = null;
        if (!disposed) {
          timer = window.setTimeout(connect, Math.min(1000 * (2 ** attempt), 30000));
          attempt += 1;
        }
      };
    }

    connect();
    return () => {
      disposed = true;
      if (timer) window.clearTimeout(timer);
      if (socket) {
        socket.onclose = null;
        socket.onerror = null;
        socket.close();
      }
    };
  }, []);
}
