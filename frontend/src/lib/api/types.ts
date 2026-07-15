// Types mirroring the FastAPI backend schemas (backend/app/schemas)

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface ProviderCredentialResponse {
  provider: string;
  endpoint: string;
  has_key: boolean;
}

export interface UpsertProviderCredentialRequest {
  provider: string;
  api_key: string;
  endpoint?: string;
}

export interface DiscussionResponse {
  id: number;
  title: string;
  question: string;
  status: string;
  use_rag: boolean;
  deep_research: boolean;
  state_json: string;
  retrieved_context: string | null;
  created_at: string;
}

export interface DiscussionCreateRequest {
  question: string;
  title?: string;
  use_rag?: boolean;
  deep_research?: boolean;
}

export interface DiscussionUpdateRequest {
  status?: string;
  state_json?: string;
  title?: string;
}

export interface MessageResponse {
  id: number;
  discussion_id: number;
  round_number: number;
  model: string;
  role: string;
  content: string;
  created_at: string;
}

export interface ChatRequest {
  provider: string;
  model: string;
  prompt: string;
  endpoint?: string;
  max_tokens?: number;
  temperature?: number;
  discussion_id?: number | null;
  include_rag_context?: boolean;
}

export interface ChatResponse {
  provider: string;
  model: string;
  output: string;
}

// SSE stream event shape from /api/proxy/chat/stream
export interface StreamEvent {
  type: "delta" | "done" | "error";
  content?: string;
  detail?: string;
}

// ---- Client-side domain types ----

export type ModelStatus =
  | "waiting"
  | "connecting"
  | "streaming"
  | "complete"
  | "error"
  | "timeout"
  | "skipped";

export type HealthStatus = "OK" | "KO" | "testing" | "unknown";

export interface ModelResult {
  text: string;
  status: ModelStatus;
  stats?: ModelStats;
  error?: string;
}

export interface ModelStats {
  inputTokens?: number;
  outputTokens?: number;
  totalTokens?: number;
  durationMs?: number;
}

export type DiscussionStatus =
  | "new"
  | "in_progress"
  | "completed"
  | "stopped"
  | "closed";

export interface DiscussionState {
  id: number | string | null;
  timestamp: number | null;
  question: string;
  instructions: string;
  models: string[];
  rounds: Record<number, Record<string, ModelResult>>;
  consensus: string;
  endpoint: string;
  consensusModel: string;
  timeout: number;
  maxTokens: number;
  attachments: AttachedFile[];
  stats: DiscussionAggregateStats;
  status: DiscussionStatus;
  totalRounds: number;
  use_rag: boolean;
  deep_research: boolean;
  retrieved_context: string | null;
  summaryFormat: "elaborate" | "compact" | "default";
  summaryInstructions: string;
  responseFormat: string;
}

export interface DiscussionAggregateStats {
  totalInputTokens: number;
  totalOutputTokens: number;
  totalTokens: number;
  avgDurationMs: number;
  peakContext: number;
  modelCount: number;
}

export interface AttachedFile {
  name: string;
  size: number;
  type: string;
  content: string;
}

export interface ProviderPreset {
  key: string;
  name: string;
  endpoint: string;
}

// Progress stepper phases (design council: Queued -> Searching -> Drafting -> Synthesizing)
export type ProgressPhase =
  | "idle"
  | "queued"
  | "searching"
  | "drafting"
  | "synthesizing"
  | "done";

// Consensus contribution weighting for the interactive bars
export interface Contribution {
  model: string;
  weight: number;
  color: string;
}
