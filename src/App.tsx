import { fetchSession } from "./services/session";
﻿import React, { useEffect, useState } from "react";
import { PublicHeader, PublicTab } from "./components/common/PublicHeader";
import { OfficerHeader } from "./components/common/OfficerHeader";
import { OfficerSidebar, OfficerTab } from "./components/common/OfficerSidebar";
import { PublicHome } from "./components/PublicHome";
import { GISCommandView } from "./components/GISCommandView";
import { DigitalTwinPage } from "./components/DigitalTwinPage";
import { PublicReportsPage } from "./components/PublicReportsPage";
import { OfficerDashboard } from "./components/OfficerDashboard";
import { OfficerAssetTable } from "./components/OfficerAssetTable";
import { OfficerLoginPage } from "./components/OfficerLoginPage";
import { AddAssetWizard } from "./components/AddAssetWizard";
import { InspectionsManager } from "./components/InspectionsManager";
import { MaintenancePlanner } from "./components/MaintenancePlanner";
import { ReviewQueue } from "./components/ReviewQueue";
import { ProfilePage } from "./components/ProfilePage";
import { SettingsPage } from "./components/SettingsPage";
import { CitizenObservationModal } from "./features/digital-twin/CitizenObservationModal";
import { NotificationModal } from "./components/NotificationModal";
import { AiAssistantDrawer } from "./components/AiAssistantDrawer";
import { useSelectedAsset } from "./hooks/useSelectedAsset";
import type { SearchResult } from "./components/common/searchModel";

import type { AssetSummary, MapFeatureCollection, TwinResponse } from "./types/twin";
import { api } from "./services/simrasTwinApi";

type Workspace = "PUBLIC" | "OFFICER" | "LOGIN";

const emptyMapFeatures: MapFeatureCollection = {
  type: "FeatureCollection",
  features: [],
  total: 0,
  limit: 5000,
  offset: 0,
};

export default function App() {
  const [workspace, setWorkspace] = useState<Workspace>("PUBLIC");
  const [publicTab, setPublicTab] = useState<PublicTab>("home");
  const [officerTab, setOfficerTab] = useState<OfficerTab>("dashboard");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Asset State
  const [assets, setAssets] = useState<AssetSummary[]>([]);
  const [registryCount, setRegistryCount] = useState(0);
  const [assetSuccess, setAssetSuccess] = useState<string | null>(null);
  const { selectedAsset, selectAsset } = useSelectedAsset(assets);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  // Geospatial background features
  const [mapFeatures, setMapFeatures] = useState<MapFeatureCollection>(emptyMapFeatures);

  // Modals & Drawers
  const [isAiOpen, setIsAiOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isCitizenReportOpen, setIsCitizenReportOpen] = useState(false);
  const [unreadNotifications, setUnreadNotifications] = useState(0);

  // Auth User Profile
  const [currentUser, setCurrentUser] = useState<{
    id: string;
    email: string;
    name: string;
    role: "PUBLIC" | "OFFICER" | "REVIEWER" | "ADMIN";
    department: string;
  } | null>(null);
  useEffect(() => {
    if (!localStorage.getItem('simras_token')) return;
    let active = true;
    fetchSession().then(user => { if (active) { setCurrentUser(user); if (user.role !== 'PUBLIC') setWorkspace('OFFICER'); } }).catch(() => { if (active) setCurrentUser(null); });
    return () => { active = false; };
  },[]);

  // 1. Initial Data Ingestion
  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    Promise.all([
      fetch("/api/v1/assets?limit=1000")
        .then(async (r) => {
          if (!r.ok) throw new Error(`Asset registry request failed: ${r.status}`);
          const data = await r.json();
          return {
            items: Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : [],
            total: typeof data?.total === "number" ? data.total : Array.isArray(data) ? data.length : 0,
          };
        })
        .catch((err) => {
          console.error("Asset registry load failed:", err);
          return { items: [], total: 0 };
        }),
      fetch("/api/v1/map/features?limit=2500")
        .then((r) => (r.ok ? r.json() : emptyMapFeatures))
        .catch(() => emptyMapFeatures),
      fetch("/api/v1/notifications/unread-count")
        .then((r) => (r.ok ? r.json() : { count: 0 }))
        .catch(() => ({ count: 0 })),
    ])
      .then(([assetResult, features, notifCount]) => {
        if (!isMounted) return;

        if (Array.isArray(assetResult.items) && assetResult.items.length > 0) {
          setAssets(assetResult.items);
          setRegistryCount(assetResult.total);
          selectAsset(assetResult.items[0]);
          setError(null);
        } else {
          setError("Infrastructure registry returned no assets.");
        }

        if (features && Array.isArray(features.features)) {
          setMapFeatures(features);
        }

        if (notifCount?.count != null) {
          setUnreadNotifications(notifCount.count);
        }

        setLoading(false);
      })
      .catch((err) => {
        if (isMounted) {
          console.error("Failed to load SIMRAS initial state:", err);
          setError("Failed to load infrastructure data. Please check network connection.");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!currentUser) return;
    const refresh = () => {
      const token = localStorage.getItem("simras_token");
      return fetch("/api/v1/notifications/unread-count", { headers: token ? { Authorization: `Bearer ${token}` } : {} }).then((response) => response.ok ? response.json() : { count: 0 }).then((data) => setUnreadNotifications(data.count ?? 0)).catch((error) => { console.error("Notification count refresh failed:", error); });
    };
    const timer = window.setInterval(refresh, 45_000);
    window.addEventListener("focus", refresh);
    refresh();
    return () => { window.clearInterval(timer); window.removeEventListener("focus", refresh); };
  }, [currentUser]);

  // Handlers for Navigation
  const handleSelectAsset = (asset: AssetSummary) => {
    selectAsset(asset);
  };

  const refreshRegistry = async () => {
    const response = await fetch("/api/v1/assets?limit=1000");
    if (!response.ok) throw new Error(`Asset registry refresh failed (${response.status})`);
    const data = await response.json();
    const items = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : [];
    setAssets(items);
    setRegistryCount(typeof data?.total === "number" ? data.total : items.length);
    return items;
  };

  const handleOpenAssetDetails = (asset: AssetSummary) => {
    selectAsset(asset, "digital-twin");
    if (workspace === "PUBLIC") {
      setPublicTab("twin");
    } else {
      setOfficerTab("twin");
    }
  };

  const handleNavigateToReports = (assetCode: string) => {
    const found = assets.find((a) => a.asset_code === assetCode);
    if (found) selectAsset(found, "reports");

    if (workspace === "PUBLIC") {
      setPublicTab("reports");
    } else {
      setOfficerTab("reports");
    }
  };

  const handlePublicTabChange = (tab: PublicTab) => {
    if (tab === "citizen_report") {
      setIsCitizenReportOpen(true);
    } else {
      setPublicTab(tab);
    }
  };

  const handleLoginSuccess = (user: any, token: string) => {
    setCurrentUser(user);
    setWorkspace("OFFICER");
    setOfficerTab("dashboard");
  };

  const handleLogout = () => {
    localStorage.removeItem("simras_token");
    localStorage.removeItem("simras_user");
    setCurrentUser(null);
    setWorkspace("PUBLIC");
    setPublicTab("home");
  };

  const handleProfileUpdate = (profile: { name: string }) => {
    setCurrentUser((existing) => {
      if (!existing) return existing;
      const updated = { ...existing, name: profile.name };
      localStorage.setItem("simras_user", JSON.stringify(updated));
      return updated;
    });
  };

  const handleSearchResult = (result: SearchResult) => {
    if (result.asset_code) {
      const view = result.type === "inspection" ? "inspections" : result.type === "maintenance" ? "maintenance" : result.type === "report" ? "reports" : "digital-twin";
      selectAsset(result.asset_code, view);
    }
    setOfficerTab(result.type === "inspection" ? "inspections" : result.type === "maintenance" ? "maintenance" : result.type === "report" ? "reports" : "twin");
  };

  const activeAsset = selectedAsset;

  // View Routing: Login Page
  if (workspace === "LOGIN") {
    return (
      <OfficerLoginPage
        onLoginSuccess={handleLoginSuccess}
        onBackToPublic={() => setWorkspace("PUBLIC")}
      />
    );
  }

  if (!activeAsset) {
    return (
      <div className="min-h-screen grid place-items-center bg-[#F4F7FA] text-sm text-slate-600">
        {loading ? "Loading infrastructure registryâ€¦" : error || "No infrastructure records are available."}
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#F4F7FA] font-sans antialiased text-slate-800">
      {/* 1. Header Navigation */}
      {workspace === "PUBLIC" ? (
        <PublicHeader
          activeTab={publicTab}
          onSelectTab={handlePublicTabChange}
          onOpenOfficerLogin={() => {
            if (currentUser) {
              setWorkspace("OFFICER");
            } else {
              setWorkspace("LOGIN");
            }
          }}
          onOpenCitizenReport={() => setIsCitizenReportOpen(true)}
        />
      ) : (
        <OfficerHeader
          currentUser={currentUser}
          unreadCount={unreadNotifications}
          onOpenNotifications={() => setIsNotificationsOpen(true)}
          onOpenAiAdvisor={() => setIsAiOpen(true)}
          onSearchResult={handleSearchResult}
          onNavigateTab={(tab) => setOfficerTab(tab as OfficerTab)}
          onLogout={handleLogout}
          onSwitchToPublic={() => setWorkspace("PUBLIC")}
        />
      )}

      {/* 2. Workspace Body */}
      {workspace === "PUBLIC" ? (
        <main className="flex-1 min-w-0">
          {/* Public Home Landing View */}
          {publicTab === "home" && (
            <PublicHome
              assets={assets}
              onNavigateToGIS={() => setPublicTab("gis")}
              onNavigateToTwin={(asset) => {
                selectAsset(asset, "digital-twin");
                setPublicTab("twin");
              }}
              onNavigateToReports={(assetCode) => {
                const found = assets.find((a) => a.asset_code === assetCode);
                if (found) selectAsset(found, "reports");
                setPublicTab("reports");
              }}
              onOpenCitizenReport={() => setIsCitizenReportOpen(true)}
            />
          )}

          {/* Public GIS Command View */}
          {publicTab === "gis" && (
            <GISCommandView
              assets={assets.filter(a => a.identity_status === "VERIFIED")}
              mapFeatures={mapFeatures}
              selectedAsset={activeAsset}
              onSelectAsset={handleSelectAsset}
              onOpenAssetDetails={handleOpenAssetDetails}
            />
          )}

          {/* Public Digital Twin View */}
          {publicTab === "twin" && (
            <DigitalTwinPage
              assets={assets.filter(a => a.identity_status === "VERIFIED")}
              selectedAsset={activeAsset}
              onSelectAsset={handleSelectAsset}
              onNavigateToReports={handleNavigateToReports}
            />
          )}

          {/* Public Reports View */}
          {publicTab === "reports" && (
            <PublicReportsPage
              assets={assets}
              selectedAsset={activeAsset}
              onSelectAsset={handleSelectAsset}
            />
          )}
        </main>
      ) : (
        /* OFFICER WORKSPACE: Sidebar + Content Area */
        <div className="flex-1 flex overflow-hidden">
          <OfficerSidebar
            activeTab={officerTab}
            onSelectTab={(tab) => {
              if (tab === "notifications") setIsNotificationsOpen(true);
              else setOfficerTab(tab);
            }}
            isCollapsed={isSidebarCollapsed}
            onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            counts={{
              assets: registryCount,
              inspections: 0,
              maintenance: 0,
              reviews: 0,
            }}
            unreadNotificationsCount={unreadNotifications}
          />

          <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 bg-[#F4F7FA]">
            {officerTab === "dashboard" && (
              <OfficerDashboard
                assets={assets}
                onSelectAsset={handleSelectAsset}
                onNavigateTab={setOfficerTab}
                currentUser={currentUser}
              />
            )}

            {officerTab === "assets" && (
              <>
                {assetSuccess && <div className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{assetSuccess}</div>}
                <OfficerAssetTable
                assets={assets}
                onSelectAsset={handleSelectAsset}
                onNavigateToTwin={(a) => {
                  selectAsset(a, "digital-twin");
                  setOfficerTab("twin");
                }}
                onNavigateToReport={(code) => {
                  const found = assets.find((a) => a.asset_code === code);
                  if (found) selectAsset(found, "reports");
                  setOfficerTab("reports");
                }}
                onNavigateToInspections={(code) => {
                  setOfficerTab("inspections");
                }}
                onNavigateToMaintenance={(code) => {
                  setOfficerTab("maintenance");
                }}
                onAddNewAsset={() => setOfficerTab("add_asset")}
                />
              </>
            )}

            {officerTab === "gis" && (
              <div className="h-[calc(100vh-8.5rem)] -m-4 sm:-m-6 lg:-m-8">
                <GISCommandView
                  assets={assets.filter(a => a.identity_status === "VERIFIED")}
                  mapFeatures={mapFeatures}
                  selectedAsset={activeAsset}
                  onSelectAsset={handleSelectAsset}
                  onOpenAssetDetails={handleOpenAssetDetails}
                />
              </div>
            )}

            {officerTab === "twin" && (
              <div className="-m-4 sm:-m-6 lg:-m-8">
                <DigitalTwinPage
                  assets={assets}
                  selectedAsset={activeAsset}
                  onSelectAsset={handleSelectAsset}
                  onNavigateToReports={handleNavigateToReports}
                />
              </div>
            )}

            {officerTab === "reports" && (
              <div className="-m-4 sm:-m-6 lg:-m-8">
                <PublicReportsPage
                  assets={assets}
                  selectedAsset={activeAsset}
                  onSelectAsset={handleSelectAsset}
                />
              </div>
            )}

            {officerTab === "add_asset" && (
              <div className="py-4">
                <AddAssetWizard
                  onSuccess={(created) => {
                    setAssetSuccess(`Submitted for review: ${created.asset_code}. Assessments remain withheld until sufficient evidence is available.`);
                    setOfficerTab("reviews");
                    void refreshRegistry().catch((refreshError) => {
                      console.error(refreshError);
                      setError(refreshError instanceof Error ? refreshError.message : "Asset registry refresh failed");
                    });
                  }}
                  onCancel={() => setOfficerTab("dashboard")}
                />
              </div>
            )}

            {officerTab === "inspections" && (
              <div className="bg-white border border-[#D8E2EA] rounded-lg p-6 shadow-sm">
                <InspectionsManager
                  selectedAssetCode={activeAsset.asset_code}
                  userRole={currentUser?.role}
                  onSelectAsset={(code) => {
                    const found = assets.find((a) => a.asset_code === code);
                    if (found) selectAsset(found);
                  }}
                />
              </div>
            )}

            {officerTab === "maintenance" && (
              <div className="bg-white border border-[#D8E2EA] rounded-lg p-6 shadow-sm">
                <MaintenancePlanner
                  selectedAssetCode={activeAsset.asset_code}
                  userRole={currentUser?.role}
                  onSelectAsset={(code) => {
                    const found = assets.find((a) => a.asset_code === code);
                    if (found) selectAsset(found);
                  }}
                />
              </div>
            )}

            {officerTab === "reviews" && (
              <div className="bg-white border border-[#D8E2EA] rounded-lg p-6 shadow-sm">
                {assetSuccess && <p role="status" className="mb-4 text-sm text-emerald-800">{assetSuccess}</p>}
                <ReviewQueue onRegistrationsChanged={refreshRegistry} />
              </div>
            )}

            {officerTab === "profile" && <ProfilePage onUserUpdate={handleProfileUpdate} />}

            {officerTab === "settings" && <SettingsPage />}
          </main>
        </div>
      )}

      {/* 3. Global Modals & Drawers */}
      {/* Citizen Hazard Observation Modal */}
      <CitizenObservationModal
        isOpen={isCitizenReportOpen}
        onClose={() => setIsCitizenReportOpen(false)}
        assetCode={activeAsset.asset_code}
        assetName={activeAsset.name}
        onSubmitted={() => {
          setIsCitizenReportOpen(false);
          alert("Thank you. Your citizen hazard report has been submitted to the Andhra Pradesh District Disaster Management Cell.");
        }}
      />

      {/* Notifications Modal */}
      <NotificationModal
        isOpen={isNotificationsOpen}
        onClose={() => setIsNotificationsOpen(false)}
        onUnreadChange={setUnreadNotifications}
        onSelectAsset={(code) => {
          setIsNotificationsOpen(false);
          const found = assets.find((a) => a.asset_code === code);
          if (found) {
            selectAsset(found, "digital-twin");
            setOfficerTab("twin");
          }
        }}
      />

      {/* AI Engineering Assistant Drawer */}
      <AiAssistantDrawer
        isOpen={isAiOpen}
        onClose={() => setIsAiOpen(false)}
        selectedAsset={activeAsset}
      />
    </div>
  );
}
