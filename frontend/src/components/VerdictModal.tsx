import React, { useEffect } from 'react';
import confetti from 'canvas-confetti';
import { CheckCircle2, XCircle, AlertTriangle, Clock, Cpu, X, ArrowUpRight } from 'lucide-react';
import { SubmissionDetail } from '../types';

interface VerdictModalProps {
  submission: SubmissionDetail | null;
  onClose: () => void;
}

export const VerdictModal: React.FC<VerdictModalProps> = ({ submission, onClose }) => {
  if (!submission) return null;

  const isAccepted = submission.status === 'accepted';
  const isWrongAnswer = submission.status === 'wrong_answer';

  useEffect(() => {
    if (isAccepted) {
      confetti({
        particleCount: 70,
        spread: 60,
        origin: { y: 0.6 },
        colors: ['#a855f7', '#3b82f6', '#10b981', '#f59e0b'],
      });
    }
  }, [isAccepted]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-lg overflow-hidden rounded-3xl border border-black/10 dark:border-white/15 bg-white/95 dark:bg-[#0c0e14]/95 p-8 shadow-2xl backdrop-blur-3xl transition-all">
        {/* Soft pastel ambient glow */}
        <div
          className={`pointer-events-none absolute -top-20 -right-20 h-56 w-56 rounded-full blur-3xl ${
            isAccepted
              ? 'bg-emerald-400/20 dark:bg-emerald-500/15'
              : 'bg-rose-400/20 dark:bg-rose-500/15'
          }`}
        />

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-6 right-6 rounded-xl p-1.5 text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-black/[0.04] dark:hover:bg-white/[0.05] transition-colors"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Verdict Status Title */}
        <div className="flex items-center gap-4 mb-6">
          <div
            className={`flex h-14 w-14 items-center justify-center rounded-2xl border ${
              isAccepted
                ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                : 'border-rose-500/30 bg-rose-500/10 text-rose-600 dark:text-rose-400'
            }`}
          >
            {isAccepted ? (
              <CheckCircle2 className="h-7 w-7" />
            ) : isWrongAnswer ? (
              <XCircle className="h-7 w-7" />
            ) : (
              <AlertTriangle className="h-7 w-7" />
            )}
          </div>
          <div>
            <span className="text-[10px] font-semibold tracking-[0.2em] text-slate-400 uppercase">
              Verdict Status
            </span>
            <h3
              className={`text-2xl font-bold tracking-tight ${
                isAccepted
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-rose-600 dark:text-rose-400'
              }`}
            >
              {submission.status.replace('_', ' ').toUpperCase()}
            </h3>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 gap-3 mb-6">
          <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] p-4">
            <div className="flex items-center gap-2 text-slate-400 mb-1">
              <Clock className="h-4 w-4" />
              <span className="text-[11px] font-medium uppercase tracking-wider">Runtime</span>
            </div>
            <p className="text-xl font-bold text-slate-900 dark:text-white font-mono">
              {submission.runtime_ms ?? 0} <span className="text-xs font-normal text-slate-400">ms</span>
            </p>
          </div>

          <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] p-4">
            <div className="flex items-center gap-2 text-slate-400 mb-1">
              <Cpu className="h-4 w-4" />
              <span className="text-[11px] font-medium uppercase tracking-wider">Memory</span>
            </div>
            <p className="text-xl font-bold text-slate-900 dark:text-white font-mono">
              {Math.round((submission.memory_kb ?? 0) / 1024)}{' '}
              <span className="text-xs font-normal text-slate-400">MB</span>
            </p>
          </div>
        </div>

        {/* First Failed Test Case (LeetCode-style diff) */}
        {submission.first_failed_case && (
          <div className="mb-6 rounded-2xl border border-rose-500/20 bg-rose-500/5 p-4 space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-rose-600 dark:text-rose-400 font-sans text-xs">
                Failed on Case {submission.first_failed_case.test_case_number} of {submission.first_failed_case.total_test_cases}
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-500 font-bold">
                WRONG ANSWER
              </span>
            </div>

            <div>
              <p className="text-slate-400 text-[10px] uppercase font-sans mb-1">Input:</p>
              <pre className="p-2 rounded bg-black/5 dark:bg-black/40 text-slate-800 dark:text-slate-200 overflow-x-auto whitespace-pre-wrap">
                {submission.first_failed_case.input || '(empty)'}
              </pre>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <p className="text-rose-500 text-[10px] uppercase font-sans mb-1">Your Output:</p>
                <pre className="p-2 rounded bg-rose-500/10 border border-rose-500/20 text-rose-700 dark:text-rose-300 overflow-x-auto whitespace-pre-wrap">
                  {submission.first_failed_case.actual_output || '(empty)'}
                </pre>
              </div>
              <div>
                <p className="text-emerald-500 text-[10px] uppercase font-sans mb-1">Expected Output:</p>
                <pre className="p-2 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-300 overflow-x-auto whitespace-pre-wrap">
                  {submission.first_failed_case.expected_output || '(empty)'}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* Error Details (if any and not already covered by first_failed_case) */}
        {submission.error_message && !submission.first_failed_case && (
          <div className="mb-6 rounded-2xl border border-rose-500/20 bg-rose-500/5 p-4">
            <p className="text-xs font-semibold text-rose-600 dark:text-rose-400 mb-1">Execution Message:</p>
            <pre className="font-mono text-xs text-rose-500 dark:text-rose-300 whitespace-pre-wrap">
              {submission.error_message}
            </pre>
          </div>
        )}

        {/* Bottom Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="w-full sm:w-auto rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900 px-6 py-2.5 text-xs font-semibold hover:opacity-90 transition-opacity shadow-sm"
          >
            Continue Solving
          </button>
        </div>
      </div>
    </div>
  );
};
