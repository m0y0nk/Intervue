import React from "react";
import { Lock, Unlock, Code2, Tag } from "lucide-react";
import { ProblemPublic } from "../types";

interface ProblemPanelProps {
  problem: ProblemPublic | undefined;
  stage: number;
}

export const ProblemPanel: React.FC<ProblemPanelProps> = ({ problem, stage }) => {
  if (!problem) {
    return (
      <div className="h-full flex items-center justify-center text-zinc-500 text-sm">
        No problem loaded.
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-y-auto pr-2 space-y-6 text-sm text-zinc-300">
      {/* Title & Metadata */}
      <div>
        <div className="flex items-center space-x-2 mb-2">
          {problem.difficulty && (
            <span
              className={`text-xs px-2 py-0.5 rounded font-medium ${
                problem.difficulty === "easy"
                  ? "bg-emerald-950/70 text-emerald-400 border border-emerald-800/60"
                  : problem.difficulty === "hard"
                  ? "bg-red-950/70 text-red-400 border border-red-800/60"
                  : "bg-amber-950/70 text-amber-400 border border-amber-800/60"
              }`}
            >
              {problem.difficulty.toUpperCase()}
            </span>
          )}
          {problem.category && (
            <span className="text-xs px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-300 flex items-center">
              <Tag className="w-3 h-3 mr-1 text-zinc-400" />
              {problem.category.replace("_", " ")}
            </span>
          )}
        </div>
        <h2 className="text-lg font-semibold text-zinc-100 tracking-tight">
          {problem.title}
        </h2>
      </div>

      {/* Statement */}
      <div className="space-y-3 leading-relaxed text-zinc-200">
        <p className="whitespace-pre-wrap">{problem.statement}</p>
      </div>

      {/* Examples */}
      <div className="space-y-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
          Examples
        </h3>
        {problem.examples.map((ex, idx) => (
          <div
            key={idx}
            className="p-3 rounded-md bg-[#121215] border border-[#27272a] space-y-2 text-xs"
          >
            <div className="flex items-start">
              <span className="font-semibold text-zinc-400 w-16 shrink-0">Input:</span>
              <code className="text-zinc-200 font-mono">{ex.input_str}</code>
            </div>
            <div className="flex items-start">
              <span className="font-semibold text-zinc-400 w-16 shrink-0">Output:</span>
              <code className="text-emerald-400 font-mono">{ex.output_str}</code>
            </div>
            {ex.explanation && (
              <div className="text-zinc-400 pt-1 text-[11px] border-t border-[#1f1f23]">
                {ex.explanation}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Revealed Constraints */}
      <div className="space-y-2 pt-2 border-t border-[#27272a]">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
            Constraints
          </h3>
          {stage >= 3 ? (
            <span className="text-[11px] flex items-center text-emerald-400">
              <Unlock className="w-3 h-3 mr-1" /> Revealed
            </span>
          ) : (
            <span className="text-[11px] flex items-center text-zinc-500">
              <Lock className="w-3 h-3 mr-1" /> Unlocks in Stage 3
            </span>
          )}
        </div>

        {stage >= 3 ? (
          <ul className="space-y-1.5 list-disc list-inside text-xs font-mono text-zinc-300 bg-[#121215] p-3 rounded-md border border-[#27272a]">
            {problem.revealed_constraints.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        ) : (
          <div className="p-3 rounded-md bg-[#121215]/60 border border-[#27272a]/60 text-xs text-zinc-500 italic">
            Constraint details are locked during initial problem discussion. They will be automatically revealed when advancing to Stage 3 (Constraint Analysis).
          </div>
        )}
      </div>

      {/* Function Signature */}
      <div className="space-y-2 pt-2 border-t border-[#27272a]">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center">
          <Code2 className="w-3.5 h-3.5 mr-1 text-zinc-400" />
          Signature Contract
        </h3>
        <div className="p-2.5 rounded bg-[#0d0d10] border border-[#27272a] font-mono text-xs text-indigo-300">
          {problem.signature.function_name}(
          {problem.signature.args.map((a) => `${a.name}: ${a.type}`).join(", ")}
          ) -&gt; {problem.signature.return_type}
        </div>
      </div>
    </div>
  );
};
