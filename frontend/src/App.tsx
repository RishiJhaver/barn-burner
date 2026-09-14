import React, { useState } from 'react';
import { Problem, SubmissionDetail } from './types';
import { Navbar } from './components/Navbar';
import { ProblemCatalog } from './components/ProblemCatalog';
import { Workspace } from './components/Workspace';
import { VerdictModal } from './components/VerdictModal';
import { StatsModal } from './components/StatsModal';
import { LoginModal } from './components/LoginModal';

export const App: React.FC = () => {
  const [activeView, setActiveView] = useState<'catalog' | 'workspace'>('catalog');
  const [selectedProblem, setSelectedProblem] = useState<Problem | null>(null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState<boolean>(false);
  const [isStatsModalOpen, setIsStatsModalOpen] = useState<boolean>(false);
  const [verdictSubmission, setVerdictSubmission] = useState<SubmissionDetail | null>(null);

  const handleSelectProblem = (problem: Problem) => {
    setSelectedProblem(problem);
    setActiveView('workspace');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleBackToCatalog = () => {
    setActiveView('catalog');
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-[#fcfdfe] dark:bg-[#07090e] text-slate-900 dark:text-slate-100 font-sans transition-colors duration-200">
      {/* Dynamic Iridescent Pastel Mesh Ambient Background (Matching reference screenshot) */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="ambient-glow -top-32 right-1/4 h-[550px] w-[550px] bg-gradient-to-br from-pink-400/40 via-purple-400/35 to-sky-300/35 dark:from-pink-600/25 dark:via-purple-600/20 dark:to-sky-500/20" />
        <div className="ambient-glow top-1/4 -right-16 h-[500px] w-[500px] bg-gradient-to-tr from-amber-300/35 via-rose-300/30 to-violet-400/30 dark:from-amber-600/20 dark:via-rose-600/15 dark:to-violet-600/15" />
        <div className="ambient-glow -bottom-24 left-1/12 h-[550px] w-[550px] bg-gradient-to-br from-cyan-300/30 via-teal-200/25 to-indigo-300/30 dark:from-cyan-600/15 dark:via-teal-600/15 dark:to-indigo-600/15" />
      </div>

      {/* Top Swiss Navbar */}
      <Navbar
        activeView={activeView}
        onNavigateHome={handleBackToCatalog}
        onOpenLogin={() => setIsLoginModalOpen(true)}
        onOpenStats={() => setIsStatsModalOpen(true)}
      />

      {/* Main View Area */}
      <main className="relative z-10 flex-1">
        {activeView === 'catalog' || !selectedProblem ? (
          <ProblemCatalog onSelectProblem={handleSelectProblem} />
        ) : (
          <Workspace
            problem={selectedProblem}
            onBack={handleBackToCatalog}
            onOpenVerdict={(submission) => setVerdictSubmission(submission)}
          />
        )}
      </main>

      {/* Interactive Modals */}
      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
      />
      <StatsModal
        isOpen={isStatsModalOpen}
        onClose={() => setIsStatsModalOpen(false)}
      />
      <VerdictModal
        submission={verdictSubmission}
        onClose={() => setVerdictSubmission(null)}
      />

      {/* Minimalist Bento Footer matching screenshot bottom row */}
      {activeView === 'catalog' && (
        <footer className="relative z-10 border-t border-black/10 dark:border-white/10 bg-white/60 dark:bg-[#0c0e14]/60 backdrop-blur-xl py-6 text-xs text-slate-500 dark:text-slate-400 transition-colors">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div>
              <span>All rights are reserved, 2026</span>
            </div>

            <div className="flex items-center gap-6 font-medium">
              <a href="https://medium.com" target="_blank" rel="noreferrer" className="hover:text-slate-900 dark:hover:text-white transition-colors">
                Medium
              </a>
              <a href="https://linkedin.com" target="_blank" rel="noreferrer" className="hover:text-slate-900 dark:hover:text-white transition-colors">
                LinkedIn
              </a>
            </div>

            <div className="flex flex-wrap items-center gap-6 text-[11px] text-slate-400 dark:text-slate-500">
              <span className="hover:text-slate-700 dark:hover:text-slate-300 cursor-pointer transition-colors">
                Terms and Conditions
              </span>
              <span className="hover:text-slate-700 dark:hover:text-slate-300 cursor-pointer transition-colors">
                Disclaimer
              </span>
              <span className="hover:text-slate-700 dark:hover:text-slate-300 cursor-pointer transition-colors">
                Privacy Policy
              </span>
            </div>
          </div>
        </footer>
      )}
    </div>
  );
};

export default App;
