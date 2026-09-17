import { api } from "../api/client";
import type { HealthStatus } from "../api/types";
import { debug } from "./debug.svelte";
import { providers } from "./providers.svelte";
import { splitModelKey, modelSupportsVision } from "../utils/helpers";
import { userSettings } from "./settings.svelte";
import { auth } from "./auth.svelte";

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
  const FAVORITES_BACKUP_KEY = "aiEnsembleFavorites";

class ModelsStore {
  #available = $state<string[]>([]);
  #selected = $state<string[]>([]);
  #favorites = $state<string[]>([]);
  #health = $state<Record<string, HealthStatus>>({});
  #errors = $state<Record<string, string>>({});
  #vision = $state<Record<string, boolean>>({});
  #discovering = $state(false);
  /** All discovered models across every provider, keyed by provider. */
  #allByProvider = $state<Record<string, string[]>>({});
  /** Filter preference to show only OK models per provider. */
  #showOnlyOkByProvider = $state<Record<string, boolean>>({});

  constructor() {
    this.restore();
    try {
      userSettings.onLoad((settings) => {
        if (Array.isArray(settings.favoriteModels) && settings.favoriteModels.length > 0) {
          this.syncRemoteFavorites(settings.favoriteModels);
        }
      });
    } catch {
      /* ignore if settings store is still initializing */
    }
  }

  get available() {
    return this.#available;
  }
  get selected() {
    return this.#selected;
  }
  get favorites() {
    return this.#favorites;
  }
  get health() {
    return this.#health;
  }
  get discovering() {
    return this.#discovering;
  }

  showOnlyOk(provider: string): boolean {
    return this.#showOnlyOkByProvider[provider] ?? false;
  }

  setShowOnlyOk(provider: string, val: boolean): void {
    this.#showOnlyOkByProvider = { ...this.#showOnlyOkByProvider, [provider]: val };
    this.persist();
  }

  toggleShowOnlyOk(provider: string): void {
    this.setShowOnlyOk(provider, !this.showOnlyOk(provider));
  }

  okCount(provider: string): number {
    const ms = this.#allByProvider[provider] ?? [];
    return ms.filter((m) => this.#health[`${provider}::${m}`] === "OK").length;
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

  errorOf(model: string): string {
    return this.#errors[model] ?? "";
  }

  visionOf(model: string): boolean | undefined {
    return this.#vision[model];
  }

  isSelected(compositeKey: string): boolean {
    return this.#selected.includes(compositeKey);
  }

  isFavorite(compositeKey: string): boolean {
    return this.#favorites.includes(compositeKey);
  }

  syncRemoteFavorites(remoteFavs: string[]): void {
    if (!Array.isArray(remoteFavs)) return;
    const merged = Array.from(new Set([...this.#favorites, ...remoteFavs]));
    if (merged.length !== this.#favorites.length) {
      this.#favorites = merged;
      this.persist();
    }
  }

  toggleFavorite(compositeKey: string): void {
    if (this.#favorites.includes(compositeKey)) {
      this.#favorites = this.#favorites.filter((m) => m !== compositeKey);
    } else {
      this.#favorites = [...this.#favorites, compositeKey];
    }
    this.persist();
    if (auth.isAuthenticated) {
      userSettings.update({ favoriteModels: this.#favorites });
    }
  }

  clearFavorites(): void {
    this.#favorites = [];
    try {
      localStorage.removeItem(FAVORITES_BACKUP_KEY);
    } catch {
      /* ignore */
    }
    this.persist();
    if (auth.isAuthenticated) {
      userSettings.update({ favoriteModels: [] });
    }
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
      localStorage.setItem(FAVORITES_BACKUP_KEY, JSON.stringify(this.#favorites));
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          selected: this.#selected,
          favorites: this.#favorites,
          allByProvider: this.#allByProvider,
          showOnlyOkByProvider: this.#showOnlyOkByProvider,
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
      if (raw) {
        const data = JSON.parse(raw) as {
          selected?: string[];
          favorites?: string[];
          allByProvider?: Record<string, string[]>;
          showOnlyOkByProvider?: Record<string, boolean>;
        };
        if (data.showOnlyOkByProvider) {
          this.#showOnlyOkByProvider = data.showOnlyOkByProvider;
        }
        if (data.allByProvider && Object.keys(data.allByProvider).length > 0) {
          this.#allByProvider = data.allByProvider;
          for (const prov of Object.keys(data.allByProvider)) {
            providers.markVerified(prov);
          }
        }
        if (data.selected && data.selected.length > 0) {
          this.#selected = data.selected;
        }
        if (data.favorites && Array.isArray(data.favorites)) {
          this.#favorites = data.favorites;
        }
      }

      // Check secondary backup key if favorites were empty
      if (this.#favorites.length === 0) {
        const backupRaw = localStorage.getItem(FAVORITES_BACKUP_KEY);
        if (backupRaw) {
          const parsed = JSON.parse(backupRaw);
          if (Array.isArray(parsed) && parsed.length > 0) {
            this.#favorites = parsed;
          }
        }
      }

      return Object.keys(this.#allByProvider).length > 0 || this.#favorites.length > 0;
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
        max_tokens: 16,
        temperature: 0.7,
      });
      this.#health = { ...this.#health, [compositeKey]: "OK" };
      delete this.#errors[compositeKey];
    } catch (err: any) {
      const errMsg = err?.message || String(err);
      this.#health = { ...this.#health, [compositeKey]: "KO" };
      this.#errors = { ...this.#errors, [compositeKey]: errMsg };
      debug.log(`Health check failed for ${compositeKey}: ${errMsg}`, "warn");
      return;
    }

    // Second: probe vision only if model name indicates multimodal support
    if (!modelSupportsVision(model)) {
      this.#vision = { ...this.#vision, [compositeKey]: false };
      return;
    }

    const { base64, code } = generateVisionTestImage();
    try {
      const res = await api.chat({
        provider,
        model,
        prompt: "reply with only the 5-character code visible in this image",
        endpoint: cred?.endpoint ?? "",
        max_tokens: 16,
        temperature: 0.7,
        attachments: [{ name: "vision.png", type: "image/png", content: base64 }],
      });
      const cleaned = (res.output || "").trim().replace(/[^A-Za-z0-9]/g, "");
      const matched = cleaned.length === 5 && cleaned === code;
      this.#vision = { ...this.#vision, [compositeKey]: matched };
    } catch {
      // If image probe fails, leave vision status unset or false, but text reachability stays OK
      this.#vision = { ...this.#vision, [compositeKey]: false };
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
    const queue = [...compositeKeys];
    const concurrency = 8;
    let index = 0;

    const worker = async (): Promise<void> => {
      while (index < queue.length) {
        const key = queue[index++];
        if (!key) break;
        await this.checkHealth(key);
        await new Promise((r) => setTimeout(r, 60));
      }
    };

    const workers = Array.from({ length: Math.min(concurrency, queue.length) }, () => worker());
    await Promise.all(workers);
  }
}

export const models = new ModelsStore();
