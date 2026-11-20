import React from "react";
import { ProblemPublic } from "../types";

interface ProblemPanelProps {
  problem: ProblemPublic | undefined;
  stage: number;
}

export const ProblemPanel: React.FC<ProblemPanelProps> = ({ problem, stage }) => {
  if (!problem) {
    return (
      <div className="h-full flex items-center justify-center text-[#A59E91] text-13 font-mono">
        No problem loaded.
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-y-auto pr-3 space-y-6 text-[#ECE6DA] text-15 leading-relaxed">
      {/* Title & Plain Metadata */}
      <div className="space-y-1.5 pb-4 border-b border-[#332E28]">
        {/* Difficulty, Topic, and LLM-allocated Time Budget */}
        {(problem.difficulty || problem.category || problem.time_limit_minutes) && (
          <div className="text-13 text-[#A59E91] font-mono space-x-2 flex items-center flex-wrap">
            {problem.difficulty && <span className="capitalize">{problem.difficulty}</span>}
            {problem.difficulty && problem.category && <span>·</span>}
            {problem.category && <span className="capitalize">{problem.category.replace("_", " ")}</span>}
            {(problem.difficulty || problem.category) && problem.time_limit_minutes && <span>·</span>}
            {problem.time_limit_minutes && (
              <span className="text-[#F5B83D]/90">
                {problem.time_limit_minutes}m target
                {problem.stage_time_budgets?.coding ? ` (${problem.stage_time_budgets.coding}m coding)` : ""}
              </span>
            )}
          </div>
        )}
        <h2 className="font-display text-28 text-[#ECE6DA] tracking-tight leading-snug">
          {problem.title}
        </h2>
      </div>

      {/* Problem Statement */}
      <div className="space-y-3">
        <p className="whitespace-pre-wrap text-[#ECE6DA] leading-relaxed">
          {problem.statement}
        </p>
      </div>

      {/* Examples as Mono Blocks with a left rule in line (#332E28) */}
      <div className="space-y-4 pt-2">
        <div className="text-13 text-[#A59E91] font-medium">Examples</div>
        {problem.examples.map((ex, idx) => (
          <div
            key={idx}
            className="pl-3.5 border-l-2 border-[#332E28] space-y-1 text-13 font-mono text-[#ECE6DA]"
          >
            <div>
              <span className="text-[#A59E91]">Input: </span>
              <span>{ex.input_str}</span>
            </div>
            <div>
              <span className="text-[#A59E91]">Output: </span>
              <span>{ex.output_str}</span>
            </div>
            {ex.explanation && (
              <div className="text-[12px] text-[#A59E91] font-sans mt-1">
                {ex.explanation}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Constraints: Locked constraints show 'Unlocks in stage 3' as a real state, not a faded box */}
      <div className="space-y-3 pt-4 border-t border-[#332E28]">
        <div className="text-13 text-[#A59E91] font-medium">Constraints</div>
        {stage >= 3 ? (
          <ul className="space-y-1 text-13 font-mono text-[#ECE6DA]">
            {problem.revealed_constraints.map((c, i) => (
              <li key={i} className="flex items-start">
                <span className="text-[#A59E91] mr-2">·</span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="pl-3.5 border-l-2 border-[#332E28] text-13 text-[#A59E91] py-1">
            Constraints unlock automatically in Stage 3.
          </div>
        )}
      </div>
    </div>
  );
};
