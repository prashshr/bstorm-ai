import type {
  AgentPersona,
  AgentPersonaCreateRequest,
  AgentPersonaUpdateRequest,
  ChatRequest,
  ChatResponse,
  DiscussionCreateRequest,
  DiscussionResponse,
  DiscussionUpdateRequest,
  Folder,
  FolderCreateRequest,
  FolderUpdateRequest,
  MessageResponse,
  OAuthCodexStartResponse,
  OAuthGoogleStartResponse,
  OAuthPollResponse,
  OAuthStatusResponse,
  ProviderCredentialResponse,
  StreamEvent,
  TokenResponse,
  UpsertProviderCredentialRequest,
} from "./types";

// On the web this is empty (same-origin via nginx). For the Capacitor Android
// app or native platforms, default to the public backend URL if VITE_API_BASE
// is not set, so API calls hit the real backend instead of failing locally.
export function getBaseUrl(): string {
  if (import.meta.env.VITE_API_BASE) {
    return import.meta.env.VITE_API_BASE;
  }
  if (typeof window !== "undefined") {
    const win = window as unknown as {
      Capacitor?: { isNativePlatform(): boolean; getPlatform(): string };
    };
    if (
      win.Capacitor?.isNativePlatform?.() ||
      window.location.protocol === "capacitor:" ||
      window.location.protocol === "file:" ||
      (window.location.hostname === "localhost" && !window.location.port)
    ) {
      return "https://ai-ensemble.samkhya.cloud";
    }
  }
  return "";
}

export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(`API ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
    this.name = "ApiError";
  }
}

type TokenGetter = () => string | null;
type UnauthorizedHandler = () => void;

let getToken: TokenGetter = () => null;
let onUnauthorized: UnauthorizedHandler = () => {};

export function configureApi(opts: {
  getToken: TokenGetter;
  onUnauthorized: UnauthorizedHandler;
}): void {
  getToken = opts.getToken;
  onUnauthorized = opts.onUnauthorized;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  auth = true,
  logoutOn401 = true,
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (auth) {
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const baseUrl = getBaseUrl();
  const resp = await fetch(`${baseUrl}${path}`, { ...options, headers });

  if (resp.status === 401) {
    // Only a 401 from our own auth layer should end the session. A 401 that
    // bubbles up from an upstream provider (e.g. a bad provider key during a
    // chat/health check) must NOT log the user out.
    if (logoutOn401) onUnauthorized();
    let detail = "Unauthorized";
    try {
      const body = await resp.json();
      detail = body.detail ?? detail;
    } catch {
      /* keep default */
    }
    throw new ApiError(401, detail);
  }

  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* keep statusText */
    }
    throw new ApiError(resp.status, detail);
  }

  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

/**
 * Combine a caller-provided AbortSignal with an optional client-side timeout.
 * The caller's signal is always honoured (e.g. the discussion agent passes a
 * combined stop/timeout signal); timeoutMs only adds an extra abort source.
 * Uses AbortSignal.any when available, with a manual fallback otherwise.
 */
function combineSignals(
  signal?: AbortSignal,
  timeoutMs?: number,
): AbortSignal | undefined {
  if (timeoutMs == null || !(timeoutMs > 0)) return signal;
  let timeoutSignal: AbortSignal;
  try {
    timeoutSignal = AbortSignal.timeout(timeoutMs);
  } catch {
    return signal;
  }
  if (!signal) return timeoutSignal;
  if (signal.aborted) return signal;
  if (timeoutSignal.aborted) return timeoutSignal;
  const anyCombine = (
    AbortSignal as unknown as {
      any?: (signals: AbortSignal[]) => AbortSignal;
    }
  ).any;
  if (typeof anyCombine === "function") {
    try {
      return anyCombine.call(AbortSignal, [signal, timeoutSignal]);
    } catch {
      /* fall through to manual combination */
    }
  }
  const controller = new AbortController();
  const onAbort = () => {
    try {
      const reason = signal.aborted
        ? (signal as AbortSignal & { reason?: unknown }).reason
        : (timeoutSignal as AbortSignal & { reason?: unknown }).reason;
      controller.abort(reason);
    } catch {
      controller.abort();
    }
  };
  signal.addEventListener("abort", onAbort, { once: true });
  timeoutSignal.addEventListener("abort", onAbort, { once: true });
  return controller.signal;
}

/** Map a UI OAuth provider key to its backend *start* URL segment.
 *  Only the start endpoints use the short "google" segment
 *  (POST /oauth/codex/start, GET /oauth/google/start); poll, status and
 *  disconnect use the full provider key ("codex" / "google-oauth"). */
function oauthStartSegment(provider: string): string {
  return provider === "google-oauth" ? "google" : provider;
}

export const api = {
  // ---- Auth ----
  register(email: string, password: string): Promise<TokenResponse> {
    return request<TokenResponse>(
      "/api/auth/register",
      { method: "POST", body: JSON.stringify({ email, password }) },
      false,
    );
  },
  login(email: string, password: string, client?: string): Promise<TokenResponse> {
    return request<TokenResponse>(
      "/api/auth/login",
      { method: "POST", body: JSON.stringify({ email, password, client }) },
      false,
    );
  },
  refresh(refreshToken: string): Promise<TokenResponse> {
    return request<TokenResponse>(
      "/api/auth/refresh",
      { method: "POST", body: JSON.stringify({ refresh_token: refreshToken }) },
      false,
    );
  },
  logout(refreshToken: string): Promise<{ ok: boolean }> {
    return request<{ ok: boolean }>(
      "/api/auth/logout",
      { method: "POST", body: JSON.stringify({ refresh_token: refreshToken }) },
      false,
    );
  },

  // ---- Providers ----
  listProviders(): Promise<ProviderCredentialResponse[]> {
    return request<ProviderCredentialResponse[]>("/api/providers");
  },
  upsertProvider(
    body: UpsertProviderCredentialRequest,
  ): Promise<ProviderCredentialResponse> {
    return request<ProviderCredentialResponse>("/api/providers", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  deleteProvider(provider: string): Promise<{ status: string }> {
    return request(`/api/providers/${encodeURIComponent(provider)}`, {
      method: "DELETE",
    });
  },
  listModels(provider: string): Promise<string[]> {
    return request<string[]>(
      `/api/providers/${encodeURIComponent(provider)}/models`,
      {},
      true,
      false,
    );
  },
  testProvider(provider: string): Promise<{ status: string; message?: string }> {
    return request(`/api/providers/${encodeURIComponent(provider)}/test`, {
      method: "POST",
    }, true, false);
  },

  // ---- OAuth (Connect with ChatGPT / Gemini) ----
  // Contract: POST codex/start, GET google/start, GET {provider}/poll?token=,
  // GET /oauth (status), DELETE /oauth/{provider}. Upstream 401s must not
  // end the user's session (logoutOn401:false like other provider calls).
  oauthStart(
    provider: string,
  ): Promise<OAuthCodexStartResponse | OAuthGoogleStartResponse> {
    const segment = oauthStartSegment(provider);
    if (segment === "codex") {
      return request<OAuthCodexStartResponse | OAuthGoogleStartResponse>(
        `/api/providers/oauth/${encodeURIComponent(segment)}/start`,
        { method: "POST" },
        true,
        false,
      );
    }
    return request<OAuthCodexStartResponse | OAuthGoogleStartResponse>(
      `/api/providers/oauth/${encodeURIComponent(segment)}/start`,
      {},
      true,
      false,
    );
  },
  oauthPoll(provider: string, token: string): Promise<OAuthPollResponse> {
    return request<OAuthPollResponse>(
      `/api/providers/oauth/${encodeURIComponent(provider)}/poll?token=${encodeURIComponent(token)}`,
      {},
      true,
      false,
    );
  },
  oauthStatus(): Promise<OAuthStatusResponse> {
    return request<OAuthStatusResponse>("/api/providers/oauth", {}, true, false);
  },
  oauthDisconnect(provider: string): Promise<unknown> {
    return request<unknown>(
      `/api/providers/oauth/${encodeURIComponent(provider)}`,
      { method: "DELETE" },
      true,
      false,
    );
  },

  // ---- Discussions ----
  listDiscussions(): Promise<DiscussionResponse[]> {
    return request<DiscussionResponse[]>("/api/discussions");
  },
  getDiscussion(id: number): Promise<DiscussionResponse> {
    return request<DiscussionResponse>(`/api/discussions/${id}`);
  },
  createDiscussion(
    body: DiscussionCreateRequest,
  ): Promise<DiscussionResponse> {
    return request<DiscussionResponse>("/api/discussions", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  updateDiscussion(
    id: number,
    body: DiscussionUpdateRequest,
  ): Promise<DiscussionResponse> {
    return request<DiscussionResponse>(`/api/discussions/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  },
  deleteDiscussion(id: number): Promise<{ deleted: boolean }> {
    return request(`/api/discussions/${id}`, { method: "DELETE" });
  },
  getMessages(id: number): Promise<MessageResponse[]> {
    return request<MessageResponse[]>(`/api/discussions/${id}/messages`);
  },
  research(id: number): Promise<DiscussionResponse> {
    return request<DiscussionResponse>(`/api/discussions/${id}/research`, {
      method: "POST",
    });
  },

  // ---- Folders ----
  listFolders(): Promise<Folder[]> {
    return request<Folder[]>("/api/folders");
  },
  createFolder(body: FolderCreateRequest): Promise<Folder> {
    return request<Folder>("/api/folders", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  updateFolder(id: number, body: FolderUpdateRequest): Promise<Folder> {
    return request<Folder>(`/api/folders/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  },
  deleteFolder(id: number): Promise<{ deleted: boolean }> {
    return request(`/api/folders/${id}`, { method: "DELETE" });
  },
  addFolderDiscussion(folderId: number, discussionId: number): Promise<Folder> {
    return request<Folder>(
      `/api/folders/${folderId}/discussions/${discussionId}`,
      { method: "POST" },
    );
  },
  removeFolderDiscussion(
    folderId: number,
    discussionId: number,
  ): Promise<Folder> {
    return request<Folder>(
      `/api/folders/${folderId}/discussions/${discussionId}`,
      { method: "DELETE" },
    );
  },

  // ---- Personas ----
  listPersonas(): Promise<AgentPersona[]> {
    return request<AgentPersona[]>("/api/personas");
  },
  createPersona(body: AgentPersonaCreateRequest): Promise<AgentPersona> {
    return request<AgentPersona>("/api/personas", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  updatePersona(id: number, body: AgentPersonaUpdateRequest): Promise<AgentPersona> {
    return request<AgentPersona>(`/api/personas/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  },
  deletePersona(id: number): Promise<{ deleted: boolean }> {
    return request(`/api/personas/${id}`, { method: "DELETE" });
  },

  // ---- Proxy chat ----
  // Provider/upstream 401s here must not end the user's session.
  chat(
    body: ChatRequest,
    signal?: AbortSignal,
    timeoutMs?: number,
  ): Promise<ChatResponse> {
    const combined = combineSignals(signal, timeoutMs);
    return request<ChatResponse>(
      "/api/proxy/chat",
      {
        method: "POST",
        body: JSON.stringify(body),
        signal: combined ?? undefined,
      },
      true,
      false,
    );
  },

  /**
   * Streaming chat via SSE. Calls onEvent for every parsed event.
   * Returns the full accumulated text on completion.
   */
  async chatStream(
    body: ChatRequest,
    onEvent: (ev: StreamEvent) => void,
    signal?: AbortSignal,
    timeoutMs?: number,
  ): Promise<string> {
    const headers = new Headers({ "Content-Type": "application/json" });
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);

    const baseUrl = getBaseUrl();
    const combined = combineSignals(signal, timeoutMs);
    const resp = await fetch(`${baseUrl}/api/proxy/chat/stream`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal: combined ?? undefined,
    });

    if (resp.status === 401) {
      // Upstream provider 401 during streaming must not log the user out.
      throw new ApiError(401, "Provider authorization failed");
    }
    if (!resp.ok || !resp.body) {
      throw new ApiError(resp.status, resp.statusText || "stream failed");
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let full = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data:")) continue;
        const payload = trimmed.slice(5).trim();
        if (!payload) continue;
        try {
          const ev = JSON.parse(payload) as StreamEvent;
          if (ev.type === "delta" && ev.content) full += ev.content;
          if (ev.type === "done" && ev.content) full = ev.content;
          onEvent(ev);
        } catch {
          /* ignore malformed keep-alive lines */
        }
      }
    }
    return full;
  },
};
