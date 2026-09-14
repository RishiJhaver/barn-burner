import React, { useState, useEffect, useRef } from 'react';
import Editor from '@monaco-editor/react';
import {
  ArrowLeft,
  Play,
  Send,
  RotateCcw,
  Code2,
  Terminal,
  FileText,
  History,
  CheckCircle2,
  XCircle,
  Clock,
  Sparkles,
  ChevronUp,
  ChevronDown,
  ArrowUpRight,
  GripVertical,
  GripHorizontal,
} from 'lucide-react';
import { Problem, ProblemDifficulty, SupportedLanguage, SubmissionDetail } from '../types';
import { submissionsApi } from '../api/submissionsApi';
import { useTheme } from '../context/ThemeContext';

interface WorkspaceProps {
  problem: Problem;
  onBack: () => void;
  onOpenVerdict: (submission: SubmissionDetail) => void;
}

const DEFAULT_TEMPLATES: Record<SupportedLanguage, string> = {
  python: `class Solution:
    def solve(self, nums: List[int], target: int) -> List[int]:
        # Write your code here
        pass
`,
  cpp: `class Solution {
public:
    int solve(vector<int>& nums, int target) {
        // Write your code here
        return 0;
    }
};
`,
  java: `class Solution {
    public int solve(int[] nums, int target) {
        // Write your code here
        return 0;
    }
}
`,
  javascript: `/**
 * @param {number[]} nums
 * @param {number} target
 * @return {number}
 */
var solve = function(nums, target) {
    // Write your code here
};
`,
};

export const Workspace: React.FC<WorkspaceProps> = ({ problem, onBack, onOpenVerdict }) => {
  const { isDark } = useTheme();
  const [language, setLanguage] = useState<SupportedLanguage>('python');
  const [code, setCode] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'description' | 'history'>('description');
  const [consoleOpen, setConsoleOpen] = useState<boolean>(true);
  const [consoleTab, setConsoleTab] = useState<'testcases' | 'output'>('testcases');
  const [selectedTestCaseIdx, setSelectedTestCaseIdx] = useState<number>(0);

  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [runResult, setRunResult] = useState<SubmissionDetail | null>(null);
  const [historyItems, setHistoryItems] = useState<SubmissionDetail[]>([]);
  const [historyLoading, setHistoryLoading] = useState<boolean>(false);

  // Resizable split pane layout state
  const [leftWidthPercent, setLeftWidthPercent] = useState<number>(45);
  const [consoleHeight, setConsoleHeight] = useState<number>(230);
  const [isDraggingHorizontal, setIsDraggingHorizontal] = useState<boolean>(false);
  const [isDraggingVertical, setIsDraggingVertical] = useState<boolean>(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const rightPanelRef = useRef<HTMLDivElement>(null);

  // Horizontal Resizer: Drag left/right to resize Problem Description vs Code/Console
  const handleHorizontalPointerDown = (e: React.PointerEvent) => {
    e.preventDefault();
    setIsDraggingHorizontal(true);

    const onPointerMove = (moveEvent: PointerEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const relativeX = moveEvent.clientX - rect.left;
      const percent = (relativeX / rect.width) * 100;
      // Clamp between 20% and 80%
      const clamped = Math.min(Math.max(percent, 20), 80);
      setLeftWidthPercent(clamped);
    };

    const onPointerUp = () => {
      setIsDraggingHorizontal(false);
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
    };

    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
  };

  // Vertical Resizer: Drag up/down to resize Monaco Editor vs Test Cases / Output Console
  const handleVerticalPointerDown = (e: React.PointerEvent) => {
    e.preventDefault();
    setIsDraggingVertical(true);

    const onPointerMove = (moveEvent: PointerEvent) => {
      if (!rightPanelRef.current) return;
      const rect = rightPanelRef.current.getBoundingClientRect();
      // Distance from bottom of right panel
      const newHeight = rect.bottom - moveEvent.clientY;
      // Clamp between 80px and 75% of right panel height
      const maxHeight = Math.max(200, rect.height * 0.75);
      const clamped = Math.min(Math.max(newHeight, 80), maxHeight);
      setConsoleHeight(clamped);
      if (!consoleOpen) {
        setConsoleOpen(true);
      }
    };

    const onPointerUp = () => {
      setIsDraggingVertical(false);
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
    };

    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
  };

  // Prevent text selection and maintain cursor styling across iframe/editor boundaries during drag
  useEffect(() => {
    if (isDraggingHorizontal) {
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    } else if (isDraggingVertical) {
      document.body.style.cursor = 'row-resize';
      document.body.style.userSelect = 'none';
    } else {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }
    return () => {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDraggingHorizontal, isDraggingVertical]);

  // Load starter template when language or problem changes
  useEffect(() => {
    const existingTemplate = problem.templates?.find(
      (t) => t.language.toLowerCase() === language.toLowerCase()
    );
    if (existingTemplate && existingTemplate.starter_code) {
      setCode(existingTemplate.starter_code);
    } else {
      setCode(DEFAULT_TEMPLATES[language] || DEFAULT_TEMPLATES.python);
    }
  }, [language, problem]);

  // Load submissions history when history tab opens
  useEffect(() => {
    if (activeTab === 'history') {
      const fetchHistory = async () => {
        setHistoryLoading(true);
        try {
          const res = await submissionsApi.getSubmissionsHistory({
            problem_slug: problem.slug,
            limit: 20,
          });
          setHistoryItems(res.items);
        } catch (err) {
          console.error('Failed to load history:', err);
        } finally {
          setHistoryLoading(false);
        }
      };
      fetchHistory();
    }
  }, [activeTab, problem.slug]);

  // Handle RUN CODE (Fast evaluation on sample test cases)
  const handleRunCode = async () => {
    setIsRunning(true);
    setConsoleTab('output');
    setConsoleOpen(true);
    try {
      const resp = await submissionsApi.runCode(problem.slug, language, code);
      const subId = resp.submission_id;

      // Poll until finished
      let attempts = 0;
      const interval = setInterval(async () => {
        attempts++;
        try {
          const detail = await submissionsApi.getSubmission(subId);
          if (detail.status !== 'pending' && detail.status !== 'processing') {
            clearInterval(interval);
            setIsRunning(false);
            setRunResult(detail);
          } else if (attempts > 30) {
            clearInterval(interval);
            setIsRunning(false);
          }
        } catch (e) {
          clearInterval(interval);
          setIsRunning(false);
        }
      }, 500);
    } catch (err: any) {
      setIsRunning(false);
      alert(err.response?.data?.detail || 'Failed to run code');
    }
  };

  // Handle SUBMIT SOLUTION (Full hidden test case execution)
  const handleSubmitCode = async () => {
    setIsSubmitting(true);
    try {
      const resp = await submissionsApi.submitCode(problem.slug, language, code);
      const subId = resp.submission_id;

      // Poll for final verdict
      let attempts = 0;
      const interval = setInterval(async () => {
        attempts++;
        try {
          const detail = await submissionsApi.getSubmission(subId);
          if (detail.status !== 'pending' && detail.status !== 'processing') {
            clearInterval(interval);
            setIsSubmitting(false);
            onOpenVerdict(detail);
          } else if (attempts > 40) {
            clearInterval(interval);
            setIsSubmitting(false);
          }
        } catch (e) {
          clearInterval(interval);
          setIsSubmitting(false);
        }
      }, 600);
    } catch (err: any) {
      setIsSubmitting(false);
      alert(err.response?.data?.detail || 'Submission failed');
    }
  };

  const getDifficultyBadge = (diff: ProblemDifficulty) => {
    switch (diff.toLowerCase()) {
      case 'easy':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Easy
          </span>
        );
      case 'medium':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            Medium
          </span>
        );
      case 'hard':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
            Hard
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] overflow-hidden bg-transparent">
      {/* Workspace Header Toolbar */}
      <div className="flex items-center justify-between border-b border-black/10 dark:border-white/10 bg-white/70 dark:bg-[#0c0e14]/75 backdrop-blur-2xl px-4 py-2.5 text-xs transition-colors">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 rounded-xl border border-black/10 dark:border-white/15 bg-black/[0.02] dark:bg-white/[0.04] px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-black/[0.06] dark:hover:bg-white/[0.08] transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Catalog</span>
          </button>
          <div className="flex items-center gap-3">
            <span className="font-bold text-slate-900 dark:text-white text-sm tracking-tight">{problem.title}</span>
            {getDifficultyBadge(problem.difficulty)}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Language Selector */}
          <div className="flex items-center gap-1.5 rounded-xl border border-black/10 dark:border-white/15 bg-white/60 dark:bg-[#12151d]/60 px-3 py-1 shadow-sm">
            <Code2 className="h-3.5 w-3.5 text-slate-600 dark:text-slate-400" />
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
              className="bg-transparent font-medium text-xs text-slate-900 dark:text-white focus:outline-none cursor-pointer"
            >
              <option value="python" className="bg-white dark:bg-[#12151d] text-slate-900 dark:text-white">Python 3.11</option>
              <option value="cpp" className="bg-white dark:bg-[#12151d] text-slate-900 dark:text-white">C++ 20</option>
              <option value="java" className="bg-white dark:bg-[#12151d] text-slate-900 dark:text-white">Java 21</option>
              <option value="javascript" className="bg-white dark:bg-[#12151d] text-slate-900 dark:text-white">JavaScript (Node.js)</option>
            </select>
          </div>

          {/* Reset Template */}
          <button
            onClick={() => {
              const tmpl = problem.templates?.find((t) => t.language === language);
              setCode(tmpl?.starter_code || DEFAULT_TEMPLATES[language]);
            }}
            title="Reset code template"
            className="rounded-xl border border-black/10 dark:border-white/15 p-2 text-slate-500 hover:text-slate-900 dark:hover:text-white hover:bg-black/[0.03] dark:hover:bg-white/[0.05] transition-colors"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Main Split Screen */}
      <div
        ref={containerRef}
        style={{ '--left-w': `${leftWidthPercent}%` } as React.CSSProperties}
        className="flex-1 flex flex-col md:flex-row overflow-hidden relative"
      >
        {/* LEFT PANEL: Problem Details & Submissions */}
        <div
          style={{ width: typeof window !== 'undefined' && window.innerWidth >= 768 ? `${leftWidthPercent}%` : undefined }}
          className="w-full md:w-[var(--left-w)] flex flex-col border-b md:border-b-0 border-black/10 dark:border-white/10 bg-white/70 dark:bg-[#0c0e14]/75 backdrop-blur-2xl overflow-hidden shrink-0"
        >
          {/* Left Tabs */}
          <div className="flex items-center gap-2 border-b border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.01] px-4 pt-2 text-xs">
            <button
              onClick={() => setActiveTab('description')}
              className={`flex items-center gap-1.5 px-3 py-2 border-b-2 font-medium transition-all ${
                activeTab === 'description'
                  ? 'border-slate-900 dark:border-white text-slate-900 dark:text-white font-semibold'
                  : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              <FileText className="h-3.5 w-3.5" />
              <span>Description</span>
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`flex items-center gap-1.5 px-3 py-2 border-b-2 font-medium transition-all ${
                activeTab === 'history'
                  ? 'border-slate-900 dark:border-white text-slate-900 dark:text-white font-semibold'
                  : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              <History className="h-3.5 w-3.5" />
              <span>Submissions</span>
            </button>
          </div>

          {/* Left Tab Content */}
          <div className="flex-1 overflow-y-auto p-6 scrollbar-thin text-slate-700 dark:text-slate-300 font-sans text-sm leading-relaxed space-y-6">
            {activeTab === 'description' ? (
              <>
                {/* Description Body */}
                <div className="whitespace-pre-wrap font-sans text-slate-800 dark:text-slate-200 leading-relaxed text-sm">
                  {problem.description}
                </div>

                {/* Sample Test Case Examples */}
                {problem.sample_test_cases && problem.sample_test_cases.length > 0 && (
                  <div className="space-y-4 pt-2">
                    <h4 className="text-[11px] font-semibold uppercase tracking-[0.15em] text-slate-400 dark:text-slate-500">
                      Examples
                    </h4>
                    {problem.sample_test_cases.map((tc, idx) => (
                      <div
                        key={idx}
                        className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] p-4 font-mono text-xs space-y-2.5 shadow-sm"
                      >
                        <p className="font-semibold text-slate-600 dark:text-slate-400">Example {idx + 1}:</p>
                        <div className="space-y-1">
                          <p className="text-slate-400 text-[10px] uppercase font-sans">Input:</p>
                          <pre className="p-2.5 rounded-xl bg-black/[0.03] dark:bg-black/40 text-slate-800 dark:text-slate-200 overflow-x-auto border border-black/[0.04] dark:border-white/[0.04]">
                            {tc.input}
                          </pre>
                        </div>
                        <div className="space-y-1">
                          <p className="text-slate-400 text-[10px] uppercase font-sans">Output:</p>
                          <pre className="p-2.5 rounded-xl bg-black/[0.03] dark:bg-black/40 text-emerald-600 dark:text-emerald-400 font-bold overflow-x-auto border border-black/[0.04] dark:border-white/[0.04]">
                            {tc.expected_output}
                          </pre>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Tags Section */}
                {problem.tags && problem.tags.length > 0 && (
                  <div className="pt-4 border-t border-black/10 dark:border-white/10">
                    <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 mb-2 uppercase tracking-wider">Related Topics</p>
                    <div className="flex flex-wrap gap-1.5">
                      {problem.tags.map((tag) => (
                        <span
                          key={tag.id}
                          className="rounded-md border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.03] px-2.5 py-1 text-xs text-slate-600 dark:text-slate-400 font-medium"
                        >
                          {tag.name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              /* Submissions History List */
              <div className="space-y-3">
                {historyLoading ? (
                  <div className="flex h-32 items-center justify-center text-xs text-slate-400">
                    Loading submissions...
                  </div>
                ) : historyItems.length === 0 ? (
                  <div className="p-8 text-center text-slate-400 text-xs">
                    No submissions recorded yet for this problem.
                  </div>
                ) : (
                  <div className="divide-y divide-black/[0.06] dark:divide-white/[0.06] text-xs">
                    {historyItems.map((sub) => (
                      <div
                        key={sub.id}
                        onClick={() => onOpenVerdict(sub)}
                        className="flex items-center justify-between py-3 px-2 hover:bg-black/[0.02] dark:hover:bg-white/[0.02] rounded-xl cursor-pointer transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          {sub.status === 'accepted' ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                          ) : (
                            <XCircle className="h-4 w-4 text-rose-500" />
                          )}
                          <div>
                            <p className={`font-semibold ${sub.status === 'accepted' ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                              {sub.status.toUpperCase()}
                            </p>
                            <p className="text-[10px] text-slate-400">{new Date(sub.created_at).toLocaleString()}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-slate-700 dark:text-slate-300 font-mono uppercase">{sub.language}</p>
                          <p className="text-[10px] text-slate-400">{sub.runtime_ms ?? 0} ms</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Horizontal Drag Handle (Left / Right) */}
        <div
          onPointerDown={handleHorizontalPointerDown}
          className={`hidden md:flex w-2.5 relative items-center justify-center cursor-col-resize select-none bg-black/[0.03] dark:bg-white/[0.03] hover:bg-blue-500/20 active:bg-blue-500/40 border-l border-r border-black/[0.06] dark:border-white/[0.06] transition-colors z-20 shrink-0 ${
            isDraggingHorizontal ? 'bg-blue-500/30 dark:bg-blue-500/40' : ''
          }`}
          title="Drag horizontally to resize problem description and code editor"
        >
          <GripVertical className="h-4 w-4 text-slate-400/60 dark:text-slate-500 hover:text-blue-500" />
        </div>

        {/* RIGHT PANEL: Monaco Editor & Interactive Console */}
        <div
          ref={rightPanelRef}
          className="flex-1 flex flex-col overflow-hidden bg-white/50 dark:bg-[#07090e]/60 backdrop-blur-xl min-w-0"
        >
          {/* Monaco Editor Container */}
          <div className="flex-1 relative overflow-hidden">
            <Editor
              height="100%"
              language={language === 'cpp' ? 'cpp' : language === 'python' ? 'python' : language === 'java' ? 'java' : 'javascript'}
              theme={isDark ? 'vs-dark' : 'light'}
              value={code}
              onChange={(val) => setCode(val || '')}
              options={{
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                fontSize: 14,
                lineHeight: 22,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                automaticLayout: true,
                tabSize: 4,
                cursorBlinking: 'smooth',
                padding: { top: 14, bottom: 14 },
              }}
            />
          </div>

          {/* Vertical Drag Handle (Up / Down) */}
          <div
            onPointerDown={handleVerticalPointerDown}
            className={`h-2.5 relative flex items-center justify-center cursor-row-resize select-none border-t border-black/[0.08] dark:border-white/[0.08] bg-black/[0.02] dark:bg-white/[0.02] hover:bg-blue-500/20 active:bg-blue-500/40 transition-colors z-10 shrink-0 ${
              isDraggingVertical ? 'bg-blue-500/30 dark:bg-blue-500/40' : ''
            }`}
            title="Drag vertically to resize code editor and testcases panel"
          >
            <GripHorizontal className="h-4 w-4 text-slate-400/60 dark:text-slate-500 hover:text-blue-500" />
          </div>

          {/* Console Drawer & Action Footer */}
          <div className="border-t border-black/10 dark:border-white/10 bg-white/80 dark:bg-[#0c0e14]/85 backdrop-blur-2xl flex flex-col">
            {/* Drawer Header Tabs */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-black/[0.06] dark:border-white/[0.06] text-xs">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setConsoleTab('testcases');
                    setConsoleOpen(true);
                  }}
                  className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                    consoleTab === 'testcases' && consoleOpen
                      ? 'bg-black/5 dark:bg-white/10 text-slate-900 dark:text-white font-semibold'
                      : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                  }`}
                >
                  Test Cases
                </button>
                <button
                  onClick={() => {
                    setConsoleTab('output');
                    setConsoleOpen(true);
                  }}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-lg font-medium transition-colors ${
                    consoleTab === 'output' && consoleOpen
                      ? 'bg-black/5 dark:bg-white/10 text-slate-900 dark:text-white font-semibold'
                      : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                  }`}
                >
                  <Terminal className="h-3 w-3" />
                  <span>Output</span>
                </button>
              </div>

              <button
                onClick={() => setConsoleOpen(!consoleOpen)}
                className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 p-1"
              >
                {consoleOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
              </button>
            </div>

            {/* Collapsible Console Drawer Body with Dynamic Resizable Height */}
            {consoleOpen && (
              <div
                style={{ height: `${consoleHeight}px` }}
                className="overflow-y-auto p-4 bg-black/[0.02] dark:bg-black/30 font-mono text-xs scrollbar-thin"
              >
                {consoleTab === 'testcases' ? (
                  <div className="space-y-3">
                    {problem.sample_test_cases && problem.sample_test_cases.length > 0 ? (
                      <div>
                        <div className="flex gap-2 mb-2">
                          {problem.sample_test_cases.map((_, i) => (
                            <button
                              key={i}
                              onClick={() => setSelectedTestCaseIdx(i)}
                              className={`px-3 py-1 rounded-xl text-xs font-semibold transition-all ${
                                selectedTestCaseIdx === i
                                  ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm'
                                  : 'bg-black/[0.03] dark:bg-white/[0.05] text-slate-600 dark:text-slate-400 hover:bg-black/[0.06] dark:hover:bg-white/[0.08]'
                              }`}
                            >
                              Case {i + 1}
                            </button>
                          ))}
                        </div>
                        <div className="space-y-2 rounded-2xl bg-white/70 dark:bg-slate-900/60 p-3.5 border border-black/10 dark:border-white/10">
                          <p className="text-slate-400 text-[10px] uppercase font-sans font-semibold">Input:</p>
                          <pre className="text-slate-800 dark:text-slate-200 whitespace-pre-wrap font-mono">
                            {problem.sample_test_cases[selectedTestCaseIdx]?.input}
                          </pre>
                          <p className="text-slate-400 text-[10px] uppercase font-sans font-semibold pt-1">Expected Output:</p>
                          <pre className="text-emerald-600 dark:text-emerald-400 font-semibold whitespace-pre-wrap font-mono">
                            {problem.sample_test_cases[selectedTestCaseIdx]?.expected_output}
                          </pre>
                        </div>
                      </div>
                    ) : (
                      <p className="text-slate-400">No sample test cases configured.</p>
                    )}
                  </div>
                ) : (
                  /* Execution Console Output */
                  <div>
                    {isRunning ? (
                      <div className="flex h-28 items-center justify-center gap-2 text-slate-700 dark:text-slate-300">
                        <div className="h-4 w-4 rounded-full border-2 border-slate-800 dark:border-white border-t-transparent animate-spin" />
                        <span>Running code in sandbox...</span>
                      </div>
                    ) : runResult ? (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between pb-2 border-b border-black/10 dark:border-white/10 font-sans">
                          <span
                            className={`font-bold text-sm ${
                              runResult.status === 'accepted' ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'
                            }`}
                          >
                            {runResult.status.toUpperCase()}
                          </span>
                          <span className="text-slate-500 font-mono text-xs">
                            Runtime: {runResult.runtime_ms ?? 0} ms | Memory: {Math.round((runResult.memory_kb ?? 0) / 1024)} MB
                          </span>
                        </div>
                        {runResult.error_message && !runResult.first_failed_case && (
                          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 font-mono text-xs">
                            {runResult.error_message}
                          </div>
                        )}

                        {runResult.first_failed_case && (
                          <div className="p-4 rounded-xl bg-rose-500/5 border border-rose-500/20 space-y-3 font-mono text-xs">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-rose-600 dark:text-rose-400 font-sans text-xs">
                                Failed on Case {runResult.first_failed_case.test_case_number} of {runResult.first_failed_case.total_test_cases}
                              </span>
                              <span className="text-[10px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-500 font-bold">
                                WRONG ANSWER
                              </span>
                            </div>

                            <div>
                              <p className="text-slate-400 text-[10px] uppercase font-sans mb-1">Input:</p>
                              <pre className="p-2 rounded bg-black/5 dark:bg-black/40 text-slate-800 dark:text-slate-200 overflow-x-auto whitespace-pre-wrap">
                                {runResult.first_failed_case.input || '(empty)'}
                              </pre>
                            </div>

                            <div className="grid grid-cols-2 gap-2">
                              <div>
                                <p className="text-rose-500 text-[10px] uppercase font-sans mb-1">Your Output:</p>
                                <pre className="p-2 rounded bg-rose-500/10 border border-rose-500/20 text-rose-700 dark:text-rose-300 overflow-x-auto whitespace-pre-wrap">
                                  {runResult.first_failed_case.actual_output || '(empty)'}
                                </pre>
                              </div>
                              <div>
                                <p className="text-emerald-500 text-[10px] uppercase font-sans mb-1">Expected Output:</p>
                                <pre className="p-2 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-300 overflow-x-auto whitespace-pre-wrap">
                                  {runResult.first_failed_case.expected_output || '(empty)'}
                                </pre>
                              </div>
                            </div>
                          </div>
                        )}
                        {runResult.sample_results && runResult.sample_results.length > 0 && (
                          <div className="space-y-2">
                            {runResult.sample_results.map((res, i) => (
                              <div key={i} className="p-3 rounded-xl bg-white/70 dark:bg-slate-900/60 border border-black/10 dark:border-white/10">
                                <p className="text-slate-700 dark:text-slate-300 font-semibold mb-1">Case {i + 1}: {res.status.toUpperCase()}</p>
                                <p className="text-slate-400 text-[10px] uppercase font-sans">Actual Output:</p>
                                <pre className="text-slate-800 dark:text-slate-200 font-mono">{res.actual_output || 'None'}</pre>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-slate-400 text-center py-6 font-sans">
                        Click "Run Code" to test your solution against sample test cases.
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Action Buttons Bar */}
            <div className="flex items-center justify-end gap-3 px-4 py-3 border-t border-black/10 dark:border-white/10 bg-white/60 dark:bg-[#0c0e14]/60">
              {/* Run Button */}
              <button
                disabled={isRunning || isSubmitting}
                onClick={handleRunCode}
                className="flex items-center gap-2 rounded-xl border border-black/15 dark:border-white/15 bg-white dark:bg-white/[0.05] px-4 py-2 text-xs font-semibold text-slate-900 dark:text-white shadow-sm hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-slate-900 disabled:opacity-50 transition-all"
              >
                {isRunning ? (
                  <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
                ) : (
                  <Play className="h-3.5 w-3.5 fill-current" />
                )}
                <span>Run Code</span>
              </button>

              {/* Submit Button */}
              <button
                disabled={isRunning || isSubmitting}
                onClick={handleSubmitCode}
                className="flex items-center gap-2 rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900 px-5 py-2 text-xs font-semibold shadow-sm hover:opacity-90 disabled:opacity-50 transition-all"
              >
                {isSubmitting ? (
                  <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
                ) : (
                  <Send className="h-3.5 w-3.5" />
                )}
                <span>Submit Solution</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
