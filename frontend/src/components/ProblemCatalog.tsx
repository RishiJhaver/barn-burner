import React, { useState, useEffect } from 'react';
import {
  Search,
  ArrowUpRight,
  Code2,
  Cpu,
  Layers,
  Sparkles,
  Terminal,
  ExternalLink,
  ChevronRight,
  Zap,
  Globe,
  CheckCircle2,
} from 'lucide-react';
import { Problem, ProblemDifficulty, Tag } from '../types';
import { problemsApi } from '../api/problemsApi';

interface ProblemCatalogProps {
  onSelectProblem: (problem: Problem) => void;
}

export const ProblemCatalog: React.FC<ProblemCatalogProps> = ({ onSelectProblem }) => {
  const [problems, setProblems] = useState<Problem[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('all');
  const [selectedTag, setSelectedTag] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [activeLangFilter, setActiveLangFilter] = useState<string | null>(null);

  useEffect(() => {
    const fetchCatalog = async () => {
      setIsLoading(true);
      try {
        const [probRes, tagsRes] = await Promise.all([
          problemsApi.getProblems({
            difficulty: selectedDifficulty !== 'all' ? selectedDifficulty : undefined,
            tag_slug: selectedTag !== 'all' ? selectedTag : undefined,
          }),
          problemsApi.getTags(),
        ]);
        setProblems(probRes.items || []);
        setTags(tagsRes || []);
      } catch (err) {
        console.error('Failed to load catalog:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchCatalog();
  }, [selectedDifficulty, selectedTag]);

  // Filter problems by search query
  const filteredProblems = problems.filter((p) => {
    const query = searchQuery.toLowerCase();
    const matchesSearch = p.title.toLowerCase().includes(query) || p.slug.toLowerCase().includes(query);
    return matchesSearch;
  });

  const getDifficultyBadge = (diff: ProblemDifficulty) => {
    switch (diff.toLowerCase()) {
      case 'easy':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium tracking-wide bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Easy
          </span>
        );
      case 'medium':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium tracking-wide bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            Medium
          </span>
        );
      case 'hard':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium tracking-wide bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
            Hard
          </span>
        );
      default:
        return null;
    }
  };

  const handleStartGuide = () => {
    if (problems.length > 0) {
      onSelectProblem(problems[0]);
    }
  };

  return (
    <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-12">
      {/* =========================================================================
          BENTO HERO SECTION (Pixel-faithful reproduction of user's reference image)
          ========================================================================= */}
      <section className="relative overflow-hidden rounded-2xl sm:rounded-3xl border border-black/15 dark:border-white/15 bg-white/70 dark:bg-[#0c0e14]/75 backdrop-blur-3xl shadow-xl transition-all">
        {/* Soft iridescent pastel glow inside the bento frame */}
        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-gradient-to-br from-pink-400/35 via-purple-400/30 to-sky-300/35 blur-3xl" />
        <div className="pointer-events-none absolute right-1/4 top-10 h-72 w-72 rounded-full bg-gradient-to-tl from-amber-300/30 via-rose-300/30 to-violet-400/25 blur-3xl" />

        {/* --- Top Bento Row: Geometric Logo + "Start from scratch" --- */}
        <div className="grid grid-cols-1 md:grid-cols-12 border-b border-black/10 dark:border-white/10">
          {/* Logo cell */}
          <div className="md:col-span-4 lg:col-span-3 p-8 sm:p-10 flex items-center md:border-r border-black/10 dark:border-white/10">
            {/* Geometric knot SVG glyph matching screenshot */}
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-black/10 dark:border-white/15 bg-black/[0.02] dark:bg-white/[0.04] text-slate-900 dark:text-white shadow-inner">
              <svg width="34" height="34" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                {/* Interlocking geometric modern loops */}
                <path d="M12 24C12 17.3726 17.3726 12 24 12C30.6274 12 36 17.3726 36 24" />
                <path d="M36 24C36 30.6274 30.6274 36 24 36C17.3726 36 12 30.6274 12 24" />
                <path d="M24 12V36" strokeDasharray="3 3" />
                <circle cx="24" cy="24" r="5" />
                <path d="M34 14L40 8M40 8H34M40 8V14" />
              </svg>
            </div>
          </div>

          {/* Heading cell */}
          <div className="md:col-span-8 lg:col-span-9 p-8 sm:p-10 flex flex-col justify-center">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-slate-900 dark:text-white">
              Start from scratch
            </h1>
            <p className="mt-2 text-sm sm:text-base text-slate-500 dark:text-slate-400 font-normal">
              All resources that we share are available. Sandboxed execution with real-time test verification.
            </p>
          </div>
        </div>

        {/* --- Bottom Bento 3-Column Grid --- */}
        <div className="grid grid-cols-1 md:grid-cols-12">
          {/* 1. Left Cell: "GUIDE" */}
          <div className="md:col-span-4 p-8 sm:p-10 flex flex-col justify-between border-b md:border-b-0 md:border-r border-black/10 dark:border-white/10 hover:bg-black/[0.015] dark:hover:bg-white/[0.015] transition-colors group">
            <div>
              <span className="text-[10px] font-semibold tracking-[0.25em] text-slate-400 dark:text-slate-500 uppercase">
                GUIDE
              </span>
              <h2 className="mt-4 text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white leading-snug">
                Start reading and doing your research on algorithmic mastery.
              </h2>
              <p className="mt-3 text-xs sm:text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                This will give you an understanding of whether you are actually interested in exploring software performance and cloud-scale problem solving.
              </p>
            </div>

            <div className="mt-8 pt-4">
              <button
                onClick={handleStartGuide}
                className="group/arrow inline-flex h-12 w-12 items-center justify-center rounded-xl border border-black/15 dark:border-white/15 bg-black/[0.03] dark:bg-white/[0.05] text-slate-900 dark:text-white hover:bg-slate-900 hover:text-white dark:hover:bg-white dark:hover:text-slate-900 transition-all transform hover:scale-105"
                title="Jump directly to first problem"
              >
                <ArrowUpRight className="h-6 w-6 transition-transform group-hover/arrow:translate-x-0.5 group-hover/arrow:-translate-y-0.5" />
              </button>
            </div>
          </div>

          {/* 2. Center Cell: "DOWNLOADS / RUNTIMES" */}
          <div className="md:col-span-4 flex flex-col border-b md:border-b-0 md:border-r border-black/10 dark:border-white/10">
            <div className="p-8 sm:p-10 flex-1 hover:bg-black/[0.015] dark:hover:bg-white/[0.015] transition-colors">
              <span className="text-[10px] font-semibold tracking-[0.25em] text-slate-400 dark:text-slate-500 uppercase">
                RUNTIMES
              </span>
              <h2 className="mt-4 text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white leading-snug">
                Explore tools and find the ones you like.
              </h2>
              <p className="mt-3 text-xs sm:text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                Single-call sandboxed compilation for C++20, Python 3.11, Java 21, and Node.js 20 with zero latency.
              </p>
            </div>

            {/* Language badges matching the [X4] [in] [💎] rounded square icons in reference */}
            <div className="p-6 sm:p-8 border-t border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.01] flex items-center gap-3">
              <div className="flex items-center gap-2.5">
                {[
                  { label: 'C++', icon: 'C++', desc: 'C++ 20 Standard' },
                  { label: 'Py', icon: 'Py', desc: 'Python 3.11 Runtime' },
                  { label: 'Java', icon: '☕', desc: 'OpenJDK 21 LTS' },
                  { label: 'JS', icon: 'JS', desc: 'Node.js 20 Engine' },
                ].map((runtime) => (
                  <button
                    key={runtime.label}
                    onClick={() => setActiveLangFilter(activeLangFilter === runtime.label ? null : runtime.label)}
                    className={`flex h-10 px-3 items-center justify-center rounded-xl border text-xs font-mono font-bold tracking-wide transition-all ${
                      activeLangFilter === runtime.label
                        ? 'border-slate-900 bg-slate-900 text-white dark:border-white dark:bg-white dark:text-slate-900 shadow-sm'
                        : 'border-black/15 dark:border-white/15 bg-white/50 dark:bg-white/[0.04] text-slate-700 dark:text-slate-300 hover:border-black/30 dark:hover:border-white/30'
                    }`}
                    title={runtime.desc}
                  >
                    {runtime.icon}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* 3. Right Cell: "LINKS & CLOUD INFRASTRUCTURE" */}
          <div className="md:col-span-4 flex flex-col justify-between">
            {/* Top link block */}
            <div className="p-8 sm:p-10 hover:bg-black/[0.015] dark:hover:bg-white/[0.015] transition-colors">
              <span className="text-[10px] font-semibold tracking-[0.25em] text-slate-400 dark:text-slate-500 uppercase">
                ENGINE
              </span>
              <h2 className="mt-4 text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white leading-snug">
                Find an online execution cluster right now!
              </h2>
            </div>

            {/* Bottom partner/tech links matching [Udemy] [coursera] [treehouse] */}
            <div className="p-6 sm:p-8 border-t border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.01] flex flex-wrap items-center justify-between gap-4">
              <a
                href="https://judge0.com"
                target="_blank"
                rel="noreferrer"
                className="group/link flex items-center gap-1.5 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
              >
                <span>⚡ Judge0</span>
                <span className="text-[10px] font-mono text-slate-400 group-hover/link:underline">judge0.com</span>
                <ArrowUpRight className="h-3 w-3 text-slate-400 group-hover/link:translate-x-0.5 group-hover/link:-translate-y-0.5 transition-transform" />
              </a>

              <a
                href="https://aws.amazon.com/ec2"
                target="_blank"
                rel="noreferrer"
                className="group/link flex items-center gap-1.5 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
              >
                <span>☁ AWS EC2</span>
                <span className="text-[10px] font-mono text-slate-400 group-hover/link:underline">aws.com</span>
                <ArrowUpRight className="h-3 w-3 text-slate-400 group-hover/link:translate-x-0.5 group-hover/link:-translate-y-0.5 transition-transform" />
              </a>

              <a
                href="https://microsoft.github.io/monaco-editor"
                target="_blank"
                rel="noreferrer"
                className="group/link flex items-center gap-1.5 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
              >
                <span>✨ Monaco</span>
                <span className="text-[10px] font-mono text-slate-400 group-hover/link:underline">monaco.dev</span>
                <ArrowUpRight className="h-3 w-3 text-slate-400 group-hover/link:translate-x-0.5 group-hover/link:-translate-y-0.5 transition-transform" />
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          PROBLEM REPOSITORY SECTION (Matching Swiss Minimalist Bento Table)
          ========================================================================= */}
      <section className="space-y-6">
        {/* Controls Bar: Search & Difficulty Pills */}
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
          {/* Search input */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search problems by title, slug, or keyword..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-2xl border border-black/10 dark:border-white/10 bg-white/60 dark:bg-[#0c0e14]/60 pl-11 pr-4 py-2.5 text-sm text-slate-900 dark:text-white placeholder-slate-400 backdrop-blur-xl focus:border-slate-900 dark:focus:border-white focus:outline-none transition-all shadow-sm"
            />
          </div>

          {/* Difficulty Segmented Filter Pills */}
          <div className="flex items-center gap-1 rounded-2xl border border-black/10 dark:border-white/10 bg-white/60 dark:bg-[#0c0e14]/60 p-1 backdrop-blur-xl">
            {['all', 'easy', 'medium', 'hard'].map((diff) => (
              <button
                key={diff}
                onClick={() => setSelectedDifficulty(diff)}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-medium uppercase tracking-wider transition-all ${
                  selectedDifficulty === diff
                    ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm font-semibold'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                {diff}
              </button>
            ))}
          </div>
        </div>

        {/* Tag Pills */}
        {tags.length > 0 && (
          <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
            <button
              onClick={() => setSelectedTag('all')}
              className={`flex-shrink-0 px-3 py-1 rounded-full text-xs font-medium transition-all ${
                selectedTag === 'all'
                  ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900'
                  : 'border border-black/10 dark:border-white/10 bg-white/40 dark:bg-white/[0.02] text-slate-600 dark:text-slate-400 hover:border-black/20 dark:hover:border-white/20'
              }`}
            >
              All Topics
            </button>
            {tags.map((tag) => (
              <button
                key={tag.id}
                onClick={() => setSelectedTag(selectedTag === tag.slug ? 'all' : tag.slug)}
                className={`flex-shrink-0 px-3 py-1 rounded-full text-xs font-medium transition-all ${
                  selectedTag === tag.slug
                    ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900'
                    : 'border border-black/10 dark:border-white/10 bg-white/40 dark:bg-white/[0.02] text-slate-600 dark:text-slate-400 hover:border-black/20 dark:hover:border-white/20'
                }`}
              >
                {tag.name}
              </button>
            ))}
          </div>
        )}

        {/* Problems List Card */}
        <div className="overflow-hidden rounded-2xl sm:rounded-3xl border border-black/10 dark:border-white/10 bg-white/70 dark:bg-[#0c0e14]/75 backdrop-blur-3xl shadow-sm">
          {isLoading ? (
            <div className="flex h-64 flex-col items-center justify-center gap-3">
              <div className="h-7 w-7 animate-spin rounded-full border-2 border-slate-900 dark:border-white border-t-transparent" />
              <p className="font-mono text-xs text-slate-400 tracking-wider">RETRIEVING PROBLEMS...</p>
            </div>
          ) : filteredProblems.length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center gap-2 p-6 text-center">
              <Terminal className="h-8 w-8 text-slate-400" />
              <p className="text-base font-semibold text-slate-800 dark:text-slate-200">No problems found</p>
              <p className="text-xs text-slate-400">Try modifying your search query or filters</p>
            </div>
          ) : (
            <div className="divide-y divide-black/[0.06] dark:divide-white/[0.06]">
              {filteredProblems.map((problem, idx) => (
                <div
                  key={problem.id}
                  onClick={() => onSelectProblem(problem)}
                  className="group flex flex-col sm:flex-row sm:items-center justify-between p-5 sm:px-8 hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors cursor-pointer"
                >
                  <div className="flex items-start sm:items-center gap-4">
                    <span className="font-mono text-xs font-semibold text-slate-400 w-8">
                      #{String(idx + 1).padStart(2, '0')}
                    </span>
                    <div>
                      <div className="flex flex-wrap items-center gap-3">
                        <h3 className="text-base font-bold text-slate-900 dark:text-white group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">
                          {problem.title}
                        </h3>
                        {getDifficultyBadge(problem.difficulty)}
                      </div>
                      <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                        {problem.tags?.map((tag) => (
                          <span
                            key={tag.id}
                            className="rounded-md px-2 py-0.5 text-[10px] font-medium text-slate-500 dark:text-slate-400 bg-black/[0.03] dark:bg-white/[0.04] border border-black/[0.06] dark:border-white/[0.06]"
                          >
                            {tag.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 mt-4 sm:mt-0 justify-end">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectProblem(problem);
                      }}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-black/10 dark:border-white/15 bg-white/80 dark:bg-white/[0.05] px-3.5 py-1.5 text-xs font-semibold text-slate-900 dark:text-white group-hover:bg-slate-900 group-hover:text-white dark:group-hover:bg-white dark:group-hover:text-slate-900 transition-all shadow-sm"
                    >
                      <span>Solve</span>
                      <ArrowUpRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
};
