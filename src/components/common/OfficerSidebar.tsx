import React from "react";
import {
  LayoutDashboard,
  MapPin,
  Box,
  ClipboardList,
  Wrench,
  FileText,
  CheckSquare,
  Bell,
  Building2,
  User,
  PlusCircle,
  ChevronLeft,
  ChevronRight,
  Settings,
} from "lucide-react";

export type OfficerTab =
  | "dashboard"
  | "gis"
  | "twin"
  | "inspections"
  | "maintenance"
  | "reports"
  | "reviews"
  | "notifications"
  | "assets"
  | "profile"
  | "add_asset"
  | "settings";

interface OfficerSidebarProps {
  currentTab?: OfficerTab;
  activeTab?: OfficerTab;
  onSelectTab: (tab: OfficerTab) => void;
  pendingReviewsCount?: number;
  unreadNotificationsCount?: number;
  collapsed?: boolean;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  className?: string;
  onCloseMobile?: () => void;
  counts?: Record<string, number>;
}

export function OfficerSidebar({
  currentTab,
  activeTab,
  onSelectTab,
  pendingReviewsCount = 0,
  unreadNotificationsCount = 0,
  collapsed,
  isCollapsed,
  onToggleCollapse,
  className = "",
  onCloseMobile,
  counts,
}: OfficerSidebarProps) {
  const selectedTab = activeTab || currentTab || "dashboard";
  const isSidebarCollapsed = isCollapsed ?? collapsed ?? false;

  const menuItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "gis", label: "GIS Command", icon: MapPin },
    { id: "twin", label: "Digital Twin", icon: Box },
    { id: "inspections", label: "Inspections", icon: ClipboardList, badge: counts?.inspections || 4 },
    { id: "maintenance", label: "Maintenance", icon: Wrench, badge: counts?.maintenance || 5 },
    { id: "reports", label: "Reports", icon: FileText },
    { id: "reviews", label: "Review Queue", icon: CheckSquare, badge: counts?.reviews || pendingReviewsCount },
    { id: "notifications", label: "Notifications", icon: Bell, badge: unreadNotificationsCount },
    { id: "assets", label: "Assets", icon: Building2, badge: counts?.assets },
    { id: "profile", label: "Profile", icon: User },
    { id: "settings", label: "Settings", icon: Settings },
  ];

  return (
    <aside
      className={`bg-white border-r border-[#D9E3EC] flex flex-col justify-between transition-all duration-200 shrink-0 select-none ${
        isSidebarCollapsed ? "w-16" : "w-60"
      } ${className}`}
    >
      <div>
        {/* New Asset Quick Action */}
        <div className="p-3 border-b border-[#D9E3EC]">
          <button
            onClick={() => onSelectTab("add_asset")}
            className={`w-full flex items-center justify-center gap-2 py-2 px-3 rounded-md bg-[#0875BE] hover:bg-[#0C4775] text-white text-xs font-bold shadow-sm transition ${
              isSidebarCollapsed ? "px-0" : ""
            }`}
            title="Add New Infrastructure Asset"
          >
            <PlusCircle className="w-4 h-4 shrink-0" />
            {!isSidebarCollapsed && <span>+ Add Infrastructure</span>}
          </button>
        </div>

        {/* Navigation Item List */}
        <nav className="p-2 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = selectedTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onSelectTab(item.id as OfficerTab);
                  if (onCloseMobile) onCloseMobile();
                }}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-xs font-semibold transition ${
                  isActive
                    ? "bg-[#EBF5FB] text-[#0875BE] border-l-4 border-l-[#0875BE] pl-2 font-bold"
                    : "text-[#172B3A] hover:text-[#0C4775] hover:bg-[#F5F8FB] border-l-4 border-l-transparent"
                } ${isSidebarCollapsed ? "justify-center px-0 border-l-0" : ""}`}
                title={item.label}
              >
                <Icon
                  className={`w-4 h-4 shrink-0 ${
                    isActive ? "text-[#0875BE]" : "text-[#61788A]"
                  }`}
                />
                {!isSidebarCollapsed && (
                  <div className="flex-1 flex items-center justify-between truncate">
                    <span className="truncate">{item.label}</span>
                    {item.badge != null && item.badge > 0 && (
                      <span
                        className={`text-[10px] font-mono font-bold px-1.5 py-0.2 rounded-full ${
                          isActive
                            ? "bg-[#0875BE] text-white"
                            : "bg-[#E2EDF5] text-[#0C4775]"
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </div>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Collapse Toggle Button */}
      {onToggleCollapse && (
        <div className="p-2 border-t border-[#D8E2EA] flex items-center justify-center">
          <button
            onClick={onToggleCollapse}
            className="w-full flex items-center justify-center gap-2 p-1.5 text-xs text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded transition"
            title={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isSidebarCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <>
                <ChevronLeft className="w-4 h-4" />
                <span className="text-[11px] font-medium">Collapse Sidebar</span>
              </>
            )}
          </button>
        </div>
      )}
    </aside>
  );
}
