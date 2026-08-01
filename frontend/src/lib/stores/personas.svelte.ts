import { api } from "../api/client";
import type { AgentPersona, AgentPersonaCreateRequest, AgentPersonaUpdateRequest } from "../api/types";
import { debug } from "./debug.svelte";

class PersonasStore {
  #list = $state<AgentPersona[]>([]);
  #loading = $state(false);

  get list() {
    return this.#list;
  }
  get loading() {
    return this.#loading;
  }

  async load(): Promise<void> {
    this.#loading = true;
    try {
      this.#list = await api.listPersonas();
      debug.log(`[ai-ensemble] Loaded ${this.#list.length} custom agent personas`);
    } catch (e) {
      debug.log(`Failed to load personas: ${e}`, "warn");
    } finally {
      this.#loading = false;
    }
  }

  async create(req: AgentPersonaCreateRequest): Promise<AgentPersona | null> {
    try {
      const persona = await api.createPersona(req);
      this.#list = [...this.#list, persona];
      return persona;
    } catch (e) {
      debug.log(`Failed to create persona: ${e}`, "error");
      return null;
    }
  }

  async update(id: number, req: AgentPersonaUpdateRequest): Promise<boolean> {
    try {
      const updated = await api.updatePersona(id, req);
      this.#list = this.#list.map((p) => (p.id === id ? updated : p));
      return true;
    } catch (e) {
      debug.log(`Failed to update persona: ${e}`, "error");
      return false;
    }
  }

  async remove(id: number): Promise<boolean> {
    try {
      await api.deletePersona(id);
      this.#list = this.#list.filter((p) => p.id !== id);
      return true;
    } catch (e) {
      debug.log(`Failed to delete persona: ${e}`, "error");
      return false;
    }
  }

  findForModel(modelKey: string): AgentPersona | undefined {
    return this.#list.find((p) => p.model === modelKey);
  }
}

export const personas = new PersonasStore();
