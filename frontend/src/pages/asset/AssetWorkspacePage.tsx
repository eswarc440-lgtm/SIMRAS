import { useState, useEffect } from 'react';
import { api } from '../../services/api';
import type { AssetSummary, TwinResponse } from '../../types/twin';
import type { EvidenceStateResponse } from '../../types/evidence';
import RealityTwinAssetViewer from '../../features/digital-twin/RealityTwinAssetViewer';
import BridgeEngineeringViewer from '../../features/digital-twin/BridgeEngineeringViewer';
import { SelectedAssetReports } from '../../features/reports/SelectedAssetReports';
import './AssetWorkspacePage.css';

type TabType = 'overview' | 'identity' | 'twin' | 'assessment' | 'inspections' | 'maintenance' | 'reports' | 'activity';

interface AssetWorkspacePageProps {
  assetCode: string;
}

export function AssetWorkspacePage({ assetCode }: AssetWorkspacePageProps) {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [asset, setAsset] = useState<AssetSummary | null>(null);
  const [twin, setTwin] = useState<TwinResponse | null>(null);
  const [evidenceState, setEvidenceState] = useState<EvidenceStateResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load asset data
  useEffect(() => {
    const loadAsset = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch asset summary
        const assetsResponse = await api.assets({ search: assetCode, limit: 1 });
        if (assetsResponse.items.length === 0) {
          throw new Error('Asset not found');
        }
        const foundAsset = assetsResponse.items[0];
        setAsset(foundAsset);

        // Fetch twin and evidence in parallel
        const [twinResult, evidenceResult] = await Promise.allSettled([
          api.twin(assetCode),
          api.state(assetCode),
        ]);

        if (twinResult.status === 'fulfilled') {
          setTwin(twinResult.value);
        }
        if (evidenceResult.status === 'fulfilled') {
          setEvidenceState(evidenceResult.value);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load asset');
      } finally {
        setLoading(false);
      }
    };

    loadAsset();
  }, [assetCode]);

  if (loading) {
    return (
      <div className="asset-workspace loading">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading asset workspace...</p>
        </div>
      </div>
    );
  }

  if (error || !asset) {
    return (
      <div className="asset-workspace error">
        <div className="error-state">
          <h2>Unable to load asset</h2>
          <p>{error || 'Asset not found'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="asset-workspace">
      {/* Header */}
      <div className="workspace-header">
        <div className="header-content">
          <div>
            <h1>{asset.name}</h1>
            <div className="asset-metadata">
              <span className="asset-code">{asset.asset_code}</span>
              <span className="asset-type">{asset.asset_type}</span>
              <span className="asset-district">{asset.district}</span>
            </div>
          </div>

          <div className="header-stats">
            <div className="stat">
              <span className="stat-label">Risk Level</span>
              <span className={`stat-value risk-${asset.risk_level?.toLowerCase()}`}>
                {asset.risk_level || 'UNKNOWN'}
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Risk Score</span>
              <span className="stat-value">{asset.risk_score ?? '--'}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Identity Status</span>
              <span className={`stat-value status-${asset.identity_status?.toLowerCase()}`}>
                {asset.identity_status}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="tab-navigation">
        <div className="tab-list">
          <button
            className={`tab-button ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            📋 Overview
          </button>
          <button
            className={`tab-button ${activeTab === 'identity' ? 'active' : ''}`}
            onClick={() => setActiveTab('identity')}
          >
            🏷️ Identity
          </button>
          <button
            className={`tab-button ${activeTab === 'twin' ? 'active' : ''}`}
            onClick={() => setActiveTab('twin')}
          >
            🔷 Digital Twin
          </button>
          <button
            className={`tab-button ${activeTab === 'assessment' ? 'active' : ''}`}
            onClick={() => setActiveTab('assessment')}
          >
            📊 Assessment
          </button>
          <button
            className={`tab-button ${activeTab === 'inspections' ? 'active' : ''}`}
            onClick={() => setActiveTab('inspections')}
          >
            🔍 Inspections
          </button>
          <button
            className={`tab-button ${activeTab === 'maintenance' ? 'active' : ''}`}
            onClick={() => setActiveTab('maintenance')}
          >
            🔧 Maintenance
          </button>
          <button
            className={`tab-button ${activeTab === 'reports' ? 'active' : ''}`}
            onClick={() => setActiveTab('reports')}
          >
            📄 Reports
          </button>
          <button
            className={`tab-button ${activeTab === 'activity' ? 'active' : ''}`}
            onClick={() => setActiveTab('activity')}
          >
            📝 Activity
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'overview' && (
          <div className="tab-pane overview-pane">
            <div className="overview-grid">
              <div className="overview-section">
                <h3>Asset Information</h3>
                <div className="info-row">
                  <span className="label">Asset Code:</span>
                  <span className="value">{asset.asset_code}</span>
                </div>
                <div className="info-row">
                  <span className="label">Name:</span>
                  <span className="value">{asset.name}</span>
                </div>
                <div className="info-row">
                  <span className="label">Type:</span>
                  <span className="value">{asset.asset_type}</span>
                </div>
                <div className="info-row">
                  <span className="label">District:</span>
                  <span className="value">{asset.district}</span>
                </div>
                <div className="info-row">
                  <span className="label">Owner:</span>
                  <span className="value">Not specified</span>
                </div>
              </div>

              <div className="overview-section">
                <h3>Risk Assessment</h3>
                <div className="info-row">
                  <span className="label">Risk Level:</span>
                  <span className={`value risk-${asset.risk_level?.toLowerCase()}`}>
                    {asset.risk_level || 'UNKNOWN'}
                  </span>
                </div>
                <div className="info-row">
                  <span className="label">Risk Score:</span>
                  <span className="value">{asset.risk_score ?? '--'}</span>
                </div>
                <div className="info-row">
                  <span className="label">Identity Status:</span>
                  <span className={`value status-${asset.identity_status?.toLowerCase()}`}>
                    {asset.identity_status}
                  </span>
                </div>
                <div className="info-row">
                  <span className="label">Last Updated:</span>
                  <span className="value">
                    {new Date().toLocaleDateString()}
                  </span>
                </div>
              </div>

              <div className="overview-section">
                <h3>Quick Actions</h3>
                <div className="action-buttons">
                  <button className="action-btn primary">
                    ✏️ Edit Asset
                  </button>
                  <button className="action-btn">
                    🔍 Schedule Inspection
                  </button>
                  <button className="action-btn">
                    🔧 Create Maintenance
                  </button>
                  <button className="action-btn">
                    📊 Generate Report
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'identity' && (
          <div className="tab-pane identity-pane">
            <div className="identity-section">
              <h3>Identity Information</h3>
              <div className="identity-form">
                <div className="form-row">
                  <div className="form-group">
                    <label>Official Name</label>
                    <input type="text" value={asset.name} readOnly />
                  </div>
                  <div className="form-group">
                    <label>Asset Type</label>
                    <input type="text" value={asset.asset_type} readOnly />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>District</label>
                    <input type="text" value={asset.district || ''} readOnly />
                  </div>
                  <div className="form-group">
                    <label>Owner / Authority</label>
                    <input type="text" value="Not specified" readOnly />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>Latitude</label>
                    <input type="number" value={asset.geometry.coordinates[1]} readOnly />
                  </div>
                  <div className="form-group">
                    <label>Longitude</label>
                    <input type="number" value={asset.geometry.coordinates[0]} readOnly />
                  </div>
                </div>

                <div className="form-group full-width">
                  <label>Description</label>
                  <textarea value={`${asset.asset_type} in ${asset.district}`} readOnly rows={3} />
                </div>

                <div className="notice">
                  <strong>Note:</strong> Identity information is locked. Contact your administrator to request changes.
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'twin' && (
          <div className="tab-pane twin-pane">
            {twin ? (
              <div className="twin-viewer">
                {asset.asset_code?.startsWith('AP_BR_') ? (
                  <BridgeEngineeringViewer assetCode={asset.asset_code} />
                ) : (
                  <RealityTwinAssetViewer assetCode={asset.asset_code} />
                )}
              </div>
            ) : (
              <div className="empty-state">
                <p>Digital Twin data is not available for this asset yet.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'assessment' && (
          <div className="tab-pane assessment-pane">
            {evidenceState ? (
              <div className="assessment-content">
                <h3>Assessment Details</h3>
                <div className="assessment-grid">
                  <div className="assessment-card">
                    <h4>Health Score</h4>
                    <div className="score-value">{evidenceState.health_score ?? '--'}</div>
                  </div>
                  <div className="assessment-card">
                    <h4>Risk Score</h4>
                    <div className="score-value">{evidenceState.risk_score ?? '--'}</div>
                  </div>
                  <div className="assessment-card">
                    <h4>Remaining Useful Life</h4>
                    <div className="score-value">{evidenceState.rul_years ?? '--'}</div>
                  </div>
                </div>
                <div className="assessment-notes">
                  <p>Assessment based on available evidence. Missing data marked as INSUFFICIENT_DATA.</p>
                </div>
              </div>
            ) : (
              <div className="empty-state">
                <p>Assessment data is loading or unavailable.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'inspections' && (
          <div className="tab-pane inspections-pane">
            <div className="inspections-content">
              <div className="section-header">
                <h3>Asset Inspections</h3>
                <button className="action-btn primary">
                  + Schedule Inspection
                </button>
              </div>
              <div className="inspections-list">
                <div className="empty-message">
                  <p>No inspections scheduled yet</p>
                  <p className="text-muted">Schedule an inspection to begin tracking asset condition</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'maintenance' && (
          <div className="tab-pane maintenance-pane">
            <div className="maintenance-content">
              <div className="section-header">
                <h3>Maintenance Plans</h3>
                <button className="action-btn primary">
                  + Create Maintenance Plan
                </button>
              </div>
              <div className="maintenance-list">
                <div className="empty-message">
                  <p>No maintenance plans created yet</p>
                  <p className="text-muted">Create a maintenance plan to track preventive and corrective actions</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'reports' && (
          <div className="tab-pane reports-pane">
            <SelectedAssetReports selected={asset} twin={twin} />
          </div>
        )}

        {activeTab === 'activity' && (
          <div className="tab-pane activity-pane">
            <div className="activity-log">
              <h3>Activity Log</h3>
              <div className="activity-list">
                <div className="activity-item">
                  <div className="activity-icon">📋</div>
                  <div className="activity-content">
                    <div className="activity-title">Asset created</div>
                    <div className="activity-meta">
                      by System • {new Date().toLocaleDateString()}
                    </div>
                  </div>
                </div>
                <div className="activity-item">
                  <div className="activity-icon">✅</div>
                  <div className="activity-content">
                    <div className="activity-title">Identity verified</div>
                    <div className="activity-meta">
                      by Officer • Last week
                    </div>
                  </div>
                </div>
              </div>
              <p className="activity-note">More activity items will appear as operations are performed.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
