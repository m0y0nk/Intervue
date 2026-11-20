import React, { useState, useEffect } from "react";
import { ChatMessage, RunCodeResponse, SessionState } from "../types";
import { StageRail } from "../components/StageRail";
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
  const [showMockModal, setShowMockModal] = useState<boolean>(Boolean(session.is_mock));

  useEffect(() => {
    if (session.is_mock) {
      setShowMockModal(true);
    }
  }, [session.is_mock]);
  const [centerView, setCenterView] = useState<"notes" | "code">(
    session.stage >= 6 ? "code" : "notes"
  );
  const [mobileTab, setMobileTab] = useState<"problem" | "work" | "dialogue">("work");

  // Local authoritative timer countdown
  const [displayMs, setDisplayMs] = useState(session.remaining_ms);

  useEffect(() => {
    setDisplayMs(session.remaining_ms);
  }, [session.remaining_ms]);

  useEffect(() => {
    if (session.status !== "running") return;
    const interval = setInterval(() => {
      setDisplayMs((prev) => Math.max(0, prev - 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [session.status]);

  // Periodic resync every 15s
  useEffect(() => {
    if (session.status !== "running") return;
    const syncInterval = setInterval(() => {
      onSyncTimer();
    }, 15000);
    return () => clearInterval(syncInterval);
  }, [session.status, onSyncTimer]);

  // Automatically switch to code editor on stage 6
  useEffect(() => {
    if (session.stage >= 6) {
      setCenterView("code");
    }
  }, [session.stage]);

  const totalSeconds = Math.floor(displayMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  const formattedTime = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  const isWarning2 = totalSeconds <= 120 && totalSeconds > 0;
  const totalDurationMs = (session.config.duration || (session.problem?.time_limit_minutes ? session.problem.time_limit_minutes * 60 : 1200)) * 1000;
  const elapsedRatio = Math.max(0, Math.min(1, (totalDurationMs - displayMs) / totalDurationMs));
  const totalMinutes = Math.round(totalDurationMs / 60000);

  return (
    <div className="flex flex-col h-screen bg-[#12110F] text-[#ECE6DA] overflow-hidden font-sans select-none">
      {/* Ready Screen Overlay */}
      {session.status === "ready" && (
        <div className="fixed inset-0 bg-[#12110F]/90 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-[#1A1815] border border-[#332E28] rounded-[10px] p-6 space-y-5 text-center">
            <div className="space-y-2">
              <h2 className="font-serif text-[28px] font-normal text-[#ECE6DA]">Problem verified & ready</h2>
              <p className="text-[13px] text-[#A59E91] leading-relaxed">
                The problem statement and hidden tests have been validated in the isolated sandbox.
                Your {totalMinutes}-minute timed session will start once you begin.
              </p>
            </div>
            <button
              onClick={onBegin}
              className="w-full py-2.5 rounded-[4px] bg-[#F5B83D] hover:bg-[#F5B83D]/90 text-[#12110F] font-medium text-[13px] transition-colors"
            >
              Start {totalMinutes}-minute interview
            </button>
          </div>
        </div>
      )}

      {/* Top Bar with Stage Rail & Controls */}
      <header className="h-14 border-b border-[#332E28] bg-[#1A1815] px-4 flex items-center justify-between shrink-0 gap-4">
        {/* Stage Rail with embedded timer */}
        <div className="flex-1 max-w-2xl">
          <StageRail
            currentStage={session.stage}
            formattedTime={formattedTime}
            progressRatio={elapsedRatio}
            isWarning={isWarning2}
            mode="topbar"
          />
        </div>

        {/* Top Controls */}
        <div className="flex items-center space-x-3 shrink-0">
          {session.is_mock && (
            <button
              onClick={() => setShowMockModal(true)}
              title="Click to view mock fallback details and retry options"
              className="px-2.5 py-1 rounded-[4px] bg-[#F5B83D]/15 border border-[#F5B83D]/40 text-[#F5B83D] text-[12px] font-mono hover:bg-[#F5B83D]/25 transition-colors flex items-center space-x-1.5"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-[#F5B83D] animate-pulse" />
              <span>Mock Fallback</span>
            </button>
          )}

          {session.status === "running" && (
            <button
              onClick={onPause}
              className="text-[13px] text-[#A59E91] hover:text-[#ECE6DA] px-2 py-1 transition-colors"
            >
              Pause
            </button>
          )}

          {session.status === "paused" && (
            <button
              onClick={onResume}
              className="px-3 py-1 rounded-[4px] bg-[#F5B83D] text-[#12110F] font-medium text-[13px] hover:bg-[#F5B83D]/90 transition-colors"
            >
              Resume
            </button>
          )}

          <button
            onClick={() => setShowResetModal(true)}
            className="text-[13px] text-[#A59E91] hover:text-[#FF7A6E] px-2 py-1 transition-colors"
          >
            Reset
          </button>

          {session.stage < 6 ? (
            <button
              onClick={onNextStage}
              className="px-3.5 py-1.5 rounded-[4px] bg-[#F5B83D] hover:bg-[#F5B83D]/90 text-[#12110F] font-medium text-[13px] transition-colors"
            >
              Next stage
            </button>
          ) : (
            <button
              onClick={() => setShowSubmitModal(true)}
              className="px-3.5 py-1.5 rounded-[4px] bg-[#F5B83D] hover:bg-[#F5B83D]/90 text-[#12110F] font-medium text-[13px] transition-colors"
            >
              Submit interview
            </button>
          )}
        </div>
      </header>

      {/* Mobile Tab Switcher */}
      <div className="md:hidden border-b border-[#332E28] bg-[#1A1815] px-2 py-1.5 flex items-center justify-around text-[13px]">
        <button
          onClick={() => setMobileTab("problem")}
          className={`px-3 py-1 rounded-[4px] font-medium ${
            mobileTab === "problem" ? "bg-[#221F1B] text-[#ECE6DA]" : "text-[#A59E91]"
          }`}
        >
          Problem
        </button>
        <button
          onClick={() => setMobileTab("work")}
          className={`px-3 py-1 rounded-[4px] font-medium ${
            mobileTab === "work" ? "bg-[#221F1B] text-[#ECE6DA]" : "text-[#A59E91]"
          }`}
        >
          Work area
        </button>
        <button
          onClick={() => setMobileTab("dialogue")}
          className={`px-3 py-1 rounded-[4px] font-medium ${
            mobileTab === "dialogue" ? "bg-[#221F1B] text-[#ECE6DA]" : "text-[#A59E91]"
          }`}
        >
          Interviewer
        </button>
      </div>

      {/* Main 3-Pane Workspace (28% / 44% / 28%) */}
      <div className="flex-1 flex overflow-hidden p-2 gap-2">

        {/* Left Pane: Problem Statement (28%) */}
        <div
          className={`w-full md:w-[28%] md:min-w-[280px] h-full overflow-hidden bg-[#1A1815] border border-[#332E28] rounded-[10px] p-4 flex flex-col relative ${
            mobileTab === "problem" ? "flex" : "hidden md:flex"
          }`}
        >
          <ProblemPanel problem={session.problem} stage={session.stage} />
          {/* Dim problem pane when paused — still readable, not interactive block */}
          {session.status === "paused" && (
            <div className="absolute inset-0 rounded-[10px] bg-[#12110F]/60 pointer-events-none" />
          )}
        </div>

        {/* Center Pane: Work Area (44%) */}
        <div
          className={`w-full md:w-[44%] md:min-w-[400px] h-full overflow-hidden bg-[#1A1815] border border-[#332E28] rounded-[10px] flex flex-col ${
            mobileTab === "work" ? "flex" : "hidden md:flex"
          }`}
        >
          {/* Work Area Header Tab Row — always accessible */}
          <div className="h-10 border-b border-[#332E28] px-3 flex items-center justify-between shrink-0 bg-[#1A1815]">
            <div className="flex items-center space-x-1">
              <button
                onClick={() => setCenterView("notes")}
                className={`px-3 py-1.5 text-[13px] rounded-[4px] font-medium transition-colors ${
                  centerView === "notes"
                    ? "bg-[#221F1B] text-[#ECE6DA] border border-[#332E28]"
                    : "text-[#A59E91] hover:text-[#ECE6DA]"
                }`}
              >
                Stage notes
              </button>
              <button
                onClick={() => setCenterView("code")}
                className={`px-3 py-1.5 text-[13px] rounded-[4px] font-medium transition-colors flex items-center space-x-1.5 ${
                  centerView === "code"
                    ? "bg-[#221F1B] text-[#ECE6DA] border border-[#332E28]"
                    : "text-[#A59E91] hover:text-[#ECE6DA]"
                }`}
              >
                <span>Code editor</span>
                {session.stage >= 6 && (
                  <span className="text-[10px] px-1 py-0.2 rounded-[2px] bg-[#332E28] text-[#ECE6DA] font-mono">
                    Stage 6
                  </span>
                )}
              </button>
            </div>
          </div>

          {/* Tab View Container */}
          <div className="flex-1 overflow-hidden relative">
            {/* Stage notes — always interactive, never dimmed */}
            <div className={`h-full ${centerView === "notes" ? "block" : "hidden"}`}>
              <NotesEditor
                currentStage={session.stage}
                notes={session.notes}
                onSaveNotes={onSaveNotes}
                stageTimeBudgets={session.stage_time_budgets || session.problem?.stage_time_budgets}
              />
            </div>
            {/* Code editor — dimmed when paused */}
            <div className={`h-full relative ${centerView === "code" ? "block" : "hidden"}`}>
              <CodeEditor
                initialCode={session.code}
                language={session.language || "python"}
                onCodeChange={onCodeChange}
                onRunCode={onRunCode}
                isRunning={isRunningCode}
                rateLimitSecondsLeft={rateLimitSecondsLeft}
              />
              {session.status === "paused" && (
                <div className="absolute inset-0 bg-[#12110F]/75 flex items-center justify-center">
                  <p className="text-[13px] text-[#A59E91] font-mono">Paused</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Pane: Interviewer Dialogue (28%) */}
        <div
          className={`w-full md:w-[28%] md:min-w-[280px] h-full overflow-hidden bg-[#1A1815] border border-[#332E28] rounded-[10px] flex flex-col relative ${
            mobileTab === "dialogue" ? "flex" : "hidden md:flex"
          }`}
        >
          <InterviewerPanel
            stage={session.stage}
            chatLog={chatLog}
            onSendMessage={onSendMessage}
            isSending={isSendingMessage}
          />
          {/* Paused overlay — covers dialogue, shows resume */}
          {session.status === "paused" && (
            <div className="absolute inset-0 rounded-[10px] bg-[#12110F]/85 flex flex-col items-center justify-center space-y-4">
              <span className="font-serif text-[28px] text-[#ECE6DA]">Interview paused</span>
              <p className="text-[13px] text-[#A59E91] font-mono">
                Timer stopped at {formattedTime}
              </p>
              <button
                onClick={onResume}
                className="px-5 py-2 rounded-[4px] bg-[#F5B83D] text-[#12110F] font-medium text-[13px] hover:bg-[#F5B83D]/90 transition-colors"
              >
                Resume interview
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Reset Confirmation Modal */}
      {showResetModal && (
        <div className="fixed inset-0 bg-[#12110F]/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="max-w-sm w-full bg-[#1A1815] border border-[#332E28] rounded-[10px] p-5 space-y-4">
            <div className="space-y-1.5">
              <h3 className="font-serif text-[18px] text-[#ECE6DA]">Abandon current session?</h3>
              <p className="text-[13px] text-[#A59E91] leading-relaxed">
                Resetting will abandon this interview attempt and return you to the setup briefing.
              </p>
            </div>
            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                onClick={() => setShowResetModal(false)}
                className="text-[13px] text-[#A59E91] hover:text-[#ECE6DA] px-2 py-1"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  setShowResetModal(false);
                  await onReset();
                }}
                className="px-3 py-1.5 rounded-[4px] bg-[#FF7A6E] text-[#12110F] text-[13px] font-medium hover:bg-[#FF7A6E]/90 transition-colors"
              >
                Confirm reset
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Submit Confirmation Modal */}
      {showSubmitModal && (
        <div className="fixed inset-0 bg-[#12110F]/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="max-w-sm w-full bg-[#1A1815] border border-[#332E28] rounded-[10px] p-5 space-y-4">
            <div className="space-y-1.5">
              <h3 className="font-serif text-[18px] text-[#ECE6DA]">Submit solution & end interview?</h3>
              <p className="text-[13px] text-[#A59E91] leading-relaxed">
                This will execute hidden evaluation test cases in the sandbox and generate your final evaluation report with 10 anchored dimensions.
              </p>
            </div>
            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                onClick={() => setShowSubmitModal(false)}
                className="text-[13px] text-[#A59E91] hover:text-[#ECE6DA] px-2 py-1"
              >
                Continue coding
              </button>
              <button
                onClick={async () => {
                  setShowSubmitModal(false);
                  await onSubmit();
                }}
                disabled={isSubmitting}
                className="px-3.5 py-1.5 rounded-[4px] bg-[#F5B83D] hover:bg-[#F5B83D]/90 text-[#12110F] text-[13px] font-medium transition-colors disabled:opacity-50"
              >
                {isSubmitting ? "Evaluating..." : "Submit solution"}
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Mock Fallback Notice Modal */}
      {showMockModal && (
        <div className="fixed inset-0 bg-[#12110F]/85 backdrop-blur-sm z-[60] flex items-center justify-center p-4">
          <div className="max-w-lg w-full bg-[#1A1815] border border-[#332E28] rounded-[10px] p-6 space-y-5 shadow-2xl">
            {/* Header */}
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 rounded-[4px] bg-[#F5B83D]/15 border border-[#F5B83D]/40 text-[#F5B83D] text-[11px] font-mono uppercase tracking-wide">
                    Deterministic Mock
                  </span>
                  <span className="text-[12px] text-[#A59E91] font-mono">
                    Offline Fallback Active
                  </span>
                </div>
                <h3 className="font-serif text-[24px] text-[#ECE6DA] leading-tight">
                  Using fallback mock problem
                </h3>
              </div>
              <button
                onClick={() => setShowMockModal(false)}
                className="text-[#A59E91] hover:text-[#ECE6DA] p-1 text-[18px] leading-none"
                title="Dismiss"
              >
                ✕
              </button>
            </div>

            {/* Comparison block: Requested vs Loaded */}
            <div className="bg-[#221F1B] border border-[#332E28] rounded-[6px] p-3.5 space-y-2.5 text-[13px]">
              <div className="flex items-baseline justify-between">
                <span className="text-[#A59E91]">Requested problem:</span>
                <span className="text-[#ECE6DA] font-medium font-mono text-right truncate max-w-[260px]">
                  {session.requested_problem_summary || session.config.source}
                </span>
              </div>
              <div className="h-[1px] bg-[#332E28]" />
              <div className="flex items-baseline justify-between">
                <span className="text-[#A59E91]">Loaded mock problem:</span>
                <span className="text-[#F5B83D] font-medium font-mono text-right truncate max-w-[260px]">
                  {session.problem?.title || "Pair Sum Target"}
                </span>
              </div>
            </div>

            {/* Why it happened */}
            {session.mock_reason && (
              <div className="space-y-1.5">
                <span className="text-[12px] text-[#A59E91] font-medium uppercase tracking-wider">
                  Why this occurred
                </span>
                <p className="text-[12px] text-[#ECE6DA]/90 font-mono bg-[#12110F] border border-[#332E28] rounded-[4px] p-2.5 leading-relaxed break-words max-h-28 overflow-y-auto">
                  {session.mock_reason}
                </p>
              </div>
            )}

            {/* How to retry guide */}
            <div className="space-y-2">
              <span className="text-[12px] text-[#A59E91] font-medium uppercase tracking-wider">
                How to retry for your requested problem
              </span>
              <ul className="text-[13px] text-[#A59E91] space-y-1.5 list-disc list-inside leading-relaxed pl-1">
                {session.config.source === "leetcode" && (
                  <li>
                    <strong className="text-[#ECE6DA]">LeetCode lookup:</strong> Verify the problem number or slug (e.g. <code className="text-[#ECE6DA] bg-[#221F1B] px-1 rounded">1</code> or <code className="text-[#ECE6DA] bg-[#221F1B] px-1 rounded">two-sum</code>), or paste the full problem text with clear examples.
                  </li>
                )}
                {session.config.source === "custom" && (
                  <li>
                    <strong className="text-[#ECE6DA]">Custom problem:</strong> Provide a complete specification with clear argument types, return type, and visible test examples.
                  </li>
                )}
                <li>
                  <strong className="text-[#ECE6DA]">Execution runners:</strong> If validation failed in sandbox, ensure Docker runner images are built via <code className="text-[#ECE6DA] bg-[#221F1B] px-1 rounded">./build-runners.sh</code>.
                </li>
                <li>
                  <strong className="text-[#ECE6DA]">AI configuration:</strong> Verify your <code className="text-[#ECE6DA] bg-[#221F1B] px-1 rounded">GEMINI_API_KEY</code> in <code className="text-[#ECE6DA] bg-[#221F1B] px-1 rounded">.env</code> is valid and has active quota.
                </li>
              </ul>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end space-x-3 pt-2 border-t border-[#332E28]">
              <button
                onClick={() => setShowMockModal(false)}
                className="px-4 py-2 rounded-[4px] text-[13px] text-[#A59E91] hover:text-[#ECE6DA] transition-colors"
              >
                Practice with this mock
              </button>
              <button
                onClick={async () => {
                  setShowMockModal(false);
                  await onReset();
                }}
                className="px-4 py-2 rounded-[4px] bg-[#F5B83D] hover:bg-[#F5B83D]/90 text-[#12110F] text-[13px] font-medium transition-colors"
              >
                Retry requested problem
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
