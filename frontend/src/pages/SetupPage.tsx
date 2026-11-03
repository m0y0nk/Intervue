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
} from "lucide-react";
import {
  InterviewCategory,
  InterviewConfig,
  InterviewDifficulty,
  InterviewMode,
  InterviewStyle,
} from "../types";

interface SetupPageProps {
  onStartSession: (config: Partial<InterviewConfig>) => Promise<void>;
  isGenerating: boolean;
  statusMessage?: string;
}

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
}) => {
  const [category, setCategory] = useState<InterviewCategory>("arrays_hashing");
  const [difficulty, setDifficulty] = useState<InterviewDifficulty>("medium");
  const [style, setStyle] = useState<InterviewStyle>("general");
  const [language, setLanguage] = useState<"python" | "java" | "cpp">("python");
  const [mode, setMode] = useState<InterviewMode>("standard");
  const [validationError, setValidationError] = useState<string | null>(null);

  const isMixedBlocked = MODE_META[mode].blocksMixed && category === "mixed";

  const handleModeChange = (newMode: InterviewMode) => {
    setMode(newMode);
    setValidationError(null);
    // Auto-fix mixed category if topic_mastery selected
    if (MODE_META[newMode].blocksMixed && category === "mixed") {
      setCategory("arrays_hashing");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (isMixedBlocked) {
      setValidationError("Topic Mastery requires a specific category, not 'Mixed'.");
      return;
    }

    try {
      await onStartSession({
        source: "random_dsa",
        mode,
        style,
        difficulty,
        category,
        language,
        framing: "standard",
        duration: 1200,
      });
    } catch (e: any) {
      // Extract 422 validation message from backend
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
      <div className="max-w-xl w-full space-y-8">
        {/* Header */}
        <div className="space-y-2 text-center">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-xs font-mono text-zinc-400 mb-2">
            <Terminal className="w-3.5 h-3.5 text-indigo-400" />
            <span>Intervue AI Technical Simulator</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-50">
            Configure Interview Session
          </h1>
          <p className="text-sm text-zinc-400">
            Rigorous 20-minute simulated coding interview. The AI acts as an evaluator, never a tutor.
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
          className="p-6 rounded-xl bg-[#121215] border border-[#27272a] space-y-6 shadow-xl"
        >
          {/* Question Source */}
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Question Source
            </label>
            <div className="p-3 rounded-md bg-[#18181c] border border-indigo-900/60 flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                <div>
                  <div className="text-xs font-medium text-zinc-100">Random DSA Problem</div>
                  <div className="text-[11px] text-zinc-400">
                    Validated algorithmic problem with differential testing
                  </div>
                </div>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950/80 border border-indigo-800 text-indigo-300">
                ACTIVE
              </span>
            </div>
          </div>

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

          {/* Category */}
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
              {/* Mixed only available when mode allows it */}
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

          {/* Difficulty & Style Grid */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Difficulty
              </label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value as InterviewDifficulty)}
                className="w-full bg-[#18181c] border border-[#27272a] rounded-md px-3 py-2 text-xs text-zinc-200 outline-none focus:border-indigo-500 transition-colors"
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
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
                expectations will be stripped from all API responses server-side. Dev tools
                inspection yields no hints.
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
