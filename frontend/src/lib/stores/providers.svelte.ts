import { api } from "../api/client";
import type { ProviderCredentialResponse } from "../api/types";
import { debug } from "./debug.svelte";
import { models } from "./models.svelte";
import { PROVIDER_PRESETS } from "../utils/helpers";

class ProvidersStore {
  #list = $state<ProviderCredentialResponse[]>([]);
  #active = $state<string | null>(null);
  #loading = $state(false);
  #verified = $state<Set<string>>(new Set());

  get list() {
    return this.#list;
  }
  get active() {
    return this.#active;
  }
  get loading() {
    return this.#loading;
  }
  get presets() {
    return PROVIDER_PRESETS;
  }

  isVerified(provider: string): boolean {
    return this.#verified.has(provider);
  }

  async load(): Promise<void> {
    this.#loading = true;
    try {
      this.#list = await api.listProviders();
      debug.log(`Loaded ${this.#list.length} providers`);
      if (!this.#active && this.#list.length > 0) {
        this.#active = this.#list[0].provider;
        models.focusProvider(this.#active);
      }
    } catch (e) {
      debug.log(`Failed to load providers: ${e}`, "error");
    } finally {
      this.#loading = false;
    }
  }

  select(provider: string | null): void {
    this.#active = provider;
    if (provider) models.focusProvider(provider);
  }

  find(provider: string): ProviderCredentialResponse | undefined {
    return this.#list.find((p) => p.provider === provider);
  }

  async save(
    provider: string,
    apiKey: string,
    endpoint: string,
    extra?: { project_id?: string; region?: string; adc_json?: string },
  ): Promise<boolean> {
    try {
      await api.upsertProvider({
        provider,
        api_key: apiKey,
        endpoint,
        project_id: extra?.project_id ?? "",
        region: extra?.region ?? "",
        adc_json: extra?.adc_json ?? "",
      });
      await this.load();
      this.#active = provider;
      models.focusProvider(provider);
      debug.log(`Saved provider ${provider}`);
      return true;
    } catch (e) {
      debug.log(`Failed to save provider ${provider}: ${e}`, "error");
      return false;
    }
  }

  async remove(provider: string): Promise<boolean> {
    try {
      await api.deleteProvider(provider);
      this.#verified.delete(provider);
      if (this.#active === provider) this.#active = null;
      await this.load();
      debug.log(`Removed provider ${provider}`);
      return true;
    } catch (e) {
      debug.log(`Failed to remove provider ${provider}: ${e}`, "error");
      return false;
    }
  }

  markVerified(provider: string): void {
    this.#verified = new Set(this.#verified).add(provider);
  }

  /** Re-discover models for every saved provider. Providers that already have
   *  a cached model list from a previous session are skipped so a browser
   *  reload does not re-probe Vertex from scratch — the already-found models
   *  and current selection stay put. Call discover() directly (e.g. refresh
   *  button) to force a fresh search. */
  async verifyAll(): Promise<void> {
    await Promise.all(
      this.#list.map((p) => {
        if (models.hasCache(p.provider)) return Promise.resolve();
        return models
          .discover(p.provider)
          .catch((e) =>
            debug.log(`Provider ${p.provider} re-verify failed: ${e}`, "warn"),
          );
      }),
    );
  }
}

export const providers = new ProvidersStore();
