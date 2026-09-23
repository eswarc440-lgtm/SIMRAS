import { useState } from 'react';
import './AddInfrastructureWizard.css';

type InfrastructureCategory = 'DAM' | 'BARRAGE' | 'BRIDGE' | 'AIRPORT' | 'TEMPLE';
type WizardStep = 'identity' | 'engineering' | 'evidence' | 'review';

interface FormData {
  // Identity
  name: string;
  category: InfrastructureCategory | '';
  district: string;
  latitude: string;
  longitude: string;
  owner: string;
  description: string;

  // Engineering - Common
  builtYear: string;
  height: string;
  length: string;
  width: string;

  // Engineering - Dam/Barrage specific
  capacity: string;
  river: string;
  gateCount: string;
  spillway: string;

  // Engineering - Bridge specific
  spanCount: string;
  maxSpan: string;
  pillarCount: string;
  material: string;
  bridgeType: string;

  // Engineering - Airport specific
  icao: string;
  iata: string;
  commissioningYear: string;
  runwayCount: string;
  runwayLength: string;
  runwayWidth: string;
  pavement: string;
  terminal: string;

  // Engineering - Temple specific
  authority: string;
  heritageStatus: string;
  gopuram: string;
  compoundArea: string;
  structuralDescription: string;

  // Evidence
  evidenceSource: string;
  evidenceAuthority: string;
  evidenceUrl: string;
  evidenceDate: string;
  evidenceNotes: string;
}

interface AddInfrastructureWizardProps {
  onComplete?: () => void;
}

export function AddInfrastructureWizard({ onComplete }: AddInfrastructureWizardProps) {
  const [step, setStep] = useState<WizardStep>('identity');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<FormData>({
    name: '',
    category: '',
    district: '',
    latitude: '',
    longitude: '',
    owner: '',
    description: '',
    builtYear: '',
    height: '',
    length: '',
    width: '',
    capacity: '',
    river: '',
    gateCount: '',
    spillway: '',
    spanCount: '',
    maxSpan: '',
    pillarCount: '',
    material: '',
    bridgeType: '',
    icao: '',
    iata: '',
    commissioningYear: '',
    runwayCount: '',
    runwayLength: '',
    runwayWidth: '',
    pavement: '',
    terminal: '',
    authority: '',
    heritageStatus: '',
    gopuram: '',
    compoundArea: '',
    structuralDescription: '',
    evidenceSource: '',
    evidenceAuthority: '',
    evidenceUrl: '',
    evidenceDate: '',
    evidenceNotes: '',
  });

  const handleInputChange = (field: keyof FormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setError(null);
  };

  const validateStep = (currentStep: WizardStep): boolean => {
    if (currentStep === 'identity') {
      if (!formData.name.trim()) {
        setError('Infrastructure name is required');
        return false;
      }
      if (!formData.category) {
        setError('Category is required');
        return false;
      }
      if (!formData.district) {
        setError('District is required');
        return false;
      }
      if (!formData.latitude || !formData.longitude) {
        setError('Latitude and longitude are required');
        return false;
      }
      if (!formData.owner) {
        setError('Owner/Authority is required');
        return false;
      }
    }
    return true;
  };

  const handleNext = () => {
    if (validateStep(step)) {
      if (step === 'identity') setStep('engineering');
      else if (step === 'engineering') setStep('evidence');
      else if (step === 'evidence') setStep('review');
    }
  };

  const handleBack = () => {
    if (step === 'engineering') setStep('identity');
    else if (step === 'evidence') setStep('engineering');
    else if (step === 'review') setStep('evidence');
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);
      setError(null);

      const payload = {
        official_name: formData.name,
        asset_type: formData.category,
        district: formData.district,
        latitude: parseFloat(formData.latitude),
        longitude: parseFloat(formData.longitude),
        owning_authority: formData.owner,
        description: formData.description,
        construction_year: formData.builtYear ? parseInt(formData.builtYear) : null,
        material: formData.material || null,
      };

      const response = await fetch('/api/v1/assets/new', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to create infrastructure');
      }

      const result = await response.json();
      // Call the completion callback instead of navigating
      onComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const stepClasses = {
    identity: step === 'identity' ? 'active' : 'completed',
    engineering: step === 'engineering' ? 'active' : (step === 'evidence' || step === 'review') ? 'completed' : '',
    evidence: step === 'evidence' ? 'active' : step === 'review' ? 'completed' : '',
    review: step === 'review' ? 'active' : '',
  };

  return (
    <div className="wizard-page">
      <div className="wizard-container">
        {/* Wizard Header */}
        <div className="wizard-header">
          <h1>Add New Infrastructure</h1>
          <p>Create a new asset in the SIMRAS registry</p>
        </div>

        {/* Progress Indicator */}
        <div className="wizard-progress">
          <div className={`progress-step ${step === 'identity' ? 'active' : 'completed'}`}>
            <div className="step-number">1</div>
            <div className="step-label">Identity</div>
          </div>
          <div className="progress-line" />
          <div className={`progress-step ${step === 'engineering' ? 'active' : step === 'review' || step === 'evidence' ? 'completed' : ''}`}>
            <div className="step-number">2</div>
            <div className="step-label">Engineering</div>
          </div>
          <div className="progress-line" />
          <div className={`progress-step ${step === 'evidence' ? 'active' : step === 'review' ? 'completed' : ''}`}>
            <div className="step-number">3</div>
            <div className="step-label">Evidence</div>
          </div>
          <div className="progress-line" />
          <div className={`progress-step ${step === 'review' ? 'active' : ''}`}>
            <div className="step-number">4</div>
            <div className="step-label">Review</div>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="error-alert">
            <span>⚠️ {error}</span>
          </div>
        )}

        {/* Form Content */}
        <div className="wizard-form">
          {step === 'identity' && (
            <div className="form-step identity-step">
              <h2>Infrastructure Identity</h2>
              <div className="form-grid">
                <div className="form-group full-width">
                  <label>Infrastructure Name *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => handleInputChange('name', e.target.value)}
                    placeholder="e.g., Prakasam Barrage"
                  />
                </div>

                <div className="form-group">
                  <label>Category *</label>
                  <select
                    value={formData.category}
                    onChange={(e) => handleInputChange('category', e.target.value as InfrastructureCategory)}
                  >
                    <option value="">Select category</option>
                    <option value="DAM">Dam</option>
                    <option value="BARRAGE">Barrage</option>
                    <option value="BRIDGE">Bridge</option>
                    <option value="AIRPORT">Airport</option>
                    <option value="TEMPLE">Temple</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>District *</label>
                  <input
                    type="text"
                    value={formData.district}
                    onChange={(e) => handleInputChange('district', e.target.value)}
                    placeholder="e.g., Krishna"
                  />
                </div>

                <div className="form-group">
                  <label>Latitude *</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={formData.latitude}
                    onChange={(e) => handleInputChange('latitude', e.target.value)}
                    placeholder="16.5333"
                  />
                </div>

                <div className="form-group">
                  <label>Longitude *</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={formData.longitude}
                    onChange={(e) => handleInputChange('longitude', e.target.value)}
                    placeholder="80.8033"
                  />
                </div>

                <div className="form-group full-width">
                  <label>Owner / Authority *</label>
                  <input
                    type="text"
                    value={formData.owner}
                    onChange={(e) => handleInputChange('owner', e.target.value)}
                    placeholder="e.g., Andhra Pradesh WRID"
                  />
                </div>

                <div className="form-group full-width">
                  <label>Description</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => handleInputChange('description', e.target.value)}
                    placeholder="Brief description of the infrastructure"
                    rows={3}
                  />
                </div>
              </div>
            </div>
          )}

          {step === 'engineering' && (
            <div className="form-step engineering-step">
              <h2>Engineering Information</h2>
              <p className="step-subtitle">Fields relevant to {formData.category || 'the selected category'}</p>
              <div className="form-grid">
                {/* Common fields */}
                <div className="form-group">
                  <label>Built Year</label>
                  <input
                    type="number"
                    value={formData.builtYear}
                    onChange={(e) => handleInputChange('builtYear', e.target.value)}
                    placeholder="e.g., 1957"
                  />
                </div>

                <div className="form-group">
                  <label>Height (m)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.height}
                    onChange={(e) => handleInputChange('height', e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>Length (m)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.length}
                    onChange={(e) => handleInputChange('length', e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>Width (m)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.width}
                    onChange={(e) => handleInputChange('width', e.target.value)}
                  />
                </div>

                {/* Dam/Barrage */}
                {(formData.category === 'DAM' || formData.category === 'BARRAGE') && (
                  <>
                    <div className="form-group full-width">
                      <label>River Name</label>
                      <input
                        type="text"
                        value={formData.river}
                        onChange={(e) => handleInputChange('river', e.target.value)}
                      />
                    </div>
                    <div className="form-group">
                      <label>Capacity (MCM)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={formData.capacity}
                        onChange={(e) => handleInputChange('capacity', e.target.value)}
                      />
                    </div>
                    <div className="form-group">
                      <label>Gate Count</label>
                      <input
                        type="number"
                        value={formData.gateCount}
                        onChange={(e) => handleInputChange('gateCount', e.target.value)}
                      />
                    </div>
                  </>
                )}

                {/* Bridge */}
                {formData.category === 'BRIDGE' && (
                  <>
                    <div className="form-group">
                      <label>Span Count</label>
                      <input
                        type="number"
                        value={formData.spanCount}
                        onChange={(e) => handleInputChange('spanCount', e.target.value)}
                      />
                    </div>
                    <div className="form-group">
                      <label>Material</label>
                      <input
                        type="text"
                        value={formData.material}
                        onChange={(e) => handleInputChange('material', e.target.value)}
                        placeholder="e.g., RCC, Steel"
                      />
                    </div>
                  </>
                )}

                {/* Airport */}
                {formData.category === 'AIRPORT' && (
                  <>
                    <div className="form-group">
                      <label>ICAO Code</label>
                      <input
                        type="text"
                        value={formData.icao}
                        onChange={(e) => handleInputChange('icao', e.target.value)}
                      />
                    </div>
                    <div className="form-group">
                      <label>Runway Length (m)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={formData.runwayLength}
                        onChange={(e) => handleInputChange('runwayLength', e.target.value)}
                      />
                    </div>
                    <div className="form-group">
                      <label>Runway Width (m)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={formData.runwayWidth}
                        onChange={(e) => handleInputChange('runwayWidth', e.target.value)}
                      />
                    </div>
                  </>
                )}

                {/* Temple */}
                {formData.category === 'TEMPLE' && (
                  <>
                    <div className="form-group full-width">
                      <label>Authority</label>
                      <input
                        type="text"
                        value={formData.authority}
                        onChange={(e) => handleInputChange('authority', e.target.value)}
                      />
                    </div>
                    <div className="form-group">
                      <label>Heritage Status</label>
                      <input
                        type="text"
                        value={formData.heritageStatus}
                        onChange={(e) => handleInputChange('heritageStatus', e.target.value)}
                      />
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {step === 'evidence' && (
            <div className="form-step evidence-step">
              <h2>Evidence & Documentation</h2>
              <p className="step-subtitle">Provide official source information</p>
              <div className="form-grid">
                <div className="form-group full-width">
                  <label>Official Source</label>
                  <input
                    type="text"
                    value={formData.evidenceSource}
                    onChange={(e) => handleInputChange('evidenceSource', e.target.value)}
                    placeholder="e.g., Andhra Pradesh WRID"
                  />
                </div>

                <div className="form-group full-width">
                  <label>Authority</label>
                  <input
                    type="text"
                    value={formData.evidenceAuthority}
                    onChange={(e) => handleInputChange('evidenceAuthority', e.target.value)}
                    placeholder="e.g., Department of Water Resources"
                  />
                </div>

                <div className="form-group full-width">
                  <label>Evidence URL</label>
                  <input
                    type="url"
                    value={formData.evidenceUrl}
                    onChange={(e) => handleInputChange('evidenceUrl', e.target.value)}
                    placeholder="https://example.com/document"
                  />
                </div>

                <div className="form-group">
                  <label>Evidence Date</label>
                  <input
                    type="date"
                    value={formData.evidenceDate}
                    onChange={(e) => handleInputChange('evidenceDate', e.target.value)}
                  />
                </div>

                <div className="form-group full-width">
                  <label>Notes</label>
                  <textarea
                    value={formData.evidenceNotes}
                    onChange={(e) => handleInputChange('evidenceNotes', e.target.value)}
                    placeholder="Additional notes about the evidence source"
                    rows={3}
                  />
                </div>
              </div>
            </div>
          )}

          {step === 'review' && (
            <div className="form-step review-step">
              <h2>Review & Submit</h2>
              <p className="step-subtitle">Please review the information before submitting</p>
              
              <div className="review-sections">
                <div className="review-section">
                  <h3>Identity Information</h3>
                  <div className="review-item">
                    <span className="label">Name:</span>
                    <span className="value">{formData.name}</span>
                  </div>
                  <div className="review-item">
                    <span className="label">Category:</span>
                    <span className="value">{formData.category}</span>
                  </div>
                  <div className="review-item">
                    <span className="label">District:</span>
                    <span className="value">{formData.district}</span>
                  </div>
                  <div className="review-item">
                    <span className="label">Location:</span>
                    <span className="value">{formData.latitude}, {formData.longitude}</span>
                  </div>
                  <div className="review-item">
                    <span className="label">Owner:</span>
                    <span className="value">{formData.owner}</span>
                  </div>
                </div>

                {formData.builtYear && (
                  <div className="review-section">
                    <h3>Engineering Data</h3>
                    {formData.builtYear && (
                      <div className="review-item">
                        <span className="label">Built Year:</span>
                        <span className="value">{formData.builtYear}</span>
                      </div>
                    )}
                    {formData.height && (
                      <div className="review-item">
                        <span className="label">Height:</span>
                        <span className="value">{formData.height} m</span>
                      </div>
                    )}
                    {formData.length && (
                      <div className="review-item">
                        <span className="label">Length:</span>
                        <span className="value">{formData.length} m</span>
                      </div>
                    )}
                  </div>
                )}

                <div className="review-notice">
                  <strong>Important:</strong> After submission, this infrastructure will enter the review queue. A reviewer will verify the information and approve it for inclusion in the registry.
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Form Actions */}
        <div className="wizard-actions">
          <button
            className="btn-secondary"
            onClick={handleBack}
            disabled={step === 'identity' || loading}
          >
            ← Back
          </button>

          {step === 'review' ? (
            <button
              className="btn-primary"
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? 'Submitting...' : 'Submit for Review'}
            </button>
          ) : (
            <button
              className="btn-primary"
              onClick={handleNext}
              disabled={loading}
            >
              Next →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
