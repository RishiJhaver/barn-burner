import React, { useEffect, useState } from 'react';
import { X, Activity, Award, CheckCircle2, TrendingUp, Zap } from 'lucide-react';
import { submissionsApi } from '../api/submissionsApi';
import { UserStats } from '../types';
import { useAuth } from '../context/AuthContext';

interface StatsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const StatsModal: React.FC<StatsModalProps> = ({ isOpen, onClose }) => {
  const { user } = useAuth();
  const [stats, setStats] = useState<UserStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (isOpen) {
      const fetchStats = async () => {
        setLoading(true);
        try {
          const data = await submissionsApi.getUserStats();
          setStats(data);
        } catch (err) {
          console.error('Failed to load stats:', err);
        } finally {
          setLoading(false);
        }
      };
      fetchStats();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-md overflow-hidden rounded-3xl border border-black/10 dark:border-white/15 bg-white/95 dark:bg-[#0c0e14]/95 p-8 shadow-2xl backdrop-blur-3xl transition-all">
        {/* Soft pastel ambient aura */}
        <div className="pointer-events-none absolute -top-20 -right-20 h-52 w-52 rounded-full bg-purple-400/20 dark:bg-purple-600/15 blur-3xl" />

        <button
          onClick={onClose}
          className="absolute top-6 right-6 rounded-xl p-1.5 text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-black/[0.04] dark:hover:bg-white/[0.05] transition-colors"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-3.5 mb-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-black/10 dark:border-white/15 bg-black/[0.02] dark:bg-white/[0.04] text-slate-900 dark:text-white">
            <Activity className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[10px] font-semibold tracking-[0.2em] text-slate-400 uppercase">
              Coder Telemetry
            </span>
            <h3 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white font-sans">
              @{user?.username || 'coder'}
            </h3>
          </div>
        </div>

        {loading ? (
          <div className="flex h-48 items-center justify-center text-xs text-slate-400 animate-pulse">
            Loading metrics...
          </div>
        ) : stats ? (
          <div className="space-y-4">
            {/* Total Solved Bento Box */}
            <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] p-5 text-center">
              <span className="text-[11px] font-semibold tracking-wider text-slate-400 uppercase">Total Solved</span>
              <p className="text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight my-1">{stats.total_solved}</p>
              <p className="text-xs text-slate-400">Problems Solved Across All Difficulties</p>
            </div>

            {/* Difficulty Breakdown Grid */}
            <div className="grid grid-cols-3 gap-2.5 text-center">
              <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-3.5">
                <p className="text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold tracking-wider uppercase">Easy</p>
                <p className="text-xl font-bold text-slate-900 dark:text-white my-0.5">{stats.easy_solved}</p>
              </div>

              <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-3.5">
                <p className="text-[10px] text-amber-600 dark:text-amber-400 font-semibold tracking-wider uppercase">Medium</p>
                <p className="text-xl font-bold text-slate-900 dark:text-white my-0.5">{stats.medium_solved}</p>
              </div>

              <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-3.5">
                <p className="text-[10px] text-rose-600 dark:text-rose-400 font-semibold tracking-wider uppercase">Hard</p>
                <p className="text-xl font-bold text-slate-900 dark:text-white my-0.5">{stats.hard_solved}</p>
              </div>
            </div>

            {/* Acceptance Ratio */}
            <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] p-4 flex items-center justify-between">
              <div>
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Total Submissions</span>
                <p className="text-base font-bold text-slate-900 dark:text-white">{stats.total_submissions}</p>
              </div>
              <div className="text-right">
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Success Rate</span>
                <p className="text-base font-bold text-emerald-600 dark:text-emerald-400">
                  {stats.acceptance_rate.toFixed(1)}%
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-8 text-center text-xs text-slate-400">
            No telemetry records found.
          </div>
        )}
      </div>
    </div>
  );
};
