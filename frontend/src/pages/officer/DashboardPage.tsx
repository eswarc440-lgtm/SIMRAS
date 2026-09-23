import { useEffect, useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useNotifications } from '../../contexts/NotificationContext';
import './DashboardPage.css';

interface DashboardMetrics {
  assigned_assets: number;
  inspection_due: number;
  inspection_overdue: number;
  maintenance_scheduled: number;
  maintenance_overdue: number;
  pending_reviews: number;
  high_risk_assets: number;
}

interface DashboardPageProps {
  onNavigate?: (page: string) => void;
}

export function DashboardPage({ onNavigate }: DashboardPageProps) {
  const { user, logout } = useAuth();
  const { unreadCount } = useNotifications();
  const [metrics, setMetrics] = useState<DashboardMetrics>({
    assigned_assets: 0,
    inspection_due: 0,
    inspection_overdue: 0,
    maintenance_scheduled: 0,
    maintenance_overdue: 0,
    pending_reviews: 0,
    high_risk_assets: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load dashboard metrics
  useEffect(() => {
    const loadMetrics = async () => {
      try {
        setLoading(true);
        // TODO: Implement API endpoint to get dashboard metrics
        // For now, these are placeholder values
        await new Promise(resolve => setTimeout(resolve, 500));
        
        setMetrics({
          assigned_assets: 12,
          inspection_due: 3,
          inspection_overdue: 1,
          maintenance_scheduled: 5,
          maintenance_overdue: 2,
          pending_reviews: 4,
          high_risk_assets: 2,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard');
      } finally {
        setLoading(false);
      }
    };

    loadMetrics();
  }, []);

  const handleNavigation = (page: string) => {
    onNavigate?.(page);
  };

  return (
    <div className="officer-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <div>
          <h1>Officer Dashboard</h1>
          <p className="dashboard-subtitle">
            Welcome back, {user?.name}. Here's your infrastructure overview.
          </p>
        </div>
        <div className="officer-info">
          <div className="info-card">
            <div className="info-label">Officer ID</div>
            <div className="info-value">{user?.officer_id}</div>
          </div>
          <div className="info-card">
            <div className="info-label">Department</div>
            <div className="info-value">{user?.department || 'N/A'}</div>
          </div>
          <div className="info-card">
            <div className="info-label">District</div>
            <div className="info-value">{user?.district || 'All'}</div>
          </div>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
        </div>
      )}

      {/* Metric Cards */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Assigned Assets</div>
          <div className="metric-value">{metrics.assigned_assets}</div>
          <button className="metric-link" onClick={() => handleNavigation('GIS')}>View all →</button>
        </div>

        <div className="metric-card urgent">
          <div className="metric-label">Inspections Due</div>
          <div className="metric-value">{metrics.inspection_due}</div>
          <button className="metric-link" onClick={() => handleNavigation('INSPECTIONS')}>View due →</button>
        </div>

        <div className="metric-card critical">
          <div className="metric-label">Inspections Overdue</div>
          <div className="metric-value">{metrics.inspection_overdue}</div>
          <button className="metric-link" onClick={() => handleNavigation('INSPECTIONS')}>View overdue →</button>
        </div>

        <div className="metric-card">
          <div className="metric-label">Maintenance Scheduled</div>
          <div className="metric-value">{metrics.maintenance_scheduled}</div>
          <button className="metric-link" onClick={() => handleNavigation('MAINTENANCE')}>View scheduled →</button>
        </div>

        <div className="metric-card urgent">
          <div className="metric-label">Maintenance Overdue</div>
          <div className="metric-value">{metrics.maintenance_overdue}</div>
          <button className="metric-link" onClick={() => handleNavigation('MAINTENANCE')}>View overdue →</button>
        </div>

        <div className="metric-card">
          <div className="metric-label">Pending Reviews</div>
          <div className="metric-value">{metrics.pending_reviews}</div>
          <button className="metric-link" onClick={() => handleNavigation('GIS')}>Review queue →</button>
        </div>

        <div className="metric-card">
          <div className="metric-label">Unread Notifications</div>
          <div className="metric-value">{unreadCount}</div>
          <button className="metric-link" onClick={() => handleNavigation('NOTIFICATIONS')}>View all →</button>
        </div>

        <div className="metric-card critical">
          <div className="metric-label">High Risk Assets</div>
          <div className="metric-value">{metrics.high_risk_assets}</div>
          <button className="metric-link" onClick={() => handleNavigation('GIS')}>View map →</button>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions">
        <h2>Quick Actions</h2>
        <div className="action-buttons">
          <button 
            className="action-button primary"
            onClick={() => handleNavigation('ADD_INFRASTRUCTURE')}
          >
            + Add Infrastructure
          </button>
          <button className="action-button">
            + Schedule Inspection
          </button>
          <button className="action-button">
            + Create Maintenance Plan
          </button>
          <button 
            className="action-button"
            onClick={() => handleNavigation('GIS')}
          >
            📍 View GIS Map
          </button>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="recent-activity">
        <h2>Recent Activity</h2>
        <div className="activity-list">
          <div className="activity-item">
            <div className="activity-icon">📋</div>
            <div className="activity-content">
              <div className="activity-title">AP_BR_00042 submitted for review</div>
              <div className="activity-time">2 hours ago</div>
            </div>
          </div>
          <div className="activity-item">
            <div className="activity-icon">✅</div>
            <div className="activity-content">
              <div className="activity-title">AP_DAM_00001 approved</div>
              <div className="activity-time">1 day ago</div>
            </div>
          </div>
          <div className="activity-item">
            <div className="activity-icon">🔍</div>
            <div className="activity-content">
              <div className="activity-title">Inspection INS_00127 completed</div>
              <div className="activity-time">2 days ago</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
