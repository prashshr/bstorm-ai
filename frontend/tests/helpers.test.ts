import { describe, it, expect, vi } from "vitest";
import {
  fuzzyMatch,
  debounce,
  colorForModel,
  splitModelKey,
  formatDate,
  normalizeAuthIdentifier,
  PROVIDER_PRESETS,
} from "../src/lib/utils/helpers";

describe("normalizeAuthIdentifier", () => {
  it("maps a bare username to the local domain", () => {
    expect(normalizeAuthIdentifier("admin")).toBe("admin@local.ai-ensemble");
  });

  it("passes through an existing email (lowercased/trimmed)", () => {
    expect(normalizeAuthIdentifier("  User@Example.com ")).toBe(
      "user@example.com",
    );
  });

  it("returns empty string for blank input", () => {
    expect(normalizeAuthIdentifier("   ")).toBe("");
  });
});

describe("fuzzyMatch", () => {
  it("matches an empty query", () => {
    expect(fuzzyMatch("anything", "")).toBe(true);
  });

  it("matches a subsequence case-insensitively", () => {
    expect(fuzzyMatch("Claude Sonnet", "clsn")).toBe(true);
    expect(fuzzyMatch("gpt-4o-mini", "4omini")).toBe(true);
  });

  it("rejects non-subsequences", () => {
    expect(fuzzyMatch("gpt", "xyz")).toBe(false);
  });
});

describe("splitModelKey", () => {
  it("splits provider::model", () => {
    expect(splitModelKey("openai::gpt-4o")).toEqual({
      provider: "openai",
      model: "gpt-4o",
    });
  });

  it("handles models that themselves contain colons", () => {
    expect(splitModelKey("vertex::google/gemini-1.5::pro")).toEqual({
      provider: "vertex",
      model: "google/gemini-1.5::pro",
    });
  });

  it("falls back to empty provider when no separator", () => {
    expect(splitModelKey("plainmodel")).toEqual({
      provider: "",
      model: "plainmodel",
    });
  });
});

describe("colorForModel", () => {
  it("is deterministic and returns an hsl string", () => {
    const a = colorForModel("openai::gpt-4o");
    const b = colorForModel("openai::gpt-4o");
    expect(a).toBe(b);
    expect(a).toMatch(/^hsl\(\d+, 70%, 55%\)$/);
  });

  it("differs for different names", () => {
    expect(colorForModel("a")).not.toBe(colorForModel("b"));
  });
});

describe("formatDate", () => {
  it("returns empty string for falsy/invalid input", () => {
    expect(formatDate(null)).toBe("");
    expect(formatDate("not-a-date")).toBe("");
  });

  it("formats a valid ISO date", () => {
    expect(formatDate("2026-01-15T10:30:00Z")).not.toBe("");
  });
});

describe("debounce", () => {
  it("invokes the function only once after the wait window", () => {
    vi.useFakeTimers();
    const fn = vi.fn();
    const d = debounce(fn, 100);
    d();
    d();
    d();
    expect(fn).not.toHaveBeenCalled();
    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });
});

describe("PROVIDER_PRESETS", () => {
  it("includes the core providers and a custom option", () => {
    const keys = PROVIDER_PRESETS.map((p) => p.key);
    expect(keys).toContain("openrouter");
    expect(keys).toContain("openai");
    expect(keys).toContain("custom");
  });
});
