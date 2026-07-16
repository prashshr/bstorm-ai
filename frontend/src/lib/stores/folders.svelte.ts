import { api } from "../api/client";
import type { Folder } from "../api/types";
import { debug } from "./debug.svelte";

class FolderStore {
  #list = $state<Folder[]>([]);
  #loading = $state(false);

  get list(): Folder[] {
    return this.#list;
  }
  get loading(): boolean {
    return this.#loading;
  }

  async load(): Promise<void> {
    this.#loading = true;
    try {
      this.#list = await api.listFolders();
    } catch (e) {
      debug.log(`Failed to load folders: ${e}`, "error");
    } finally {
      this.#loading = false;
    }
  }

  async create(name: string): Promise<Folder> {
    const f = await api.createFolder({ name });
    this.#list = [...this.#list, f];
    return f;
  }

  async rename(id: number, name: string): Promise<void> {
    const updated = await api.updateFolder(id, { name });
    this.#list = this.#list.map((f) => (f.id === id ? updated : f));
  }

  async reorder(id: number, position: number): Promise<void> {
    const updated = await api.updateFolder(id, { position });
    this.#list = this.#list.map((f) => (f.id === id ? updated : f));
  }

  async remove(id: number): Promise<void> {
    await api.deleteFolder(id);
    this.#list = this.#list.filter((f) => f.id !== id);
  }

  async addDiscussion(folderId: number, discussionId: number): Promise<void> {
    const updated = await api.addFolderDiscussion(folderId, discussionId);
    this.#list = this.#list.map((f) => (f.id === folderId ? updated : f));
  }

  async removeDiscussion(folderId: number, discussionId: number): Promise<void> {
    const updated = await api.removeFolderDiscussion(folderId, discussionId);
    this.#list = this.#list.map((f) => (f.id === folderId ? updated : f));
  }

  /** Discussions contained in any folder, keyed for quick lookup. */
  get folderDiscussionIds(): Set<number> {
    const s = new Set<number>();
    for (const f of this.#list) for (const id of f.discussion_ids) s.add(id);
    return s;
  }
}

export const folders = new FolderStore();
