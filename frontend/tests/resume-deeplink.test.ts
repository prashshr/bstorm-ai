import { describe, it, expect, beforeEach, vi } from "vitest";

/**
 * Regression test: reloading a deep link to an in-progress discussion with RAG
 * context must continue the EXISTING discussion, not create a duplicate.
 */

const createDiscussion = vi.fn(async (_b: unknown) => ({ id: 1, retrieved_context: null, use_rag: false }));
const updateDiscussion = vi.fn(async (_id: unknown, _b: unknown) => ({}));
const chatStream = vi.fn(async (_b: unknown, _cb: (e: unknown) => void) => "ok");

vi.mock("../src/lib/api/client", () => ({
  api: {
    createDiscussion: (b: unknown) => createDiscussion(b),
    updateDiscussion: (id: unknown, b: unknown) => updateDiscussion(id, b),
    chatStream: (b: unknown, cb: (e: unknown) => void) => chatStream(b, cb),
    chat: vi.fn(async () => ({ provider: "p", model: "m", output: "ok" })),
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

describe("resume() on deep link", () => {
  beforeEach(() => {
    localStorage.clear();
    createDiscussion.mockReset();
    updateDiscussion.mockClear();
    chatStream.mockReset();
    discussion.reset();
  });

  it("does not create a new discussion when resuming", async () => {
    chatStream.mockImplementation(async (_b: unknown, onEvent: (e: unknown) => void) => {
      onEvent({ type: "delta", content: "answer" });
      onEvent({ type: "done", content: "answer" });
      return "answer";
    });
    // existing server discussion, RAG context present, no rounds yet
    (discussion as any).load({
      id: 4242,
      question: "Best AI hardware?",
      models: ["openai::gpt-4o"],
      instructions: "",
      status: "in_progress",
      retrieved_context: "UNTRUSTED WEB DATA ...",
      rounds: {},
      userMessages: {},
      consensuses: {},
      use_rag: true,
    });

    await discussion.resume();

    expect(createDiscussion).not.toHaveBeenCalled();   // <-- the regression
    expect(updateDiscussion).toHaveBeenCalled();       // original record updated
    // the id is unchanged, so no duplicate was created
    expect(discussion.data.id).toBe(4242);
    // and the round actually ran
    expect(discussion.data.rounds[1]).toBeDefined();
    expect(discussion.running).toBe(false);
  });

  it("is a no-op without a server-backed discussion id", async () => {
    (discussion as any).load({ id: null, question: "q", models: ["openai::gpt-4o"], rounds: {} });
    await discussion.resume();
    expect(createDiscussion).not.toHaveBeenCalled();
    expect(discussion.running).toBe(false);
  });

  it("is a no-op when the roster is empty", async () => {
    (discussion as any).load({ id: 7, question: "q", models: [], rounds: {} });
    await discussion.resume();
    expect(chatStream).not.toHaveBeenCalled();
  });
});
