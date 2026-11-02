import React, { useState } from "react";
import {
  Play,
  Pause,
  RotateCcw,
  ChevronRight,
  Send,
  AlertTriangle,
  Code2,
  FileText,
  CheckCircle,
} from "lucide-react";
import { ChatMessage, RunCodeResponse, SessionState } from "../types";
import { Timer } from "../components/Timer";
import { ProblemPanel } from "../components/ProblemPanel";
import { NotesEditor } from "../components/NotesEditor";
import { CodeEditor } from "../components/CodeEditor";
import { InterviewerPanel } from "../components/InterviewerPanel";

interface WorkspacePageProps {
  session: SessionState;
  chatLog: ChatMessage[];
  onBegin: () => Promise<void>;
  onPause: () => Promise<void>;
  onResume: () => Promise<void>;
  onReset: () => Promise<void>;
  onNextStage: () => Promise<void>;
  onSaveNotes: (stage: number, content: string) => void;
  onCodeChange: (code: string) => void;
  onRunCode: () => Promise<RunCodeResponse>;
  onSubmit: () => Promise<void>;
  onSendMessage: (msg: string) => Promise<void>;
  onSyncTimer: () => void;
  isSendingMessage: boolean;
  isRunningCode: boolean;
  isSubmitting: boolean;
  rateLimitSecondsLeft: number;
}

const STAGE_NAMES = [
  "Understanding",
  "Brute force",
  "Constraints",
  "Optimal approach",
  "Edge cases",
  "Coding",
];

export const WorkspacePage: React.FC<WorkspacePageProps> = ({
  session,
  chatLog,
  onBegin,
  onPause,
  onResume,
  onReset,
  onNextStage,
  onSaveNotes,
  onCodeChange,
  onRunCode,
  onSubmit,
  onSendMessage,
  onSyncTimer,
  isSendingMessage,
  isRunningCode,
  isSubmitting,
  rateLimitSecondsLeft,
}) => {
  const [showResetModal, setShowResetModal] = useState(false);
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [centerView, setCenterView] = useState<"notes" | "code">(
    session.stage >= 6 ? "code" : "notes"
  );

  return (
    <div className="flex flex-col h-screen bg-[#09090b] text-zinc-100 overflow-hidden font-sans">
      {/* Ready Screen Overlay (Timer has not started yet) */}
      {session.status === "ready" && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-[#121215] border border-[#27272a] rounded-xl p-6 text-center space-y-5 shadow-2xl">
            <div className="w-12 h-12 rounded-full bg-indigo-950/80 border border-indigo-700/80 flex items-center justify-center mx-auto text-indigo-400">
              <CheckCircle className="w-6 h-6" />
            </div>
            <div className="space-y-1.5">
              <h2 className="text-xl font-bold text-zinc-100">Problem Validated & Ready</h2>
              <p className="text-xs text-zinc-400 leading-relaxed">
                The problem has passed all differential verification tests in the sandbox.
                Your 20-minute authoritative timer will begin once you click below.
              </p>
            </div>
            <button
              onClick={onBegin}
              className="w-full py-2.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-colors shadow-lg shadow-indigo-600/30"
            >
              Begin Interview
            </button>
          </div>
        </div>
      )}

      {/* Header Bar */}
      <header className="h-14 border-b border-[#27272a] bg-[#0c0c0f] px-4 flex items-center justify-between shrink-0">
        {/* Left: Stage Progress */}
        <div className="flex items-center space-x-3">
          <div className="text-xs font-semibold text-zinc-300 font-mono">
            STAGE {session.stage}/6:
          </div>
          <div className="flex items-center space-x-1.5">
            {STAGE_NAMES.map((name, idx) => {
              const stageNum = idx + 1;
              const isCurrent = session.stage === stageNum;
              const isPassed = session.stage > stageNum;
              return (
                <div
                  key={stageNum}
                  className={`text-[11px] px-2.5 py-1 rounded font-medium flex items-center space-x-1 transition-colors ${
                    isCurrent
                      ? "bg-indigo-950/80 border border-indigo-700 text-indigo-300"
                      : isPassed
                      ? "bg-zinc-900 border border-zinc-800 text-zinc-400"
                      : "text-zinc-600"
                  }`}
                >
                  <span>{stageNum}. {name}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Center: Authoritative Timer */}
        <div className="flex items-center space-x-2">
          <Timer
            remainingMs={session.remaining_ms}
            status={session.status}
            lastResumedAt={session.last_resumed_at}
            onSyncRequest={onSyncTimer}
          />
          {session.status === "running" && (
            <button
              onClick={onPause}
              title="Pause interview"
              className="p-1.5 rounded bg-[#18181c] hover:bg-[#222228] border border-[#27272a] text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              <Pause className="w-4 h-4" />
            </button>
          )}
          {session.status === "paused" && (
            <button
              onClick={onResume}
              title="Resume interview"
              className="p-1.5 rounded bg-emerald-950/60 hover:bg-emerald-900/60 border border-emerald-800 text-emerald-400 transition-colors"
            >
              <Play className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Right: Stage Control & Actions */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowResetModal(true)}
            title="Reset attempt"
            className="p-1.5 rounded bg-[#18181c] hover:bg-[#222228] border border-[#27272a] text-zinc-400 hover:text-red-400 transition-colors text-xs flex items-center space-x-1"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset</span>
          </button>

          {session.stage < 6 ? (
            <button
              onClick={onNextStage}
              className="px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs flex items-center space-x-1.5 transition-colors"
            >
              <span>Next Stage</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              onClick={() => setShowSubmitModal(true)}
              className="px-3.5 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs flex items-center space-x-1.5 transition-colors"
            >
              <span>Submit Interview</span>
              <Send className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </header>

      {/* Main 3-Panel Workspace */}
      <div className="flex-1 grid grid-cols-12 gap-2 p-2 overflow-hidden">
        {/* Left: Problem Statement & Constraints (3 cols) */}
        <div className="col-span-3 h-full overflow-hidden p-3 rounded-lg bg-[#0e0e11] border border-[#27272a]">
          <ProblemPanel problem={session.problem} stage={session.stage} />
        </div>

        {/* Center: Stage Notes & Code Editor (6 cols) */}
        <div className="col-span-6 h-full flex flex-col space-y-2 overflow-hidden">
          {/* Switch tabs between Notes and Code */}
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center space-x-2 text-xs">
              <button
                onClick={() => setCenterView("notes")}
                className={`px-3 py-1 rounded font-medium flex items-center space-x-1.5 transition-colors ${
                  centerView === "notes"
                    ? "bg-[#18181c] text-indigo-300 border border-indigo-900/40"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Stage Notes</span>
              </button>
              <button
                onClick={() => setCenterView("code")}
                className={`px-3 py-1 rounded font-medium flex items-center space-x-1.5 transition-colors ${
                  centerView === "code"
                    ? "bg-[#18181c] text-indigo-300 border border-indigo-900/40"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                <Code2 className="w-3.5 h-3.5" />
                <span>Code Editor</span>
                {session.stage >= 6 && (
                  <span className="text-[10px] px-1 rounded bg-indigo-950 text-indigo-400 border border-indigo-800">
                    STAGE 6
                  </span>
                )}
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-hidden">
            {centerView === "notes" ? (
              <NotesEditor
                currentStage={session.stage}
                notes={session.notes}
                onSaveNotes={onSaveNotes}
              />
            ) : (
              <CodeEditor
                initialCode={session.code}
                onCodeChange={onCodeChange}
                onRunCode={onRunCode}
                isRunning={isRunningCode}
                rateLimitSecondsLeft={rateLimitSecondsLeft}
              />
            )}
          </div>
        </div>

        {/* Right: Interviewer Dialogue (3 cols) */}
        <div className="col-span-3 h-full overflow-hidden">
          <InterviewerPanel
            stage={session.stage}
            chatLog={chatLog}
            onSendMessage={onSendMessage}
            isSending={isSendingMessage}
          />
        </div>
      </div>

      {/* Reset Confirmation Modal */}
      {showResetModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="max-w-sm w-full bg-[#121215] border border-[#27272a] rounded-lg p-5 space-y-4">
            <div className="flex items-center space-x-2 text-amber-400 font-semibold text-sm">
              <AlertTriangle className="w-4 h-4" />
              <span>Abandon Current Attempt?</span>
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Resetting will abandon this attempt (marking it abandoned in history). You will be returned to the setup screen to launch a fresh session.
            </p>
            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                onClick={() => setShowResetModal(false)}
                className="px-3 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-300"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  setShowResetModal(false);
                  await onReset();
                }}
                className="px-3 py-1.5 rounded bg-red-600 hover:bg-red-500 text-xs text-white font-medium"
              >
                Confirm Reset
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Submit Confirmation Modal */}
      {showSubmitModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="max-w-sm w-full bg-[#121215] border border-[#27272a] rounded-lg p-5 space-y-4">
            <div className="flex items-center space-x-2 text-indigo-400 font-semibold text-sm">
              <Send className="w-4 h-4" />
              <span>Submit & End Interview?</span>
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">
              This will execute hidden evaluation test cases once in the sandbox and generate your final evaluation report with 10 scored dimensions and hiring verdict.
            </p>
            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                onClick={() => setShowSubmitModal(false)}
                className="px-3 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-300"
              >
                Continue Coding
              </button>
              <button
                onClick={async () => {
                  setShowSubmitModal(false);
                  await onSubmit();
                }}
                disabled={isSubmitting}
                className="px-3.5 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-xs text-white font-medium disabled:opacity-50"
              >
                {isSubmitting ? "Evaluating..." : "Submit Solution"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
