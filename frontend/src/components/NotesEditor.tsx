import React, { useState, useEffect, useRef } from "react";

interface NotesEditorProps {
  currentStage: number;
  notes: Record<string, string>;
  onSaveNotes: (stage: number, content: string) => Promise<void> | void;
}

const STAGES = [
  { id: 1, name: "Understanding" },
  { id: 2, name: "Brute force" },
  { id: 3, name: "Constraints" },
  { id: 4, name: "Optimal" },
  { id: 5, name: "Edge cases" },
  { id: 6, name: "Coding" },
];

export const NotesEditor: React.FC<NotesEditorProps> = ({
  currentStage,
  notes,
  onSaveNotes,
}) => {
  const [selectedStage, setSelectedStage] = useState<number>(currentStage);
  const [localNotes, setLocalNotes] = useState<Record<string, string>>(() => ({ ...notes }));
  const [isSaving, setIsSaving] = useState<boolean>(false);

  const localNotesRef = useRef<Record<string, string>>({ ...notes });
  const lastSavedRef = useRef<Record<string, string>>({ ...notes });
  const selectedStageRef = useRef<number>(selectedStage);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  selectedStageRef.current = selectedStage;

  useEffect(() => {
    setLocalNotes((prev) => {
      const updated = { ...prev };
      for (const [k, v] of Object.entries(notes)) {
        if (updated[k] === undefined || updated[k] === lastSavedRef.current[k]) {
          updated[k] = v;
          lastSavedRef.current[k] = v;
        }
      }
      localNotesRef.current = updated;
      return updated;
    });
  }, [notes]);

  useEffect(() => {
    setSelectedStage(currentStage);
  }, [currentStage]);

  const handleSelectTab = (stage: number) => {
    if (stage === selectedStage) return;

    const currentStageStr = String(selectedStage);
    const currentContent = localNotesRef.current[currentStageStr] ?? "";

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
      saveTimeoutRef.current = null;
    }

    if (currentContent !== (lastSavedRef.current[currentStageStr] ?? "")) {
      onSaveNotes(selectedStage, currentContent);
      lastSavedRef.current[currentStageStr] = currentContent;
    }

    setSelectedStage(stage);
    setIsSaving(false);
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newContent = e.target.value;
    const stageStr = String(selectedStage);

    setLocalNotes((prev) => {
      const next = { ...prev, [stageStr]: newContent };
      localNotesRef.current = next;
      return next;
    });

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    setIsSaving(true);

    const activeStage = selectedStage;
    saveTimeoutRef.current = setTimeout(async () => {
      try {
        await onSaveNotes(activeStage, newContent);
        lastSavedRef.current[String(activeStage)] = newContent;
      } finally {
        setIsSaving(false);
      }
    }, 1500);
  };

  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
      const stg = selectedStageRef.current;
      const stgStr = String(stg);
      const content = localNotesRef.current[stgStr] ?? "";
      if (content !== (lastSavedRef.current[stgStr] ?? "")) {
        onSaveNotes(stg, content);
        lastSavedRef.current[stgStr] = content;
      }
    };
  }, []);

  const activeContent = localNotes[String(selectedStage)] ?? "";
  const selectedStageMeta = STAGES.find((s) => s.id === selectedStage) || STAGES[0];

  return (
    <div className="flex flex-col h-full bg-[#1A1815] rounded-[10px] overflow-hidden">
      {/* 6-Stage Notes Tab Rail */}
      <div className="border-b border-[#332E28] bg-[#1A1815] px-2 py-1.5 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-1 overflow-x-auto no-scrollbar py-0.5">
          {STAGES.map((s) => {
            const isCurrentInterviewStage = s.id === currentStage;
            const isTabActive = s.id === selectedStage;
            const isPassed = s.id < currentStage;

            return (
              <button
                key={s.id}
                onClick={() => handleSelectTab(s.id)}
                className={`px-2.5 py-1 text-[13px] rounded-[4px] font-medium transition-colors flex items-center space-x-1.5 ${
                  isTabActive
                    ? "bg-[#221F1B] text-[#ECE6DA] border border-[#332E28]"
                    : "text-[#A59E91] hover:text-[#ECE6DA]"
                }`}
              >
                <span className="opacity-60">{s.id}.</span>
                <span>{s.name}</span>
                {isCurrentInterviewStage && (
                  <span className="w-1.5 h-1.5 rounded-full bg-[#F5B83D]" title="Active interview stage" />
                )}
                {isPassed && !isCurrentInterviewStage && (
                  <span className="text-[#A59E91] text-[10px]">✓</span>
                )}
              </button>
            );
          })}
        </div>

        {/* Auto-save Status */}
        <div className="shrink-0 pl-3 pr-2 text-[11px] font-mono select-none text-[#A59E91]">
          {isSaving ? "Saving..." : "Saved"}
        </div>
      </div>

      {/* Editor Body */}
      <div className="relative flex-1 p-3 flex flex-col bg-[#12110F]">
        <textarea
          value={activeContent}
          onChange={handleChange}
          placeholder={`Jot down thoughts for Stage ${selectedStageMeta.id} (${selectedStageMeta.name})...\n• Clarifications and assumptions\n• Constraints and time/space targets\n• Edge cases to consider`}
          className="w-full flex-1 bg-transparent resize-none font-mono text-[13px] text-[#ECE6DA] leading-relaxed placeholder:text-[#6B645A] focus:outline-none"
          spellCheck={false}
        />
        {activeContent.trim() === "" && (
          <div className="text-[11px] text-[#6B645A] select-none pt-2 border-t border-[#332E28]/50 flex items-center justify-between">
            <span>Notes are automatically preserved across all stages.</span>
            <span>Stage {selectedStageMeta.id} / 6</span>
          </div>
        )}
      </div>
    </div>
  );
};
