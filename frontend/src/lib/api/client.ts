import type {
  ChatRequest,
  ChatResponse,
  DiscussionCreateRequest,
  DiscussionResponse,
  DiscussionUpdateRequest,
  Folder,
  FolderCreateRequest,
  FolderUpdateRequest,
  MessageResponse,
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

  // ---- Proxy chat ----
  // Provider/upstream 401s here must not end the user's session.
  chat(body: ChatRequest, signal?: AbortSignal): Promise<ChatResponse> {
    return request<ChatResponse>(
      "/api/proxy/chat",
      { method: "POST", body: JSON.stringify(body), signal },
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
  ): Promise<string> {
    const headers = new Headers({ "Content-Type": "application/json" });
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);

    const baseUrl = getBaseUrl();
    const resp = await fetch(`${baseUrl}/api/proxy/chat/stream`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal,
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
