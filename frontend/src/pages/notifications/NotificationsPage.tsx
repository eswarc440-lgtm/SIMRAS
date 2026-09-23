import { useEffect, useState } from 'react';
import { useNotifications } from '../../contexts/NotificationContext';
import './NotificationsPage.css';

type FilterType = 'all' | 'unread' | 'risk' | 'inspections' | 'maintenance' | 'assets' | 'plans' | 'evidence';

export function NotificationsPage() {
  const { notifications, refreshNotifications, markRead, markAllRead } = useNotifications();
  const [filter, setFilter] = useState<FilterType>('all');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    refreshNotifications().finally(() => setLoading(false));
  }, [refreshNotifications]);

  const filteredNotifications = notifications.filter(n => {
    if (filter === 'unread') return !n.is_read;
    if (filter === 'risk') return n.notification_type.includes('RISK');
    if (filter === 'inspections') return n.notification_type.includes('INSPECTION');
    if (filter === 'maintenance') return n.notification_type.includes('MAINTENANCE');
    if (filter === 'assets') return n.notification_type.includes('ASSET');
    if (filter === 'plans') return n.notification_type.includes('PLAN');
    if (filter === 'evidence') return n.notification_type.includes('EVIDENCE');
    return true;
  });

  const handleNotificationClick = (notification: any) => {
    if (!notification.is_read) {
      markRead(notification.id);
    }
    if (notification.link) {
      // Navigate to the notification link
      window.location.href = notification.link;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return '#e74c3c';
      case 'HIGH':
        return '#f39c12';
      case 'MEDIUM':
        return '#3498db';
      case 'LOW':
        return '#27ae60';
      default:
        return '#95a5a6';
    }
  };

  const getSeverityLabel = (severity: string) => {
    return severity[0] + severity.slice(1).toLowerCase();
  };

  return (
    <div className="notifications-page">
      <div className="notifications-container">
        {/* Header */}
        <div className="notifications-header">
          <div>
            <h1>Notifications</h1>
            <p className="header-subtitle">Stay updated on infrastructure changes</p>
          </div>
          {notifications.some(n => !n.is_read) && (
            <button 
              className="mark-all-btn"
              onClick={markAllRead}
            >
              Mark all as read
            </button>
          )}
        </div>

        {/* Filters */}
        <div className="notification-filters">
          <button
            className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          <button
            className={`filter-btn ${filter === 'unread' ? 'active' : ''}`}
            onClick={() => setFilter('unread')}
          >
            Unread
          </button>
          <button
            className={`filter-btn ${filter === 'risk' ? 'active' : ''}`}
            onClick={() => setFilter('risk')}
          >
            Risk
          </button>
          <button
            className={`filter-btn ${filter === 'inspections' ? 'active' : ''}`}
            onClick={() => setFilter('inspections')}
          >
            Inspections
          </button>
          <button
            className={`filter-btn ${filter === 'maintenance' ? 'active' : ''}`}
            onClick={() => setFilter('maintenance')}
          >
            Maintenance
          </button>
          <button
            className={`filter-btn ${filter === 'assets' ? 'active' : ''}`}
            onClick={() => setFilter('assets')}
          >
            Assets
          </button>
          <button
            className={`filter-btn ${filter === 'plans' ? 'active' : ''}`}
            onClick={() => setFilter('plans')}
          >
            Plans
          </button>
          <button
            className={`filter-btn ${filter === 'evidence' ? 'active' : ''}`}
            onClick={() => setFilter('evidence')}
          >
            Evidence
          </button>
        </div>

        {/* Notifications List */}
        <div className="notifications-list">
          {loading ? (
            <div className="loading-state">Loading notifications...</div>
          ) : filteredNotifications.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📭</div>
              <h3>No notifications</h3>
              <p>You're all caught up! Check back later.</p>
            </div>
          ) : (
            filteredNotifications.map(notification => (
              <div
                key={notification.id}
                className={`notification-card ${!notification.is_read ? 'unread' : ''}`}
                onClick={() => handleNotificationClick(notification)}
              >
                <div className="notification-header">
                  <div className="notification-title">
                    <span
                      className="severity-badge"
                      style={{ background: getSeverityColor(notification.severity) }}
                      title={notification.severity}
                    >
                      {notification.severity[0]}
                    </span>
                    <span className="title-text">{notification.title}</span>
                  </div>
                  <div className="notification-time">
                    {new Date(notification.created_at).toLocaleString()}
                  </div>
                </div>

                <div className="notification-body">
                  <p className="message">{notification.message}</p>

                  <div className="notification-meta">
                    <span className="type-badge">{notification.notification_type}</span>
                    {notification.asset_id && <span className="meta-badge">Asset</span>}
                    {notification.inspection_id && <span className="meta-badge">Inspection</span>}
                    {notification.maintenance_id && <span className="meta-badge">Maintenance</span>}
                    {notification.plan_id && <span className="meta-badge">Plan</span>}
                  </div>

                  {notification.link && (
                    <div className="notification-action">
                      <button className="action-link">
                        View details →
                      </button>
                    </div>
                  )}
                </div>

                {!notification.is_read && <div className="unread-indicator" />}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
