import { api } from "../api/client";
import type { HealthStatus } from "../api/types";
import { debug } from "./debug.svelte";
import { providers } from "./providers.svelte";
import { splitModelKey, modelSupportsVision } from "../utils/helpers";

/** Generate a tiny PNG with a random 5-char alphanumeric code rendered on a
 *  white background. Returns the PNG as base64 and the code so the caller can
 *  verify the model actually READ the image (not just accepted it). */
function generateVisionTestImage(): { base64: string; code: string } {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let code = "";
  for (let i = 0; i < 5; i++) code += chars[Math.floor(Math.random() * chars.length)];
  const canvas = document.createElement("canvas");
  canvas.width = 120;
  canvas.height = 30;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, 120, 30);
  ctx.fillStyle = "#000";
  ctx.font = "bold 20px monospace";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(code, 60, 16);
  return { base64: canvas.toDataURL("image/png").split(",")[1], code };
}

  const STORAGE_KEY = "aiEnsembleModels";

class ModelsStore {
  #available = $state<string[]>([]);
  #selected = $state<string[]>([]);
  #health = $state<Record<string, HealthStatus>>({});
  #vision = $state<Record<string, boolean>>({});
  #discovering = $state(false);
  /** All discovered models across every provider, keyed by provider. */
  #allByProvider = $state<Record<string, string[]>>({});

  get available() {
    return this.#available;
  }
  get selected() {
    return this.#selected;
  }
  get health() {
    return this.#health;
  }
  get discovering() {
    return this.#discovering;
  }

  /** Flat list of all composite model keys discovered across providers. */
  get all(): string[] {
    return Object.entries(this.#allByProvider).flatMap(([provider, ms]) =>
      ms.map((model) => `${provider}::${model}`),
    );
  }

  healthOf(model: string): HealthStatus {
    return this.#health[model] ?? "unknown";
  }

  visionOf(model: string): boolean | undefined {
    return this.#vision[model];
  }

  isSelected(compositeKey: string): boolean {
    return this.#selected.includes(compositeKey);
  }

  /** Whether a provider already has a cached model list (from a prior session),
   *  so verifyAll can skip re-discovering it on reload. */
  hasCache(provider: string): boolean {
    return provider in this.#allByProvider;
  }

  /** Point the active model list at a provider, using the cached discovery
   *  when present so the MODELS section shows already-found models immediately
   *  after a reload (no re-search needed). */
  focusProvider(provider: string): void {
    this.#available = this.#allByProvider[provider] ?? [];
  }

  /** Persist discovered models + current selection so a browser reload keeps
   *  the already-found models and chosen selection instead of re-discovering
   *  from scratch. */
  persist(): void {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          selected: this.#selected,
          allByProvider: this.#allByProvider,
        }),
      );
    } catch {
      /* ignore quota / private-mode errors */
    }
  }

  /** Restore discovered models + selection from localStorage. Returns true if
   *  anything was restored (so callers can skip an unnecessary re-discovery). */
  restore(): boolean {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return false;
      const data = JSON.parse(raw) as {
        selected?: string[];
        allByProvider?: Record<string, string[]>;
      };
      if (data.allByProvider && Object.keys(data.allByProvider).length > 0) {
        this.#allByProvider = data.allByProvider;
        for (const prov of Object.keys(data.allByProvider)) {
          providers.markVerified(prov);
        }
      }
      if (data.selected && data.selected.length > 0) {
        this.#selected = data.selected;
      }
      return Object.keys(this.#allByProvider).length > 0;
    } catch {
      return false;
    }
  }

  async discover(provider: string): Promise<void> {
    this.#discovering = true;
    try {
      const discovered = await api.listModels(provider);
      this.#available = discovered;
      this.#allByProvider = {
        ...this.#allByProvider,
        [provider]: discovered,
      };
      providers.markVerified(provider);
      this.persist();
      debug.log(`Discovered ${discovered.length} models for ${provider}`);
    } catch (e) {
      this.#available = [];
      providers.markVerified(provider);
      debug.log(`Model discovery failed for ${provider}: ${e}`, "error");
    } finally {
      this.#discovering = false;
    }
  }

  toggle(compositeKey: string): void {
    if (this.#selected.includes(compositeKey)) {
      this.#selected = this.#selected.filter((m) => m !== compositeKey);
    } else {
      this.#selected = [...this.#selected, compositeKey];
    }
    this.persist();
  }

  remove(compositeKey: string): void {
    this.#selected = this.#selected.filter((m) => m !== compositeKey);
    this.persist();
  }

  setSelected(models: string[]): void {
    this.#selected = [...models];
    this.persist();
  }

  clearSelection(): void {
    this.#selected = [];
    this.persist();
  }

  /** Background health check for one model. Tests reachability (text ping)
   *  AND vision capability (probe with a 1×1 GIF attachment). */
  async checkHealth(compositeKey: string): Promise<void> {
    const { provider, model } = splitModelKey(compositeKey);
    if (!provider || !model) return;
    this.#health = { ...this.#health, [compositeKey]: "testing" };
    const cred = providers.find(provider);
    try {
      // First: text-only ping to confirm reachability.
      await api.chat({
        provider,
        model,
        prompt: "ping",
        endpoint: cred?.endpoint ?? "",
        max_tokens: 4,
        temperature: 0,
      });
      this.#health = { ...this.#health, [compositeKey]: "OK" };
    } catch {
      this.#health = { ...this.#health, [compositeKey]: "KO" };
      return;
    }

    // Second: probe vision by embedding a unique code in a tiny PNG and asking
    // the model to read it back. Only models that return the EXACT code are
    // marked vision-capable — this catches providers that silently accept image
    // attachments but don't actually process them (e.g. DeepSeek).
    const { base64, code } = generateVisionTestImage();
    try {
      const res = await api.chat({
        provider,
        model,
        prompt: "reply with only the 5-character code visible in this image",
        endpoint: cred?.endpoint ?? "",
        max_tokens: 8,
        temperature: 0,
        attachments: [{ name: "vision.png", type: "image/png", content: base64 }],
      });
      // The model MUST return the exact 5-char code and nothing else.
      // Strip whitespace/punctuation, then verify it's exactly 5 chars
      // and matches the embedded code. Any deviation = not vision.
      const cleaned = (res.output || "").trim().replace(/[^A-Za-z0-9]/g, "");
      const matched = cleaned.length === 5 && cleaned === code;
      if (!matched) {
        debug.log(`Vision check failed for ${compositeKey}: got "${(res.output || "").trim().slice(0, 40)}" expected "${code}"`);
      }
      this.#vision = { ...this.#vision, [compositeKey]: matched };
    } catch (e) {
      const msg = e instanceof Error ? e.message.toLowerCase() : String(e).toLowerCase();
      if (/image|multimodal|unsupported content|type.*not.*accept|format.*not.*support/i.test(msg)) {
        this.#vision = { ...this.#vision, [compositeKey]: false };
        return;
      }
      // Transient error (rate-limit / timeout) — leave vision status unset so
      // the name heuristic fallback applies.
    }
  }

  async addManualModel(provider: string, modelName: string): Promise<void> {
    const current = this.#allByProvider[provider] ?? [];
    if (current.includes(modelName)) return;
    const updated = [...current, modelName];
    this.#allByProvider = { ...this.#allByProvider, [provider]: updated };
    if (providers.active === provider) {
      this.#available = updated;
    }
    providers.markVerified(provider);
    this.persist();
    debug.log(`Manual model "${modelName}" added for ${provider}`);
  }

  async checkAllHealth(compositeKeys: string[]): Promise<void> {
    for (const key of compositeKeys) {
      await this.checkHealth(key);
    }
  }
}

export const models = new ModelsStore();
