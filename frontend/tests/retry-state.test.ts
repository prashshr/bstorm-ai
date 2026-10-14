import { describe, it, expect, beforeEach, vi } from "vitest";

/**
 * Regression test: retrying a single model must not leave the store in a
 * running state, or the user cannot start another discussion until a reload.
 */

const chatStreamMock = vi.fn(async (_b: unknown, _cb: (e: unknown) => void) => "ok");
const chatMock = vi.fn(async (_b: unknown) => ({ provider: "p", model: "m", output: "ok" }));

vi.mock("../src/lib/api/client", () => ({
  api: {
    createDiscussion: vi.fn(async () => ({ id: 1, retrieved_context: null, use_rag: false })),
    updateDiscussion: vi.fn(async () => ({})),
    chatStream: (b: unknown, cb: (e: unknown) => void) => chatStreamMock(b, cb),
    chat: (b: unknown) => chatMock(b),
    deliberationTopology: vi.fn(async () => ({
      model_count: 1, consensus_score: 4, consensus_percent: 100,
      has_disagreement: false, primary_divergence: "unanimous",
      dissenting_model: null, should_deliberate_round_2: false,
      deliberation_directive: null, summary_badge: "ok", rationale: "ok",
    })),
    analyzeTurn: vi.fn(async () => ({ needs_fresh_entities: false, interaction_type: "x", confidence: 1, reasoning: "" })),
    retrieveContext: vi.fn(async () => ({ retrieved_context: null, query: "", searched: false })),
  },
}));

vi.mock("../src/lib/stores/providers.svelte", () => ({
  providers: { find: () => ({ endpoint: "" }) },
}));

import { discussion } from "../src/lib/stores/discussion.svelte";

describe("retryModel running-state", () => {
  beforeEach(() => {
    localStorage.clear();
    chatStreamMock.mockReset();
    chatMock.mockReset();
    discussion.reset();
  });

  it("returns to idle after a successful retry", async () => {
    chatStreamMock.mockImplementation(async (_b: unknown, onEvent: (e: unknown) => void) => {
      onEvent({ type: "delta", content: "hi" });
      onEvent({ type: "done", content: "hi" });
      return "hi";
    });
    // seed a round with a failed model so retry has something to act on
    (discussion as any).load({
      id: 7, question: "q", models: ["openai::gpt-4o"], status: "stopped",
      rounds: { 1: { "openai::gpt-4o": { text: "", status: "error" } } },
    });
    expect(discussion.running).toBe(false);

    await discussion.retryModel("openai::gpt-4o", 1);
    expect(discussion.running).toBe(false);   // <-- the regression
    expect(["done", "idle"]).toContain(discussion.phase);
  });

  it("returns to idle after a FAILED retry", async () => {
    chatStreamMock.mockRejectedValue(new Error("boom"));
    chatMock.mockRejectedValue(new Error("boom"));
    (discussion as any).load({
      id: 8, question: "q", models: ["openai::gpt-4o"], status: "stopped",
      rounds: { 1: { "openai::gpt-4o": { text: "", status: "timeout" } } },
    });
    await discussion.retryModel("openai::gpt-4o", 1);
    expect(discussion.running).toBe(false);   // <-- the regression on the error path
  });

  it("a new start() works after a retry (not permanently blocked)", async () => {
    chatStreamMock.mockResolvedValue("done");
    (discussion as any).load({
      id: 9, question: "q", models: ["openai::gpt-4o"], status: "stopped",
      rounds: { 1: { "openai::gpt-4o": { text: "", status: "error" } } },
    });
    await discussion.retryModel("openai::gpt-4o", 1);
    expect(discussion.running).toBe(false);
    // the guard in start() relies on running being false
    await expect(
      discussion.start({
        question: "fresh", models: ["openai::gpt-4o"], instructions: "",
        consensusEnabled: false, endpoint: "", consensusModel: "",
        totalRounds: 1, timeout: 120, maxTokens: 100, ragMode: "model-only",
        deepResearch: false, responseFormat: "compact", responseFormatText: "",
        summaryFormat: "compact", summaryFormatText: "", summaryInstructions: "",
      }),
    ).resolves.toBeUndefined();
    expect(discussion.running).toBe(false);
  });
});
