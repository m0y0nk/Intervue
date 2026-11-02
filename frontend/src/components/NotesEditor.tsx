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
  const [content, setContent] = useState<string>(notes[String(currentStage)] || "");
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [lastSavedContent, setLastSavedContent] = useState<string>(notes[String(currentStage)] || "");

  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Keep selected tab updated when stage advances
  useEffect(() => {
    setSelectedStage(currentStage);
    const initial = notes[String(currentStage)] || "";
    setContent(initial);
    setLastSavedContent(initial);
  }, [currentStage]);

  // Flush any pending save immediately when switching tabs
  const handleSelectTab = (stage: number) => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
      saveTimeoutRef.current = null;
      if (content !== lastSavedContent) {
        onSaveNotes(selectedStage, content);
        setLastSavedContent(content);
      }
    }
    setSelectedStage(stage);
    const nextContent = notes[String(stage)] || "";
    setContent(nextContent);
    setLastSavedContent(nextContent);
    setIsSaving(false);
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newContent = e.target.value;
    setContent(newContent);

    // If there is an existing debounce timer, reset it
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    // Set saving indicator
    setIsSaving(true);

    // Debounce save by 1.5 seconds after user stops typing
    saveTimeoutRef.current = setTimeout(async () => {
      try {
        await onSaveNotes(selectedStage, newContent);
        setLastSavedContent(newContent);
      } finally {
        setIsSaving(false);
      }
    }, 1500);
  };

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

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
          value={content}
          onChange={handleChange}
          placeholder={`Write structured notes for ${STAGE_LABELS[selectedStage]} here... (e.g. assumptions, Big-O analysis, trade-offs)`}
          className="w-full h-full bg-transparent resize-none outline-none font-mono text-xs text-zinc-200 leading-relaxed placeholder:text-zinc-600 focus:ring-0 focus:outline-none"
          spellCheck={false}
        />
      </div>
    </div>
  );
};
