import { api } from "../api/client";
import type { DiscussionResponse } from "../api/types";
import { debug } from "./debug.svelte";
import { fuzzyMatch } from "../utils/helpers";

export type HistoryFilter = "all" | "completed" | "running";
export type HistorySort = "newest" | "oldest" | "az";

class HistoryStore {
  #items = $state<DiscussionResponse[]>([]);
  #filter = $state<HistoryFilter>("all");
  #sort = $state<HistorySort>("newest");
  #search = $state("");
  #loading = $state(false);

  get items() {
    return this.#items;
  }
  get filter() {
    return this.#filter;
  }
  get sort() {
    return this.#sort;
  }
  get search() {
    return this.#search;
  }
  get loading() {
    return this.#loading;
  }

  get visible(): DiscussionResponse[] {
    let out = [...this.#items];

    if (this.#filter === "completed") {
      out = out.filter((d) => d.status === "completed");
    } else if (this.#filter === "running") {
      out = out.filter(
        (d) => d.status === "in_progress" || d.status === "new",
      );
    }

    if (this.#search.trim()) {
      out = out.filter(
        (d) =>
          fuzzyMatch(d.question, this.#search) ||
          fuzzyMatch(d.title, this.#search),
      );
    }

    if (this.#sort === "newest") {
      out.sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );
    } else if (this.#sort === "oldest") {
      out.sort(
        (a, b) =>
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      );
    } else {
      out.sort((a, b) => a.question.localeCompare(b.question));
    }

    return out;
  }

  async load(): Promise<void> {
    this.#loading = true;
    try {
      this.#items = await api.listDiscussions();
      debug.log(`Loaded ${this.#items.length} discussions`);
    } catch (e) {
      debug.log(`Failed to load history: ${e}`, "error");
    } finally {
      this.#loading = false;
    }
  }

  async remove(id: number): Promise<void> {
    try {
      await api.deleteDiscussion(id);
      this.#items = this.#items.filter((d) => d.id !== id);
    } catch (e) {
      debug.log(`Failed to delete discussion ${id}: ${e}`, "error");
    }
  }

  setFilter(f: HistoryFilter): void {
    this.#filter = f;
  }
  setSort(s: HistorySort): void {
    this.#sort = s;
  }
  setSearch(q: string): void {
    this.#search = q;
  }
}

export const history = new HistoryStore();
