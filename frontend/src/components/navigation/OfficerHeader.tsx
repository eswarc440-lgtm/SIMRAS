import { useAuth } from '../../contexts/AuthContext';
import { useNotifications } from '../../contexts/NotificationContext';
import { useState, useRef, useEffect } from 'react';
import './OfficerHeader.css';

interface OfficerHeaderProps {
  onNavigate?: (page: string) => void;
}

// Format notification time (e.g., "2 hours ago", "just now")
function formatNotificationTime(date: Date): string {
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  
  return date.toLocaleDateString();
}

export function OfficerHeader({ onNavigate }: OfficerHeaderProps) {
  const { user, logout } = useAuth();
  const { unreadCount, notifications, markRead, refreshNotifications, notificationSound, setNotificationSound } = useNotifications();
  const [showNotificationDropdown, setShowNotificationDropdown] = useState(false);
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const notificationRef = useRef<HTMLDivElement>(null);
  const userRef = useRef<HTMLDivElement>(null);

  // Close dropdowns when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (notificationRef.current && !notificationRef.current.contains(event.target as Node)) {
        setShowNotificationDropdown(false);
      }
      if (userRef.current && !userRef.current.contains(event.target as Node)) {
        setShowUserDropdown(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    await logout();
    // Navigate back to home via callback
    onNavigate?.('GIS');
  };

  const handleNotificationClick = (notification: any) => {
    if (!notification.is_read) {
      markRead(notification.id);
    }
    if (notification.link) {
      onNavigate?.(notification.link);
      setShowNotificationDropdown(false);
    }
  };

  return (
    <header className="officer-header">
      <div className="header-container">
        {/* Logo */}
        <button 
          className="header-logo"
          onClick={() => onNavigate?.('DASHBOARD')}
          style={{ background: 'none', border: 'none', cursor: 'pointer' }}
        >
          <span className="logo-icon">🏗️</span>
          <span className="logo-text">SIMRAS Officer Workspace</span>
        </button>

        {/* Navigation */}
        <nav className="header-nav">
          <button 
            className="nav-link"
            onClick={() => onNavigate?.('DASHBOARD')}
          >
            Dashboard
          </button>
          <button 
            className="nav-link"
            onClick={() => onNavigate?.('GIS')}
          >
            GIS
          </button>
          <button 
            className="nav-link"
            onClick={() => onNavigate?.('TWIN')}
          >
            Digital Twin
          </button>
          <button 
            className="nav-link"
            onClick={() => onNavigate?.('INSPECTIONS')}
          >
            Inspections
          </button>
          <button 
            className="nav-link"
            onClick={() => onNavigate?.('MAINTENANCE')}
          >
            Maintenance
          </button>
          <button 
            className="nav-link"
            onClick={() => onNavigate?.('REPORTS')}
          >
            Reports
          </button>
          <button 
            className="nav-link"
            onClick={() => onNavigate?.('DASHBOARD')}
          >
            Reviews
          </button>
        </nav>

        {/* Actions */}
        <div className="header-actions">
          {/* Add Infrastructure Button */}
          <button 
            className="add-infrastructure-btn"
            onClick={() => onNavigate?.('ADD_INFRASTRUCTURE')}
          >
            + Add Infrastructure
          </button>

          {/* Notifications Bell */}
          <div className="notification-container" ref={notificationRef}>
            <button 
              className="notification-bell"
              onClick={() => {
                setShowNotificationDropdown(!showNotificationDropdown);
                refreshNotifications();
              }}
              aria-label={`${unreadCount} unread notifications`}
            >
              🔔
              {unreadCount > 0 && (
                <span className="notification-badge">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>

            {showNotificationDropdown && (
              <div className="notification-dropdown">
                <div className="dropdown-header">
                  <h3>Notifications</h3>
                  <div className="dropdown-controls">
                    {unreadCount > 0 && (
                      <button 
                        className="mark-all-read-btn"
                        onClick={() => {
                          // Mark all read implementation
                        }}
                      >
                        Mark all read
                      </button>
                    )}
                    <button 
                      className="sound-toggle-btn"
                      onClick={() => setNotificationSound(!notificationSound)}
                      title={notificationSound ? 'Sound on' : 'Sound off'}
                    >
                      {notificationSound ? '🔔' : '🔕'}
                    </button>
                  </div>
                </div>

                <div className="notification-list">
                  {notifications.length === 0 ? (
                    <div className="empty-state">
                      <p>No notifications yet</p>
                    </div>
                  ) : (
                    notifications.slice(0, 10).map(notification => (
                      <div
                        key={notification.id}
                        className={`notification-item ${!notification.is_read ? 'unread' : ''} severity-${notification.severity?.toLowerCase()}`}
                        onClick={() => handleNotificationClick(notification)}
                      >
                        <div className="notification-icon">
                          {notification.severity === 'CRITICAL' ? '🔴' :
                           notification.severity === 'HIGH' ? '🟠' :
                           notification.severity === 'MEDIUM' ? '🟡' :
                           notification.severity === 'LOW' ? '🟢' : '⚪'}
                        </div>
                        <div className="notification-content">
                          <div className="notification-title">{notification.title}</div>
                          <div className="notification-message">{notification.message}</div>
                          <div className="notification-time">
                            {formatNotificationTime(new Date(notification.created_at))}
                          </div>
                        </div>
                        {!notification.is_read && <div className="unread-indicator" />}
                      </div>
                    ))
                  )}
                </div>

                <div className="dropdown-footer">
                  <button 
                    className="view-all-link"
                    onClick={() => {
                      onNavigate?.('NOTIFICATIONS');
                      setShowNotificationDropdown(false);
                    }}
                  >
                    View all notifications →
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* User Profile */}
          <div className="user-container" ref={userRef}>
            <button 
              className="user-profile-btn"
              onClick={() => setShowUserDropdown(!showUserDropdown)}
            >
              <span className="user-avatar">{user?.name?.[0]?.toUpperCase() || 'O'}</span>
              <span className="user-name">{user?.name || 'Officer'}</span>
            </button>

            {showUserDropdown && (
              <div className="user-dropdown">
                <div className="dropdown-header">
                  <div className="user-info">
                    <div className="user-name-full">{user?.name}</div>
                    <div className="user-role">{user?.role}</div>
                  </div>
                </div>

                <div className="dropdown-divider" />

                <button 
                  className="dropdown-link"
                  onClick={() => {
                    // Profile settings
                  }}
                >
                  Profile Settings
                </button>
                <button 
                  className="dropdown-link"
                  onClick={() => {
                    // API keys
                  }}
                >
                  API Keys
                </button>
                <button 
                  className="dropdown-link"
                  onClick={() => {
                    // Preferences
                  }}
                >
                  Preferences
                </button>

                <div className="dropdown-divider" />

                <button 
                  className="logout-btn"
                  onClick={handleLogout}
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
