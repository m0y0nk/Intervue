import React from "react";

export const STAGES = [
  { id: 1, name: "Understanding" },
  { id: 2, name: "Brute force" },
  { id: 3, name: "Constraints" },
  { id: 4, name: "Optimal" },
  { id: 5, name: "Edge cases" },
  { id: 6, name: "Coding" },
];

interface StageRailProps {
  currentStage: number; // 1 to 6
  formattedTime?: string; // e.g. "20:00" or countdown
  progressRatio?: number; // 0 to 1 for active segment fill/drain
  isWarning?: boolean; // time < 2 mins (turns fail color #FF7A6E)
  mode?: "preview" | "topbar" | "nav";
  onSelectStage?: (stage: number) => void;
  className?: string;
}

export const StageRail: React.FC<StageRailProps> = ({
  currentStage = 1,
  formattedTime = "20:00",
  progressRatio = 0,
  isWarning = false,
  mode = "topbar",
  onSelectStage,
  className = "",
}) => {
  return (
    <div className={`w-full ${className}`}>
      {/* 6 Segments Bar */}
      <div className="grid grid-cols-6 gap-1.5 items-stretch">
        {STAGES.map((stage) => {
          const isDone = stage.id < currentStage;
          const isActive = stage.id === currentStage;
          const isUpcoming = stage.id > currentStage;

          return (
            <div
              key={stage.id}
              onClick={() => onSelectStage && onSelectStage(stage.id)}
              className={`flex flex-col select-none transition-colors ${
                onSelectStage ? "cursor-pointer" : ""
              }`}
            >
              {/* Rail Segment Line/Track */}
              <div
                className={`h-1.5 w-full rounded-[1px] relative overflow-hidden transition-all duration-200 ${
                  isDone
                    ? "bg-[#A59E91]"
                    : isActive
                    ? "bg-[#332E28]"
                    : "bg-[#332E28]"
                }`}
              >
                {/* Active segment fill animation / progress */}
                {isActive && (
                  <div
                    className={`absolute inset-y-0 left-0 transition-all duration-300 ${
                      isWarning ? "bg-[#FF7A6E]" : "bg-[#F5B83D]"
                    }`}
                    style={{
                      width: `${Math.max(12, Math.min(100, (1 - progressRatio) * 100))}%`,
                    }}
                  />
                )}
              </div>

              {/* Label and Timer Details */}
              <div className="mt-1.5 flex items-baseline justify-between text-[11px] leading-tight">
                <span
                  className={`truncate font-medium ${
                    isActive
                      ? isWarning
                        ? "text-[#FF7A6E]"
                        : "text-[#ECE6DA]"
                      : isDone
                      ? "text-[#A59E91]"
                      : "text-[#6B645A]"
                  }`}
                >
                  <span className="opacity-60 mr-1">{stage.id}.</span>
                  {stage.name}
                </span>

                {/* Show Timer inside the active segment */}
                {isActive && formattedTime && (
                  <span
                    className={`ml-1 font-mono text-[11px] shrink-0 font-medium ${
                      isWarning ? "text-[#FF7A6E]" : "text-[#F5B83D]"
                    }`}
                  >
                    {formattedTime}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
