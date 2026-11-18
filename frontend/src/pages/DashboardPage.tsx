import React, { useCallback, useEffect, useState } from "react";
import { api } from "../services/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DimensionStat {
  name: string;
  avg_score: number;
}

interface DashboardData {
  total_interviews: number;
  average_score: number;
  coding_accuracy: number;
  average_algorithmic_score: number;
  average_implementation_score: number;
  average_time_mgmt_score: number;
  category_performance: Record<string, number>;
  strongest_dimensions: DimensionStat[];
  weakest_dimensions: DimensionStat[];
  verdict_distribution: Record<string, number>;
  idea_to_code_trend: Array<{
    session_id: string;
    date: string | null;
    algorithmic_score: number | null;
    implementation_score: number | null;
    gap: number | null;
  }>;
  recent_sessions: RecentSession[];
}

interface RecentSession {
  session_id: string;
  problem_title: string;
  category: string | null;
  difficulty: string | null;
  style: string | null;
  mode: string | null;
  language: string | null;
  score: number;
  verdict: string;
  verdict_color: string;
  created_at: string | null;
}

export interface RevisionCandidate {
  session_id: string;
  problem_id: string;
  problem_title: string;
  category: string | null;
  difficulty: string | null;
  source: string | null;
  score: number | null;
  verdict: string | null;
  created_at: string | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const VERDICT_STYLES: Record<string, string> = {
  strong_hire: "text-[#7BD88F] border-[#7BD88F]/40 bg-[#1A1815]",
  hire: "text-[#7BD88F] border-[#7BD88F]/40 bg-[#1A1815]",
  borderline: "text-[#F5B83D] border-[#F5B83D]/40 bg-[#1A1815]",
  no_hire: "text-[#FF7A6E] border-[#FF7A6E]/40 bg-[#1A1815]",
};

const VERDICT_LABELS: Record<string, string> = {
  strong_hire: "Strong hire",
  hire: "Hire",
  borderline: "Borderline",
  no_hire: "No hire",
};

function ScoreBar({ score, max = 10 }: { score: number; max?: number }) {
  const pct = Math.min(100, (score / max) * 100);
  const color =
    pct >= 70 ? "bg-[#7BD88F]" : pct >= 50 ? "bg-[#F5B83D]" : "bg-[#FF7A6E]";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-[#12110F] border border-[#332E28] rounded-[2px] overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[11px] font-mono text-[#A59E91] w-6 text-right">
        {score.toFixed(1)}
      </span>
    </div>
  );
}

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <div className="bg-[#1A1815] border border-[#332E28] rounded-[10px] p-4">
      <p className="text-[13px] text-[#A59E91] mb-1">{label}</p>
      <p className="font-serif text-[28px] text-[#ECE6DA] leading-tight">{value}</p>
      {sub && <p className="text-[11px] text-[#6B645A] mt-1">{sub}</p>}
    </div>
  );
}

function formatDate(iso: string | null): string {
  if (!iso) return "-";
  try {
    return new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function formatCategory(cat: string | null): string {
  if (!cat) return "-";
  return cat.replace(/_/g, " ");
}

// ---------------------------------------------------------------------------
// DashboardPage
// ---------------------------------------------------------------------------

interface DashboardPageProps {
  onStartRevision?: (candidate: RevisionCandidate) => void;
  onNewInterview?: () => void;
}

export function DashboardPage({ onStartRevision, onNewInterview }: DashboardPageProps) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [candidates, setCandidates] = useState<RevisionCandidate[]>([]);
  const [recommendations, setRecommendations] = useState<string[]>([]);
  const [narrative, setNarrative] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [recsLoading, setRecsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "history" | "revision">("overview");
  const [historyData, setHistoryData] = useState<{ items: RecentSession[]; total: number; total_pages: number }>({
    items: [],
    total: 0,
    total_pages: 0,
  });
  const [historyPage, setHistoryPage] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dash, revCandidates] = await Promise.all([
        api.getDashboard(),
        api.getRevisionCandidates(),
      ]);
      setData(dash);
      setCandidates(revCandidates);
    } catch (e: any) {
      setError(e.message || "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadRecommendations = useCallback(async () => {
    setRecsLoading(true);
    try {
      const res = await api.getDashboardRecommendations();
      setRecommendations(res.recommendations || []);
      setNarrative(res.narrative || "");
    } catch {
      setRecommendations(["Recommendations unavailable at this time."]);
    } finally {
      setRecsLoading(false);
    }
  }, []);

  const loadHistory = useCallback(async (page: number) => {
    try {
      const res = await api.getHistory(page);
      setHistoryData(res);
      setHistoryPage(page);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    if (activeTab === "history") loadHistory(historyPage);
  }, [activeTab, historyPage, loadHistory]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#12110F] flex items-center justify-center">
        <div className="text-[#A59E91] text-[13px]">Loading analytics...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#12110F] flex items-center justify-center">
        <div className="text-[#FF7A6E] text-[13px]">{error}</div>
      </div>
    );
  }

  const d = data!;
  const hasData = d.total_interviews > 0;

  return (
    <div className="min-h-screen bg-[#12110F] text-[#ECE6DA] font-sans">
      {/* Header */}
      <header className="border-b border-[#332E28] bg-[#1A1815] px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="font-serif text-[28px] font-normal tracking-tight text-[#ECE6DA]">
            Intervue Dashboard
          </h1>
          <p className="text-[13px] text-[#A59E91] mt-0.5">
            Interview analytics and session history
          </p>
        </div>
        <button
          onClick={onNewInterview}
          className="text-[13px] font-medium bg-[#F5B83D] hover:bg-[#F5B83D]/90 text-[#12110F] px-3.5 py-1.5 rounded-[4px] transition-colors"
        >
          New interview
        </button>
      </header>

      {/* Tabs */}
      <nav className="border-b border-[#332E28] bg-[#1A1815] px-6 flex gap-6">
        {(["overview", "history", "revision"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`text-[13px] py-3 border-b-2 font-medium transition-colors ${
              activeTab === tab
                ? "border-[#F5B83D] text-[#ECE6DA]"
                : "border-transparent text-[#A59E91] hover:text-[#ECE6DA]"
            }`}
          >
            {tab === "revision" ? "Revision candidates" : tab === "overview" ? "Overview" : "History"}
            {tab === "revision" && candidates.length > 0 && (
              <span className="ml-1.5 text-[11px] font-mono bg-[#221F1B] border border-[#332E28] text-[#ECE6DA] px-1.5 py-0.5 rounded-[4px]">
                {candidates.length}
              </span>
            )}
          </button>
        ))}
      </nav>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* OVERVIEW TAB */}
        {activeTab === "overview" && (
          <div className="space-y-8">
            {!hasData ? (
              <div className="text-center py-24 space-y-3">
                <p className="text-[#ECE6DA] font-serif text-[18px]">No interviews completed yet.</p>
                <p className="text-[#A59E91] text-[13px]">
                  Complete your first timed session to see analytics and score breakdowns here.
                </p>
                <div className="pt-2">
                  <button
                    onClick={onNewInterview}
                    className="text-[13px] font-medium bg-[#F5B83D] hover:bg-[#F5B83D]/90 text-[#12110F] px-4 py-2 rounded-[4px] transition-colors"
                  >
                    Start interview
                  </button>
                </div>
              </div>
            ) : (
              <>
                {/* Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <StatCard label="Total interviews" value={d.total_interviews} />
                  <StatCard
                    label="Average score"
                    value={`${d.average_score.toFixed(1)}/10`}
                    sub="All finished sessions"
                  />
                  <StatCard
                    label="Coding accuracy"
                    value={`${d.coding_accuracy.toFixed(1)}/10`}
                    sub="Test pass rate"
                  />
                  <StatCard
                    label="Algo vs implementation"
                    value={`${d.average_algorithmic_score.toFixed(1)} / ${d.average_implementation_score.toFixed(1)}`}
                    sub="Idea-to-code gap"
                  />
                </div>

                {/* Verdict Distribution */}
                <section>
                  <h2 className="text-[13px] text-[#A59E91] mb-3">
                    Verdict distribution
                  </h2>
                  <div className="flex flex-wrap gap-3">
                    {Object.entries(d.verdict_distribution).map(([v, count]) => (
                      <div
                        key={v}
                        className={`border rounded-[4px] px-3 py-1.5 text-[13px] font-mono ${
                          VERDICT_STYLES[v] || "text-[#A59E91] bg-[#1A1815] border-[#332E28]"
                        }`}
                      >
                        <span className="font-semibold mr-1">{count}x</span>
                        <span>{VERDICT_LABELS[v] || v}</span>
                      </div>
                    ))}
                  </div>
                </section>

                {/* Dimension Strengths / Weaknesses */}
                <div className="grid md:grid-cols-2 gap-6">
                  <section className="bg-[#1A1815] border border-[#332E28] rounded-[10px] p-5">
                    <h2 className="text-[13px] font-medium text-[#7BD88F] mb-4">
                      Demonstrated strengths
                    </h2>
                    <div className="space-y-3">
                      {d.strongest_dimensions.map((dim) => (
                        <div key={dim.name}>
                          <div className="flex justify-between text-[13px] mb-1">
                            <span className="text-[#ECE6DA]">{dim.name}</span>
                          </div>
                          <ScoreBar score={dim.avg_score} />
                        </div>
                      ))}
                      {d.strongest_dimensions.length === 0 && (
                        <p className="text-[#6B645A] text-[13px]">No data recorded yet.</p>
                      )}
                    </div>
                  </section>

                  <section className="bg-[#1A1815] border border-[#332E28] rounded-[10px] p-5">
                    <h2 className="text-[13px] font-medium text-[#FF7A6E] mb-4">
                      Areas needing development
                    </h2>
                    <div className="space-y-3">
                      {d.weakest_dimensions.map((dim) => (
                        <div key={dim.name}>
                          <div className="flex justify-between text-[13px] mb-1">
                            <span className="text-[#ECE6DA]">{dim.name}</span>
                          </div>
                          <ScoreBar score={dim.avg_score} />
                        </div>
                      ))}
                      {d.weakest_dimensions.length === 0 && (
                        <p className="text-[#6B645A] text-[13px]">No data recorded yet.</p>
                      )}
                    </div>
                  </section>
                </div>

                {/* Category Performance */}
                {Object.keys(d.category_performance).length > 0 && (
                  <section>
                    <h2 className="text-[13px] text-[#A59E91] mb-3">
                      Category performance
                    </h2>
                    <div className="bg-[#1A1815] border border-[#332E28] rounded-[10px] p-5 space-y-3">
                      {Object.entries(d.category_performance)
                        .sort(([, a], [, b]) => b - a)
                        .map(([cat, score]) => (
                          <div key={cat}>
                            <div className="flex justify-between text-[13px] mb-1">
                              <span className="text-[#ECE6DA] capitalize">{formatCategory(cat)}</span>
                            </div>
                            <ScoreBar score={score} />
                          </div>
                        ))}
                    </div>
                  </section>
                )}

                {/* Idea-to-Code Trend */}
                {d.idea_to_code_trend.length > 1 && (
                  <section>
                    <h2 className="text-[13px] text-[#A59E91] mb-3">
                      Idea-to-code trend (last {d.idea_to_code_trend.length} sessions)
                    </h2>
                    <div className="bg-[#1A1815] border border-[#332E28] rounded-[10px] overflow-hidden">
                      <table className="w-full text-[13px]">
                        <thead>
                          <tr className="border-b border-[#332E28] text-[#A59E91] text-[11px]">
                            <th className="text-left px-4 py-2 font-medium">Date</th>
                            <th className="text-right px-4 py-2 font-medium">Algo</th>
                            <th className="text-right px-4 py-2 font-medium">Impl</th>
                            <th className="text-right px-4 py-2 font-medium">Gap</th>
                          </tr>
                        </thead>
                        <tbody>
                          {d.idea_to_code_trend.map((entry, i) => {
                            const gap = entry.gap;
                            const gapColor =
                              gap === null
                                ? "text-[#A59E91]"
                                : gap > 2
                                ? "text-[#FF7A6E]"
                                : gap > 1
                                ? "text-[#F5B83D]"
                                : "text-[#7BD88F]";
                            return (
                              <tr key={i} className="border-b border-[#332E28]/50 last:border-0 font-mono">
                                <td className="px-4 py-2 text-[#A59E91] font-sans text-[11px]">
                                  {formatDate(entry.date)}
                                </td>
                                <td className="px-4 py-2 text-right text-[#ECE6DA]">
                                  {entry.algorithmic_score?.toFixed(1) ?? "-"}
                                </td>
                                <td className="px-4 py-2 text-right text-[#ECE6DA]">
                                  {entry.implementation_score?.toFixed(1) ?? "-"}
                                </td>
                                <td className={`px-4 py-2 text-right ${gapColor}`}>
                                  {gap !== null ? (gap > 0 ? `+${gap.toFixed(1)}` : gap.toFixed(1)) : "-"}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </section>
                )}

                {/* Coach Recommendations */}
                <section>
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-[13px] text-[#A59E91]">
                      Targeted recommendations
                    </h2>
                    {recommendations.length === 0 && (
                      <button
                        onClick={loadRecommendations}
                        disabled={recsLoading}
                        className="text-[13px] text-[#F5B83D] hover:underline disabled:opacity-50 transition-colors"
                      >
                        {recsLoading ? "Analyzing..." : "Generate coaching recommendations"}
                      </button>
                    )}
                  </div>
                  {recommendations.length > 0 && (
                    <div className="bg-[#1A1815] border border-[#332E28] rounded-[10px] p-5 space-y-3">
                      {narrative && (
                        <p className="text-[#ECE6DA] text-[13px] border-b border-[#332E28] pb-3 mb-3 leading-relaxed">
                          {narrative}
                        </p>
                      )}
                      <ul className="space-y-2">
                        {recommendations.map((rec, i) => (
                          <li key={i} className="flex gap-2 text-[13px] text-[#A59E91]">
                            <span className="text-[#ECE6DA]">•</span>
                            <span>{rec}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {recommendations.length === 0 && !recsLoading && (
                    <div className="bg-[#1A1815] border border-[#332E28] rounded-[10px] p-5 text-[#A59E91] text-[13px] text-center">
                      Click &ldquo;Generate coaching recommendations&rdquo; to evaluate patterns across your recent interviews.
                    </div>
                  )}
                </section>

                {/* Recent Sessions */}
                {d.recent_sessions.length > 0 && (
                  <section>
                    <h2 className="text-[13px] text-[#A59E91] mb-3">
                      Recent sessions
                    </h2>
                    <div className="bg-[#1A1815] border border-[#332E28] rounded-[10px] overflow-hidden">
                      <table className="w-full text-[13px]">
                        <thead>
                          <tr className="border-b border-[#332E28] text-[#A59E91] text-[11px]">
                            <th className="text-left px-4 py-2 font-medium">Problem</th>
                            <th className="text-left px-4 py-2 hidden md:table-cell font-medium">Category</th>
                            <th className="text-left px-4 py-2 hidden md:table-cell font-medium">Language</th>
                            <th className="text-right px-4 py-2 font-medium">Score</th>
                            <th className="text-right px-4 py-2 font-medium">Verdict</th>
                            <th className="text-right px-4 py-2 hidden md:table-cell font-medium">Date</th>
                          </tr>
                        </thead>
                        <tbody>
                          {d.recent_sessions.map((s) => (
                            <tr key={s.session_id} className="border-b border-[#332E28]/50 last:border-0 hover:bg-[#221F1B] transition-colors">
                              <td className="px-4 py-3 text-[#ECE6DA] font-medium truncate max-w-xs">
                                {s.problem_title}
                              </td>
                              <td className="px-4 py-3 text-[#A59E91] text-[11px] hidden md:table-cell capitalize">
                                {formatCategory(s.category)}
                              </td>
                              <td className="px-4 py-3 text-[#A59E91] text-[11px] hidden md:table-cell uppercase font-mono">
                                {s.language}
                              </td>
                              <td className="px-4 py-3 text-right text-[#ECE6DA] font-mono">
                                {s.score.toFixed(1)}
                              </td>
                              <td className="px-4 py-3 text-right">
                                <span
                                  className={`text-[11px] font-mono border rounded-[4px] px-2 py-0.5 ${
                                    VERDICT_STYLES[s.verdict] || "text-[#A59E91] border-[#332E28]"
                                  }`}
                                >
                                  {VERDICT_LABELS[s.verdict] || s.verdict}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-right text-[#6B645A] text-[11px] hidden md:table-cell">
                                {formatDate(s.created_at)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>
                )}
              </>
            )}
          </div>
        )}

        {/* HISTORY TAB */}
        {activeTab === "history" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-[13px] text-[#A59E91]">
                {historyData.total} total completed sessions
              </p>
            </div>

            {historyData.items.length === 0 ? (
              <div className="text-center py-24 text-[#A59E91] text-[13px]">
                No completed sessions found.
              </div>
            ) : (
              <>
                <div className="bg-[#1A1815] border border-[#332E28] rounded-[10px] overflow-hidden">
                  <table className="w-full text-[13px]">
                    <thead>
                      <tr className="border-b border-[#332E28] text-[#A59E91] text-[11px]">
                        <th className="text-left px-4 py-2 font-medium">Problem</th>
                        <th className="text-left px-4 py-2 hidden md:table-cell font-medium">Category</th>
                        <th className="text-left px-4 py-2 hidden md:table-cell font-medium">Mode</th>
                        <th className="text-left px-4 py-2 hidden md:table-cell font-medium">Language</th>
                        <th className="text-right px-4 py-2 font-medium">Score</th>
                        <th className="text-right px-4 py-2 font-medium">Verdict</th>
                        <th className="text-right px-4 py-2 hidden lg:table-cell font-medium">Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {historyData.items.map((s: RecentSession) => (
                        <tr
                          key={s.session_id}
                          className="border-b border-[#332E28]/50 last:border-0 hover:bg-[#221F1B] transition-colors"
                        >
                          <td className="px-4 py-3 text-[#ECE6DA] font-medium truncate max-w-xs">
                            {s.problem_title}
                          </td>
                          <td className="px-4 py-3 text-[#A59E91] text-[11px] hidden md:table-cell capitalize">
                            {formatCategory(s.category)}
                          </td>
                          <td className="px-4 py-3 text-[#A59E91] text-[11px] hidden md:table-cell capitalize">
                            {s.mode?.replace(/_/g, " ") ?? "-"}
                          </td>
                          <td className="px-4 py-3 text-[#A59E91] text-[11px] hidden md:table-cell uppercase font-mono">
                            {s.language}
                          </td>
                          <td className="px-4 py-3 text-right text-[#ECE6DA] font-mono">
                            {s.score?.toFixed(1) ?? "-"}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {s.verdict ? (
                              <span
                                className={`text-[11px] font-mono border rounded-[4px] px-2 py-0.5 ${
                                  VERDICT_STYLES[s.verdict] || "text-[#A59E91] border-[#332E28]"
                                }`}
                              >
                                {VERDICT_LABELS[s.verdict] || s.verdict}
                              </span>
                            ) : (
                              <span className="text-[#6B645A] text-[11px]">-</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-right text-[#6B645A] text-[11px] hidden lg:table-cell">
                            {formatDate(s.created_at)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {historyData.total_pages > 1 && (
                  <div className="flex items-center justify-center gap-3 pt-2">
                    <button
                      onClick={() => loadHistory(historyPage - 1)}
                      disabled={historyPage <= 1}
                      className="text-[13px] text-[#A59E91] hover:text-[#ECE6DA] disabled:opacity-30 transition-colors px-3 py-1.5 border border-[#332E28] rounded-[4px]"
                    >
                      Prev
                    </button>
                    <span className="text-[11px] text-[#A59E91] font-mono">
                      Page {historyPage} of {historyData.total_pages}
                    </span>
                    <button
                      onClick={() => loadHistory(historyPage + 1)}
                      disabled={historyPage >= historyData.total_pages}
                      className="text-[13px] text-[#A59E91] hover:text-[#ECE6DA] disabled:opacity-30 transition-colors px-3 py-1.5 border border-[#332E28] rounded-[4px]"
                    >
                      Next
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* REVISION TAB */}
        {activeTab === "revision" && (
          <div className="space-y-4">
            <p className="text-[13px] text-[#A59E91]">
              Past problems eligible for revision mode to measure idea-to-code improvement.
            </p>

            {candidates.length === 0 ? (
              <div className="text-center py-24 text-[#A59E91] text-[13px]">
                No revision candidates available yet. Complete more interview sessions to unlock revision.
              </div>
            ) : (
              <div className="bg-[#1A1815] border border-[#332E28] rounded-[10px] overflow-hidden">
                <table className="w-full text-[13px]">
                  <thead>
                    <tr className="border-b border-[#332E28] text-[#A59E91] text-[11px]">
                      <th className="text-left px-4 py-2 font-medium">Problem</th>
                      <th className="text-left px-4 py-2 hidden md:table-cell font-medium">Category</th>
                      <th className="text-left px-4 py-2 hidden md:table-cell font-medium">Difficulty</th>
                      <th className="text-right px-4 py-2 font-medium">Prior score</th>
                      <th className="text-right px-4 py-2 font-medium">Verdict</th>
                      <th className="text-right px-4 py-2 font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidates.map((c) => (
                      <tr
                        key={c.session_id}
                        className="border-b border-[#332E28]/50 last:border-0 hover:bg-[#221F1B] transition-colors"
                      >
                        <td className="px-4 py-3 text-[#ECE6DA] font-medium truncate max-w-xs">
                          {c.problem_title}
                        </td>
                        <td className="px-4 py-3 text-[#A59E91] text-[11px] hidden md:table-cell capitalize">
                          {formatCategory(c.category)}
                        </td>
                        <td className="px-4 py-3 text-[#A59E91] text-[11px] hidden md:table-cell capitalize">
                          {c.difficulty ?? "-"}
                        </td>
                        <td className="px-4 py-3 text-right text-[#ECE6DA] font-mono">
                          {c.score?.toFixed(1) ?? "-"}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {c.verdict ? (
                            <span
                              className={`text-[11px] font-mono border rounded-[4px] px-2 py-0.5 ${
                                VERDICT_STYLES[c.verdict] || "text-[#A59E91] border-[#332E28]"
                              }`}
                            >
                              {VERDICT_LABELS[c.verdict] || c.verdict}
                            </span>
                          ) : (
                            <span className="text-[#6B645A] text-[11px]">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => onStartRevision?.(c)}
                            className="text-[13px] bg-[#221F1B] hover:bg-[#332E28] text-[#ECE6DA] border border-[#332E28] px-3 py-1 rounded-[4px] transition-colors"
                          >
                            Revise
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
