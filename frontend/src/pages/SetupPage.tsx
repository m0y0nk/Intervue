import React, { useState } from "react";
import {
  InterviewCategory,
  InterviewDifficulty,
  InterviewMode,
  InterviewSource,
  InterviewStyle,
  SessionCreatePayload,
} from "../types";
import { StageRail } from "../components/StageRail";

interface SetupPageProps {
  onStartSession: (payload: SessionCreatePayload) => Promise<void>;
  isGenerating: boolean;
  statusMessage?: string;
  onViewDashboard?: () => void;
}

const SOURCES: { id: InterviewSource; label: string; desc: string }[] = [
  { id: "random_dsa", label: "Random DSA", desc: "Algorithmic problem from repository" },
  { id: "leetcode", label: "LeetCode", desc: "Lookup by number or paste problem text" },
  { id: "adaptive", label: "Adaptive", desc: "Weakness targeting from your history" },
  { id: "custom", label: "Custom", desc: "User-defined statement and constraints" },
];

const MODES: { id: InterviewMode; label: string; desc: string }[] = [
  { id: "standard", label: "Standard", desc: "Full problem metadata visible" },
  { id: "blind_mock", label: "Blind mock", desc: "Title, topic, and difficulty concealed" },
  { id: "topic_mastery", label: "Topic mastery", desc: "Focused single-category drill" },
  { id: "revision", label: "Revision", desc: "Re-attempt a prior completed problem" },
];

const FRAMINGS: { id: "standard" | "business"; label: string; desc: string }[] = [
  { id: "standard", label: "Standard", desc: "Classic algorithmic formulation" },
  { id: "business", label: "Business scenario", desc: "Real-world context concealing algorithm names" },
];

export const SetupPage: React.FC<SetupPageProps> = ({
  onStartSession,
  isGenerating,
  statusMessage,
  onViewDashboard,
}) => {
  const [source, setSource] = useState<InterviewSource>("random_dsa");
  const [framing, setFraming] = useState<"standard" | "business">("standard");
  const [mode, setMode] = useState<InterviewMode>("standard");

  const [category, setCategory] = useState<InterviewCategory>("arrays_hashing");
  const [difficulty, setDifficulty] = useState<InterviewDifficulty>("medium");
  const [style, setStyle] = useState<InterviewStyle>("general");
  const [language, setLanguage] = useState<"python" | "java" | "cpp">("python");

  // Source-specific inputs
  const [leetcodeId, setLeetcodeId] = useState("");
  const [leetcodeStatement, setLeetcodeStatement] = useState("");
  const [isFetchingLeetcode, setIsFetchingLeetcode] = useState(false);
  const [leetcodeFetchError, setLeetcodeFetchError] = useState<string | null>(null);
  const [fetchedMeta, setFetchedMeta] = useState<{
    id: string;
    title: string;
    difficulty: string;
    tags: string[];
  } | null>(null);

  const [customStatement, setCustomStatement] = useState("");
  const [customUrl, setCustomUrl] = useState("");
  const [customConstraints, setCustomConstraints] = useState("");

  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSourceChange = (newSource: InterviewSource) => {
    setSource(newSource);
    setValidationError(null);
    setLeetcodeFetchError(null);
    if (newSource !== "random_dsa" && newSource !== "leetcode" && framing === "business") {
      setFraming("standard");
    }
    if (newSource === "adaptive") {
      setDifficulty("adaptive");
    } else if (difficulty === "adaptive") {
      setDifficulty("medium");
    }
  };

  const handleModeChange = (newMode: InterviewMode) => {
    setMode(newMode);
    setValidationError(null);
    if (newMode === "topic_mastery" && category === "mixed") {
      setCategory("arrays_hashing");
    }
  };

  const handleFetchLeetcode = async () => {
    const query = leetcodeId.trim();
    if (!query) {
      setLeetcodeFetchError("Enter a problem number (e.g. 42) or title slug (e.g. trapping-rain-water).");
      return;
    }
    setIsFetchingLeetcode(true);
    setLeetcodeFetchError(null);
    try {
      const res = await fetch(`/api/leetcode/problem/${encodeURIComponent(query)}`);
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `LeetCode problem '${query}' not found.`);
      }
      const data = await res.json();
      setLeetcodeStatement(data.content);
      setFetchedMeta({
        id: data.id,
        title: data.title,
        difficulty: data.difficulty,
        tags: data.topic_tags || [],
      });
    } catch (err: any) {
      setLeetcodeFetchError(err.message || "Failed to fetch problem from LeetCode.");
      setFetchedMeta(null);
    } finally {
      setIsFetchingLeetcode(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (mode === "topic_mastery" && category === "mixed") {
      setValidationError("Topic mastery requires a specific category rather than Mixed.");
      return;
    }

    if (source === "leetcode" && !leetcodeStatement && !leetcodeId.trim()) {
      setValidationError("Provide a LeetCode problem number or paste the problem statement.");
      return;
    }

    if (source === "custom" && (!customStatement || customStatement.trim().length < 20)) {
      setValidationError("Provide a problem statement for your custom problem (at least 20 characters).");
      return;
    }

    try {
      await onStartSession({
        config: {
          source,
          mode,
          style,
          difficulty: source === "leetcode" ? undefined : difficulty,
          category: mode === "topic_mastery" ? category : undefined,
          language,
          framing: (source === "random_dsa" || source === "leetcode") ? framing : "standard",
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

  // Helper label for Ticket summary
  const selectedSourceLabel = SOURCES.find((s) => s.id === source)?.label ?? source;
  const selectedModeLabel = MODES.find((m) => m.id === mode)?.label ?? mode;
  const selectedFramingLabel = framing === "business" ? "Business scenario" : "Standard";

  return (
    <div className="min-h-screen bg-[#12110F] text-[#ECE6DA] flex items-center justify-center p-4 sm:p-8 selection:bg-[#F5B83D] selection:text-[#12110F]">
      <div className="max-w-4xl w-full">
        {/* Top Header */}
        <div className="flex items-baseline justify-between mb-8 pb-4 border-b border-[#332E28]">
          <div>
            <h1 className="font-display text-28 sm:text-[32px] text-[#ECE6DA] tracking-tight leading-snug">
              Interview session briefing
            </h1>
            <p className="text-13 text-[#A59E91] mt-1">
              Rigorous 20-minute timed simulation across 6 progressive interview stages.
            </p>
          </div>
          {onViewDashboard && (
            <button
              type="button"
              onClick={onViewDashboard}
              className="text-13 text-[#A59E91] hover:text-[#ECE6DA] transition-colors border-b border-[#332E28] hover:border-[#ECE6DA] pb-0.5"
            >
              Past sessions
            </button>
          )}
        </div>

        {/* Validation Error Banner */}
        {validationError && (
          <div className="mb-6 p-3 rounded-[4px] bg-[#1A1815] border border-[#FF7A6E] text-[#FF7A6E] text-13 flex items-start space-x-2">
            <span className="font-semibold shrink-0">Notice:</span>
            <span>{validationError}</span>
          </div>
        )}

        {/* Two-Column Briefing Form */}
        <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
          {/* Left Column: Form Controls (7 cols) */}
          <div className="md:col-span-7 space-y-6">
            {/* 1. Question Source Segmented Control */}
            <div className="space-y-2">
              <label className="text-13 text-[#A59E91] block">Question source</label>
              <div className="grid grid-cols-2 gap-1.5 p-1 rounded-[4px] bg-[#1A1815] border border-[#332E28]">
                {SOURCES.map((s) => {
                  const isActive = source === s.id;
                  return (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => handleSourceChange(s.id)}
                      className={`px-3 py-2 text-left rounded-[3px] text-13 transition-all ${
                        isActive
                          ? "bg-[#221F1B] text-[#ECE6DA] border border-[#6B645A] font-medium"
                          : "text-[#A59E91] hover:text-[#ECE6DA] hover:bg-[#221F1B]/40"
                      }`}
                    >
                      <div className="font-medium">{s.label}</div>
                      <div className="text-[11px] text-[#A59E91] truncate mt-0.5">{s.desc}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Source Specific Inputs: LeetCode */}
            {source === "leetcode" && (
              <div className="p-4 rounded-[4px] bg-[#1A1815] border border-[#332E28] space-y-3.5">
                <div className="text-13 font-medium text-[#ECE6DA]">LeetCode problem lookup</div>
                <div>
                  <label className="text-[12px] text-[#A59E91] block mb-1">
                    Problem number or title slug
                  </label>
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      value={leetcodeId}
                      onChange={(e) => {
                        setLeetcodeId(e.target.value);
                        if (leetcodeFetchError) setLeetcodeFetchError(null);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          handleFetchLeetcode();
                        }
                      }}
                      placeholder="e.g. 42 or trapping-rain-water"
                      className="flex-1 bg-[#12110F] border border-[#6B645A] rounded-[4px] px-3 py-1.5 text-13 text-[#ECE6DA] placeholder-[#6B645A] outline-none"
                    />
                    <button
                      type="button"
                      onClick={handleFetchLeetcode}
                      disabled={isFetchingLeetcode || !leetcodeId.trim()}
                      className="px-3.5 py-1.5 rounded-[4px] bg-[#221F1B] hover:bg-[#332E28] border border-[#6B645A] text-[#ECE6DA] text-13 disabled:opacity-40 transition-colors shrink-0"
                    >
                      {isFetchingLeetcode ? "Fetching..." : "Fetch"}
                    </button>
                  </div>
                  {leetcodeFetchError && (
                    <div className="text-[12px] text-[#FF7A6E] mt-1.5">{leetcodeFetchError}</div>
                  )}
                </div>

                {fetchedMeta && (
                  <div className="p-2.5 rounded-[4px] bg-[#221F1B] border border-[#332E28] text-13">
                    <div className="flex items-baseline space-x-2">
                      <span className="font-medium text-[#7BD88F]">#{fetchedMeta.id} {fetchedMeta.title}</span>
                      <span className="text-[11px] text-[#A59E91] capitalize">({fetchedMeta.difficulty})</span>
                    </div>
                  </div>
                )}

                <div>
                  <label className="text-[12px] text-[#A59E91] block mb-1">
                    Problem statement (populated or paste manually)
                  </label>
                  <textarea
                    rows={4}
                    value={leetcodeStatement}
                    onChange={(e) => setLeetcodeStatement(e.target.value)}
                    placeholder="Problem description, examples, and constraints..."
                    className="w-full bg-[#12110F] border border-[#6B645A] rounded-[4px] p-2.5 text-13 text-[#ECE6DA] font-mono placeholder-[#6B645A] outline-none resize-y"
                  />
                </div>
              </div>
            )}

            {/* Source Specific Inputs: Custom */}
            {source === "custom" && (
              <div className="p-4 rounded-[4px] bg-[#1A1815] border border-[#332E28] space-y-3">
                <div className="text-13 font-medium text-[#ECE6DA]">Custom problem specification</div>
                <div>
                  <label className="text-[12px] text-[#A59E91] block mb-1">Problem statement and examples</label>
                  <textarea
                    rows={4}
                    value={customStatement}
                    onChange={(e) => setCustomStatement(e.target.value)}
                    placeholder="Describe inputs, outputs, expectations, and examples..."
                    className="w-full bg-[#12110F] border border-[#6B645A] rounded-[4px] p-2.5 text-13 text-[#ECE6DA] font-mono placeholder-[#6B645A] outline-none resize-y"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[12px] text-[#A59E91] block mb-1">Source URL (optional)</label>
                    <input
                      type="text"
                      value={customUrl}
                      onChange={(e) => setCustomUrl(e.target.value)}
                      placeholder="https://..."
                      className="w-full bg-[#12110F] border border-[#6B645A] rounded-[4px] px-2.5 py-1.5 text-13 text-[#ECE6DA] outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-[12px] text-[#A59E91] block mb-1">Extra constraints (optional)</label>
                    <input
                      type="text"
                      value={customConstraints}
                      onChange={(e) => setCustomConstraints(e.target.value)}
                      placeholder="e.g. N <= 10^5, O(N)"
                      className="w-full bg-[#12110F] border border-[#6B645A] rounded-[4px] px-2.5 py-1.5 text-13 text-[#ECE6DA] outline-none"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Source Notice: Adaptive */}
            {source === "adaptive" && (
              <div className="p-3.5 rounded-[4px] bg-[#1A1815] border border-[#332E28] text-13 text-[#A59E91]">
                Target category and difficulty are determined mathematically from stored evaluation score gaps across completed interviews.
              </div>
            )}

            {/* 2. Problem Framing Segmented Control (Random DSA & LeetCode) */}
            {(source === "random_dsa" || source === "leetcode") && (
              <div className="space-y-2">
                <label className="text-13 text-[#A59E91] block">Problem framing</label>
                <div className="grid grid-cols-2 gap-1.5 p-1 rounded-[4px] bg-[#1A1815] border border-[#332E28]">
                  {FRAMINGS.map((f) => {
                    const isActive = framing === f.id;
                    return (
                      <button
                        key={f.id}
                        type="button"
                        onClick={() => setFraming(f.id)}
                        className={`px-3 py-2 text-left rounded-[3px] text-13 transition-all ${
                          isActive
                            ? "bg-[#221F1B] text-[#ECE6DA] border border-[#6B645A] font-medium"
                            : "text-[#A59E91] hover:text-[#ECE6DA] hover:bg-[#221F1B]/40"
                        }`}
                      >
                        <div className="font-medium">{f.label}</div>
                        <div className="text-[11px] text-[#A59E91] truncate mt-0.5">{f.desc}</div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 3. Interview Mode Segmented Control */}
            <div className="space-y-2">
              <label className="text-13 text-[#A59E91] block">Interview mode</label>
              <div className="grid grid-cols-2 gap-1.5 p-1 rounded-[4px] bg-[#1A1815] border border-[#332E28]">
                {MODES.map((m) => {
                  const isActive = mode === m.id;
                  return (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => handleModeChange(m.id)}
                      className={`px-3 py-2 text-left rounded-[3px] text-13 transition-all ${
                        isActive
                          ? "bg-[#221F1B] text-[#ECE6DA] border border-[#6B645A] font-medium"
                          : "text-[#A59E91] hover:text-[#ECE6DA] hover:bg-[#221F1B]/40"
                      }`}
                    >
                      <div className="font-medium">{m.label}</div>
                      <div className="text-[11px] text-[#A59E91] truncate mt-0.5">{m.desc}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 4. Plain Selects Below */}
            <div className="pt-2 border-t border-[#332E28] space-y-4">
              {/* Show Category ONLY when Topic Mastery needs it */}
              {mode === "topic_mastery" && (
                <div className="space-y-1.5">
                  <label className="text-13 text-[#A59E91] block">Topic category</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value as InterviewCategory)}
                    className="w-full bg-[#1A1815] border border-[#6B645A] rounded-[4px] px-3 py-2 text-13 text-[#ECE6DA] outline-none"
                  >
                    <option value="arrays_hashing">Arrays & Hashing</option>
                    <option value="two_pointers">Two Pointers</option>
                    <option value="sliding_window">Sliding Window</option>
                    <option value="binary_search">Binary Search</option>
                    <option value="stack_queue">Stack & Queue</option>
                    <option value="linked_lists">Linked Lists</option>
                    <option value="trees">Trees</option>
                    <option value="graphs">Graphs</option>
                    <option value="dynamic_programming">Dynamic Programming</option>
                    <option value="greedy">Greedy</option>
                    <option value="backtracking">Backtracking</option>
                    <option value="heaps">Heaps</option>
                    <option value="intervals">Intervals</option>
                  </select>
                </div>
              )}

              {/* Difficulty (only if not LeetCode or Adaptive) */}
              {source !== "leetcode" && source !== "adaptive" && (
                <div className="space-y-1.5">
                  <label className="text-13 text-[#A59E91] block">Difficulty</label>
                  <select
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value as InterviewDifficulty)}
                    className="w-full bg-[#1A1815] border border-[#6B645A] rounded-[4px] px-3 py-2 text-13 text-[#ECE6DA] outline-none"
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>
              )}

              {/* Style & Language */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-13 text-[#A59E91] block">Interviewer style</label>
                  <select
                    value={style}
                    onChange={(e) => setStyle(e.target.value as InterviewStyle)}
                    className="w-full bg-[#1A1815] border border-[#6B645A] rounded-[4px] px-3 py-2 text-13 text-[#ECE6DA] outline-none"
                  >
                    <option value="general">General (balanced)</option>
                    <option value="google">Google (probing, terse)</option>
                    <option value="amazon">Amazon (ownership, edge cases)</option>
                    <option value="meta">Meta (speed & correctness)</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-13 text-[#A59E91] block">Programming language</label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value as "python" | "java" | "cpp")}
                    className="w-full bg-[#1A1815] border border-[#6B645A] rounded-[4px] px-3 py-2 text-13 text-[#ECE6DA] outline-none font-mono"
                  >
                    <option value="python">Python 3.12</option>
                    <option value="java">Java 21</option>
                    <option value="cpp">C++ 20</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Sticky Session Ticket (5 cols) */}
          <div className="md:col-span-5 md:sticky md:top-8">
            <div className="p-5 rounded-[10px] bg-[#1A1815] border border-[#332E28] space-y-6">
              <div>
                <div className="text-[11px] font-mono uppercase tracking-wider text-[#A59E91]">
                  Session Ticket
                </div>
                <div className="font-display text-28 text-[#ECE6DA] mt-0.5">
                  20:00 Authoritative
                </div>
              </div>

              {/* Identity Motif: Preview of Stage Rail with 20:00 on it */}
              <div className="pt-2 pb-2">
                <StageRail
                  currentStage={1}
                  formattedTime="20:00"
                  progressRatio={0}
                  mode="preview"
                />
              </div>

              {/* Ticket Specification Summary */}
              <div className="space-y-2 pt-3 border-t border-[#332E28] text-13 font-mono">
                <div className="flex justify-between py-0.5">
                  <span className="text-[#A59E91]">Source</span>
                  <span className="text-[#ECE6DA]">{selectedSourceLabel}</span>
                </div>
                <div className="flex justify-between py-0.5">
                  <span className="text-[#A59E91]">Framing</span>
                  <span className="text-[#ECE6DA]">{selectedFramingLabel}</span>
                </div>
                <div className="flex justify-between py-0.5">
                  <span className="text-[#A59E91]">Mode</span>
                  <span className="text-[#ECE6DA]">{selectedModeLabel}</span>
                </div>
                {mode === "topic_mastery" && (
                  <div className="flex justify-between py-0.5">
                    <span className="text-[#A59E91]">Category</span>
                    <span className="text-[#ECE6DA] capitalize">{category.replace("_", " ")}</span>
                  </div>
                )}
                <div className="flex justify-between py-0.5">
                  <span className="text-[#A59E91]">Language</span>
                  <span className="text-[#ECE6DA] uppercase">{language}</span>
                </div>
                <div className="flex justify-between py-0.5">
                  <span className="text-[#A59E91]">Sandbox</span>
                  <span className="text-[#ECE6DA]">Isolated ephemeral</span>
                </div>
              </div>

              {/* Single Amber Action: Start button */}
              <div className="pt-3">
                <button
                  type="submit"
                  disabled={isGenerating}
                  className="w-full py-3 px-4 rounded-[4px] bg-[#F5B83D] hover:bg-[#e5aa32] text-[#12110F] font-semibold text-15 tracking-tight transition-colors disabled:opacity-50"
                >
                  {isGenerating
                    ? statusMessage || "Preparing sandbox..."
                    : "Start 20-minute interview"}
                </button>
              </div>

              <div className="text-[12px] text-[#A59E91] text-center leading-relaxed">
                Stage progression is candidate-driven. Constraints unlock automatically at Stage 3.
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
