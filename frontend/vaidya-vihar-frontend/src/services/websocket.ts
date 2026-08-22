import { io, Socket } from 'socket.io-client';
import { useEffect, useRef, useCallback, useState } from 'react';

// Get WebSocket URL based on current location
const getWebSocketUrl = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return process.env.REACT_APP_WS_URL || `${protocol}//${host}`;
};

const SOCKET_URL = getWebSocketUrl();

interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  priority: string;
  data: Record<string, unknown>;
  created_at: string;
  read: boolean;
  action_url?: string;
  reference_id?: string;
  reference_type?: string;
}

interface UseWebSocketOptions {
  autoConnect?: boolean;
  auth?: Record<string, string>;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
  onNotification?: (notification: Notification) => void;
  onTyping?: (data: { user_id: number; is_typing: boolean }) => void;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  connectionId: string | null;
  notifications: Notification[];
  unreadCount: number;
  connect: () => void;
  disconnect: () => void;
  sendNotification: (type: string, data: Record<string, unknown>) => void;
  subscribe: (channel: string) => void;
  unsubscribe: (channel: string) => void;
  markAsRead: (notificationId: string) => void;
  markAllAsRead: () => void;
  clearNotifications: () => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    autoConnect = true,
    auth,
    onConnect,
    onDisconnect,
    onError,
    onNotification,
    onTyping,
  } = options;

  const socketRef = useRef<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionId, setConnectionId] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const connect = useCallback(() => {
    if (socketRef.current?.connected) return;

    const socket = io(SOCKET_URL, {
      autoConnect: false,
      auth,
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socket.on('connect', () => {
      setIsConnected(true);
      setConnectionId(socket.id || null);
      onConnect?.();
      console.log('WebSocket connected:', socket.id);
    });

    socket.on('disconnect', () => {
      setIsConnected(false);
      setConnectionId(null);
      onDisconnect?.();
      console.log('WebSocket disconnected');
    });

    socket.on('connect_error', (error: Error) => {
      console.error('WebSocket connection error:', error);
      onError?.(error);
    });

    socket.on('notification', (notification: Notification) => {
      setNotifications(prev => [notification, ...prev]);
      onNotification?.(notification);
      
      // Show browser notification if permitted
      if (Notification.permission === 'granted') {
        new Notification(notification.title, {
          body: notification.message,
          icon: '/logo.png',
          tag: notification.id,
        });
      }
    });

    socket.on('typing', (data: { user_id: number; is_typing: boolean }) => {
      onTyping?.(data);
    });

    socket.on('error', (error: Error) => {
      console.error('WebSocket error:', error);
      onError?.(error);
    });

    socketRef.current = socket;
    socket.connect();
  }, [auth, onConnect, onDisconnect, onError, onNotification, onTyping]);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      setIsConnected(false);
      setConnectionId(null);
    }
  }, []);

  const sendNotification = useCallback((type: string, data: Record<string, unknown>) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(type, data);
    }
  }, []);

  const subscribe = useCallback((channel: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('subscribe', { channel });
    }
  }, []);

  const unsubscribe = useCallback((channel: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('unsubscribe', { channel });
    }
  }, []);

  const markAsRead = useCallback((notificationId: string) => {
    setNotifications(prev =>
      prev.map(n => (n.id === notificationId ? { ...n, read: true } : n))
    );
    if (socketRef.current?.connected) {
      socketRef.current.emit('mark_read', { notification_id: notificationId });
    }
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  const unreadCount = notifications.filter(n => !n.read).length;

  return {
    isConnected,
    connectionId,
    notifications,
    unreadCount,
    connect,
    disconnect,
    sendNotification,
    subscribe,
    unsubscribe,
    markAsRead,
    markAllAsRead,
    clearNotifications,
  };
}

// Notification bell component hook
export function useNotificationBell() {
  const [permission, setPermission] = useState<NotificationPermission>('default');
  const {
    isConnected,
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
  } = useWebSocket();

  useEffect(() => {
    if ('Notification' in window) {
      setPermission(Notification.permission);
    }
  }, []);

  const requestPermission = useCallback(async () => {
    if ('Notification' in window) {
      const result = await Notification.requestPermission();
      setPermission(result);
      return result;
    }
    return 'denied';
  }, []);

  const showLocalNotification = useCallback((title: string, options?: NotificationOptions) => {
    if (permission === 'granted') {
      new Notification(title, options);
    }
  }, [permission]);

  return {
    permission,
    requestPermission,
    showLocalNotification,
    isConnected,
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
  };
}

// Hook for real-time updates on specific resources
export function useRealtimeUpdates(
  resourceType: 'customers' | 'appointments' | 'inventory' | 'orders',
  resourceId?: string,
  onUpdate?: (data: unknown) => void
) {
  const { isConnected, subscribe, unsubscribe, sendNotification } = useWebSocket();

  useEffect(() => {
    if (!isConnected) return;

    const channel = resourceId
      ? `${resourceType}:${resourceId}`
      : resourceType;

    subscribe(channel);

    return () => {
      unsubscribe(channel);
    };
  }, [isConnected, resourceType, resourceId, subscribe, unsubscribe]);

  const requestUpdate = useCallback(() => {
    sendNotification('request_update', { resource_type: resourceType, resource_id: resourceId });
  }, [resourceType, resourceId, sendNotification]);

  return { requestUpdate };
}

export default useWebSocket;

