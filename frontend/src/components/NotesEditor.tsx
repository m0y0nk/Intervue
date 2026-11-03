import React, { useState, useEffect, useRef } from "react";
import { Check } from "lucide-react";

interface NotesEditorProps {
  currentStage: number;
  notes: Record<string, string>;
  onSaveNotes: (stage: number, content: string) => Promise<void> | void;
}

const STAGE_LABELS: Record<number, string> = {
  1: "1. Understanding",
  2: "2. Brute Force",
  3: "3. Constraints",
  4: "4. Optimal",
  5: "5. Edge Cases",
  6: "6. Coding Notes",
};

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

  // Merge external notes updates if any stage changed externally and isn't dirty
  useEffect(() => {
    setLocalNotes((prev) => {
      const updated = { ...prev };
      for (const [k, v] of Object.entries(notes)) {
        // If not in localNotes or was already saved, update from parent
        if (updated[k] === undefined || updated[k] === lastSavedRef.current[k]) {
          updated[k] = v;
          lastSavedRef.current[k] = v;
        }
      }
      localNotesRef.current = updated;
      return updated;
    });
  }, [notes]);

  // Keep selected tab updated when interview stage advances
  useEffect(() => {
    setSelectedStage(currentStage);
  }, [currentStage]);

  // Flush pending save immediately when switching tabs
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

    // Update in-memory local notes immediately
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

  // Flush on unmount
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

  return (
    <div className="flex flex-col h-full bg-[#121215] border border-[#27272a] rounded-lg overflow-hidden">
      {/* Stage Tabs Header */}
      <div className="flex items-center justify-between border-b border-[#27272a] bg-[#0e0e11] px-2 py-1 text-xs">
        {/* Scrollable tabs with hidden scrollbar to prevent flicker */}
        <div className="flex items-center space-x-1 overflow-x-auto no-scrollbar py-0.5">
          {([1, 2, 3, 4, 5, 6] as const).map((s) => (
            <button
              key={s}
              onClick={() => handleSelectTab(s)}
              className={`px-3 py-1.5 rounded-md font-medium whitespace-nowrap transition-colors flex items-center space-x-1.5 ${
                selectedStage === s
                  ? "bg-[#1f1f23] text-indigo-300 border border-indigo-900/40"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <span>{STAGE_LABELS[s]}</span>
              {s < currentStage && <Check className="w-3 h-3 text-emerald-400" />}
              {s === currentStage && (
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
              )}
            </button>
          ))}
        </div>

        {/* Fixed-width save indicator isolated from tab overflow */}
        <div className="shrink-0 pl-3 pr-2 w-20 text-right text-[11px] font-mono select-none flex items-center justify-end">
          {isSaving ? (
            <span className="flex items-center text-amber-400/90">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 mr-1.5 animate-pulse" />
              Saving
            </span>
          ) : (
            <span className="text-zinc-500">Saved</span>
          )}
        </div>
      </div>

      {/* Text Area */}
      <div className="relative flex-1 p-3">
        <textarea
          value={activeContent}
          onChange={handleChange}
          placeholder={`Write structured notes for ${STAGE_LABELS[selectedStage]} here... (e.g. assumptions, Big-O analysis, trade-offs)`}
          className="w-full h-full bg-transparent resize-none outline-none font-mono text-xs text-zinc-200 leading-relaxed placeholder:text-zinc-600 focus:ring-0 focus:outline-none"
          spellCheck={false}
        />
      </div>
    </div>
  );
};
