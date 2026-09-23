import './Breadcrumb.css';

interface BreadcrumbItem {
  label: string;
  action?: () => void;
  isActive?: boolean;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
}

export function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <nav className="breadcrumb" aria-label="Breadcrumb navigation">
      <ol className="breadcrumb-list">
        {items.map((item, index) => (
          <li key={index} className="breadcrumb-item">
            {item.action && !item.isActive ? (
              <>
                <button
                  className="breadcrumb-link"
                  onClick={item.action}
                >
                  {item.label}
                </button>
                {index < items.length - 1 && (
                  <span className="breadcrumb-separator">/</span>
                )}
              </>
            ) : (
              <>
                <span className={`breadcrumb-text ${item.isActive ? 'active' : ''}`}>
                  {item.label}
                </span>
              </>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
