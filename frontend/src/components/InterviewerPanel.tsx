import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Ban } from "lucide-react";
import { ChatMessage } from "../types";

interface InterviewerPanelProps {
  stage: number;
  chatLog: ChatMessage[];
  onSendMessage: (msg: string) => Promise<void>;
  isSending: boolean;
}

export const InterviewerPanel: React.FC<InterviewerPanelProps> = ({
  stage,
  chatLog,
  onSendMessage,
  isSending,
}) => {
  const [inputMsg, setInputMsg] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatLog]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMsg.trim() || isSending || stage >= 6) return;
    const msg = inputMsg.trim();
    setInputMsg("");
    await onSendMessage(msg);
  };

  const isCodingStage = stage >= 6;

  return (
    <div className="flex flex-col h-full bg-[#121215] border border-[#27272a] rounded-lg overflow-hidden">
      {/* Header */}
      <div className="px-3.5 py-2.5 border-b border-[#27272a] bg-[#0e0e11] flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Bot className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-semibold text-zinc-200">Interviewer Dialogue</span>
        </div>
        <span className="text-[11px] text-zinc-500 font-mono">
          {isCodingStage ? "Offline in Stage 6" : "Stage Active"}
        </span>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-3.5 space-y-3.5 text-xs">
        {chatLog.length === 0 ? (
          <div className="text-zinc-500 text-center py-6 leading-relaxed">
            Begin the interview by clarifying any ambiguities or discussing assumptions with the interviewer.
          </div>
        ) : (
          chatLog.map((m, idx) => (
            <div
              key={idx}
              className={`flex flex-col ${
                m.sender === "candidate" ? "items-end" : "items-start"
              }`}
            >
              <div className="flex items-center space-x-1.5 mb-1 text-[11px] text-zinc-500">
                {m.sender === "candidate" ? (
                  <>
                    <span>You</span>
                    <User className="w-3 h-3 text-zinc-400" />
                  </>
                ) : (
                  <>
                    <Bot className="w-3 h-3 text-indigo-400" />
                    <span>Interviewer</span>
                  </>
                )}
                <span className="text-[10px] text-zinc-600">
                  (Stage {m.stage})
                </span>
              </div>
              <div
                className={`max-w-[90%] p-2.5 rounded-lg leading-relaxed ${
                  m.sender === "candidate"
                    ? "bg-[#1f1f23] text-zinc-100 border border-[#2e2e34]"
                    : "bg-[#0d0d10] text-zinc-200 border border-[#27272a]"
                }`}
              >
                {m.message}
              </div>
            </div>
          ))
        )}
        <div ref={endRef} />
      </div>

      {/* Input or Disabled Notice */}
      <div className="p-3 border-t border-[#27272a] bg-[#0e0e11]">
        {isCodingStage ? (
          <div className="flex items-center space-x-2 p-2 rounded bg-zinc-900/60 border border-zinc-800 text-zinc-500 text-xs">
            <Ban className="w-4 h-4 text-zinc-500 shrink-0" />
            <span>
              Interviewer dialogue is paused during Coding (Stage 6). Focus on writing and running your code.
            </span>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex items-center space-x-2">
            <input
              type="text"
              value={inputMsg}
              onChange={(e) => setInputMsg(e.target.value)}
              placeholder="Ask clarifying questions or present your reasoning..."
              disabled={isSending}
              className="flex-1 bg-[#141418] border border-[#27272a] rounded-md px-3 py-1.5 text-xs text-zinc-100 placeholder:text-zinc-600 outline-none focus:border-indigo-500 transition-colors"
            />
            <button
              type="submit"
              disabled={isSending || !inputMsg.trim()}
              className="p-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white transition-colors"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
