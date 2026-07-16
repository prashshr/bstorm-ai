export type Tab = "new" | "current" | "history";

const VALID: Tab[] = ["new", "current", "history"];

class NavStore {
  #tab = $state<Tab>("new");
  #sidebarCollapsed = $state(false);
  #focusMode = $state(false);
  #settingByHash = false;

  get tab() {
    return this.#tab;
  }
  get sidebarCollapsed() {
    return this.#sidebarCollapsed;
  }
  get focusMode() {
    return this.#focusMode;
  }

  init(): void {
    this.#applyHash();
    window.addEventListener("hashchange", () => {
      if (this.#settingByHash) return;
      this.#applyHash();
    });
  }

  #applyHash(): void {
    const h = window.location.hash.replace(/^#/, "") as Tab;
    if (VALID.includes(h)) this.#tab = h;
  }

  go(tab: Tab): void {
    this.#tab = tab;
    this.#settingByHash = true;
    window.location.hash = tab;
    setTimeout(() => (this.#settingByHash = false), 0);
  }

  toggleSidebar(): void {
    this.#sidebarCollapsed = !this.#sidebarCollapsed;
  }
  toggleFocusMode(): void {
    this.#focusMode = !this.#focusMode;
  }
}

export const nav = new NavStore();
