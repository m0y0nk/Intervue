import React, { useState, useEffect, useRef } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { java } from "@codemirror/lang-java";
import { cpp } from "@codemirror/lang-cpp";
import { Play, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { RunCodeResponse, TestResultItem } from "../types";

interface CodeEditorProps {
  initialCode: string;
  language?: string;
  onCodeChange: (code: string) => Promise<void> | void;
  onRunCode: () => Promise<RunCodeResponse>;
  isRunning: boolean;
  rateLimitSecondsLeft: number;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({
  initialCode,
  language = "python",
  onCodeChange,
  onRunCode,
  isRunning,
  rateLimitSecondsLeft,
}) => {
  const getDefaultTemplate = (lang: string) => {
    if (lang === "java") {
      return `import java.util.*;

// Pre-defined ListNode and TreeNode types are available.
// Keep class Solution public with your member method.
public class Solution {
    public int[] solution(int[] nums) {
        // Write your solution here
        return new int[]{};
    }
}
`;
    }
    if (lang === "cpp") {
      return `#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <algorithm>

// Pre-defined ListNode and TreeNode types are available.
// Keep class Solution with your public member function.
class Solution {
public:
    std::vector<int> solution(std::vector<int>& nums) {
        // Write your solution here
        return {};
    }
};
`;
    }
    return `# Pre-defined ListNode and TreeNode classes are available.
def solution(*args):
    # Write your solution here
    pass
`;
  };

  const effectiveInitial = initialCode && initialCode.trim() ? initialCode : getDefaultTemplate(language);
  const [code, setCode] = useState<string>(effectiveInitial);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [lastSavedCode, setLastSavedCode] = useState<string>(effectiveInitial);
  const [runResults, setRunResults] = useState<RunCodeResponse | null>(null);
  const [activeTab, setActiveTab] = useState<"editor" | "results">("editor");

  const codeRef = useRef<string>(effectiveInitial);
  const lastSavedCodeRef = useRef<string>(effectiveInitial);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync initialCode only when initialCode changes and user is not actively editing unsaved changes
  useEffect(() => {
    if (initialCode && initialCode.trim()) {
      // Only overwrite if code is currently empty or matches what was previously saved
      if (!codeRef.current || codeRef.current === lastSavedCodeRef.current) {
        setCode(initialCode);
        codeRef.current = initialCode;
        setLastSavedCode(initialCode);
        lastSavedCodeRef.current = initialCode;
      }
    }
  }, [initialCode]);

  const handleChange = (val: string) => {
    setCode(val);
    codeRef.current = val;

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    setIsSaving(true);

    // Debounce autosave: 1.5 seconds after candidate stops typing
    saveTimeoutRef.current = setTimeout(async () => {
      try {
        await onCodeChange(val);
        setLastSavedCode(val);
        lastSavedCodeRef.current = val;
      } finally {
        setIsSaving(false);
      }
    }, 1500);
  };

  const handleRun = async () => {
    // Flush any pending save immediately before running
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
      saveTimeoutRef.current = null;
    }
    if (codeRef.current !== lastSavedCodeRef.current) {
      await onCodeChange(codeRef.current);
      setLastSavedCode(codeRef.current);
      lastSavedCodeRef.current = codeRef.current;
      setIsSaving(false);
    }

    try {
      const res = await onRunCode();
      setRunResults(res);
      setActiveTab("results");
    } catch (e: any) {
      setRunResults({
        status: "runtime_error",
        all_passed: false,
        results: [],
        stdout: "",
        stderr: "",
        error: e.message || "Run failed",
      });
      setActiveTab("results");
    }
  };

  // Flush on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
      if (codeRef.current !== lastSavedCodeRef.current) {
        onCodeChange(codeRef.current);
        lastSavedCodeRef.current = codeRef.current;
      }
    };
  }, []);

  return (
    <div className="flex flex-col h-full bg-[#0d0d10] border border-[#27272a] rounded-lg overflow-hidden">
      {/* Editor Header */}
      <div className="flex items-center justify-between border-b border-[#27272a] bg-[#121215] px-3 py-2 text-xs">
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setActiveTab("editor")}
            className={`px-2.5 py-1 rounded font-medium transition-colors ${
              activeTab === "editor"
                ? "bg-[#1f1f23] text-zinc-100"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            {language === "java" ? "Solution.java" : language === "cpp" ? "solution.cpp" : "solution.py"}
          </button>
          <button
            onClick={() => setActiveTab("results")}
            className={`px-2.5 py-1 rounded font-medium transition-colors flex items-center space-x-1.5 ${
              activeTab === "results"
                ? "bg-[#1f1f23] text-zinc-100"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <span>Test Results</span>
            {runResults && (
              <span
                className={`w-2 h-2 rounded-full ${
                  runResults.all_passed ? "bg-emerald-400" : "bg-red-400"
                }`}
              />
            )}
          </button>
        </div>

        {/* Right side: Save indicator & Run Button */}
        <div className="flex items-center space-x-3">
          <div className="w-16 text-right text-[11px] font-mono select-none flex items-center justify-end">
            {isSaving ? (
              <span className="flex items-center text-amber-400/90">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 mr-1.5 animate-pulse" />
                Saving
              </span>
            ) : (
              <span className="text-zinc-500">Saved</span>
            )}
          </div>

          {rateLimitSecondsLeft > 0 && (
            <span className="text-[11px] text-zinc-500 font-mono">
              Wait {rateLimitSecondsLeft.toFixed(1)}s
            </span>
          )}
          <button
            onClick={handleRun}
            disabled={isRunning || rateLimitSecondsLeft > 0}
            className="flex items-center space-x-1.5 px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 disabled:opacity-40 disabled:hover:bg-zinc-800 text-zinc-100 font-medium transition-colors"
          >
            {isRunning ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-zinc-300" />
            ) : (
              <Play className="w-3.5 h-3.5 text-emerald-400 fill-emerald-400" />
            )}
            <span>Run Code</span>
          </button>
        </div>
      </div>

      {/* Editor or Results Display */}
      <div className="flex-1 relative overflow-hidden">
        {activeTab === "editor" ? (
          <CodeMirror
            value={code}
            height="100%"
            theme="dark"
            extensions={language === "java" ? [java()] : language === "cpp" ? [cpp()] : [python()]}
            onChange={handleChange}
            basicSetup={{
              lineNumbers: true,
              highlightActiveLineGutter: true,
              foldGutter: false,
              dropCursor: false,
              allowMultipleSelections: false,
              indentOnInput: false,
              bracketMatching: false,
              closeBrackets: false,
              autocompletion: false, // CRITICAL: Disabled completely
              highlightSpecialChars: false,
              history: true,
              drawSelection: true,
              syntaxHighlighting: true,
              defaultKeymap: true,
              searchKeymap: true,
              historyKeymap: true,
              lintKeymap: false,
              completionKeymap: false, // CRITICAL: Disabled completely
            }}
            className="h-full font-mono text-xs"
          />
        ) : (
          <div className="h-full overflow-y-auto p-4 space-y-4 text-xs font-mono">
            {!runResults ? (
              <div className="text-zinc-500 text-center py-8">
                Click "Run Code" above to execute your solution against visible example test cases.
              </div>
            ) : (
              <div className="space-y-4">
                {/* Status Banner */}
                <div
                  className={`p-3 rounded border flex items-center justify-between ${
                    runResults.all_passed
                      ? "bg-emerald-950/40 border-emerald-800/60 text-emerald-300"
                      : "bg-red-950/40 border-red-800/60 text-red-300"
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    {runResults.all_passed ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-400" />
                    )}
                    <span className="font-semibold uppercase tracking-wider text-xs">
                      {runResults.all_passed ? "All Visible Tests Passed" : "Tests Failed"}
                    </span>
                  </div>
                  <span className="text-[11px] opacity-80">
                    Status: {runResults.status}
                  </span>
                </div>

                {/* Error Banner if any */}
                {runResults.error && (
                  <div className="p-3 rounded bg-red-950/30 border border-red-900/40 text-red-300 text-xs whitespace-pre-wrap">
                    {runResults.error}
                  </div>
                )}
                {runResults.compile_error && (
                  <div className="p-3 rounded bg-red-950/30 border border-red-900/40 text-red-300 text-xs whitespace-pre-wrap">
                    {runResults.compile_error}
                  </div>
                )}

                {/* Results list */}
                {runResults.results.map((res: TestResultItem, idx: number) => (
                  <div
                    key={idx}
                    className={`p-3 rounded border ${
                      res.passed
                        ? "bg-[#121215] border-[#27272a]"
                        : "bg-red-950/20 border-red-900/40"
                    } space-y-2`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-zinc-400">Test Case {idx + 1}</span>
                      <span
                        className={`text-[11px] px-1.5 py-0.5 rounded font-bold ${
                          res.passed
                            ? "bg-emerald-950/60 text-emerald-400 border border-emerald-800/60"
                            : "bg-red-950/60 text-red-400 border border-red-800/60"
                        }`}
                      >
                        {res.passed ? "PASSED" : "FAILED"}
                      </span>
                    </div>

                    <div className="space-y-1 text-xs">
                      <div className="flex">
                        <span className="text-zinc-500 w-20 shrink-0">Input:</span>
                        <span className="text-zinc-200">{JSON.stringify(res.input)}</span>
                      </div>
                      <div className="flex">
                        <span className="text-zinc-500 w-20 shrink-0">Expected:</span>
                        <span className="text-emerald-400">{JSON.stringify(res.expected)}</span>
                      </div>
                      <div className="flex">
                        <span className="text-zinc-500 w-20 shrink-0">Actual:</span>
                        <span className={res.passed ? "text-emerald-400" : "text-red-400"}>
                          {res.actual !== undefined ? JSON.stringify(res.actual) : "None"}
                        </span>
                      </div>
                      {res.error && (
                        <div className="text-red-400 pt-1 text-[11px]">{res.error}</div>
                      )}
                    </div>
                  </div>
                ))}

                {/* Stdout if present */}
                {runResults.stdout && (
                  <div className="space-y-1">
                    <span className="text-zinc-500 text-[11px]">Standard Output:</span>
                    <pre className="p-2.5 rounded bg-[#070709] border border-[#27272a] text-zinc-300 text-xs overflow-x-auto">
                      {runResults.stdout}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
