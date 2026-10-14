import { describe, it, expect } from "vitest";
import { buildCompactedTranscript } from "../src/lib/utils/compaction";
import type { DiscussionState } from "../src/lib/api/types";

/**
 * Regression test: the final compaction tier must honour the budget so
 * prompt + transcript together stay bounded for very large discussions.
 */
const MODELS = ["openai::gpt-4o"];

function makeData(turns: number, respLen: number, consLen: number) {
  const userMessages: Record<number, string> = {};
  const rounds: DiscussionState["rounds"] = {};
  const consensuses: Record<number, string> = {};
  for (let i = 1; i <= turns; i++) {
    userMessages[i] = `question ${i} ` + "u".repeat(200);
    rounds[i] = {};
    for (const m of MODELS) {
      rounds[i][m] = { text: `resp${i} ` + "x".repeat(respLen), status: "complete" };
    }
    consensuses[i] = `consensus ${i} ` + "c".repeat(consLen);
  }
  return { userMessages, rounds, consensuses };
}

describe("compaction budget enforcement", () => {
  it("bounds the transcript at the most aggressive tier", () => {
    const data = makeData(40, 12_000, 3_000); // ~480k chars
    const r = buildCompactedTranscript(data, 41, "openai::gpt-4o", 40_000);
    const budget = Math.max(15_000, 70_000 - 40_000); // 30k remaining
    expect(r.text.length).toBeLessThanOrEqual(budget);
    expect(r.text).toContain("truncated");
    expect(r.tier).toBe(2);
  });

  it("does not truncate when the transcript already fits", () => {
    const data = makeData(2, 300, 500);
    const r = buildCompactedTranscript(data, 3, "openai::gpt-4o", 100);
    expect(r.tier).toBe(0);
    expect(r.text).not.toContain("transcript truncated");
    expect(r.text).toContain("question 1");
  });

  it("keeps at least the floor when a huge RAG prompt leaves little room", () => {
    const data = makeData(40, 12_000, 3_000);
    const r = buildCompactedTranscript(data, 41, "openai::gpt-4o", 65_000);
    expect(r.text.length).toBeLessThanOrEqual(15_000);
    expect(r.text.length).toBeGreaterThan(0);
  });
});
