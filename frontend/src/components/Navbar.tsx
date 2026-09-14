import React, { useState } from 'react';
import { Sun, Moon, Shield, User as UserIcon, LogOut, Activity, ChevronDown, Terminal, Cpu } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';

interface NavbarProps {
  onOpenStats: () => void;
  onOpenLogin: () => void;
  activeView: 'catalog' | 'workspace';
  onNavigateHome: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenStats,
  onOpenLogin,
  activeView,
  onNavigateHome,
}) => {
  const { isDark, toggleTheme } = useTheme();
  const { user, loginDemo, logout, isAdmin } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  return (
    <header className="sticky top-0 z-40 w-full border-b border-black/[0.08] dark:border-white/[0.08] bg-white/70 dark:bg-[#090b10]/70 backdrop-blur-2xl transition-colors duration-200">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand Logo & Geometric Glyph */}
        <div className="flex items-center gap-8">
          <button
            onClick={onNavigateHome}
            className="group flex items-center gap-3 text-left focus:outline-none"
          >
            {/* Minimalist Geometric SVG Icon matching the user's reference */}
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-black/10 dark:border-white/15 bg-black/[0.03] dark:bg-white/[0.05] text-slate-900 dark:text-white transition-all group-hover:scale-105">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="7" height="7" rx="1" />
                <rect x="14" y="3" width="7" height="7" rx="1" />
                <rect x="14" y="14" width="7" height="7" rx="1" />
                <rect x="3" y="14" width="7" height="7" rx="1" />
              </svg>
            </div>
            <div>
              <span className="text-base font-bold tracking-tight text-slate-900 dark:text-white">
                CODE<span className="text-purple-600 dark:text-purple-400">GRID</span>
              </span>
              <span className="hidden sm:inline-block ml-2 text-[10px] font-mono tracking-widest text-slate-400 dark:text-slate-500 uppercase">
                // v3.0
              </span>
            </div>
          </button>

          {/* Navigation links */}
          <nav className="hidden md:flex items-center gap-1 text-xs font-semibold tracking-wide uppercase">
            <button
              onClick={onNavigateHome}
              className={`px-3.5 py-1.5 rounded-full transition-all ${
                activeView === 'catalog'
                  ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              Problems
            </button>
            <button
              onClick={onOpenStats}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-black/[0.04] dark:hover:bg-white/[0.04] transition-all"
            >
              <Activity className="h-3.5 w-3.5" />
              Telemetry
            </button>
          </nav>
        </div>

        {/* Right Action Tools */}
        <div className="flex items-center gap-3">
          {/* Light / Dark Mode Toggle */}
          <button
            onClick={toggleTheme}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-black/10 dark:border-white/15 bg-black/[0.02] dark:bg-white/[0.04] text-slate-700 dark:text-slate-300 hover:bg-black/[0.06] dark:hover:bg-white/[0.08] transition-colors"
            title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            {isDark ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4 text-slate-700" />}
          </button>

          {/* Quick Demo Switcher or Profile */}
          {user ? (
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 rounded-xl border border-black/10 dark:border-white/15 bg-black/[0.02] dark:bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-slate-900 dark:text-white hover:bg-black/[0.05] dark:hover:bg-white/[0.08] transition-colors"
              >
                <div className={`h-2 w-2 rounded-full ${isAdmin ? 'bg-amber-400' : 'bg-emerald-400'}`} />
                <span className="font-mono">{user.username}</span>
                <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
              </button>

              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-56 rounded-2xl border border-black/10 dark:border-white/15 bg-white/95 dark:bg-slate-900/95 p-2 shadow-2xl backdrop-blur-xl animate-fadeIn z-50">
                  <div className="px-3 py-2 border-b border-black/[0.06] dark:border-white/[0.06]">
                    <p className="text-xs font-semibold text-slate-900 dark:text-white">{user.username}</p>
                    <p className="text-[11px] font-mono text-slate-500 truncate">{user.email}</p>
                    <span className="inline-block mt-1 px-2 py-0.5 rounded-full text-[9px] font-mono tracking-wider uppercase font-bold bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
                      {user.role}
                    </span>
                  </div>

                  <div className="py-1">
                    <button
                      onClick={() => {
                        setShowUserMenu(false);
                        onOpenStats();
                      }}
                      className="flex w-full items-center gap-2 px-3 py-2 text-xs text-slate-700 dark:text-slate-300 hover:bg-black/[0.04] dark:hover:bg-white/[0.04] rounded-lg transition-colors"
                    >
                      <Activity className="h-3.5 w-3.5" />
                      View Analytics
                    </button>
                    <button
                      onClick={() => {
                        loginDemo(isAdmin ? 'user' : 'admin');
                        setShowUserMenu(false);
                      }}
                      className="flex w-full items-center gap-2 px-3 py-2 text-xs text-purple-600 dark:text-purple-400 hover:bg-purple-500/10 rounded-lg transition-colors font-medium"
                    >
                      <Shield className="h-3.5 w-3.5" />
                      Switch to {isAdmin ? 'Coder' : 'Admin'} Mode
                    </button>
                    <button
                      onClick={() => {
                        logout();
                        setShowUserMenu(false);
                      }}
                      className="flex w-full items-center gap-2 px-3 py-2 text-xs text-rose-500 hover:bg-rose-500/10 rounded-lg transition-colors"
                    >
                      <LogOut className="h-3.5 w-3.5" />
                      Sign Out
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <button
              onClick={onOpenLogin}
              className="flex items-center gap-2 rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900 px-4 py-1.5 text-xs font-semibold tracking-wide hover:opacity-90 transition-opacity shadow-sm"
            >
              <UserIcon className="h-3.5 w-3.5" />
              Sign In
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
