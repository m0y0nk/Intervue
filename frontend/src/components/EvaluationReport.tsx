import React from "react";
import {
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Award,
  TrendingUp,
  TrendingDown,
  Minus,
  Sparkles,
  GitCompare,
  LayoutDashboard,
} from "lucide-react";
import { FinalEvaluationReport } from "../types";

interface EvaluationReportProps {
  report: FinalEvaluationReport;
  onNewInterview: () => void;
  onViewDashboard?: () => void;
}

export const EvaluationReport: React.FC<EvaluationReportProps> = ({
  report,
  onNewInterview,
  onViewDashboard,
}) => {
  const getVerdictStyle = (v: string) => {
    switch (v) {
      case "strong_hire":
        return "bg-emerald-950/80 text-emerald-400 border-emerald-700";
      case "hire":
        return "bg-blue-950/80 text-blue-400 border-blue-700";
      case "borderline":
        return "bg-amber-950/80 text-amber-400 border-amber-700";
      default:
        return "bg-red-950/80 text-red-400 border-red-700";
    }
  };

  const rev = report.revision_comparison;

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6 text-zinc-100">
      {/* Top Banner */}
      <div className="flex items-center justify-between border-b border-[#27272a] pb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Interview Evaluation Report</h1>
          <p className="text-zinc-400 text-xs mt-1 font-mono">Session ID: {report.session_id}</p>
        </div>
        <div className="flex items-center space-x-2">
          {onViewDashboard && (
            <button
              onClick={onViewDashboard}
              className="flex items-center space-x-2 px-3 py-2 rounded-md bg-zinc-800 hover:bg-zinc-700 text-xs font-semibold text-zinc-200 transition-colors border border-zinc-700"
            >
              <LayoutDashboard className="w-3.5 h-3.5 text-indigo-400" />
              <span>Dashboard</span>
            </button>
          )}
          <button
            onClick={onNewInterview}
            className="flex items-center space-x-2 px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white transition-colors shadow-lg shadow-indigo-600/20"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>New Interview</span>
          </button>
        </div>
      </div>

      {/* Revision Comparison Card (if in revision mode) */}
      {rev && (
        <div className="p-5 rounded-lg bg-[#15151c] border border-indigo-900/60 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <GitCompare className="w-4 h-4 text-indigo-400" />
              <h2 className="text-xs font-semibold uppercase tracking-wider text-indigo-300">
                Revision Mode: Comparison vs Prior Attempt
              </h2>
            </div>
            <span className="text-[11px] font-mono text-zinc-400">
              Prior: {rev.prior_session_id}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded bg-[#0f0f13] border border-zinc-800">
              <span className="text-[10px] text-zinc-400 block mb-1">Score Progress</span>
              <div className="flex items-baseline space-x-2">
                <span className="text-lg font-bold text-zinc-100">{rev.current_score}</span>
                <span className="text-xs text-zinc-500">from {rev.prior_score}</span>
                <span
                  className={`text-xs font-semibold flex items-center ${
                    rev.score_delta > 0
                      ? "text-emerald-400"
                      : rev.score_delta < 0
                      ? "text-red-400"
                      : "text-zinc-400"
                  }`}
                >
                  {rev.score_delta > 0 ? (
                    <TrendingUp className="w-3 h-3 mr-0.5" />
                  ) : rev.score_delta < 0 ? (
                    <TrendingDown className="w-3 h-3 mr-0.5" />
                  ) : (
                    <Minus className="w-3 h-3 mr-0.5" />
                  )}
                  {rev.score_delta > 0 ? `+${rev.score_delta}` : rev.score_delta}
                </span>
              </div>
            </div>

            <div className="p-3 rounded bg-[#0f0f13] border border-zinc-800">
              <span className="text-[10px] text-zinc-400 block mb-1">Verdict Transition</span>
              <div className="text-xs font-semibold capitalize text-zinc-200">
                <span className="text-zinc-500">{rev.prior_verdict.replace("_", " ")}</span>
                <span className="mx-1.5 text-zinc-600">→</span>
                <span className="text-indigo-300">{rev.current_verdict.replace("_", " ")}</span>
              </div>
            </div>

            <div className="p-3 rounded bg-[#0f0f13] border border-zinc-800">
              <span className="text-[10px] text-zinc-400 block mb-1">Hidden Tests</span>
              <div className="text-xs font-semibold text-zinc-200">
                <span className="text-zinc-500">{rev.prior_tests_passed}</span>
                <span className="mx-1.5 text-zinc-600">→</span>
                <span className="text-emerald-400 font-bold">{rev.current_tests_passed}</span>
                <span className="text-zinc-500 font-normal"> / {rev.tests_total}</span>
              </div>
            </div>
          </div>

          <p className="text-xs text-zinc-300 bg-[#0f0f13] p-3 rounded border border-zinc-800/80 leading-relaxed">
            {rev.summary}
          </p>
        </div>
      )}

      {/* Primary Verdict & Scores Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total Score */}
        <div className="p-5 rounded-lg bg-[#121215] border border-[#27272a] flex flex-col justify-between">
          <span className="text-xs uppercase font-semibold text-zinc-400 tracking-wider">
            Overall Score
          </span>
          <div className="my-3 flex items-baseline space-x-2">
            <span className="text-4xl font-extrabold text-zinc-50">{report.total_score}</span>
            <span className="text-zinc-500 text-sm font-medium">/ 10.0</span>
          </div>
          <span className="text-xs text-zinc-400">Weighted according to interview style</span>
        </div>

        {/* Verdict */}
        <div className="p-5 rounded-lg bg-[#121215] border border-[#27272a] flex flex-col justify-between">
          <span className="text-xs uppercase font-semibold text-zinc-400 tracking-wider">
            Hiring Verdict
          </span>
          <div className="my-3">
            <span
              className={`text-base font-bold uppercase tracking-wider px-3 py-1.5 rounded border inline-block ${getVerdictStyle(
                report.verdict
              )}`}
            >
              {report.verdict.replace("_", " ")}
            </span>
          </div>
          <span className="text-xs text-zinc-400">Fixed numeric benchmark evaluation</span>
        </div>

        {/* Hidden Test Accuracy */}
        <div className="p-5 rounded-lg bg-[#121215] border border-[#27272a] flex flex-col justify-between">
          <span className="text-xs uppercase font-semibold text-zinc-400 tracking-wider">
            Hidden Test Accuracy
          </span>
          <div className="my-3 flex items-baseline space-x-2">
            <span className="text-4xl font-extrabold text-emerald-400">
              {report.tests_passed}
            </span>
            <span className="text-zinc-500 text-sm font-medium">/ {report.tests_total}</span>
          </div>
          <span className="text-xs text-zinc-400">Deterministic code execution accuracy</span>
        </div>
      </div>

      {/* Idea-to-Code Gap Card */}
      <div className="p-5 rounded-lg bg-[#121215] border border-[#27272a] space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-indigo-400 flex items-center space-x-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Idea-to-Code Gap Analysis</span>
          </h3>
          {(report.algorithmic_score !== undefined || report.implementation_score !== undefined) && (
            <div className="flex items-center space-x-3 text-xs font-mono">
              <span className="text-zinc-400">
                Algorithmic Reasoning:{" "}
                <strong className="text-indigo-300">{report.algorithmic_score ?? "-"}</strong>/10
              </span>
              <span className="text-zinc-600">|</span>
              <span className="text-zinc-400">
                Implementation:{" "}
                <strong className="text-emerald-300">{report.implementation_score ?? "-"}</strong>/10
              </span>
            </div>
          )}
        </div>
        <p className="text-xs text-zinc-300 leading-relaxed bg-[#0c0c0f] p-3 rounded border border-zinc-800">
          {report.idea_to_code_gap}
        </p>
      </div>

      {/* 10 Dimension Breakdown */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
          Detailed Anchored Dimension Scores
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {report.dimension_scores.map((dim, idx) => (
            <div
              key={idx}
              className="p-3.5 rounded-lg bg-[#121215] border border-[#27272a] flex flex-col justify-between space-y-2"
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-zinc-200">{dim.name}</span>
                <div className="flex items-center space-x-2">
                  {dim.is_deterministic && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 font-mono">
                      Deterministic
                    </span>
                  )}
                  <span className="text-xs font-mono font-bold text-zinc-100">
                    {dim.score.toFixed(1)}
                  </span>
                </div>
              </div>
              <p className="text-[11px] text-zinc-400 leading-relaxed">{dim.rationale}</p>
              {dim.evidence_quote && (
                <div className="text-[10px] text-zinc-500 italic border-l-2 border-indigo-700/60 pl-2 mt-1">
                  &ldquo;{dim.evidence_quote}&rdquo;
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Strengths & Weaknesses */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-5 rounded-lg bg-[#121215] border border-[#27272a] space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center space-x-1.5">
            <CheckCircle2 className="w-4 h-4" />
            <span>Demonstrated Strengths</span>
          </h3>
          <ul className="space-y-2 text-xs text-zinc-300 list-disc list-inside">
            {report.strengths.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>

        <div className="p-5 rounded-lg bg-[#121215] border border-[#27272a] space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-amber-400 flex items-center space-x-1.5">
            <AlertCircle className="w-4 h-4" />
            <span>Areas for Development</span>
          </h3>
          <ul className="space-y-2 text-xs text-zinc-300 list-disc list-inside">
            {report.weaknesses.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* Actionable Recommendations */}
      <div className="p-5 rounded-lg bg-[#121215] border border-[#27272a] space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-300 flex items-center space-x-1.5">
          <Award className="w-4 h-4 text-indigo-400" />
          <span>Actionable Recommendations</span>
        </h3>
        <ul className="space-y-2 text-xs text-zinc-300 list-disc list-inside">
          {report.recommendations.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};
