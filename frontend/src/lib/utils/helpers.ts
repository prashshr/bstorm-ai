/**
 * Normalize an auth identifier. The backend expects an EmailStr, but the UI
 * allows plain usernames (e.g. "admin") for convenience, mapping them to the
 * local domain — matching the legacy monolith behaviour exactly.
 */
import type { DiscussionState } from "../api/types";

export function normalizeAuthIdentifier(value: string): string {
  const id = (value || "").trim().toLowerCase();
  if (!id) return "";
  return id.includes("@") ? id : `${id}@local.ai-ensemble`;
}

/** Subsequence-based fuzzy matcher (matches the legacy behaviour). */
export function fuzzyMatch(text: string, query: string): boolean {
  if (!query) return true;
  const t = text.toLowerCase();
  const q = query.toLowerCase();
  let i = 0;
  for (const ch of t) {
    if (ch === q[i]) i++;
    if (i === q.length) return true;
  }
  return i === q.length;
}

/** Debounce a function by `wait` ms. */
export function debounce<T extends (...args: never[]) => void>(
  fn: T,
  wait: number,
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout> | undefined;
  return (...args: Parameters<T>) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

/** Deterministic color for a model/provider name (for contribution bars). */
export function colorForModel(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 70%, 55%)`;
}

/** Split a composite "provider::model" key. */
export function splitModelKey(key: string): { provider: string; model: string } {
  const idx = key.indexOf("::");
  if (idx === -1) return { provider: "", model: key };
  return { provider: key.slice(0, idx), model: key.slice(idx + 2) };
}

export function formatDate(iso: string | number | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Copy text to the clipboard. Falls back to a hidden textarea + execCommand
 * for insecure contexts / older browsers. Resolves to true on success.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    /* fall through to legacy path */
  }
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}

export function randomSuffix(len = 5): string {
  const chars = "abcdefghijklmnopqrstuvwxyz";
  let s = "";
  for (let i = 0; i < len; i++) {
    s += chars[Math.floor(Math.random() * chars.length)];
  }
  return s;
}

export function downloadFile(filename: string, content: string, mime: string): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export const PROVIDER_PRESETS = [
  { key: "openrouter", name: "OpenRouter", endpoint: "https://openrouter.ai/api/v1" },
  { key: "openai", name: "OpenAI Official", endpoint: "https://api.openai.com/v1" },
  { key: "perplexity", name: "Perplexity AI", endpoint: "https://api.perplexity.ai" },
  {
    key: "vertex",
    name: "Google Vertex",
    endpoint: "https://us-central1-aiplatform.googleapis.com/v1",
  },
  { key: "mammouth", name: "Mammouth AI", endpoint: "https://api.mammouth.ai/v1" },
  { key: "requesty", name: "Requesty AI", endpoint: "https://router.requesty.ai/v1" },
  { key: "custom", name: "Custom Compatible", endpoint: "" },
];

const PRESET_NAME_BY_KEY: Record<string, string> = Object.fromEntries(
  PROVIDER_PRESETS.map((p) => [p.key, p.name]),
);

/** Canonical names for OAuth subscription providers whose raw keys are
 *  misleading when shown verbatim or prettified (e.g. "copilot"). */
const OAUTH_PROVIDER_NAMES: Record<string, string> = {
  codex: "ChatGPT (Codex)",
  copilot: "GitHub Copilot",
  openrouter: "OpenRouter",
};

/** Map a provider key to a brand logo icon name (falls back to the generic
 *  bot glyph when the provider has no dedicated mark). */
const PROVIDER_ICON_BY_KEY: Record<string, string> = {
  codex: "chatgpt",
  openai: "chatgpt",
  copilot: "copilot",
  openrouter: "openrouter",
  anthropic: "anthropic",
  claude: "anthropic",
  gemini: "gemini",
  vertex: "gemini",
  perplexity: "perplexity",
  github: "github-mark",
};

export function providerIconName(key: string): string {
  return PROVIDER_ICON_BY_KEY[key] ?? "bot";
}

/** Best-effort check whether a model name suggests vision/multimodal support. */
export const VISION_RE = /(gpt-4o|gpt-5|gpt-4-visual|gpt-4-turbo|vision|gemini|claude|llama-3\.2-vision|llama-4|llava|qwen-vl|qwen2\.5-vl|qwen3|qwen-3|pixtral|moondream|ministral|gemma-3|internvl|smolvlm|aya-vision|phi-3-vision|phi-4-vision|o1(?!-mini)|o4|mimo|kimi)/i;
export const TEXT_ONLY_RE = /(deepseek(?!.*(?:vl|vision))|reasoner|o1-mini|o3-mini|text-|instruct(?!.*(?:vl|vision)))/i;

export function modelSupportsVision(modelName: string): boolean {
  if (VISION_RE.test(modelName)) {
    if (TEXT_ONLY_RE.test(modelName) && !/(vl|vision)/i.test(modelName)) {
      return false;
    }
    return true;
  }
  return false;
}

/** Human-readable provider name for a credential key, falling back to a
 *  prettified version of the key when no preset matches. An optional
 *  `label` overrides the display name (used for custom providers that the
 *  user has named). */
export function providerDisplayName(key: string, label?: string): string {
  if (label) return label;
  if (OAUTH_PROVIDER_NAMES[key]) return OAUTH_PROVIDER_NAMES[key];
  if (PRESET_NAME_BY_KEY[key]) return PRESET_NAME_BY_KEY[key];
  return key
    .split(/[-_]/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export interface MentionParse {
  /** Models explicitly mentioned, or `null` when everyone answers. */
  targets: string[] | null;
  /** Mention tokens that matched at least one roster model (display names). */
  matched: string[];
}

/**
 * Parse `@mention` routing tokens from a message.
 *
 * - `@all` / `@everyone` → everyone answers (`targets: null`)
 * - `@gpt-4o`, `@claude`, `@openai`, `@openrouter/meta-llama/…` → only the
 *   roster models whose id/provider match answer this round
 * - tokens matching nothing are ignored (left as plain text)
 *
 * Returns the roster-ordered subset of models to prompt for this message.
 */
export function parseModelMentions(text: string, roster: string[]): MentionParse {
  if (!text || roster.length === 0) return { targets: null, matched: [] };
  const tokens = [...text.matchAll(/@([A-Za-z0-9][\w./-]*)/g)].map((m) =>
    m[1].toLowerCase(),
  );
  if (tokens.length === 0) return { targets: null, matched: [] };

  const matched = new Set<string>();
  let sawAll = false;
  for (const token of tokens) {
    if (token === "all" || token === "everyone") {
      sawAll = true;
      continue;
    }
    for (const key of roster) {
      const { provider, model } = splitModelKey(key);
      const providerLc = provider.toLowerCase();
      const modelLc = model.toLowerCase();
      const full = `${providerLc}/${modelLc}`;
      if (modelLc.includes(token) || providerLc === token || full.includes(token)) {
        matched.add(key);
      }
    }
  }
  if (sawAll) return { targets: null, matched: [...matched] };
  if (matched.size === 0) return { targets: null, matched: [] };
  // Preserve roster order so UI and prompts stay deterministic.
  return { targets: roster.filter((k) => matched.has(k)), matched: roster.filter((k) => matched.has(k)) };
}

/**
 * Recover a discussion state wiped by the legacy hash-load bug.
 *
 * That bug passed the raw server response envelope into discussion.load(),
 * producing a stored state with empty `rounds` while the original (pre-wipe)
 * state survived as a JSON string in the wrapper's own `state_json` field —
 * so the discussion looked empty in the UI even though the data was still
 * on the server (and in localStorage).
 *
 * If `rounds` is empty and `state_json` holds a JSON string, unwrap it and
 * merge the inner content over the wrapper (repeatedly, for double-wipes).
 * Server-envelope fields (`id`, `title`, `question`, `status`,
 * `retrieved_context`) are kept when the inner state lacks them. The stale
 * `state_json` / `created_at` keys are dropped so future persists write a
 * clean state instead of re-wrapping.
 */
export function recoverDiscussionState<T extends object>(state: T): T {
  let current = state as Record<string, unknown>;
  let changed = false;

  // Cap far above any real wrap depth (observed up to 7 on live data) so
  // multi-wrapped histories fully unwrap; the guard only exists to stop a
  // pathological self-nesting string from looping forever.
  for (let depth = 0; depth < 64; depth++) {
    const rounds = current.rounds;
    const hasRounds =
      !!rounds && typeof rounds === "object" && Object.keys(rounds as object).length > 0;
    const nested = current.state_json;
    if (hasRounds || typeof nested !== "string" || nested.trim() === "") break;

    let inner: unknown;
    try {
      inner = JSON.parse(nested);
    } catch {
      break;
    }
    if (!inner || typeof inner !== "object") break;

    // Inner content wins (the wrapper's rounds are empty); fall back to the
    // outer envelope for identity fields the inner state is missing.
    const merged: Record<string, unknown> = { ...current, ...inner };
    for (const key of ["id", "title", "question", "status", "retrieved_context"]) {
      const innerVal = merged[key];
      const outerVal = current[key];
      const missing = innerVal === undefined || innerVal === null || innerVal === "";
      const present = outerVal !== undefined && outerVal !== null && outerVal !== "";
      if (missing && present) merged[key] = outerVal;
    }
    current = merged;
    changed = true;
  }

  // Drop stale wrapper keys so future persists can't re-wrap the state:
  // - after any unwrap (changed), the merged object still carries the nested
  //   string, and
  // - even with rounds present, a leftover *valid* nested state_json string
  //   would be serialized again by persist() — growing one nesting level per
  //   save and burying the real content deeper on every load.
  // Empty/invalid strings never nest deeper, so they are left untouched.
  const nested = current.state_json;
  const nestsObject =
    typeof nested === "string" && nested.trim() !== "" && (() => {
      try {
        const v = JSON.parse(nested);
        return !!v && typeof v === "object";
      } catch {
        return false;
      }
    })();
  if (changed || nestsObject) {
    const out: Record<string, unknown> = { ...current };
    delete out.state_json;
    delete out.created_at;
    return out as T;
  }
  return state;
}

/** Earliest round where at least one model never produced a complete answer
 *  (interrupted, errored or timed out) — the round a "Resume" action should
 *  re-run. Detection uses the round's own entries so roster changes after
 *  the round ran can't produce false positives. Null when nothing to resume. */
export function findResumableRound(
  data: Pick<DiscussionState, "rounds">,
): { round: number; missing: string[] } | null {
  const roundNums = Object.keys(data.rounds)
    .map(Number)
    .sort((a, b) => a - b);
  for (const rn of roundNums) {
    const entries = data.rounds[rn] ?? {};
    const missing = Object.entries(entries)
      .filter(([, r]) => !(r.status === "complete" && r.text))
      .map(([k]) => k);
    if (missing.length > 0) return { round: rn, missing };
  }
  return null;
}
