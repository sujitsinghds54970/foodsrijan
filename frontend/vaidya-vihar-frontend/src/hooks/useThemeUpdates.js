import { useEffect, useRef } from 'react';
import toast from 'react-hot-toast';
import { useTheme } from '../context/ThemeContext';
import api from '../services/api';
import { authenticatedSocketUrl } from '../services/domainSocketUrl';

const BASE_DELAY_MS = 1000;
const MAX_DELAY_MS = 30000;

export default function useThemeUpdates() {
  const { updateTheme } = useTheme();
  const updateRef = useRef(updateTheme);

  useEffect(() => { updateRef.current = updateTheme; }, [updateTheme]);

  useEffect(() => {
    let socket = null;
    let reconnectTimer = null;
    let attempt = 0;
    let disposed = false;

    const refreshTheme = async () => {
      const response = await api.get('/api/themes/resolved');
      const tokens = response.data?.theme?.tokens || response.data?.data?.theme?.tokens;
      if (!tokens || typeof tokens !== 'object') throw new Error('Resolved theme did not include tokens.');
      updateRef.current(tokens);
      toast.success('Workspace theme updated');
    };

    const scheduleReconnect = () => {
      if (disposed) return;
      reconnectTimer = window.setTimeout(connect, Math.min(BASE_DELAY_MS * (2 ** attempt), MAX_DELAY_MS));
      attempt += 1;
    };

    function connect() {
      const url = authenticatedSocketUrl('/api/ws/theme-updates');
      if (disposed || !url) return;
      socket = new WebSocket(url);
      socket.onopen = () => { attempt = 0; };
      socket.onmessage = (message) => {
        try {
          const event = JSON.parse(String(message.data));
          if (event?.event === 'theme.published') {
            void refreshTheme().catch(() => toast.error('The published workspace theme could not be loaded.'));
          }
        } catch {
          // Ignore non-domain messages such as keep-alive responses.
        }
      };
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        socket = null;
        scheduleReconnect();
      };
    }

    connect();
    return () => {
      disposed = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      if (socket) {
        socket.onclose = null;
        socket.onerror = null;
        socket.close();
      }
    };
  }, []);
}
