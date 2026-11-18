import React from "react";
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
  const getVerdictColor = (v: string) => {
    switch (v) {
      case "strong_hire":
      case "hire":
        return "text-[#7BD88F] border-[#7BD88F]/40";
      case "borderline":
        return "text-[#F5B83D] border-[#F5B83D]/40";
      default:
        return "text-[#FF7A6E] border-[#FF7A6E]/40";
    }
  };

  const formatVerdict = (v: string) => {
    return v.replace(/_/g, " ").toLowerCase();
  };

  const rev = report.revision_comparison;

  return (
    <div className="max-w-4xl mx-auto py-10 px-4 space-y-8 text-[#ECE6DA] font-sans">
      {/* Top Header */}
      <div className="flex items-baseline justify-between border-b border-[#332E28] pb-6">
        <div>
          <h1 className="font-serif text-[28px] font-normal tracking-tight text-[#ECE6DA]">
            Interview Evaluation Report
          </h1>
          <p className="text-[#A59E91] text-[13px] mt-1 font-mono">
            Session: {report.session_id}
          </p>
        </div>
        <div className="flex items-center space-x-3">
          {onViewDashboard && (
            <button
              onClick={onViewDashboard}
              className="px-3 py-1.5 rounded-[4px] border border-[#332E28] text-[13px] text-[#A59E91] hover:text-[#ECE6DA] hover:bg-[#1A1815] transition-colors"
            >
              Dashboard
            </button>
          )}
          <button
            onClick={onNewInterview}
            className="px-3.5 py-1.5 rounded-[4px] bg-[#F5B83D] hover:bg-[#F5B83D]/90 text-[#12110F] text-[13px] font-medium transition-colors"
          >
            New interview
          </button>
        </div>
      </div>

      {/* Revision Comparison Card */}
      {rev && (
        <div className="p-5 rounded-[10px] bg-[#1A1815] border border-[#332E28] space-y-4">
          <div className="flex items-center justify-between text-[13px]">
            <span className="font-medium text-[#ECE6DA]">Revision comparison</span>
            <span className="font-mono text-[11px] text-[#A59E91]">
              Prior: {rev.prior_session_id}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded-[4px] bg-[#12110F] border border-[#332E28]">
              <span className="text-[11px] text-[#A59E91] block mb-1">Score progress</span>
              <div className="flex items-baseline space-x-2">
                <span className="text-[18px] font-mono font-medium text-[#ECE6DA]">
                  {rev.current_score}
                </span>
                <span className="text-[11px] text-[#A59E91]">from {rev.prior_score}</span>
                <span
                  className={`text-[11px] font-mono font-medium ${
                    rev.score_delta > 0
                      ? "text-[#7BD88F]"
                      : rev.score_delta < 0
                      ? "text-[#FF7A6E]"
                      : "text-[#A59E91]"
                  }`}
                >
                  {rev.score_delta > 0 ? `+${rev.score_delta}` : rev.score_delta}
                </span>
              </div>
            </div>

            <div className="p-3 rounded-[4px] bg-[#12110F] border border-[#332E28]">
              <span className="text-[11px] text-[#A59E91] block mb-1">Verdict transition</span>
              <div className="text-[13px] font-mono text-[#ECE6DA] capitalize">
                <span className="text-[#A59E91]">{rev.prior_verdict.replace(/_/g, " ")}</span>
                <span className="mx-2 text-[#6B645A]">→</span>
                <span className="text-[#ECE6DA]">{rev.current_verdict.replace(/_/g, " ")}</span>
              </div>
            </div>

            <div className="p-3 rounded-[4px] bg-[#12110F] border border-[#332E28]">
              <span className="text-[11px] text-[#A59E91] block mb-1">Hidden tests</span>
              <div className="text-[13px] font-mono text-[#ECE6DA]">
                <span className="text-[#A59E91]">{rev.prior_tests_passed}</span>
                <span className="mx-2 text-[#6B645A]">→</span>
                <span className="text-[#7BD88F] font-medium">{rev.current_tests_passed}</span>
                <span className="text-[#A59E91]"> / {rev.tests_total}</span>
              </div>
            </div>
          </div>

          <p className="text-[13px] text-[#ECE6DA] leading-relaxed p-3 rounded-[4px] bg-[#12110F] border border-[#332E28]">
            {rev.summary}
          </p>
        </div>
      )}

      {/* Primary Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total Score */}
        <div className="p-5 rounded-[10px] bg-[#1A1815] border border-[#332E28] flex flex-col justify-between">
          <span className="text-[13px] text-[#A59E91]">Overall score</span>
          <div className="my-3 flex items-baseline space-x-2">
            <span className="font-serif text-[44px] leading-none text-[#ECE6DA]">
              {report.total_score}
            </span>
            <span className="text-[#A59E91] text-[13px] font-mono">/ 10.0</span>
          </div>
          <span className="text-[11px] text-[#A59E91]">Weighted by selected interview style</span>
        </div>

        {/* Verdict */}
        <div className="p-5 rounded-[10px] bg-[#1A1815] border border-[#332E28] flex flex-col justify-between">
          <span className="text-[13px] text-[#A59E91]">Hiring recommendation</span>
          <div className="my-3">
            <span
              className={`text-[15px] font-medium capitalize px-3 py-1 rounded-[4px] border ${getVerdictColor(
                report.verdict
              )}`}
            >
              {formatVerdict(report.verdict)}
            </span>
          </div>
          <span className="text-[11px] text-[#A59E91]">Evaluated against rubric anchors</span>
        </div>

        {/* Hidden Test Accuracy */}
        <div className="p-5 rounded-[10px] bg-[#1A1815] border border-[#332E28] flex flex-col justify-between">
          <span className="text-[13px] text-[#A59E91]">Hidden test accuracy</span>
          <div className="my-3 flex items-baseline space-x-2">
            <span className="font-serif text-[44px] leading-none text-[#7BD88F]">
              {report.tests_passed}
            </span>
            <span className="text-[#A59E91] text-[13px] font-mono">/ {report.tests_total}</span>
          </div>
          <span className="text-[11px] text-[#A59E91]">Verified in isolated runner</span>
        </div>
      </div>

      {/* Idea-to-Code Gap Card */}
      <div className="p-5 rounded-[10px] bg-[#1A1815] border border-[#332E28] space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-[13px] font-medium text-[#ECE6DA]">
            Idea-to-code gap analysis
          </h3>
          {(report.algorithmic_score !== undefined || report.implementation_score !== undefined) && (
            <div className="flex items-center space-x-3 text-[11px] font-mono">
              <span className="text-[#A59E91]">
                Algorithmic: <span className="text-[#ECE6DA]">{report.algorithmic_score ?? "-"}</span> / 10
              </span>
              <span className="text-[#332E28]">|</span>
              <span className="text-[#A59E91]">
                Implementation: <span className="text-[#ECE6DA]">{report.implementation_score ?? "-"}</span> / 10
              </span>
            </div>
          )}
        </div>
        <p className="text-[13px] text-[#ECE6DA] leading-relaxed p-3.5 rounded-[4px] bg-[#12110F] border border-[#332E28]">
          {report.idea_to_code_gap}
        </p>
      </div>

      {/* 10 Dimension Breakdown */}
      <div className="space-y-3">
        <h3 className="text-[13px] text-[#A59E91]">
          Anchored dimension breakdown
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {report.dimension_scores.map((dim, idx) => (
            <div
              key={idx}
              className="p-3.5 rounded-[10px] bg-[#1A1815] border border-[#332E28] flex flex-col justify-between space-y-2"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-[13px] text-[#ECE6DA]">{dim.name}</span>
                <div className="flex items-center space-x-2">
                  {dim.is_deterministic && (
                    <span className="text-[10px] font-mono text-[#A59E91]">
                      deterministic
                    </span>
                  )}
                  <span className="text-[13px] font-mono font-medium text-[#ECE6DA]">
                    {dim.score.toFixed(1)}
                  </span>
                </div>
              </div>
              <p className="text-[13px] text-[#A59E91] leading-relaxed">{dim.rationale}</p>
              {dim.evidence_quote && (
                <div className="text-[11px] text-[#6B645A] italic border-l border-[#332E28] pl-2.5 mt-1 font-mono">
                  &ldquo;{dim.evidence_quote}&rdquo;
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Strengths & Weaknesses */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-5 rounded-[10px] bg-[#1A1815] border border-[#332E28] space-y-3">
          <h3 className="text-[13px] font-medium text-[#7BD88F]">
            Demonstrated strengths
          </h3>
          <ul className="space-y-2 text-[13px] text-[#ECE6DA] list-disc list-inside">
            {report.strengths.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>

        <div className="p-5 rounded-[10px] bg-[#1A1815] border border-[#332E28] space-y-3">
          <h3 className="text-[13px] font-medium text-[#FF7A6E]">
            Areas for development
          </h3>
          <ul className="space-y-2 text-[13px] text-[#ECE6DA] list-disc list-inside">
            {report.weaknesses.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* Actionable Recommendations */}
      <div className="p-5 rounded-[10px] bg-[#1A1815] border border-[#332E28] space-y-3">
        <h3 className="text-[13px] font-medium text-[#ECE6DA]">
          Actionable recommendations
        </h3>
        <ul className="space-y-2 text-[13px] text-[#ECE6DA] list-disc list-inside">
          {report.recommendations.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};
