export type InterviewSource = "ai_business" | "leetcode" | "random_dsa" | "adaptive" | "custom";
export type InterviewMode = "standard" | "blind_mock" | "topic_mastery" | "revision";
export type InterviewStyle = "google" | "amazon" | "meta" | "general";
export type InterviewDifficulty = "easy" | "medium" | "hard" | "adaptive";
export type InterviewCategory =
  | "arrays_hashing"
  | "two_pointers"
  | "sliding_window"
  | "binary_search"
  | "stack_queue"
  | "linked_lists"
  | "trees"
  | "graphs"
  | "dynamic_programming"
  | "greedy"
  | "backtracking"
  | "heaps"
  | "intervals"
  | "mixed";

export interface InterviewConfig {
  source: InterviewSource;
  mode: InterviewMode;
  style: InterviewStyle;
  difficulty: InterviewDifficulty;
  category: InterviewCategory;
  language: "python" | "java" | "cpp";
  framing: "standard" | "business";
  duration: number;
}

export interface SessionCreatePayload {
  config: Partial<InterviewConfig>;
  leetcode_id?: string;
  leetcode_statement?: string;
  custom_statement?: string;
  custom_url?: string;
  custom_extra_constraints?: string;
}

export interface ProblemExample {
  input_str: string;
  output_str: string;
  explanation?: string;
}

export interface FunctionArg {
  name: string;
  type: string;
}

export interface FunctionSignature {
  function_name: string;
  args: FunctionArg[];
  return_type: string;
}

export interface TestCase {
  args: any[];
  expected: any;
}

export interface ProblemPublic {
  id: string;
  title: string;
  statement: string;
  examples: ProblemExample[];
  signature: FunctionSignature;
  revealed_constraints: string[];
  visible_tests: TestCase[];
  starter_code: Record<string, string>;
  checker: string;
  category?: string;
  difficulty?: string;
}

export interface SessionState {
  id: string;
  status: "generating" | "ready" | "running" | "paused" | "finished" | "abandoned";
  stage: number;
  stage_name: string;
  active_ms_accumulated: number;
  remaining_ms: number;
  started_at?: string;
  last_resumed_at?: string;
  config: InterviewConfig;
  problem?: ProblemPublic;
  notes: Record<string, string>;
  code: string;
  language: string;
}

export interface ChatMessage {
  id?: string;
  sender: "interviewer" | "candidate" | "system";
  message: string;
  stage: number;
  timestamp: string;
}

export interface TestResultItem {
  passed: boolean;
  input: any[];
  expected: any;
  actual?: any;
  error?: string;
  duration_ms?: number;
}

export interface RunCodeResponse {
  status: string;
  all_passed: boolean;
  results: TestResultItem[];
  stdout: string;
  stderr: string;
  compile_error?: string;
  error?: string;
}

export interface SubmitResponse {
  status: string;
  passed_count: number;
  total_count: number;
  failure_category?: string;
  coding_score: number;
  finished_at: string;
}

export interface DimensionScore {
  name: string;
  score: number;
  is_deterministic: boolean;
  evidence_quote?: string;
  rationale: string;
}

export interface FinalEvaluationReport {
  session_id: string;
  total_score: number;
  verdict: "strong_hire" | "hire" | "borderline" | "no_hire";
  dimension_scores: DimensionScore[];
  strengths: string[];
  weaknesses: string[];
  idea_to_code_gap: string;
  recommendations: string[];
  tests_passed: number;
  tests_total: number;
  stage_timings: Record<string, number>;
}
