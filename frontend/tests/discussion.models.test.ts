import { describe, it, expect, beforeEach, vi } from "vitest";
import { discussion } from "../src/lib/stores/discussion.svelte";

// Mock the API client so turns run without a network.
vi.mock("../src/lib/api/client", () => ({
  api: {
    createDiscussion: vi.fn(async () => ({ id: 1, retrieved_context: null })),
    updateDiscussion: vi.fn(async () => ({})),
    chatStream: vi.fn(async (_body: unknown, onEvent: (e: { type: string; content?: string }) => void) => {
      onEvent({ type: "delta", content: "hello" });
      return "hello";
    }),
    chat: vi.fn(async () => ({ output: "consensus" })),
  },
}));

describe("discussion model list across turns", () => {
  beforeEach(() => {
    discussion.reset();
  });

  it("captures the model list at start and uses it for the first turn", async () => {
    await discussion.start({
      question: "q",
      models: ["a::m1", "b::m2"],
      instructions: "",
      consensusEnabled: true,
      endpoint: "",
      consensusModel: "a::m1",
      totalRounds: 1,
      timeout: 120,
      maxTokens: 6000,
      ragMode: "model-self",
      deepResearch: false,
      responseFormat: "default",
      summaryFormat: "default",
      summaryFormatText: "",
      responseFormatText: "",
      summaryInstructions: "",
    });
    expect(discussion.data.models).toEqual(["a::m1", "b::m2"]);
    expect(Object.keys(discussion.data.rounds[1])).toEqual(["a::m1", "b::m2"]);
  });

  it("propagates an add/remove to the next turn via nextTurn(modelKeys)", async () => {
    await discussion.start({
      question: "q",
      models: ["a::m1"],
      instructions: "",
      consensusEnabled: true,
      endpoint: "",
      consensusModel: "a::m1",
      totalRounds: 1,
      timeout: 120,
      maxTokens: 6000,
      ragMode: "model-self",
      deepResearch: false,
      responseFormat: "default",
      summaryFormat: "default",
      summaryFormatText: "",
      responseFormatText: "",
      summaryInstructions: "",
    });
    // Simulate the user removing m1 and adding b::m2 + c::m3 between turns.
    await discussion.nextTurn("follow up", ["b::m2", "c::m3"]);
    expect(discussion.data.models).toEqual(["b::m2", "c::m3"]);
    expect(Object.keys(discussion.data.rounds[2])).toEqual(["b::m2", "c::m3"]);
  });
});
