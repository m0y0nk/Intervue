import React from "react";
import { CheckCircle2, AlertCircle, ArrowLeft, RefreshCw, Award } from "lucide-react";
import { FinalEvaluationReport } from "../types";

interface EvaluationReportProps {
  report: FinalEvaluationReport;
  onNewInterview: () => void;
}

export const EvaluationReport: React.FC<EvaluationReportProps> = ({
  report,
  onNewInterview,
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

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-8 text-zinc-100">
      {/* Top Banner */}
      <div className="flex items-center justify-between border-b border-[#27272a] pb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Interview Evaluation Report</h1>
          <p className="text-zinc-400 text-sm mt-1">Session ID: {report.session_id}</p>
        </div>
        <button
          onClick={onNewInterview}
          className="flex items-center space-x-2 px-4 py-2 rounded-md bg-zinc-800 hover:bg-zinc-700 text-xs font-semibold text-zinc-100 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>New Interview</span>
        </button>
      </div>

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

      {/* Idea-to-Code Gap */}
      <div className="p-5 rounded-lg bg-[#121215] border border-[#27272a] space-y-2">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-indigo-400">
          Idea-to-Code Gap Analysis
        </h3>
        <p className="text-sm text-zinc-300 leading-relaxed">{report.idea_to_code_gap}</p>
      </div>

      {/* 10 Dimension Breakdown */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
          Detailed Dimension Scores
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
                  <span className="text-sm font-mono font-bold text-zinc-100">
                    {dim.score.toFixed(1)}
                  </span>
                </div>
              </div>
              <p className="text-[11px] text-zinc-400 leading-relaxed">{dim.rationale}</p>
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
