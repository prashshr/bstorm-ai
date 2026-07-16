import { api } from "../api/client";
import type { HealthStatus } from "../api/types";
import { debug } from "./debug.svelte";
import { providers } from "./providers.svelte";
import { splitModelKey } from "../utils/helpers";

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
  }

  remove(compositeKey: string): void {
    this.#selected = this.#selected.filter((m) => m !== compositeKey);
  }

  setSelected(models: string[]): void {
    this.#selected = [...models];
  }

  clearSelection(): void {
    this.#selected = [];
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
