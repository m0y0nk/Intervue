import React, { useEffect, useState } from "react";
import { Clock, AlertTriangle } from "lucide-react";

interface TimerProps {
  remainingMs: number;
  status: "generating" | "ready" | "running" | "paused" | "finished" | "abandoned";
  lastResumedAt?: string;
  onSyncRequest?: () => void;
}

export const Timer: React.FC<TimerProps> = ({
  remainingMs: initialRemainingMs,
  status,
  lastResumedAt,
  onSyncRequest,
}) => {
  const [displayMs, setDisplayMs] = useState(initialRemainingMs);

  useEffect(() => {
    setDisplayMs(initialRemainingMs);
  }, [initialRemainingMs]);

  useEffect(() => {
    if (status !== "running") return;

    const interval = setInterval(() => {
      setDisplayMs((prev) => {
        const next = Math.max(0, prev - 1000);
        return next;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [status]);

  // Periodic resync every 15s
  useEffect(() => {
    if (status !== "running") return;
    const syncInterval = setInterval(() => {
      onSyncRequest?.();
    }, 15000);
    return () => clearInterval(syncInterval);
  }, [status, onSyncRequest]);

  const totalSeconds = Math.floor(displayMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  const formattedTime = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

  const isWarning5 = totalSeconds <= 300 && totalSeconds > 120;
  const isWarning2 = totalSeconds <= 120 && totalSeconds > 0;

  return (
    <div className="flex items-center space-x-3 px-3 py-1.5 rounded-md bg-[#121215] border border-[#27272a] text-sm">
      <Clock
        className={`w-4 h-4 ${
          isWarning2
            ? "text-red-400 animate-pulse"
            : isWarning5
            ? "text-amber-400"
            : "text-zinc-400"
        }`}
      />
      <span
        className={`font-mono text-base font-semibold tracking-wider ${
          isWarning2
            ? "text-red-400 font-bold"
            : isWarning5
            ? "text-amber-300"
            : "text-zinc-100"
        }`}
      >
        {formattedTime}
      </span>
      {status === "paused" && (
        <span className="text-xs px-1.5 py-0.5 rounded bg-amber-950/60 border border-amber-800/60 text-amber-300">
          PAUSED
        </span>
      )}
      {status === "running" && (
        <span className="flex h-2 w-2 relative">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
      )}
      {isWarning2 && (
        <div className="flex items-center text-xs text-red-400">
          <AlertTriangle className="w-3.5 h-3.5 mr-1" />
          <span>&lt;2m left</span>
        </div>
      )}
    </div>
  );
};
