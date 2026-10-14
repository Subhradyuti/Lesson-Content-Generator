import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useState, useEffect } from "react";
import {
  FlaskConical,
  History,
  LayoutDashboard,
  LogOut,
  Menu,
  Sparkles,
  X,
} from "lucide-react";
import clsx from "clsx";

import { Logo } from "./Logo";
import { RecentRuns } from "./RecentRuns";
import { ThemeToggle } from "./ThemeToggle";
import { config } from "../lib/config";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", Icon: LayoutDashboard },
  { to: "/generate", label: "Generate", Icon: Sparkles },
  { to: "/history", label: "Run History", Icon: History },
];

function SettingsSheet() {
  return (
    <details className="group">
      <summary className="flex cursor-pointer list-none items-center gap-3 rounded-xl px-2.5 py-2 text-muted transition-colors hover:bg-raised/60 hover:text-ink [&::-webkit-details-marker]:hidden">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg border border-line bg-raised text-faint">
          <FlaskConical className="h-3.5 w-3.5" aria-hidden="true" />
        </span>
        <span className="flex-1 text-[13px] font-medium">Backend settings</span>
        <span className="text-[10px] text-faint transition-transform group-open:rotate-180">▾</span>
      </summary>
      <div className="mt-1.5 space-y-2 rounded-xl border border-line bg-raised/60 p-3">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold tracking-wider text-faint uppercase">
            API base URL
          </p>
          <p className="truncate font-mono text-xs text-muted">
            {config.apiBaseUrl || "(same-origin / proxied)"}
          </p>
        </div>
        <div className="min-w-0">
          <p className="text-[10px] font-semibold tracking-wider text-faint uppercase">
            Authentication
          </p>
          <p className="font-mono text-xs text-muted">
            {config.authRequired ? "X-API-Key configured" : "No API key (open backend)"}
          </p>
        </div>
      </div>
    </details>
  );
}

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  // Close the mobile drawer on navigation.
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  const closeSidebar = () => setSidebarOpen(false);

  return (
    <div className="min-h-screen bg-canvas">
      {/* Ambient background */}
      <div className="bg-grid pointer-events-none fixed inset-0 opacity-60" aria-hidden="true" />
      <div
        className="pointer-events-none fixed top-[-260px] right-[-160px] h-[520px] w-[520px] rounded-full blur-[140px]"
        style={{
          background: "radial-gradient(circle, rgba(124,139,255,0.16), transparent 70%)",
        }}
        aria-hidden="true"
      />
      <div
        className="pointer-events-none fixed bottom-[-240px] left-[-180px] h-[480px] w-[480px] rounded-full blur-[150px]"
        style={{
          background: "radial-gradient(circle, rgba(154,107,255,0.10), transparent 70%)",
        }}
        aria-hidden="true"
      />

      {/* Mobile top bar */}
      <header className="sticky top-0 z-40 flex items-center justify-between border-b border-line bg-canvas/85 px-4 py-3 backdrop-blur-md lg:hidden">
        <Logo markOnly />
        <span className="text-[13px] font-semibold text-ink">
          Lesson <span className="text-gradient">Forge</span>
        </span>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <button
            type="button"
            className="icon-btn border border-line bg-raised"
            onClick={() => setSidebarOpen((v) => !v)}
            aria-label={sidebarOpen ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={sidebarOpen}
          >
            {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </header>

      {/* Sidebar overlay (mobile) */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-50 flex w-[276px] flex-col border-r border-line bg-sunken/90 backdrop-blur-md transition-transform duration-300 lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
        )}
        id="app-sidebar"
        aria-label="Primary navigation"
      >
        <div className="flex h-16 items-center border-b border-line px-5">
          <Logo />
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-5">
          <p className="px-2 text-[11px] font-semibold tracking-wider text-faint uppercase">
            Workspace
          </p>
          <nav className="mt-2 space-y-0.5" aria-label="Main navigation">
            {NAV_ITEMS.map(({ to, label, Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                onClick={closeSidebar}
                className={({ isActive }) =>
                  clsx(
                    "flex items-center gap-3 rounded-xl px-2.5 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-raised text-ink shadow-sm ring-1 ring-line"
                      : "text-muted hover:bg-raised/60 hover:text-ink",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon
                      className={clsx("h-[18px] w-[18px]", isActive ? "text-accent" : "text-faint")}
                      aria-hidden="true"
                    />
                    <span>{label}</span>
                    {isActive && (
                      <span
                        className="ml-auto h-1.5 w-1.5 rounded-full bg-accent"
                        aria-hidden="true"
                      />
                    )}
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          <RecentRuns onNavigate={closeSidebar} />
        </div>

        <div className="space-y-3 border-t border-line px-4 py-4">
          <div className="flex items-center justify-between">
            <p className="text-[11px] text-faint">Theme</p>
            <ThemeToggle />
          </div>
          <SettingsSheet />
          <div className="flex items-center gap-2.5 rounded-xl border border-line bg-raised px-3 py-2.5">
            <span className="relative flex h-2 w-2 shrink-0" aria-hidden="true">
              <span className="animate-ping-dot absolute inline-flex h-full w-full rounded-full bg-pass opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-pass" />
            </span>
            <span className="text-xs text-muted">
              Backend <span className="font-semibold text-ink">connected</span>
            </span>
            <LogOut className="ml-auto h-3.5 w-3.5 text-faint" aria-hidden="true" />
          </div>
          <p className="text-center text-[10px] text-faint">
            Lesson Forge v1.0 · Rubric rag-beginner-v1
          </p>
        </div>
      </aside>

      {/* Main content */}
      <main className="relative z-10 min-h-screen lg:pl-[276px]">
        <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8 lg:px-10 lg:py-10">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

