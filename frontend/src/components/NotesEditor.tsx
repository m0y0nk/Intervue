import React, { useState, useEffect } from "react";
import { Check, Edit3 } from "lucide-react";

interface NotesEditorProps {
  currentStage: number;
  notes: Record<string, string>;
  onSaveNotes: (stage: number, content: string) => void;
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
  const [saveStatus, setSaveStatus] = useState<string>("Saved");

  // Keep selected tab updated when stage advances
  useEffect(() => {
    setSelectedStage(currentStage);
    setContent(notes[String(currentStage)] || "");
  }, [currentStage]);

  // When user switches tab manually
  const handleSelectTab = (stage: number) => {
    setSelectedStage(stage);
    setContent(notes[String(stage)] || "");
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newContent = e.target.value;
    setContent(newContent);
    setSaveStatus("Saving...");
  };

  // Debounced autosave
  useEffect(() => {
    const timer = setTimeout(() => {
      onSaveNotes(selectedStage, content);
      setSaveStatus("Saved");
    }, 800);
    return () => clearTimeout(timer);
  }, [content, selectedStage, onSaveNotes]);

  return (
    <div className="flex flex-col h-full bg-[#121215] border border-[#27272a] rounded-lg overflow-hidden">
      {/* Stage Tabs */}
      <div className="flex items-center border-b border-[#27272a] bg-[#0e0e11] px-2 py-1 overflow-x-auto text-xs">
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
        <div className="ml-auto pl-3 text-[11px] text-zinc-500 font-mono">
          {saveStatus}
        </div>
      </div>

      {/* Text Area */}
      <div className="relative flex-1 p-3">
        <textarea
          value={content}
          onChange={handleChange}
          placeholder={`Write structured notes for ${STAGE_LABELS[selectedStage]} here... (e.g. assumptions, Big-O analysis, trade-offs)`}
          className="w-full h-full bg-transparent resize-none outline-none font-mono text-xs text-zinc-200 leading-relaxed placeholder:text-zinc-600"
        />
      </div>
    </div>
  );
};
