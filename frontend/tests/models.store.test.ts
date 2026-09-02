import { describe, it, expect, beforeEach, vi } from "vitest";

vi.mock("../src/lib/api/client", () => ({
  api: {
    listModels: vi.fn(async () => ["gpt-4o", "claude-3-7-sonnet", "deepseek-chat"]),
    chat: vi.fn(async () => ({ output: "ping" })),
  },
}));

import { models } from "../src/lib/stores/models.svelte";

describe("models store favorites and selection", () => {
  beforeEach(() => {
    localStorage.clear();
    models.clearSelection();
    models.clearFavorites();
  });

  it("toggles favorite models and stores composite keys", () => {
    const key1 = "openrouter::openai/gpt-4o";
    const key2 = "opencode::openai/gpt-4o";

    expect(models.isFavorite(key1)).toBe(false);

    models.toggleFavorite(key1);
    expect(models.isFavorite(key1)).toBe(true);
    expect(models.favorites).toContain(key1);

    models.toggleFavorite(key2);
    expect(models.favorites.length).toBe(2);
    expect(models.isFavorite(key2)).toBe(true);

    // Toggle off
    models.toggleFavorite(key1);
    expect(models.isFavorite(key1)).toBe(false);
    expect(models.favorites).not.toContain(key1);
    expect(models.favorites).toContain(key2);
  });

  it("persists and restores favorites from localStorage", () => {
    models.toggleFavorite("vertex::gemini-2.5-pro");
    models.toggleFavorite("openrouter::deepseek/deepseek-chat");

    expect(models.favorites.length).toBe(2);

    // Call restore
    const restored = models.restore();
    expect(models.isFavorite("vertex::gemini-2.5-pro")).toBe(true);
    expect(models.isFavorite("openrouter::deepseek/deepseek-chat")).toBe(true);
  });
});
