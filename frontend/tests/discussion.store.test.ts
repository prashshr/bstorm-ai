import { describe, it, expect, beforeEach } from "vitest";
import { discussion } from "../src/lib/stores/discussion.svelte";
import type { DiscussionState } from "../src/lib/api/types";

function seed(enabled: boolean) {
  discussion.reset();
  const state: DiscussionState = {
    id: 1,
    timestamp: Date.now(),
    question: "q",
    instructions: "",
    models: ["openai::gpt-4o", "anthropic::claude"],
    rounds: {
      1: {
        "openai::gpt-4o": {
          text: "x".repeat(400),
          status: "complete",
          stats: { outputTokens: 100, durationMs: 1000 },
        },
        "anthropic::claude": {
          text: "y".repeat(200),
          status: "complete",
          stats: { outputTokens: 50, durationMs: 800 },
        },
      },
    },
    consensus: "",
    endpoint: "",
    consensusModel: "openai::gpt-4o",
    timeout: 120,
    maxTokens: 6000,
    attachments: [],
    stats: { totalInputTokens: 0, totalOutputTokens: 150, totalTokens: 150, avgDurationMs: 900, peakContext: 0, modelCount: 2 },
    status: "completed",
    totalRounds: 1,
    use_rag: false,
    deep_research: false,
    retrieved_context: null,
    summaryFormat: "default",
    summaryInstructions: "",
    responseFormat: "default",
  };
  discussion.load(state);
  return enabled;
}

describe("discussion store contributions", () => {
  beforeEach(() => {
    discussion.reset();
    seed(true);
    discussion.data;
  });

  it("derives contribution weights summing to ~100", () => {
    const contribs = discussion.contributions;
    expect(contribs.length).toBe(2);
    const sum = contribs.reduce((a, c) => a + c.weight, 0);
    expect(sum).toBe(100);
  });

  it("weights the larger output higher", () => {
    const contribs = discussion.contributions;
    const gpt = contribs.find((c) => c.model === "openai::gpt-4o")!;
    const claude = contribs.find((c) => c.model === "anthropic::claude")!;
    expect(gpt.weight).toBeGreaterThan(claude.weight);
  });

  it("skipModel marks a result as skipped", () => {
    discussion.skipModel("anthropic::claude", 1);
    expect(discussion.data.rounds[1]["anthropic::claude"].status).toBe(
      "skipped",
    );
  });

  it("buildTranscript includes question, rounds and model names", () => {
    const t = discussion.buildTranscript();
    expect(t).toContain("# Question");
    expect(t).toContain("## Round 1");
    expect(t).toContain("### gpt-4o");
    expect(t).toContain("### claude");
  });
});
