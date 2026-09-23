import React, { useState, useRef, useEffect } from "react";
import {
  Bell,
  LogOut,
  User,
  Shield,
  ChevronDown,
  Menu,
  X,
  ExternalLink,
  Sparkles,
  Settings,
} from "lucide-react";
import { GovernmentEmblem } from "./PublicHeader";
import { GlobalSearch } from "./GlobalSearch";
import type { SearchResult } from "./searchModel";

interface OfficerHeaderProps {
  currentUser?: {
    name?: string;
    role?: string;
    department?: string;
    email?: string;
  } | null;
  officerName?: string;
  officerRole?: string;
  unreadCount?: number;
  unreadNotificationsCount?: number;
  onOpenNotifications: () => void;
  onOpenAiAdvisor?: () => void;
  onLogout: () => void;
  onSwitchToPublic: () => void;
  onNavigateTab?: (tab: string) => void;
  onSearchResult?: (result: SearchResult) => void;
  onToggleMobileSidebar?: () => void;
  isMobileSidebarOpen?: boolean;
}

export function OfficerHeader({
  currentUser,
  officerName,
  officerRole,
  unreadCount,
  unreadNotificationsCount,
  onOpenNotifications,
  onOpenAiAdvisor,
  onLogout,
  onSwitchToPublic,
  onNavigateTab,
  onSearchResult,
  onToggleMobileSidebar,
  isMobileSidebarOpen,
}: OfficerHeaderProps) {
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const name = currentUser?.name || officerName || "Er. K. V. Raman";
  const role = currentUser?.role || officerRole || "Executive Engineer";
  const department = currentUser?.department || "Andhra Pradesh Water Resources Dept (APWRD)";
  const count = unreadCount ?? unreadNotificationsCount ?? 0;

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setUserDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <header className="bg-[#0B3B63] text-white border-b border-[#0D4E7A] shadow-md sticky top-0 z-40 select-none">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Left Section: Mobile Toggle & Brand */}
        <div className="flex items-center gap-3">
          {onToggleMobileSidebar && (
            <button
              onClick={onToggleMobileSidebar}
              className="lg:hidden p-2 text-slate-300 hover:text-white rounded-md hover:bg-[#0D4E7A] transition"
              aria-label="Toggle navigation sidebar"
            >
              {isMobileSidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          )}

          <div
            onClick={onSwitchToPublic}
            className="flex items-center gap-2.5 cursor-pointer group"
            title="Return to Public View"
          >
            <GovernmentEmblem className="w-9 h-9 drop-shadow" />
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <img src="/images/ap-government-emblem.png" alt="Andhra Pradesh Government Emblem" className="h-12 w-12 shrink-0 object-contain" />
<span className="text-lg font-bold tracking-tight text-white font-sans">
                  SIMRAS
                </span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#16689A] text-sky-100 font-bold uppercase tracking-wider">
                  Officer Desk
                </span>
              </div>
              <span className="text-[10px] text-slate-300 hidden sm:block truncate max-w-[280px]">
                {department}
              </span>
            </div>
          </div>
        </div>

        {/* Center Search Bar */}
        <div className="hidden md:flex items-center flex-1 max-w-md mx-4">
          {onSearchResult && <GlobalSearch onSelect={onSearchResult} />}
        </div>

        {/* Right Section: AI Advisor + Notifications + Officer Profile */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          {/* AI Advisor Button */}
          {onOpenAiAdvisor && (
            <button
              onClick={onOpenAiAdvisor}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-gradient-to-r from-sky-600 to-[#1268A8] text-white hover:brightness-110 shadow-sm transition border border-sky-400/30"
              title="Launch AI Infrastructure Engineering Advisor"
            >
              <Sparkles className="w-3.5 h-3.5 text-sky-200" />
              <span className="hidden sm:inline">AI Engineering Advisor</span>
            </button>
          )}

          {/* Notifications Bell */}
          <button
            onClick={onOpenNotifications}
            className="relative p-2 rounded-md text-slate-300 hover:text-white hover:bg-[#0D4E7A] transition"
            title="View Critical System Alerts"
          >
            <Bell className="w-5 h-5" />
            {count > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 rounded-full bg-red-500 text-[10px] font-bold flex items-center justify-center text-white ring-2 ring-[#0B3B63]">
                {count > 9 ? "9+" : count}
              </span>
            )}
          </button>

          <div className="h-6 w-px bg-slate-700/60 hidden sm:block" />

          {/* User Profile Dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setUserDropdownOpen(!userDropdownOpen)}
              className="flex items-center gap-2 p-1.5 rounded-md hover:bg-[#0D4E7A] transition"
            >
              <div className="w-8 h-8 rounded-full bg-[#16689A] border border-[#18A8D8]/50 flex items-center justify-center text-white font-bold text-xs">
                {name.charAt(0)}
              </div>
              <div className="hidden lg:flex flex-col text-left">
                <span className="text-xs font-semibold text-white leading-tight">
                  {name}
                </span>
                <span className="text-[10px] text-sky-200 leading-tight truncate max-w-[120px]">
                  {role}
                </span>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {/* Dropdown Menu */}
            {userDropdownOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-white rounded-md shadow-xl border border-[#D8E2EA] py-1.5 z-50 text-slate-800 text-xs animate-in fade-in slide-in-from-top-2">
                <div className="px-3 py-2 border-b border-slate-100">
                  <p className="font-bold text-slate-900 truncate">{name}</p>
                  <p className="text-[11px] text-slate-500 truncate">{role}</p>
                  <p className="text-[10px] text-[#1268A8] font-medium truncate mt-0.5">{department}</p>
                </div>

                {onNavigateTab && (
                  <>
                    <button
                      onClick={() => { setUserDropdownOpen(false); onNavigateTab("profile"); }}
                      className="w-full text-left px-3 py-2 hover:bg-slate-50 flex items-center gap-2 text-slate-700 font-medium"
                    >
                      <User className="w-4 h-4 text-slate-400" />
                      <span>My Profile</span>
                    </button>
                    <button
                      onClick={() => { setUserDropdownOpen(false); onNavigateTab("settings"); }}
                      className="w-full text-left px-3 py-2 hover:bg-slate-50 flex items-center gap-2 text-slate-700 font-medium"
                    >
                      <Settings className="w-4 h-4 text-slate-400" />
                      <span>Settings</span>
                    </button>
                  </>
                )}

                <button
                  onClick={() => {
                    setUserDropdownOpen(false);
                    onSwitchToPublic();
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-slate-50 flex items-center gap-2 text-slate-700 font-medium"
                >
                  <ExternalLink className="w-4 h-4 text-slate-400" />
                  <span>View Citizen Public Portal</span>
                </button>

                <div className="border-t border-slate-100 my-1" />

                <button
                  onClick={() => {
                    setUserDropdownOpen(false);
                    onLogout();
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-red-50 text-red-600 font-semibold flex items-center gap-2"
                >
                  <LogOut className="w-4 h-4 text-red-500" />
                  <span>Sign Out Session</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

