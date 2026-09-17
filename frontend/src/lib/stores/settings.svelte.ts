import { auth } from "./auth.svelte";

export interface UserSettingsData {
  defaultRagMode: "model-self" | "model-only";
  defaultConsensusEnabled: boolean;
  defaultResponseFormat: "none" | "compact" | "elaborate" | "custom";
  defaultSummaryFormat: "none" | "compact" | "elaborate" | "custom";
  defaultTimeout: number;
  defaultMaxTokens: number;
  themeAccent: string;
  autoMinimizeComposer: boolean;
  showThinking: boolean;
  favoriteModels?: string[];
}

const DEFAULT_SETTINGS: UserSettingsData = {
  defaultRagMode: "model-self",
  defaultConsensusEnabled: false,
  defaultResponseFormat: "compact",
  defaultSummaryFormat: "compact",
  defaultTimeout: 120,
  defaultMaxTokens: 6000,
  themeAccent: "#b35d25",
  autoMinimizeComposer: true,
  showThinking: false,
  favoriteModels: [],
};

class SettingsStore {
  data = $state<UserSettingsData>({ ...DEFAULT_SETTINGS });
  loaded = $state(false);
  modalOpen = $state(false);
  #listeners: ((data: UserSettingsData) => void)[] = [];

  constructor() {
    this.loadFromLocal();
  }

  onLoad(cb: (data: UserSettingsData) => void): () => void {
    this.#listeners.push(cb);
    if (this.loaded) cb(this.data);
    return () => {
      this.#listeners = this.#listeners.filter((fn) => fn !== cb);
    };
  }

  loadFromLocal() {
    try {
      const raw = localStorage.getItem("aiEnsembleUserSettings");
      if (raw) {
        const parsed = JSON.parse(raw);
        this.data = { ...DEFAULT_SETTINGS, ...parsed };
      }
    } catch {
      /* ignore */
    }
  }

  saveToLocal() {
    try {
      localStorage.setItem("aiEnsembleUserSettings", JSON.stringify(this.data));
    } catch {
      /* ignore */
    }
  }

  async fetchRemote() {
    if (!auth.token) return;
    try {
      const res = await fetch("/api/user/settings", {
        headers: { Authorization: `Bearer ${auth.token}` },
      });
      if (res.ok) {
        const json = await res.json();
        if (json.settings && Object.keys(json.settings).length > 0) {
          this.data = { ...DEFAULT_SETTINGS, ...json.settings };
          this.saveToLocal();
          for (const cb of this.#listeners) {
            try { cb(this.data); } catch { /* ignore */ }
          }
        }
      }
    } catch {
      /* ignore */
    } finally {
      this.loaded = true;
    }
  }

  async update(newSettings: Partial<UserSettingsData>) {
    this.data = { ...this.data, ...newSettings };
    this.saveToLocal();

    if (newSettings.themeAccent) {
      document.documentElement.style.setProperty("--accent", newSettings.themeAccent);
    }

    if (!auth.token) return;
    try {
      await fetch("/api/user/settings", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${auth.token}`,
        },
        body: JSON.stringify({ settings: this.data }),
      });
    } catch {
      /* ignore */
    }
  }

  openModal() {
    this.modalOpen = true;
  }

  closeModal() {
    this.modalOpen = false;
  }
}

export const userSettings = new SettingsStore();
