/**
 * Normalize an auth identifier. The backend expects an EmailStr, but the UI
 * allows plain usernames (e.g. "admin") for convenience, mapping them to the
 * local domain — matching the legacy monolith behaviour exactly.
 */
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

/** Best-effort check whether a model name suggests vision/multimodal support. */
const VISION_RE = /(gpt-4o|gpt-4-visual|gpt-4-turbo|vision|gemini|claude-3\.5|claude-4|llama-3\.2-vision|llama-4|llava|qwen-vl|qwen2\.5-vl|pixtral|moondream|ministral|gemma-3|internvl|smolvlm|aya-vision|phi-3-vision|phi-4-vision|o1|o4)/i;
const TEXT_ONLY_RE = /(deepseek|reasoner|o1-mini|o3-mini|text-|instruct)/i;

export function modelSupportsVision(modelName: string): boolean {
  if (TEXT_ONLY_RE.test(modelName) && !VISION_RE.test(modelName)) return false;
  return VISION_RE.test(modelName);
}

/** Human-readable provider name for a credential key, falling back to a
 *  prettified version of the key when no preset matches. An optional
 *  `label` overrides the display name (used for custom providers that
 *  the user has named). */
export function providerDisplayName(key: string, label?: string): string {
  if (label) return label;
  if (PRESET_NAME_BY_KEY[key]) return PRESET_NAME_BY_KEY[key];
  return key
    .split(/[-_]/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
