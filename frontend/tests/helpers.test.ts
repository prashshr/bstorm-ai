import { describe, it, expect, vi } from "vitest";
import {
  fuzzyMatch,
  debounce,
  colorForModel,
  splitModelKey,
  formatDate,
  normalizeAuthIdentifier,
  copyToClipboard,
  modelSupportsVision,
  PROVIDER_PRESETS,
  parseModelMentions,
  findResumableRound,
} from "../src/lib/utils/helpers";

describe("copyToClipboard", () => {
  it("uses the async clipboard API in a secure context", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    vi.stubGlobal("isSecureContext", true);
    const ok = await copyToClipboard("hello");
    expect(ok).toBe(true);
    expect(writeText).toHaveBeenCalledWith("hello");
    vi.unstubAllGlobals();
  });
});

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

describe("modelSupportsVision", () => {
  it("correctly identifies vision-capable models", () => {
    expect(modelSupportsVision("gpt-4o")).toBe(true);
    expect(modelSupportsVision("claude-3.5-sonnet")).toBe(true);
    expect(modelSupportsVision("gemini-2.5-flash")).toBe(true);
    expect(modelSupportsVision("qwen-vl-plus")).toBe(true);
  });

  it("correctly identifies text-only models", () => {
    expect(modelSupportsVision("deepseek-chat")).toBe(false);
    expect(modelSupportsVision("deepseek-reasoner")).toBe(false);
    expect(modelSupportsVision("text-davinci-003")).toBe(false);
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

describe("parseModelMentions", () => {
  const roster = [
    "openai::gpt-4o",
    "anthropic::claude-3-5-sonnet-20241022",
    "openrouter::meta-llama/llama-3.3-70b-instruct",
    "gemini::gemini-2.5-flash",
  ];

  it("returns null (everyone) when there are no mentions", () => {
    expect(parseModelMentions("hello everyone", roster).targets).toBeNull();
  });

  it("routes to all models on @all", () => {
    const r = parseModelMentions("@all what do you think?", roster);
    expect(r.targets).toBeNull();
  });

  it("@all wins over specific mentions", () => {
    const r = parseModelMentions("@gpt-4o @all compare", roster);
    expect(r.targets).toBeNull();
  });

  it("matches a model id substring", () => {
    const r = parseModelMentions("@gpt-4o summarize this", roster);
    expect(r.targets).toEqual(["openai::gpt-4o"]);
  });

  it("matches a model id prefix used casually (@claude)", () => {
    const r = parseModelMentions("@claude do you agree?", roster);
    expect(r.targets).toEqual(["anthropic::claude-3-5-sonnet-20241022"]);
  });

  it("matches a provider name for all its models", () => {
    const r = parseModelMentions("@anthropic weigh in", roster);
    expect(r.targets).toEqual(["anthropic::claude-3-5-sonnet-20241022"]);
  });

  it("matches slashed ids like @meta-llama/llama-3.3", () => {
    const r = parseModelMentions("@meta-llama/llama-3.3 thoughts?", roster);
    expect(r.targets).toEqual(["openrouter::meta-llama/llama-3.3-70b-instruct"]);
  });

  it("unions multiple mentions and preserves roster order", () => {
    const r = parseModelMentions("@gemini and @gpt-4o please answer", roster);
    expect(r.targets).toEqual(["openai::gpt-4o", "gemini::gemini-2.5-flash"]);
  });

  it("ignores tokens that match nothing (everyone answers)", () => {
    const r = parseModelMentions("@nonexistentmodel hi", roster);
    expect(r.targets).toBeNull();
    expect(r.matched).toEqual([]);
  });

  it("is case-insensitive", () => {
    const r = parseModelMentions("@GPT-4O @Anthropic", roster);
    expect(r.targets).toEqual(["openai::gpt-4o", "anthropic::claude-3-5-sonnet-20241022"]);
  });

  it("handles empty roster or empty text", () => {
    expect(parseModelMentions("@gpt-4o", []).targets).toBeNull();
    expect(parseModelMentions("", roster).targets).toBeNull();
  });
});

describe("findResumableRound", () => {
  const complete = (text = "answer") => ({ status: "complete" as const, text });

  it("returns null when there are no rounds", () => {
    expect(findResumableRound({ rounds: {} })).toBeNull();
  });

  it("returns null when every model completed", () => {
    expect(
      findResumableRound({
        rounds: { 1: { a: complete(), b: complete() } },
      }),
    ).toBeNull();
  });

  it("finds a round with a skipped/interrupted model", () => {
    const r = findResumableRound({
      rounds: { 1: { a: complete(), b: { status: "skipped", text: "" } } },
    });
    expect(r?.round).toBe(1);
    expect(r?.missing).toEqual(["b"]);
  });

  it("finds the earliest incomplete round", () => {
    const r = findResumableRound({
      rounds: {
        1: { a: { status: "error", text: "" }, b: complete() },
        2: { a: { status: "waiting", text: "" } },
      },
    });
    expect(r?.round).toBe(1);
    expect(r?.missing).toEqual(["a"]);
  });

  it("treats complete-but-empty responses as missing", () => {
    const r = findResumableRound({ rounds: { 1: { a: complete("") } } });
    expect(r?.missing).toEqual(["a"]);
  });

  it("ignores models added to the roster after the round ran", () => {
    // round 1 only ever ran model a; model b joined later and must not
    // make the old round look resumable
    expect(findResumableRound({ rounds: { 1: { a: complete() } } })).toBeNull();
  });

  it("returns entries for a round that never got responses", () => {
    const r = findResumableRound({
      rounds: { 1: { a: { status: "waiting", text: "" } } },
    });
    expect(r).toEqual({ round: 1, missing: ["a"] });
  });
});
