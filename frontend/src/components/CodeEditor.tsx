import React, { useState, useEffect, useRef } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { java } from "@codemirror/lang-java";
import { cpp } from "@codemirror/lang-cpp";
import { RunCodeResponse } from "../types";

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

class Solution {
public:
    std::vector<int> solution(std::vector<int>& nums) {
        // Write your solution here
        return {};
    }
};
`;
    }
    return `def solution(*args):
    # Write your solution here
    pass
`;
  };

  const effectiveInitial = initialCode && initialCode.trim() ? initialCode : getDefaultTemplate(language);
  const [code, setCode] = useState<string>(effectiveInitial);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [lastSavedCode, setLastSavedCode] = useState<string>(effectiveInitial);
  const [runResults, setRunResults] = useState<RunCodeResponse | null>(null);
  const [showDrawer, setShowDrawer] = useState<boolean>(false);

  const codeRef = useRef<string>(effectiveInitial);
  const lastSavedCodeRef = useRef<string>(effectiveInitial);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (initialCode && initialCode.trim()) {
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

    saveTimeoutRef.current = setTimeout(async () => {
      try {
        await onCodeChange(val);
        setLastSavedCode(val);
        lastSavedCodeRef.current = val;
      } finally {
        setIsSaving(false);
      }
    }, 1200);
  };

  const handleRun = async () => {
    if (isRunning || rateLimitSecondsLeft > 0) return;

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

    setShowDrawer(true);
    try {
      const res = await onRunCode();
      setRunResults(res);
    } catch (e: any) {
      setRunResults({
        status: "runtime_error",
        all_passed: false,
        results: [],
        stdout: "",
        stderr: "",
        error: e.message || "Execution error",
      });
    }
  };

  // Keyboard shortcut: Ctrl+Enter or Cmd+Enter to run code
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        handleRun();
      }
      if (e.key === "Escape" && showDrawer) {
        setShowDrawer(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isRunning, rateLimitSecondsLeft, showDrawer]);

  return (
    <div className="flex flex-col h-full bg-[#221F1B] border border-[#332E28] rounded-[10px] overflow-hidden relative">
      {/* Editor Sub-Bar */}
      <div className="flex items-center justify-between border-b border-[#332E28] px-3.5 py-2 text-13 bg-[#1A1815]">
        <div className="flex items-center space-x-2 font-mono text-[12px] text-[#A59E91]">
          <span>{language === "java" ? "Solution.java" : language === "cpp" ? "solution.cpp" : "solution.py"}</span>
          <span>·</span>
          <span>{isSaving ? "Saving..." : "Saved"}</span>
        </div>

        <div className="flex items-center space-x-3">
          {rateLimitSecondsLeft > 0 && (
            <span className="text-[11px] font-mono text-[#A59E91]">
              Wait {rateLimitSecondsLeft.toFixed(1)}s
            </span>
          )}

          {runResults && (
            <button
              type="button"
              onClick={() => setShowDrawer(!showDrawer)}
              className="text-13 text-[#A59E91] hover:text-[#ECE6DA] transition-colors"
            >
              {showDrawer ? "Hide results" : "View results"}
            </button>
          )}

          {/* Action: Run Code in amber #F5B83D with text #12110F */}
          <button
            type="button"
            onClick={handleRun}
            disabled={isRunning || rateLimitSecondsLeft > 0}
            className="px-3 py-1.5 rounded-[4px] bg-[#F5B83D] hover:bg-[#e5aa32] text-[#12110F] text-13 font-semibold disabled:opacity-40 transition-colors"
          >
            {isRunning ? "Running..." : "Run code"}
          </button>
        </div>
      </div>

      {/* CodeMirror Raised Area */}
      <div className="flex-1 overflow-hidden relative">
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
            autocompletion: false,
            highlightSpecialChars: false,
            history: true,
            drawSelection: true,
            syntaxHighlighting: true,
            defaultKeymap: true,
            searchKeymap: true,
            historyKeymap: true,
            lintKeymap: false,
            completionKeymap: false,
          }}
          className="h-full font-mono text-13"
        />

        {/* Bottom Drawer: Execution Results */}
        {showDrawer && (
          <div className="absolute inset-x-0 bottom-0 max-h-[55%] flex flex-col bg-[#1A1815] border-t border-[#332E28] z-20">
            <div className="px-3.5 py-2 border-b border-[#332E28] flex items-center justify-between text-13 bg-[#12110F]">
              <span className="font-medium text-[#ECE6DA]">Test execution results</span>
              <button
                onClick={() => setShowDrawer(false)}
                className="text-13 text-[#A59E91] hover:text-[#ECE6DA]"
              >
                Close
              </button>
            </div>

            <div className="p-3.5 overflow-y-auto space-y-3 font-mono text-13">
              {isRunning && (
                <div className="text-[#A59E91]">Running test cases in sandbox...</div>
              )}

              {!isRunning && !runResults && (
                <div className="text-[#A59E91]">Run code to view test execution outputs.</div>
              )}

              {!isRunning && runResults && (
                <>
                  {/* Overall Summary */}
                  <div className="flex items-center space-x-2 text-13">
                    <span
                      className={`font-semibold ${
                        runResults.all_passed ? "text-[#7BD88F]" : "text-[#FF7A6E]"
                      }`}
                    >
                      {runResults.all_passed ? "All tests passed" : "Tests failed"}
                    </span>
                    <span className="text-[#A59E91]">({runResults.status})</span>
                  </div>

                  {/* Errors if any */}
                  {runResults.error && (
                    <div className="p-2.5 rounded-[4px] bg-[#12110F] border border-[#FF7A6E] text-[#FF7A6E] text-13 whitespace-pre-wrap">
                      {runResults.error}
                    </div>
                  )}

                  {runResults.compile_error && (
                    <div className="p-2.5 rounded-[4px] bg-[#12110F] border border-[#FF7A6E] text-[#FF7A6E] text-13 whitespace-pre-wrap">
                      {runResults.compile_error}
                    </div>
                  )}

                  {/* Test case rows */}
                  {runResults.results && runResults.results.length > 0 && (
                    <div className="space-y-1.5 pt-1">
                      {runResults.results.map((r, i) => (
                        <div
                          key={i}
                          className="p-2 rounded-[4px] bg-[#12110F] border border-[#332E28] text-13 flex flex-col space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[#A59E91]">Test case {i + 1}</span>
                            <span
                              className={`font-medium ${
                                r.passed ? "text-[#7BD88F]" : "text-[#FF7A6E]"
                              }`}
                            >
                              {r.passed ? "Pass" : "Fail"}
                            </span>
                          </div>
                          <div>
                            <span className="text-[#A59E91]">Input: </span>
                            <span className="text-[#ECE6DA]">{JSON.stringify(r.input)}</span>
                          </div>
                          <div>
                            <span className="text-[#A59E91]">Expected: </span>
                            <span className="text-[#ECE6DA]">{JSON.stringify(r.expected)}</span>
                          </div>
                          <div>
                            <span className="text-[#A59E91]">Actual: </span>
                            <span className={r.passed ? "text-[#7BD88F]" : "text-[#FF7A6E]"}>
                              {r.actual !== undefined ? JSON.stringify(r.actual) : "None"}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {runResults.stdout && (
                    <div className="pt-2">
                      <div className="text-[11px] text-[#A59E91] mb-1">Standard Output:</div>
                      <pre className="p-2 bg-[#12110F] border border-[#332E28] rounded-[4px] text-[12px] text-[#ECE6DA] whitespace-pre-wrap">
                        {runResults.stdout}
                      </pre>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
