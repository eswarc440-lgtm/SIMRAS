import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

interface AssetContextType {
  selectedAssetCode: string | null;
  setSelectedAssetCode: (code: string | null) => void;
}

const AssetContext = createContext<AssetContextType | undefined>(undefined);

export function AssetProvider({ children }: { children: ReactNode }) {
  const [selectedAssetCode, setSelectedAssetCodeInternal] = useState<string | null>(() => {
    // Initialize from URL params if available
    const params = new URLSearchParams(window.location.search);
    return params.get('asset');
  });

  // Sync state to URL when it changes
  const setSelectedAssetCode = (code: string | null) => {
    setSelectedAssetCodeInternal(code);
    
    // Update URL without reloading the page
    const url = new URL(window.location.href);
    if (code) {
      url.searchParams.set('asset', code);
    } else {
      url.searchParams.delete('asset');
    }
    window.history.replaceState({}, '', url);
  };

  // Listen for URL changes (e.g., browser back button)
  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      const assetFromUrl = params.get('asset');
      setSelectedAssetCodeInternal(assetFromUrl);
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  return (
    <AssetContext.Provider value={{ selectedAssetCode, setSelectedAssetCode }}>
      {children}
    </AssetContext.Provider>
  );
}

export function useSelectedAsset() {
  const context = useContext(AssetContext);
  if (!context) {
    throw new Error('useSelectedAsset must be used within AssetProvider');
  }
  return context;
}
