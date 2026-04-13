import { useState, useEffect } from "react";
import { Outlet, NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Briefcase,
  Search,
  FileText,
  MessageSquare,
  Settings,
  Wifi,
  WifiOff,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { checkHealth } from "@/lib/api";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/applications", label: "Applications", icon: Briefcase },
  { to: "/search", label: "Job Search", icon: Search },
  { to: "/resume", label: "Resume Review", icon: FileText },
  { to: "/chat", label: "Chat", icon: MessageSquare },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const [apiOnline, setApiOnline] = useState(false);

  useEffect(() => {
    let mounted = true;
    const ping = () =>
      checkHealth()
        .then(() => mounted && setApiOnline(true))
        .catch(() => mounted && setApiOnline(false));
    ping();
    const id = setInterval(ping, 30_000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950 text-gray-100">
      {/* Sidebar */}
      <aside
        className={`${
          collapsed ? "w-18" : "w-64"
        } flex flex-col border-r border-gray-800 bg-gray-900 transition-all duration-200`}
      >
        {/* Brand */}
        <div className="flex h-16 items-center justify-between border-b border-gray-800 px-4">
          {!collapsed && (
            <span className="text-xl font-bold tracking-tight text-accent">
              JobPilot
            </span>
          )}
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-800 hover:text-gray-100"
          >
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-accent/10 text-accent"
                    : "text-gray-400 hover:bg-gray-800 hover:text-gray-100"
                }`
              }
            >
              <Icon size={20} className="shrink-0" />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* Status footer */}
        <div className="border-t border-gray-800 px-4 py-3">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span
              className={`h-2 w-2 rounded-full ${
                apiOnline ? "bg-emerald-500 animate-pulse-dot" : "bg-red-500"
              }`}
            />
            {!collapsed && <span>{apiOnline ? "API Connected" : "API Offline"}</span>}
          </div>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top header */}
        <header className="flex h-16 items-center justify-between border-b border-gray-800 bg-gray-900 px-6">
          <h1 className="text-lg font-semibold text-gray-100">JobPilot</h1>
          <div className="flex items-center gap-3">
            <span
              className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
                apiOnline
                  ? "bg-emerald-500/10 text-emerald-400"
                  : "bg-red-500/10 text-red-400"
              }`}
            >
              {apiOnline ? <Wifi size={14} /> : <WifiOff size={14} />}
              {apiOnline ? "Online" : "Offline"}
            </span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
