import React, { useState } from 'react';
import { X, Shield, User, Sparkles, Cloud, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({ isOpen, onClose }) => {
  const { loginDemo } = useAuth();
  const [customUsername, setCustomUsername] = useState('');
  const [role, setRole] = useState<'user' | 'admin'>('user');
  const [activeTab, setActiveTab] = useState<'demo' | 'cognito'>('demo');

  if (!isOpen) return null;

  const handleCustomLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customUsername.trim()) return;
    await loginDemo(role, customUsername.trim(), `${customUsername.trim()}@codegrid.dev`);
    onClose();
  };

  const handleCognitoRedirect = () => {
    alert(
      "AWS Cognito Hosted UI is set up for Phase 7 Cloud Deployment. For local testing, use the Instant Demo Login to get immediate admin or user access!"
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-md overflow-hidden rounded-3xl border border-black/10 dark:border-white/15 bg-white/95 dark:bg-[#0c0e14]/95 p-8 shadow-2xl backdrop-blur-3xl transition-all">
        {/* Soft pastel ambient glow */}
        <div className="pointer-events-none absolute -top-20 -right-20 h-52 w-52 rounded-full bg-purple-400/20 dark:bg-purple-600/15 blur-3xl" />

        <button
          onClick={onClose}
          className="absolute top-6 right-6 rounded-xl p-1.5 text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-black/[0.04] dark:hover:bg-white/[0.05] transition-colors"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Modal Header */}
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl border border-black/10 dark:border-white/15 bg-black/[0.02] dark:bg-white/[0.04] text-slate-900 dark:text-white">
            <User className="h-6 w-6" />
          </div>
          <span className="text-[10px] font-semibold tracking-[0.2em] text-slate-400 uppercase">
            Authentication
          </span>
          <h3 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white font-sans">
            Sign In to CodeGrid
          </h3>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Select your authentication gateway
          </p>
        </div>

        {/* Auth Mode Tabs */}
        <div className="flex gap-1.5 rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] p-1 mb-6 text-xs">
          <button
            onClick={() => setActiveTab('demo')}
            className={`flex-1 py-2 rounded-xl font-medium transition-all ${
              activeTab === 'demo'
                ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm font-semibold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            Instant Demo
          </button>
          <button
            onClick={() => setActiveTab('cognito')}
            className={`flex-1 py-2 rounded-xl font-medium transition-all ${
              activeTab === 'cognito'
                ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm font-semibold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            AWS Cognito
          </button>
        </div>

        {activeTab === 'demo' ? (
          <div className="space-y-4">
            {/* Quick 1-Click Presets */}
            <div className="space-y-2">
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                1-Click Quick Access:
              </p>
              <div className="grid grid-cols-2 gap-2.5">
                <button
                  onClick={async () => {
                    await loginDemo('user', 'alex_coder', 'alex@codegrid.dev');
                    onClose();
                  }}
                  className="flex flex-col items-start rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] p-3.5 text-left hover:border-black/30 dark:hover:border-white/30 transition-all"
                >
                  <span className="font-bold text-slate-900 dark:text-white text-xs">👤 Coder Alex</span>
                  <span className="text-[10px] text-slate-400 mt-0.5">Role: Coder</span>
                </button>

                <button
                  onClick={async () => {
                    await loginDemo('admin', 'elena_admin', 'elena@codegrid.dev');
                    onClose();
                  }}
                  className="flex flex-col items-start rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] p-3.5 text-left hover:border-black/30 dark:hover:border-white/30 transition-all"
                >
                  <span className="font-bold text-slate-900 dark:text-white text-xs">🛡️ Admin Elena</span>
                  <span className="text-[10px] text-slate-400 mt-0.5">Role: Admin</span>
                </button>
              </div>
            </div>

            {/* Custom Username Form */}
            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-black/10 dark:border-white/10"></div>
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="bg-white dark:bg-[#0c0e14] px-2 text-slate-400">Or custom handle</span>
              </div>
            </div>

            <form onSubmit={handleCustomLogin} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-500 dark:text-slate-400 mb-1 text-[11px] font-semibold uppercase tracking-wider">
                  Coder Handle
                </label>
                <input
                  type="text"
                  placeholder="e.g. dev_rishi"
                  value={customUsername}
                  onChange={(e) => setCustomUsername(e.target.value)}
                  className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white/60 dark:bg-white/[0.04] px-3.5 py-2.5 text-slate-900 dark:text-white placeholder-slate-400 focus:border-slate-900 dark:focus:border-white focus:outline-none transition-all shadow-sm"
                />
              </div>

              <div className="flex gap-4 pt-1">
                <label className="flex items-center gap-2 cursor-pointer text-slate-700 dark:text-slate-300">
                  <input
                    type="radio"
                    name="role"
                    checked={role === 'user'}
                    onChange={() => setRole('user')}
                    className="accent-slate-900 dark:accent-white"
                  />
                  <span>Coder</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer text-slate-700 dark:text-slate-300">
                  <input
                    type="radio"
                    name="role"
                    checked={role === 'admin'}
                    onChange={() => setRole('admin')}
                    className="accent-slate-900 dark:accent-white"
                  />
                  <span>Admin</span>
                </label>
              </div>

              <button
                type="submit"
                className="w-full mt-2 rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900 py-2.5 font-semibold hover:opacity-90 transition-opacity shadow-sm"
              >
                Sign In
              </button>
            </form>
          </div>
        ) : (
          /* AWS Cognito Tab */
          <div className="space-y-4 text-xs">
            <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] p-4 space-y-2 text-slate-700 dark:text-slate-300">
              <p className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <Cloud className="h-4 w-4" />
                <span>AWS Cognito User Pool</span>
              </p>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed font-sans">
                Dual-Mode Authentication is active. The backend verifies cryptographic RS256 JWT tokens against AWS Cognito JWKS.
              </p>
            </div>

            <button
              onClick={handleCognitoRedirect}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900 py-3 font-semibold shadow-sm hover:opacity-90 transition-opacity"
            >
              <span>Continue with AWS Cognito</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
