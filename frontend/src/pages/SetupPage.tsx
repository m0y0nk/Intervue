import React, { useState } from "react";
import { Terminal, Shield, Sparkles, Clock, ArrowRight, Loader2 } from "lucide-react";
import { InterviewCategory, InterviewConfig, InterviewDifficulty, InterviewStyle } from "../types";

interface SetupPageProps {
  onStartSession: (config: Partial<InterviewConfig>) => Promise<void>;
  isGenerating: boolean;
  statusMessage?: string;
}

export const SetupPage: React.FC<SetupPageProps> = ({
  onStartSession,
  isGenerating,
  statusMessage,
}) => {
  const [category, setCategory] = useState<InterviewCategory>("arrays_hashing");
  const [difficulty, setDifficulty] = useState<InterviewDifficulty>("medium");
  const [style, setStyle] = useState<InterviewStyle>("general");
  const [language, setLanguage] = useState<"python" | "java" | "cpp">("python");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onStartSession({
      source: "random_dsa",
      mode: "standard",
      style: style,
      difficulty: difficulty,
      category: category,
      language: language,
      framing: "standard",
      duration: 1200,
    });
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

        {/* Configuration Card */}
        <form
          onSubmit={handleSubmit}
          className="p-6 rounded-xl bg-[#121215] border border-[#27272a] space-y-6 shadow-xl"
        >
          {/* Question Source (Random DSA for Phase 1) */}
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

          {/* Category */}
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Problem Category
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as InterviewCategory)}
              className="w-full bg-[#18181c] border border-[#27272a] rounded-md px-3 py-2 text-xs text-zinc-200 outline-none focus:border-indigo-500 transition-colors"
            >
              <option value="arrays_hashing">Arrays & Hashing</option>
              <option value="two_pointers">Two Pointers</option>
              <option value="sliding_window">Sliding Window</option>
              <option value="binary_search">Binary Search</option>
              <option value="stack_queue">Stack & Queue</option>
              <option value="linked_lists">Linked Lists</option>
              <option value="trees">Trees</option>
              <option value="dynamic_programming">Dynamic Programming</option>
            </select>
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
                <option value="meta">Meta (Speed & correctness)</option>
              </select>
            </div>

            {/* Language */}
            <div className="space-y-2">
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
