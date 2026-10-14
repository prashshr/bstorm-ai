const THEME_KEY = "aiEnsembleTheme";
export type Theme = "dark" | "light" | "high-contrast" | "ps-xai-orange";

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
    const themes: Theme[] = ["dark", "light", "high-contrast", "ps-xai-orange"];
    const currentIndex = themes.indexOf(this.#theme);
    const nextIndex = (currentIndex + 1) % themes.length;
    this.set(themes[nextIndex]);
  }
}

export const theme = new ThemeStore();
