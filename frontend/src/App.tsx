import React, { useState, useEffect, useCallback } from "react";
import { api } from "./services/api";
import {
  ChatMessage,
  FinalEvaluationReport,
  InterviewConfig,
  RunCodeResponse,
  SessionCreatePayload,
  SessionState,
} from "./types";
import { SetupPage } from "./pages/SetupPage";
import { WorkspacePage } from "./pages/WorkspacePage";
import { DashboardPage, RevisionCandidate } from "./pages/DashboardPage";
import { EvaluationReport } from "./components/EvaluationReport";

export function App() {
  const [currentView, setCurrentView] = useState<"setup" | "dashboard" | "workspace" | "report">("setup");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [session, setSession] = useState<SessionState | null>(null);
  const [chatLog, setChatLog] = useState<ChatMessage[]>([]);
  const [finalReport, setFinalReport] = useState<FinalEvaluationReport | null>(null);

  const [isGenerating, setIsGenerating] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [isRunningCode, setIsRunningCode] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [rateLimitSecondsLeft, setRateLimitSecondsLeft] = useState(0);

  // Restore session on load if saved
  useEffect(() => {
    const savedId = localStorage.getItem("intervue_active_session");
    if (savedId) {
      api.getSession(savedId)
        .then((s) => {
          if (s.status === "finished") {
            api.getReport(savedId).then((rep) => {
              setFinalReport(rep);
              setCurrentView("report");
            }).catch(() => {
              localStorage.removeItem("intervue_active_session");
            });
          } else if (s.status !== "abandoned") {
            setSessionId(savedId);
            setSession(s);
            setCurrentView("workspace");
            api.getChat(savedId).then(setChatLog).catch(() => {});
          } else {
            localStorage.removeItem("intervue_active_session");
          }
        })
        .catch(() => {
          localStorage.removeItem("intervue_active_session");
        });
    }
  }, []);

  // Rate limiter ticker
  useEffect(() => {
    if (rateLimitSecondsLeft <= 0) return;
    const t = setInterval(() => {
      setRateLimitSecondsLeft((prev) => Math.max(0, prev - 0.2));
    }, 200);
    return () => clearInterval(t);
  }, [rateLimitSecondsLeft]);

  // Polling during problem generation
  useEffect(() => {
    if (!sessionId || !isGenerating) return;

    const interval = setInterval(async () => {
      try {
        const state = await api.getSession(sessionId);
        if (state.status === "ready" || state.status === "running") {
          setIsGenerating(false);
          setSession(state);
          setCurrentView("workspace");
          clearInterval(interval);
        } else if (state.status === "abandoned") {
          setIsGenerating(false);
          setStatusMessage(state.code ? `Generation failed: ${state.code}` : "Problem generation failed or unsupported. Please try again.");
          clearInterval(interval);
        }
      } catch (e) {
        console.error("Polling error", e);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [sessionId, isGenerating]);

  // Start new session
  const handleStartSession = async (payload: SessionCreatePayload | Partial<InterviewConfig>) => {
    setIsGenerating(true);
    setStatusMessage("Validating problem in sandbox differential pipeline...");
    try {
      const res = await api.createSession(payload);
      setSessionId(res.session_id);
      localStorage.setItem("intervue_active_session", res.session_id);
    } catch (e: any) {
      setIsGenerating(false);
      // Re-throw so SetupPage can display the 422 validation error inline
      throw e;
    }
  };

  // Begin interview (starts timer)
  const handleBegin = async () => {
    if (!sessionId) return;
    const s = await api.beginSession(sessionId);
    setSession(s);
  };

  // Pause
  const handlePause = async () => {
    if (!sessionId) return;
    const s = await api.pauseSession(sessionId);
    setSession(s);
  };

  // Resume
  const handleResume = async () => {
    if (!sessionId) return;
    const s = await api.resumeSession(sessionId);
    setSession(s);
  };

  // Reset
  const handleReset = async () => {
    if (!sessionId) return;
    await api.resetSession(sessionId);
    localStorage.removeItem("intervue_active_session");
    setSessionId(null);
    setSession(null);
    setChatLog([]);
    setCurrentView("setup");
  };

  // Next Stage
  const handleNextStage = async () => {
    if (!sessionId) return;
    try {
      const s = await api.nextStage(sessionId);
      setSession(s);
      const chats = await api.getChat(sessionId);
      setChatLog(chats);
    } catch (e: any) {
      alert(e.message);
    }
  };

  // Save notes
  const handleSaveNotes = useCallback(async (stage: number, content: string) => {
    setSession((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        notes: {
          ...prev.notes,
          [String(stage)]: content,
        },
      };
    });
    if (!sessionId) return;
    await api.updateNotes(sessionId, stage, content);
  }, [sessionId]);

  // Save code
  const handleCodeChange = useCallback(async (code: string) => {
    setSession((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        code: code,
      };
    });
    if (!sessionId) return;
    await api.updateCode(sessionId, code);
  }, [sessionId]);

  // Run code
  const handleRunCode = async (): Promise<RunCodeResponse> => {
    if (!sessionId) throw new Error("No active session");
    setIsRunningCode(true);
    try {
      const res = await api.runCode(sessionId);
      setRateLimitSecondsLeft(5.0);
      return res;
    } finally {
      setIsRunningCode(false);
    }
  };

  // Submit interview
  const handleSubmit = async () => {
    if (!sessionId) return;
    setIsSubmitting(true);
    try {
      await api.submitCode(sessionId);
      const rep = await api.getReport(sessionId);
      setFinalReport(rep);
      setCurrentView("report");
    } catch (e: any) {
      alert(`Submission failed: ${e.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Send message to interviewer
  const handleSendMessage = async (msg: string) => {
    if (!sessionId) return;
    setIsSendingMessage(true);
    // Optimistic user chat update
    const candidateMsg: ChatMessage = {
      sender: "candidate",
      message: msg,
      stage: session?.stage || 1,
      timestamp: new Date().toISOString(),
    };
    setChatLog((prev) => [...prev, candidateMsg]);

    try {
      const res = await api.sendInterviewerMessage(sessionId, msg);
      const interviewerMsg: ChatMessage = {
        sender: "interviewer",
        message: res.message,
        stage: res.stage,
        timestamp: new Date().toISOString(),
      };
      setChatLog((prev) => [...prev, interviewerMsg]);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setIsSendingMessage(false);
    }
  };

  // Sync timer
  const handleSyncTimer = useCallback(async () => {
    if (!sessionId) return;
    try {
      const s = await api.getSession(sessionId);
      if (s.status === "finished") {
        const rep = await api.getReport(sessionId);
        setFinalReport(rep);
        setCurrentView("report");
      } else {
        setSession(s);
      }
    } catch (e) {
      console.error("Timer sync failed", e);
    }
  }, [sessionId]);

  // Start fresh after report
  const handleNewInterview = () => {
    localStorage.removeItem("intervue_active_session");
    setSessionId(null);
    setSession(null);
    setChatLog([]);
    setFinalReport(null);
    setCurrentView("setup");
  };

  // Start revision interview directly from Dashboard
  const handleStartRevision = async (candidate: RevisionCandidate) => {
    setCurrentView("setup");
    await handleStartSession({
      config: {
        mode: "revision",
        category: (candidate.category as any) || "arrays_hashing",
        source: (candidate.source as any) || "random_dsa",
        difficulty: (candidate.difficulty as any) || "medium",
      },
    });
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100">
      {currentView === "setup" && (
        <SetupPage
          onStartSession={handleStartSession}
          isGenerating={isGenerating}
          statusMessage={statusMessage}
          onViewDashboard={() => setCurrentView("dashboard")}
        />
      )}

      {currentView === "dashboard" && (
        <DashboardPage
          onNewInterview={handleNewInterview}
          onStartRevision={handleStartRevision}
        />
      )}

      {currentView === "workspace" && session && (
        <WorkspacePage
          session={session}
          chatLog={chatLog}
          onBegin={handleBegin}
          onPause={handlePause}
          onResume={handleResume}
          onReset={handleReset}
          onNextStage={handleNextStage}
          onSaveNotes={handleSaveNotes}
          onCodeChange={handleCodeChange}
          onRunCode={handleRunCode}
          onSubmit={handleSubmit}
          onSendMessage={handleSendMessage}
          onSyncTimer={handleSyncTimer}
          isSendingMessage={isSendingMessage}
          isRunningCode={isRunningCode}
          isSubmitting={isSubmitting}
          rateLimitSecondsLeft={rateLimitSecondsLeft}
        />
      )}

      {currentView === "report" && finalReport && (
        <EvaluationReport
          report={finalReport}
          onNewInterview={handleNewInterview}
          onViewDashboard={() => setCurrentView("dashboard")}
        />
      )}
    </div>
  );
}

export default App;
