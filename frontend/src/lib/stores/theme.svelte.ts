const THEME_KEY = "aiEnsembleTheme";
export type Theme = "dark" | "light" | "ps-xai-orange";

class ThemeStore {
  #theme = $state<Theme>("dark");

  get theme() {
    return this.#theme;
  }

  init(): void {
    const saved = localStorage.getItem(THEME_KEY) as Theme | null;
    this.set(saved ?? "dark");
  }

  set(theme: Theme): void {
    this.#theme = theme;
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_KEY, theme);
  }

  toggle(): void {
    this.set(this.#theme === "dark" ? "light" : "dark");
  }
}

export const theme = new ThemeStore();
