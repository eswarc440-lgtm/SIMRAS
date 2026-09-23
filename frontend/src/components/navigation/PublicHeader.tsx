import './PublicHeader.css';

interface PublicHeaderProps {
  onLoginClick?: () => void;
}

export function PublicHeader({ onLoginClick }: PublicHeaderProps) {
  return (
    <header className="public-header">
      <div className="header-container">
        {/* Logo */}
        <div className="header-logo">
          <span className="logo-icon">🏗️</span>
          <span className="logo-text">SIMRAS</span>
        </div>

        {/* Navigation */}
        <nav className="header-nav">
          <a href="#gis" className="nav-link">
            GIS Command
          </a>
          <a href="#digital-twin" className="nav-link">
            Digital Twin
          </a>
          <a href="#reports" className="nav-link">
            Reports
          </a>
        </nav>

        {/* Officer Login */}
        <div className="header-actions">
          <button 
            onClick={onLoginClick}
            className="officer-login-btn"
          >
            Officer Login
          </button>
        </div>
      </div>
    </header>
  );
}
