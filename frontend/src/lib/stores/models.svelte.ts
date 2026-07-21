import { api } from "../api/client";
import type { HealthStatus } from "../api/types";
import { debug } from "./debug.svelte";
import { providers } from "./providers.svelte";
import { splitModelKey } from "../utils/helpers";

const STORAGE_KEY = "aiEnsembleModels";

class ModelsStore {
  #available = $state<string[]>([]);
  #selected = $state<string[]>([]);
  #health = $state<Record<string, HealthStatus>>({});
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

  isSelected(compositeKey: string): boolean {
    return this.#selected.includes(compositeKey);
  }

  /** Whether a provider already has a cached model list (from a prior session),
   *  so verifyAll can skip re-discovering it on reload. */
  hasCache(provider: string): boolean {
    return (
      !!this.#allByProvider[provider] &&
      this.#allByProvider[provider].length > 0
    );
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
          if (data.allByProvider[prov].length > 0) {
            providers.markVerified(prov);
          }
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
      debug.log(`Model discovery failed for ${provider}: ${e}`, "error");
      throw e;
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

  /** Background health check for one model via a minimal proxy chat call. */
  async checkHealth(compositeKey: string): Promise<void> {
    const { provider, model } = splitModelKey(compositeKey);
    if (!provider || !model) return;
    this.#health = { ...this.#health, [compositeKey]: "testing" };
    try {
      const cred = providers.find(provider);
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
    }
  }

  async checkAllHealth(compositeKeys: string[]): Promise<void> {
    for (const key of compositeKeys) {
      await this.checkHealth(key);
    }
  }
}

export const models = new ModelsStore();
