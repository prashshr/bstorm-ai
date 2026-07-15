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
    key: "google-vertex",
    name: "Google Vertex",
    endpoint: "https://us-central1-aiplatform.googleapis.com/v1",
  },
  { key: "mammouth", name: "Mammouth AI", endpoint: "https://api.mammouth.ai/v1" },
  { key: "requesty", name: "Requesty AI", endpoint: "https://router.requesty.ai/v1" },
  { key: "custom", name: "Custom Compatible", endpoint: "" },
];
