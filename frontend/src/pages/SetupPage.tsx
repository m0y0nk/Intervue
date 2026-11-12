import React, { useState } from "react";
import {
  Terminal,
  Shield,
  Sparkles,
  Clock,
  ArrowRight,
  Loader2,
  Eye,
  EyeOff,
  BookOpen,
  RefreshCw,
  AlertCircle,
  Briefcase,
  Target,
  Code2,
  FileCode,
  LayoutDashboard,
} from "lucide-react";
import {
  InterviewCategory,
  InterviewConfig,
  InterviewDifficulty,
  InterviewMode,
  InterviewSource,
  InterviewStyle,
  SessionCreatePayload,
} from "../types";

interface SetupPageProps {
  onStartSession: (payload: SessionCreatePayload) => Promise<void>;
  isGenerating: boolean;
  statusMessage?: string;
  onViewDashboard?: () => void;
}

const SOURCE_META: Record<
  InterviewSource,
  {
    label: string;
    icon: React.ReactNode;
    description: string;
  }
> = {
  random_dsa: {
    label: "Random DSA",
    icon: <Sparkles className="w-3.5 h-3.5" />,
    description: "Standard algorithmic problem with sandbox differential validation.",
  },
  ai_business: {
    label: "Business Scenario",
    icon: <Briefcase className="w-3.5 h-3.5" />,
    description: "Real-world domain framing (fintech, logistics, streaming) hiding the DSA core.",
  },
  adaptive: {
    label: "Adaptive Practice",
    icon: <Target className="w-3.5 h-3.5" />,
    description: "History-driven weakness targeting. Requires >= 5 completed interviews.",
  },
  leetcode: {
    label: "LeetCode Paste",
    icon: <Code2 className="w-3.5 h-3.5" />,
    description: "Paste a problem statement from LeetCode. Converted and verified in sandbox.",
  },
  custom: {
    label: "Custom Problem",
    icon: <FileCode className="w-3.5 h-3.5" />,
    description: "Paste your own problem statement, constraints, or problem URL.",
  },
};

const MODE_META: Record<
  InterviewMode,
  {
    label: string;
    icon: React.ReactNode;
    description: string;
    blocksMixed?: boolean;
  }
> = {
  standard: {
    label: "Standard",
    icon: <BookOpen className="w-3.5 h-3.5" />,
    description: "Full metadata visible. Default interview experience.",
  },
  blind_mock: {
    label: "Blind Mock",
    icon: <EyeOff className="w-3.5 h-3.5" />,
    description: "Title, category & difficulty hidden server-side. Real-world FAANG simulation.",
  },
  topic_mastery: {
    label: "Topic Mastery",
    icon: <Shield className="w-3.5 h-3.5" />,
    description: "Focused practice on a single topic. Category is required.",
    blocksMixed: true,
  },
  revision: {
    label: "Revision",
    icon: <RefreshCw className="w-3.5 h-3.5" />,
    description: "Reload a past problem for comparison. Requires completed history.",
  },
};

export const SetupPage: React.FC<SetupPageProps> = ({
  onStartSession,
  isGenerating,
  statusMessage,
  onViewDashboard,
}) => {
  const [source, setSource] = useState<InterviewSource>("random_dsa");
  const [category, setCategory] = useState<InterviewCategory>("arrays_hashing");
  const [difficulty, setDifficulty] = useState<InterviewDifficulty>("medium");
  const [style, setStyle] = useState<InterviewStyle>("general");
  const [language, setLanguage] = useState<"python" | "java" | "cpp">("python");
  const [mode, setMode] = useState<InterviewMode>("standard");
  const [framing, setFraming] = useState<"standard" | "business">("standard");

  // Source-specific inputs
  const [leetcodeId, setLeetcodeId] = useState("");
  const [leetcodeStatement, setLeetcodeStatement] = useState("");
  const [customStatement, setCustomStatement] = useState("");
  const [customUrl, setCustomUrl] = useState("");
  const [customConstraints, setCustomConstraints] = useState("");

  const [validationError, setValidationError] = useState<string | null>(null);

  const isMixedBlocked = MODE_META[mode].blocksMixed && category === "mixed";

  const handleModeChange = (newMode: InterviewMode) => {
    setMode(newMode);
    setValidationError(null);
    if (MODE_META[newMode].blocksMixed && category === "mixed") {
      setCategory("arrays_hashing");
    }
  };

  const handleSourceChange = (newSource: InterviewSource) => {
    setSource(newSource);
    setValidationError(null);
    if (newSource !== "random_dsa" && framing === "business") {
      setFraming("standard");
    }
    if (newSource === "adaptive") {
      setDifficulty("adaptive");
    } else if (difficulty === "adaptive") {
      setDifficulty("medium");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (isMixedBlocked) {
      setValidationError("Topic Mastery requires a specific category, not 'Mixed'.");
      return;
    }

    if (source === "leetcode" && (!leetcodeStatement || leetcodeStatement.trim().length < 30)) {
      setValidationError("Please paste the full LeetCode problem statement (statement, examples, and constraints).");
      return;
    }

    if (source === "custom" && (!customStatement || customStatement.trim().length < 20)) {
      setValidationError("Please provide a problem statement for your custom problem.");
      return;
    }

    try {
      await onStartSession({
        config: {
          source,
          mode,
          style,
          difficulty,
          category,
          language,
          framing: source === "ai_business" ? "business" : framing,
          duration: 1200,
        },
        leetcode_id: leetcodeId.trim() || undefined,
        leetcode_statement: leetcodeStatement.trim() || undefined,
        custom_statement: customStatement.trim() || undefined,
        custom_url: customUrl.trim() || undefined,
        custom_extra_constraints: customConstraints.trim() || undefined,
      });
    } catch (e: any) {
      const raw = e?.message ?? "";
      try {
        const parsed = JSON.parse(raw);
        setValidationError(parsed?.detail ?? raw);
      } catch {
        setValidationError(raw);
      }
    }
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 flex items-center justify-center p-6">
      <div className="max-w-2xl w-full space-y-6">
        {/* Header */}
        <div className="space-y-2 text-center relative">
          {onViewDashboard && (
            <div className="absolute right-0 top-0">
              <button
                type="button"
                onClick={onViewDashboard}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs text-zinc-300 hover:text-zinc-100 transition-colors"
              >
                <LayoutDashboard className="w-3.5 h-3.5 text-indigo-400" />
                <span>Dashboard</span>
              </button>
            </div>
          )}
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-xs font-mono text-zinc-400 mb-1">
            <Terminal className="w-3.5 h-3.5 text-indigo-400" />
            <span>Intervue AI Technical Simulator</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-50">
            Configure Interview Session
          </h1>
          <p className="text-xs text-zinc-400">
            Rigorous 20-minute simulated technical interview with sandbox code execution.
          </p>
        </div>

        {/* Validation Error Banner */}
        {validationError && (
          <div className="flex items-start space-x-3 px-4 py-3 rounded-lg bg-red-950/60 border border-red-800/70 text-red-300 text-xs leading-relaxed">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-400" />
            <span>{validationError}</span>
          </div>
        )}

        {/* Configuration Card */}
        <form
          onSubmit={handleSubmit}
          className="p-6 rounded-xl bg-[#121215] border border-[#27272a] space-y-5 shadow-xl"
        >
          {/* Question Source */}
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Question Source
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {(Object.keys(SOURCE_META) as InterviewSource[]).map((s) => {
                const meta = SOURCE_META[s];
                const isActive = source === s;
                return (
                  <button
                    key={s}
                    type="button"
                    onClick={() => handleSourceChange(s)}
                    className={`flex items-start space-x-2 p-2.5 rounded-md border text-left transition-colors ${
                      isActive
                        ? "bg-indigo-950/80 border-indigo-700 text-indigo-200"
                        : "bg-[#18181c] border-[#27272a] text-zinc-400 hover:border-zinc-700 hover:text-zinc-300"
                    }`}
                  >
                    <span className={`mt-0.5 shrink-0 ${isActive ? "text-indigo-400" : "text-zinc-500"}`}>
                      {meta.icon}
                    </span>
                    <div>
                      <div className="text-xs font-medium">{meta.label}</div>
                      <div className="text-[10px] text-zinc-500 leading-tight mt-0.5">
                        {meta.description}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* LeetCode Paste Inputs */}
          {source === "leetcode" && (
            <div className="p-3.5 rounded-lg bg-[#18181c] border border-zinc-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-zinc-200 flex items-center space-x-1.5">
                  <Code2 className="w-3.5 h-3.5 text-amber-400" />
                  <span>LeetCode Problem Details</span>
                </span>
                <span className="text-[10px] text-zinc-500">No public API; paste verbatim</span>
              </div>
              <div>
                <label className="text-[11px] text-zinc-400 mb-1 block">Problem # / ID (optional)</label>
                <input
                  type="text"
                  value={leetcodeId}
                  onChange={(e) => setLeetcodeId(e.target.value)}
                  placeholder="e.g. 42 or trapping-rain-water"
                  className="w-full bg-[#121215] border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-200 outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="text-[11px] text-zinc-400 mb-1 block">
                  Pasted Statement, Examples &amp; Constraints <span className="text-red-400">*</span>
                </label>
                <textarea
                  rows={4}
                  value={leetcodeStatement}
                  onChange={(e) => setLeetcodeStatement(e.target.value)}
                  placeholder="Paste the problem description, example inputs/outputs, and constraints from LeetCode..."
                  className="w-full bg-[#121215] border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-200 outline-none focus:border-indigo-500 font-mono resize-y"
                />
              </div>
            </div>
          )}

          {/* Custom Problem Inputs */}
          {source === "custom" && (
            <div className="p-3.5 rounded-lg bg-[#18181c] border border-zinc-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-zinc-200 flex items-center space-x-1.5">
                  <FileCode className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Custom Problem Specification</span>
                </span>
                <span className="text-[10px] text-zinc-500">Verified in sandbox</span>
              </div>
              <div>
                <label className="text-[11px] text-zinc-400 mb-1 block">
                  Problem Statement &amp; Examples <span className="text-red-400">*</span>
                </label>
                <textarea
                  rows={4}
                  value={customStatement}
                  onChange={(e) => setCustomStatement(e.target.value)}
                  placeholder="Describe the function requirements, expected inputs, outputs, and edge cases..."
                  className="w-full bg-[#121215] border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-200 outline-none focus:border-indigo-500 font-mono resize-y"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] text-zinc-400 mb-1 block">Source URL (optional)</label>
                  <input
                    type="text"
                    value={customUrl}
                    onChange={(e) => setCustomUrl(e.target.value)}
                    placeholder="https://..."
                    className="w-full bg-[#121215] border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-200 outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-zinc-400 mb-1 block">Extra Constraints (optional)</label>
                  <input
                    type="text"
                    value={customConstraints}
                    onChange={(e) => setCustomConstraints(e.target.value)}
                    placeholder="e.g. N <= 10^5, O(N) time"
                    className="w-full bg-[#121215] border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-200 outline-none focus:border-indigo-500"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Adaptive Notice */}
          {source === "adaptive" && (
            <div className="p-3 rounded-lg bg-indigo-950/30 border border-indigo-800/50 text-xs text-indigo-300/90 space-y-1">
              <div className="font-semibold flex items-center space-x-1.5">
                <Target className="w-3.5 h-3.5 text-indigo-400" />
                <span>Deterministic History Analysis</span>
              </div>
              <p className="text-[11px] text-indigo-200/70 leading-relaxed">
                Intervue analyzes your stored evaluation scores to identify your weakest categories and dimension gaps. Category and difficulty are chosen automatically. Requires at least 5 completed interview attempts.
              </p>
            </div>
          )}

          {/* AI Business Notice */}
          {source === "ai_business" && (
            <div className="p-3 rounded-lg bg-emerald-950/30 border border-emerald-800/50 text-xs text-emerald-300/90 space-y-1">
              <div className="font-semibold flex items-center space-x-1.5">
                <Briefcase className="w-3.5 h-3.5 text-emerald-400" />
                <span>Business Context Concealment</span>
              </div>
              <p className="text-[11px] text-emerald-200/70 leading-relaxed">
                The problem is disguised inside a realistic domain (e-commerce, fintech, logistics, cloud infra). Algorithm and data structure names are strictly concealed from the statement.
              </p>
            </div>
          )}

          {/* Interview Mode */}
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Interview Mode
            </label>
            <div className="grid grid-cols-2 gap-2">
              {(Object.keys(MODE_META) as InterviewMode[]).map((m) => {
                const meta = MODE_META[m];
                const isActive = mode === m;
                return (
                  <button
                    key={m}
                    type="button"
                    onClick={() => handleModeChange(m)}
                    className={`flex items-start space-x-2.5 px-3 py-2.5 rounded-md border text-left transition-colors ${
                      isActive
                        ? "bg-indigo-950/80 border-indigo-700 text-indigo-200"
                        : "bg-[#18181c] border-[#27272a] text-zinc-400 hover:border-zinc-600 hover:text-zinc-300"
                    }`}
                  >
                    <span className={`mt-0.5 shrink-0 ${isActive ? "text-indigo-400" : "text-zinc-500"}`}>
                      {meta.icon}
                    </span>
                    <div>
                      <div className="text-xs font-semibold">{meta.label}</div>
                      <div className="text-[10px] leading-snug mt-0.5 text-zinc-500">
                        {meta.description}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Category (Hidden/auto when adaptive) */}
          {source !== "adaptive" && (
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Problem Category
              </label>
              <select
                value={category}
                onChange={(e) => {
                  setCategory(e.target.value as InterviewCategory);
                  setValidationError(null);
                }}
                className="w-full bg-[#18181c] border border-[#27272a] rounded-md px-3 py-2 text-xs text-zinc-200 outline-none focus:border-indigo-500 transition-colors"
              >
                <option value="arrays_hashing">Arrays &amp; Hashing</option>
                <option value="two_pointers">Two Pointers</option>
                <option value="sliding_window">Sliding Window</option>
                <option value="binary_search">Binary Search</option>
                <option value="stack_queue">Stack &amp; Queue</option>
                <option value="linked_lists">Linked Lists</option>
                <option value="trees">Trees</option>
                <option value="graphs">Graphs</option>
                <option value="dynamic_programming">Dynamic Programming</option>
                <option value="greedy">Greedy</option>
                <option value="backtracking">Backtracking</option>
                <option value="heaps">Heaps</option>
                <option value="intervals">Intervals</option>
                {!MODE_META[mode].blocksMixed && (
                  <option value="mixed">Mixed (Surprise me)</option>
                )}
              </select>
              {MODE_META[mode].blocksMixed && (
                <p className="text-[11px] text-amber-400/80 flex items-center space-x-1">
                  <AlertCircle className="w-3 h-3" />
                  <span>Topic Mastery requires a specific category — Mixed is unavailable.</span>
                </p>
              )}
            </div>
          )}

          {/* Difficulty & Style Grid */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Difficulty
              </label>
              <select
                value={difficulty}
                disabled={source === "adaptive"}
                onChange={(e) => setDifficulty(e.target.value as InterviewDifficulty)}
                className="w-full bg-[#18181c] border border-[#27272a] rounded-md px-3 py-2 text-xs text-zinc-200 outline-none focus:border-indigo-500 transition-colors disabled:opacity-50"
              >
                {source === "adaptive" ? (
                  <option value="adaptive">Adaptive (Calculated from Weaknesses)</option>
                ) : (
                  <>
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </>
                )}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Interview Style
              </label>
              <select
                value={style}
                onChange={(e) => setStyle(e.target.value as InterviewStyle)}
                className="w-full bg-[#18181c] border border-[#27272a] rounded-md px-3 py-2 text-xs text-zinc-200 outline-none focus:border-indigo-500 transition-colors"
              >
                <option value="general">General (Balanced)</option>
                <option value="google">Google (Probing, terse)</option>
                <option value="amazon">Amazon (Ownership, edge cases)</option>
                <option value="meta">Meta (Speed &amp; correctness)</option>
              </select>
            </div>

            {/* Language */}
            <div className="space-y-2 col-span-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Target Language
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value as "python" | "java" | "cpp")}
                className="w-full bg-[#18181c] border border-[#27272a] rounded-md px-3 py-2 text-xs text-zinc-200 outline-none focus:border-indigo-500 transition-colors"
              >
                <option value="python">Python 3.12 (Isolated Sandbox)</option>
                <option value="java">Java 21 Temurin (Isolated Sandbox)</option>
                <option value="cpp">C++ 20 (g++ -O2 Isolated Sandbox)</option>
              </select>
            </div>
          </div>

          {/* Blind mode notice */}
          {mode === "blind_mock" && (
            <div className="flex items-start space-x-2.5 px-3 py-2.5 rounded-md bg-amber-950/30 border border-amber-800/50 text-xs text-amber-300/80">
              <Eye className="w-3.5 h-3.5 shrink-0 mt-0.5 text-amber-400" />
              <span>
                <strong>Blind Mode active.</strong> Title, category, difficulty and complexity
                expectations will be stripped from all API responses server-side.
              </span>
            </div>
          )}

          {/* Execution Environment Info */}
          <div className="p-3 rounded-md bg-[#0e0e11] border border-[#27272a] flex items-center justify-between text-xs font-mono text-zinc-400">
            <div className="flex items-center space-x-2">
              <Shield className="w-3.5 h-3.5 text-emerald-400" />
              <span>
                {language === "python" && "Python 3.12 (CPython Ephemeral Runner)"}
                {language === "java" && "Java 21 (Temurin Alpine Runner)"}
                {language === "cpp" && "C++ 20 (Alpine g++ Runner)"}
              </span>
            </div>
            <div className="flex items-center space-x-1.5 text-zinc-400">
              <Clock className="w-3.5 h-3.5" />
              <span>20:00 Fixed</span>
            </div>
          </div>

          {/* Start Button */}
          <button
            type="submit"
            disabled={isGenerating}
            className="w-full flex items-center justify-center space-x-2 py-2.5 rounded-md bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-xs transition-colors shadow-lg shadow-indigo-600/20"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>{statusMessage || "Validating problem in sandbox..."}</span>
              </>
            ) : (
              <>
                <span>Launch Interview Session</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
