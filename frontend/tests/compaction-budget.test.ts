import { describe, it, expect } from "vitest";
import {
  buildCompactedTranscript,
  PROMPT_BUDGET_CHARS,
} from "../src/lib/utils/compaction";
import type { DiscussionState } from "../src/lib/api/types";

/**
 * The budget contract, stated explicitly:
 *
 *   budget = max(FLOOR_BUDGET_CHARS, PROMPT_BUDGET_CHARS - promptLength)
 *
 * The floor is deliberate — a huge prompt (RAG context, instructions,
 * attachments) must not starve the transcript to nothing. When it applies, the
 * combined prompt therefore EXCEEDS the nominal budget, and the result reports
 * `floorApplied` so that is visible instead of silent. These tests assert both
 * the bounded case and the floored case, and that the floor is reported.
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

const BIG = () => makeData(40, 12_000, 3_000);

describe("compaction budget contract", () => {
  it("bounds the transcript at the most aggressive tier", () => {
    const r = buildCompactedTranscript(BIG(), 41, "openai::gpt-4o", 40_000);
    expect(r.text.length).toBeLessThanOrEqual(r.budgetUsed);
    expect(r.text).toContain("truncated");
    expect(r.tier).toBe(2);
  });

  it("does not truncate when the transcript already fits", () => {
    const r = buildCompactedTranscript(makeData(2, 300, 500), 3, "openai::gpt-4o", 100);
    expect(r.tier).toBe(0);
    expect(r.text).not.toContain("transcript truncated");
    expect(r.text).toContain("question 1");
    expect(r.floorApplied).toBe(false);
  });

  it("reports floorApplied when a huge prompt leaves less room than the floor", () => {
    // 65k prompt of the 70k budget leaves 5k — below the 15k floor.
    const r = buildCompactedTranscript(BIG(), 41, "openai::gpt-4o", 65_000);
    expect(r.floorApplied).toBe(true);
    expect(r.budgetUsed).toBe(15_000);
    // The floor is intentional: the transcript is NOT cut below it, which is
    // why the combined prompt then exceeds the nominal budget.
    expect(r.text.length).toBeLessThanOrEqual(15_000);
    expect(r.text.length).toBeGreaterThan(0);
  });

  it("honours the full remaining budget when it is above the floor", () => {
    const promptLength = 20_000;
    const r = buildCompactedTranscript(BIG(), 41, "openai::gpt-4o", promptLength);
    expect(r.floorApplied).toBe(false);
    expect(r.budgetUsed).toBe(PROMPT_BUDGET_CHARS - promptLength);
    expect(r.text.length).toBeLessThanOrEqual(PROMPT_BUDGET_CHARS - promptLength);
  });
});
