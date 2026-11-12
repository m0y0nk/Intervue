import {
  ChatMessage,
  FinalEvaluationReport,
  InterviewConfig,
  RunCodeResponse,
  SessionCreatePayload,
  SessionState,
  SubmitResponse,
} from "../types";

const BASE_URL = "/api";

export const api = {
  async createSession(
    payload: SessionCreatePayload | Partial<InterviewConfig>
  ): Promise<{ session_id: string; status: string }> {
    const body = "config" in payload ? payload : { config: payload };
    const res = await fetch(`${BASE_URL}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getSession(sessionId: string): Promise<SessionState> {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async beginSession(sessionId: string): Promise<SessionState> {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/begin`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async pauseSession(sessionId: string): Promise<SessionState> {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/pause`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async resumeSession(sessionId: string): Promise<SessionState> {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/resume`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async resetSession(sessionId: string): Promise<{ status: string; session_id: string }> {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/reset`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async nextStage(sessionId: string): Promise<SessionState> {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/stage/next`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async updateNotes(sessionId: string, stage: number, content: string): Promise<void> {
    await fetch(`${BASE_URL}/sessions/${sessionId}/notes`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stage, content }),
    });
  },

  async updateCode(sessionId: string, code: string, language: string = "python"): Promise<void> {
    await fetch(`${BASE_URL}/sessions/${sessionId}/code`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, language }),
    });
  },

  async getChat(sessionId: string): Promise<ChatMessage[]> {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/chat`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async sendInterviewerMessage(
    sessionId: string,
    message: string
  ): Promise<{ message: string; stage: number }> {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/interviewer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (!res.ok) {
      if (res.status === 409) {
        throw new Error("Interviewer is not available in the Coding stage.");
      }
      throw new Error(await res.text());
    }
    return res.json();
  },

  async runCode(sessionId: string): Promise<RunCodeResponse> {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/run`, { method: "POST" });
    if (!res.ok) {
      const errText = await res.text();
      try {
        const errJson = JSON.parse(errText);
        throw new Error(errJson.detail || "Run code failed");
      } catch {
        throw new Error(errText || "Run code failed");
      }
    }
    return res.json();
  },

  async submitCode(sessionId: string): Promise<SubmitResponse> {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/submit`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getReport(sessionId: string): Promise<FinalEvaluationReport> {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/report`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getDashboard(): Promise<any> {
    const res = await fetch(`${BASE_URL}/dashboard`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
};
