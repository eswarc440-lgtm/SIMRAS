import { createContext, useContext, useState, useEffect, useCallback, ReactNode, useRef } from 'react';
import { useAuth } from './AuthContext';

interface Notification {
  id: number;
  user_id: number;
  notification_type: string;
  severity: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  title: string;
  message: string;
  asset_id: number | null;
  inspection_id: number | null;
  maintenance_id: number | null;
  plan_id: number | null;
  link: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
  updated_at: string;
}

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  loading: boolean;
  error: string | null;
  refreshNotifications: () => Promise<void>;
  refreshUnreadCount: () => Promise<void>;
  markRead: (id: number) => Promise<void>;
  markAllRead: () => Promise<void>;
  playNotificationSound: (severity?: string) => void;
  notificationSound: boolean;
  setNotificationSound: (enabled: boolean) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function NotificationProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);
  const [notificationSound, setNotificationSound] = useState(true);
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastRefreshRef = useRef<number>(0);

  // Play notification sound with severity levels
  const playNotificationSound = useCallback((severity: string = 'MEDIUM') => {
    if (!notificationSound) return;

    try {
      // Create audio context for notification sound
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const now = audioContext.currentTime;

      // Different beep patterns based on severity
      const frequencies = {
        'INFO': [800],
        'LOW': [600],
        'MEDIUM': [800, 600],
        'HIGH': [1000, 800, 600],
        'CRITICAL': [1200, 1000, 800, 600],
      };

      const freqs = (frequencies as Record<string, number[]>)[severity] || [800];
      let time = now;

      for (const freq of freqs) {
        const osc = audioContext.createOscillator();
        const gain = audioContext.createGain();

        osc.connect(gain);
        gain.connect(audioContext.destination);

        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.1, time);
        gain.gain.exponentialRampToValueAtTime(0.01, time + 0.1);

        osc.start(time);
        osc.stop(time + 0.1);

        time += 0.15;
      }
    } catch (err) {
      // Silently fail if audio context not available
    }
  }, [notificationSound]);

  // Refresh notifications list with debouncing
  const refreshNotifications = useCallback(async () => {
    if (!isAuthenticated) return;

    try {
      setLoading(true);
      const response = await fetch('/api/v1/notifications?limit=50&offset=0', {
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setNotifications(data);
        setError(null);
      } else if (response.status !== 401) {
        setError('Failed to load notifications');
      }
    } catch (err) {
      console.error('Error fetching notifications:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  // Refresh unread count with debouncing to prevent excessive API calls
  const refreshUnreadCount = useCallback(async () => {
    if (!isAuthenticated) return;

    // Debounce: don't refresh more than once per 2 seconds
    const now = Date.now();
    if (now - lastRefreshRef.current < 2000) {
      return;
    }

    lastRefreshRef.current = now;

    try {
      const response = await fetch('/api/v1/notifications/unread-count', {
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        const newCount = data.count;

        // Play sound only if count increased (new notifications)
        if (newCount > unreadCount) {
          playNotificationSound('MEDIUM');
        }

        setUnreadCount(newCount);
      } else if (response.status !== 401) {
        setUnreadCount(0);
      }
    } catch (err) {
      console.error('Error fetching unread count:', err);
    }
  }, [isAuthenticated, unreadCount, playNotificationSound]);

  // Mark single notification as read
  const markRead = useCallback(async (id: number) => {
    try {
      const response = await fetch(`/api/v1/notifications/${id}/read`, {
        method: 'POST',
        credentials: 'include',
      });

      if (response.ok) {
        setNotifications(prev =>
          prev.map(n =>
            n.id === id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n
          )
        );
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
    } catch (err) {
      console.error('Error marking notification as read:', err);
    }
  }, []);

  // Mark all notifications as read
  const markAllRead = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/notifications/read-all', {
        method: 'POST',
        credentials: 'include',
      });

      if (response.ok) {
        setNotifications(prev =>
          prev.map(n => ({ ...n, is_read: true, read_at: new Date().toISOString() }))
        );
        setUnreadCount(0);
      }
    } catch (err) {
      console.error('Error marking all notifications as read:', err);
    }
  }, []);

  // Initial load when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      refreshNotifications();
      refreshUnreadCount();
    } else {
      // Clear when logged out
      setNotifications([]);
      setUnreadCount(0);
      setError(null);
    }
  }, [isAuthenticated, refreshNotifications, refreshUnreadCount]);

  // Setup polling
  useEffect(() => {
    if (!isAuthenticated) {
      if (pollingInterval) {
        clearInterval(pollingInterval);
        setPollingInterval(null);
      }
      return;
    }

    const interval = setInterval(() => {
      refreshUnreadCount();
    }, 30000); // Poll every 30 seconds

    setPollingInterval(interval);

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [isAuthenticated, refreshUnreadCount]);

  // Refresh on focus
  useEffect(() => {
    if (!isAuthenticated) return;

    const handleFocus = () => {
      refreshUnreadCount();
    };

    window.addEventListener('focus', handleFocus);
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        refreshUnreadCount();
      }
    });

    return () => {
      window.removeEventListener('focus', handleFocus);
    };
  }, [isAuthenticated, refreshUnreadCount]);

  const value: NotificationContextType = {
    notifications,
    unreadCount,
    loading,
    error,
    refreshNotifications,
    refreshUnreadCount,
    markRead,
    markAllRead,
    playNotificationSound,
    notificationSound,
    setNotificationSound,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within NotificationProvider');
  }
  return context;
}
