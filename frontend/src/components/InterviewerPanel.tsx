import React, { useState, useRef, useEffect } from "react";
import { ChatMessage } from "../types";

interface InterviewerPanelProps {
  stage: number;
  chatLog: ChatMessage[];
  onSendMessage: (msg: string) => Promise<void>;
  isSending: boolean;
  hasError?: boolean;
  onRetry?: () => void;
}

export const InterviewerPanel: React.FC<InterviewerPanelProps> = ({
  stage,
  chatLog,
  onSendMessage,
  isSending,
  hasError = false,
  onRetry,
}) => {
  const [inputMsg, setInputMsg] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatLog, isSending]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMsg.trim() || isSending || stage >= 6) return;
    const msg = inputMsg.trim();
    setInputMsg("");
    await onSendMessage(msg);
  };

  const isCodingStage = stage >= 6;

  return (
    <div className="flex flex-col h-full bg-[#1A1815] border border-[#332E28] rounded-[10px] overflow-hidden text-[#ECE6DA]">
      {/* Pane Header */}
      <div className="px-4 py-3 border-b border-[#332E28] flex items-center justify-between text-13">
        <span className="font-medium text-[#ECE6DA]">Interviewer dialogue</span>
        <span className="text-[12px] text-[#A59E91]">
          {isCodingStage ? "Offline in Stage 6" : "Stage active"}
        </span>
      </div>

      {/* Transcript Log (Left-aligned text with hairline divider between turns) */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-13">
        {chatLog.length === 0 ? (
          <div className="text-[#A59E91] text-center py-10 leading-relaxed text-13">
            Begin the interview by clarifying problem requirements or stating initial assumptions.
          </div>
        ) : (
          chatLog.map((m, idx) => (
            <div key={idx} className="space-y-1 pb-3 border-b border-[#332E28]/60 last:border-b-0">
              <div className="flex items-baseline space-x-2">
                <span className="text-[11px] font-mono text-[#A59E91]">
                  {m.sender === "candidate" ? "You" : "Interviewer"}
                </span>
                <span className="text-[10px] font-mono text-[#6B645A]">
                  Stage {m.stage}
                </span>
              </div>
              <div className="text-[#ECE6DA] leading-relaxed whitespace-pre-wrap">
                {m.message}
              </div>
            </div>
          ))
        )}

        {/* State: Interviewer Thinking */}
        {isSending && (
          <div className="space-y-1 pb-2">
            <div className="text-[11px] font-mono text-[#A59E91]">Interviewer</div>
            <div className="text-13 text-[#A59E91] italic">
              Reviewing your response...
            </div>
          </div>
        )}

        {/* State: Interviewer Error with Retry */}
        {hasError && onRetry && (
          <div className="p-3 rounded-[4px] bg-[#12110F] border border-[#FF7A6E] text-13 text-[#FF7A6E] flex items-center justify-between">
            <span>Interviewer connection paused.</span>
            <button
              onClick={onRetry}
              className="text-[12px] text-[#ECE6DA] underline hover:text-[#F5B83D] ml-2"
            >
              Retry
            </button>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {/* Transcript Input Pinned to Bottom */}
      <div className="p-3 border-t border-[#332E28] bg-[#1A1815]">
        {isCodingStage ? (
          <div className="text-[12px] text-[#A59E91] py-1 text-center">
            Dialogue is paused during Coding (Stage 6). Focus on implementing and testing your solution.
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex space-x-2">
            <input
              type="text"
              value={inputMsg}
              onChange={(e) => setInputMsg(e.target.value)}
              disabled={isSending}
              placeholder="Type your response and press Enter..."
              className="flex-1 bg-[#12110F] border border-[#6B645A] rounded-[4px] px-3 py-2 text-13 text-[#ECE6DA] placeholder-[#6B645A] outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isSending || !inputMsg.trim()}
              className="px-3.5 py-2 rounded-[4px] bg-[#221F1B] hover:bg-[#332E28] border border-[#6B645A] text-[#ECE6DA] text-13 disabled:opacity-40 transition-colors shrink-0"
            >
              Send
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
