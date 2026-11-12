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
  strong_hire: "text-emerald-400 bg-emerald-900/30 border-emerald-700",
  hire: "text-green-400 bg-green-900/30 border-green-700",
  borderline: "text-amber-400 bg-amber-900/30 border-amber-700",
  no_hire: "text-red-400 bg-red-900/30 border-red-700",
};

const VERDICT_LABELS: Record<string, string> = {
  strong_hire: "Strong Hire",
  hire: "Hire",
  borderline: "Borderline",
  no_hire: "No Hire",
};

function ScoreBar({ score, max = 10 }: { score: number; max?: number }) {
  const pct = Math.min(100, (score / max) * 100);
  const color =
    pct >= 85 ? "bg-emerald-500" : pct >= 70 ? "bg-green-500" : pct >= 55 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-zinc-400 w-6 text-right">{score.toFixed(1)}</span>
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
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
      <p className="text-xs text-zinc-500 uppercase tracking-widest mb-1">{label}</p>
      <p className="text-2xl font-bold text-zinc-100">{value}</p>
      {sub && <p className="text-xs text-zinc-500 mt-1">{sub}</p>}
    </div>
  );
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
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
  if (!cat) return "—";
  return cat.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
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
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <div className="text-zinc-500 text-sm animate-pulse">Loading dashboard…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <div className="text-red-400 text-sm">{error}</div>
      </div>
    );
  }

  const d = data!;
  const hasData = d.total_interviews > 0;

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100">
      {/* Header */}
      <header className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Intervue Dashboard</h1>
          <p className="text-xs text-zinc-500 mt-0.5">Your interview analytics & history</p>
        </div>
        <button
          onClick={onNewInterview}
          className="text-sm bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-1.5 rounded-lg transition-colors"
        >
          + New Interview
        </button>
      </header>

      {/* Tabs */}
      <nav className="border-b border-zinc-800 px-6 flex gap-6">
        {(["overview", "history", "revision"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`text-sm py-3 border-b-2 transition-colors capitalize ${
              activeTab === tab
                ? "border-indigo-500 text-zinc-100"
                : "border-transparent text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {tab === "revision" ? "Revision Candidates" : tab.charAt(0).toUpperCase() + tab.slice(1)}
            {tab === "revision" && candidates.length > 0 && (
              <span className="ml-1.5 text-xs bg-indigo-900/60 text-indigo-300 px-1.5 py-0.5 rounded-full">
                {candidates.length}
              </span>
            )}
          </button>
        ))}
      </nav>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* ---------------------------------------------------------------- */}
        {/* OVERVIEW TAB                                                       */}
        {/* ---------------------------------------------------------------- */}
        {activeTab === "overview" && (
          <div className="space-y-8">
            {!hasData ? (
              <div className="text-center py-24">
                <p className="text-zinc-500 text-sm">No interviews completed yet.</p>
                <p className="text-zinc-600 text-xs mt-1">
                  Complete your first session to see analytics here.
                </p>
                <button
                  onClick={onNewInterview}
                  className="mt-6 text-sm bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2 rounded-lg transition-colors"
                >
                  Start Interview
                </button>
              </div>
            ) : (
              <>
                {/* Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <StatCard label="Total Interviews" value={d.total_interviews} />
                  <StatCard
                    label="Avg Score"
                    value={`${d.average_score}/10`}
                    sub="All finished sessions"
                  />
                  <StatCard
                    label="Coding Accuracy"
                    value={`${d.coding_accuracy}/10`}
                    sub="Test pass rate"
                  />
                  <StatCard
                    label="Algo vs Impl"
                    value={`${d.average_algorithmic_score} / ${d.average_implementation_score}`}
                    sub="Idea-to-Code gap"
                  />
                </div>

                {/* Verdict Distribution */}
                <section>
                  <h2 className="text-sm font-medium text-zinc-400 mb-3 uppercase tracking-widest">
                    Verdict Distribution
                  </h2>
                  <div className="flex flex-wrap gap-3">
                    {Object.entries(d.verdict_distribution).map(([v, count]) => (
                      <div
                        key={v}
                        className={`border rounded-lg px-4 py-2 text-sm ${VERDICT_STYLES[v] || "text-zinc-400 bg-zinc-900 border-zinc-700"}`}
                      >
                        <span className="font-semibold">{count}×</span>{" "}
                        {VERDICT_LABELS[v] || v}
                      </div>
                    ))}
                  </div>
                </section>

                {/* Dimension Strengths / Weaknesses */}
                <div className="grid md:grid-cols-2 gap-6">
                  <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
                    <h2 className="text-xs font-medium text-emerald-400 uppercase tracking-widest mb-4">
                      ↑ Strengths
                    </h2>
                    <div className="space-y-3">
                      {d.strongest_dimensions.map((dim) => (
                        <div key={dim.name}>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="text-zinc-300">{dim.name}</span>
                          </div>
                          <ScoreBar score={dim.avg_score} />
                        </div>
                      ))}
                      {d.strongest_dimensions.length === 0 && (
                        <p className="text-zinc-600 text-xs">No data yet.</p>
                      )}
                    </div>
                  </section>

                  <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
                    <h2 className="text-xs font-medium text-red-400 uppercase tracking-widest mb-4">
                      ↓ Needs Work
                    </h2>
                    <div className="space-y-3">
                      {d.weakest_dimensions.map((dim) => (
                        <div key={dim.name}>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="text-zinc-300">{dim.name}</span>
                          </div>
                          <ScoreBar score={dim.avg_score} />
                        </div>
                      ))}
                      {d.weakest_dimensions.length === 0 && (
                        <p className="text-zinc-600 text-xs">No data yet.</p>
                      )}
                    </div>
                  </section>
                </div>

                {/* Category Performance */}
                {Object.keys(d.category_performance).length > 0 && (
                  <section>
                    <h2 className="text-sm font-medium text-zinc-400 mb-3 uppercase tracking-widest">
                      Category Performance
                    </h2>
                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-3">
                      {Object.entries(d.category_performance)
                        .sort(([, a], [, b]) => b - a)
                        .map(([cat, score]) => (
                          <div key={cat}>
                            <div className="flex justify-between text-sm mb-1">
                              <span className="text-zinc-300">{formatCategory(cat)}</span>
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
                    <h2 className="text-sm font-medium text-zinc-400 mb-3 uppercase tracking-widest">
                      Idea-to-Code Trend (last {d.idea_to_code_trend.length} sessions)
                    </h2>
                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-zinc-800 text-zinc-500 text-xs">
                            <th className="text-left px-4 py-2">Date</th>
                            <th className="text-right px-4 py-2">Algo</th>
                            <th className="text-right px-4 py-2">Impl</th>
                            <th className="text-right px-4 py-2">Gap</th>
                          </tr>
                        </thead>
                        <tbody>
                          {d.idea_to_code_trend.map((entry, i) => {
                            const gap = entry.gap;
                            const gapColor =
                              gap === null
                                ? "text-zinc-500"
                                : gap > 2
                                ? "text-red-400"
                                : gap > 1
                                ? "text-amber-400"
                                : "text-emerald-400";
                            return (
                              <tr key={i} className="border-b border-zinc-800/50 last:border-0">
                                <td className="px-4 py-2 text-zinc-500 text-xs">
                                  {formatDate(entry.date)}
                                </td>
                                <td className="px-4 py-2 text-right text-zinc-300">
                                  {entry.algorithmic_score?.toFixed(1) ?? "—"}
                                </td>
                                <td className="px-4 py-2 text-right text-zinc-300">
                                  {entry.implementation_score?.toFixed(1) ?? "—"}
                                </td>
                                <td className={`px-4 py-2 text-right font-mono ${gapColor}`}>
                                  {gap !== null ? (gap > 0 ? `+${gap.toFixed(1)}` : gap.toFixed(1)) : "—"}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </section>
                )}

                {/* Recommendations */}
                <section>
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-widest">
                      Coach Recommendations
                    </h2>
                    {recommendations.length === 0 && (
                      <button
                        onClick={loadRecommendations}
                        disabled={recsLoading}
                        className="text-xs text-indigo-400 hover:text-indigo-300 disabled:opacity-50 transition-colors"
                      >
                        {recsLoading ? "Generating…" : "Get recommendations →"}
                      </button>
                    )}
                  </div>
                  {recommendations.length > 0 && (
                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-3">
                      {narrative && (
                        <p className="text-zinc-400 text-sm italic border-b border-zinc-800 pb-3 mb-3">
                          {narrative}
                        </p>
                      )}
                      <ul className="space-y-2">
                        {recommendations.map((rec, i) => (
                          <li key={i} className="flex gap-3 text-sm text-zinc-300">
                            <span className="text-indigo-400 mt-0.5">•</span>
                            <span>{rec}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {recommendations.length === 0 && !recsLoading && (
                    <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-xl p-5 text-zinc-600 text-sm text-center">
                      Click "Get recommendations" for AI-powered coaching based on your stats.
                    </div>
                  )}
                </section>

                {/* Recent Sessions */}
                {d.recent_sessions.length > 0 && (
                  <section>
                    <h2 className="text-sm font-medium text-zinc-400 mb-3 uppercase tracking-widest">
                      Recent Sessions
                    </h2>
                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-zinc-800 text-zinc-500 text-xs">
                            <th className="text-left px-4 py-2">Problem</th>
                            <th className="text-left px-4 py-2 hidden md:table-cell">Category</th>
                            <th className="text-left px-4 py-2 hidden md:table-cell">Lang</th>
                            <th className="text-right px-4 py-2">Score</th>
                            <th className="text-right px-4 py-2">Verdict</th>
                            <th className="text-right px-4 py-2 hidden md:table-cell">Date</th>
                          </tr>
                        </thead>
                        <tbody>
                          {d.recent_sessions.map((s) => (
                            <tr key={s.session_id} className="border-b border-zinc-800/50 last:border-0 hover:bg-zinc-800/30 transition-colors">
                              <td className="px-4 py-3 text-zinc-200 font-medium truncate max-w-xs">
                                {s.problem_title}
                              </td>
                              <td className="px-4 py-3 text-zinc-500 text-xs hidden md:table-cell">
                                {formatCategory(s.category)}
                              </td>
                              <td className="px-4 py-3 text-zinc-500 text-xs hidden md:table-cell uppercase">
                                {s.language}
                              </td>
                              <td className="px-4 py-3 text-right text-zinc-300 font-mono">
                                {s.score.toFixed(1)}
                              </td>
                              <td className="px-4 py-3 text-right">
                                <span
                                  className={`text-xs border rounded px-2 py-0.5 ${
                                    VERDICT_STYLES[s.verdict] || "text-zinc-400 border-zinc-700"
                                  }`}
                                >
                                  {VERDICT_LABELS[s.verdict] || s.verdict}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-right text-zinc-600 text-xs hidden md:table-cell">
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

        {/* ---------------------------------------------------------------- */}
        {/* HISTORY TAB                                                        */}
        {/* ---------------------------------------------------------------- */}
        {activeTab === "history" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-xs text-zinc-500">
                {historyData.total} total finished sessions
              </p>
            </div>

            {historyData.items.length === 0 ? (
              <div className="text-center py-24 text-zinc-500 text-sm">
                No finished sessions yet.
              </div>
            ) : (
              <>
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-zinc-800 text-zinc-500 text-xs">
                        <th className="text-left px-4 py-2">Problem</th>
                        <th className="text-left px-4 py-2 hidden md:table-cell">Category</th>
                        <th className="text-left px-4 py-2 hidden md:table-cell">Mode</th>
                        <th className="text-left px-4 py-2 hidden md:table-cell">Lang</th>
                        <th className="text-right px-4 py-2">Score</th>
                        <th className="text-right px-4 py-2">Verdict</th>
                        <th className="text-right px-4 py-2 hidden lg:table-cell">Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {historyData.items.map((s: RecentSession) => (
                        <tr
                          key={s.session_id}
                          className="border-b border-zinc-800/50 last:border-0 hover:bg-zinc-800/30 transition-colors"
                        >
                          <td className="px-4 py-3 text-zinc-200 font-medium truncate max-w-xs">
                            {s.problem_title}
                          </td>
                          <td className="px-4 py-3 text-zinc-500 text-xs hidden md:table-cell">
                            {formatCategory(s.category)}
                          </td>
                          <td className="px-4 py-3 text-zinc-500 text-xs hidden md:table-cell capitalize">
                            {s.mode?.replace(/_/g, " ") ?? "—"}
                          </td>
                          <td className="px-4 py-3 text-zinc-500 text-xs hidden md:table-cell uppercase">
                            {s.language}
                          </td>
                          <td className="px-4 py-3 text-right text-zinc-300 font-mono">
                            {s.score?.toFixed(1) ?? "—"}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {s.verdict ? (
                              <span
                                className={`text-xs border rounded px-2 py-0.5 ${
                                  VERDICT_STYLES[s.verdict] || "text-zinc-400 border-zinc-700"
                                }`}
                              >
                                {VERDICT_LABELS[s.verdict] || s.verdict}
                              </span>
                            ) : (
                              <span className="text-zinc-600 text-xs">—</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-right text-zinc-600 text-xs hidden lg:table-cell">
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
                      className="text-xs text-zinc-400 hover:text-zinc-200 disabled:opacity-30 transition-colors px-3 py-1.5 border border-zinc-800 rounded-lg"
                    >
                      ← Prev
                    </button>
                    <span className="text-xs text-zinc-500">
                      Page {historyPage} of {historyData.total_pages}
                    </span>
                    <button
                      onClick={() => loadHistory(historyPage + 1)}
                      disabled={historyPage >= historyData.total_pages}
                      className="text-xs text-zinc-400 hover:text-zinc-200 disabled:opacity-30 transition-colors px-3 py-1.5 border border-zinc-800 rounded-lg"
                    >
                      Next →
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ---------------------------------------------------------------- */}
        {/* REVISION TAB                                                       */}
        {/* ---------------------------------------------------------------- */}
        {activeTab === "revision" && (
          <div className="space-y-4">
            <p className="text-xs text-zinc-500">
              Sessions you can re-attempt in Revision mode to compare your improvement.
            </p>

            {candidates.length === 0 ? (
              <div className="text-center py-24 text-zinc-500 text-sm">
                No revision candidates yet. Complete interviews that have a linked problem.
              </div>
            ) : (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-800 text-zinc-500 text-xs">
                      <th className="text-left px-4 py-2">Problem</th>
                      <th className="text-left px-4 py-2 hidden md:table-cell">Category</th>
                      <th className="text-left px-4 py-2 hidden md:table-cell">Difficulty</th>
                      <th className="text-right px-4 py-2">Prior Score</th>
                      <th className="text-right px-4 py-2">Verdict</th>
                      <th className="text-right px-4 py-2">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidates.map((c) => (
                      <tr
                        key={c.session_id}
                        className="border-b border-zinc-800/50 last:border-0 hover:bg-zinc-800/30 transition-colors"
                      >
                        <td className="px-4 py-3 text-zinc-200 font-medium truncate max-w-xs">
                          {c.problem_title}
                        </td>
                        <td className="px-4 py-3 text-zinc-500 text-xs hidden md:table-cell">
                          {formatCategory(c.category)}
                        </td>
                        <td className="px-4 py-3 text-zinc-500 text-xs hidden md:table-cell capitalize">
                          {c.difficulty ?? "—"}
                        </td>
                        <td className="px-4 py-3 text-right text-zinc-300 font-mono">
                          {c.score?.toFixed(1) ?? "—"}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {c.verdict ? (
                            <span
                              className={`text-xs border rounded px-2 py-0.5 ${
                                VERDICT_STYLES[c.verdict] || "text-zinc-400 border-zinc-700"
                              }`}
                            >
                              {VERDICT_LABELS[c.verdict] || c.verdict}
                            </span>
                          ) : (
                            <span className="text-zinc-600 text-xs">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => onStartRevision?.(c)}
                            className="text-xs bg-indigo-900/60 hover:bg-indigo-800/60 text-indigo-300 border border-indigo-700/50 px-3 py-1.5 rounded-lg transition-colors"
                          >
                            Revise →
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

