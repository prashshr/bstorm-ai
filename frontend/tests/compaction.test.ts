import { describe, it, expect } from "vitest";
import {
  buildPromptTranscript,
  buildCompactedTranscript,
  PROMPT_BUDGET_CHARS,
} from "../src/lib/utils/compaction";
import type { DiscussionState } from "../src/lib/api/types";

const MODELS = ["openai::gpt-4o", "anthropic::claude", "gemini::flash", "openrouter::llama"];

function respText(turn: number, model: string, len: number): string {
  return `resp-turn${turn}-${model} ` + "x".repeat(len) + `-ENDMARKER${turn}`;
}

function makeData(turns: number, respLen: number) {
  const userMessages: Record<number, string> = {};
  const rounds: DiscussionState["rounds"] = {};
  const consensuses: Record<number, string> = {};
  for (let i = 1; i <= turns; i++) {
    userMessages[i] = `question ${i} ` + "u".repeat(200);
    rounds[i] = {};
    for (const m of MODELS) {
      rounds[i][m] = { text: respText(i, m, respLen), status: "complete" };
    }
    consensuses[i] = `consensus ${i} ` + "c".repeat(3000);
  }
  return { userMessages, rounds, consensuses };
}

const KEY = "openai::gpt-4o";

describe("buildPromptTranscript", () => {
  it("renders the legacy structure at tier 0", () => {
    const data = makeData(3, 500);
    const out = buildPromptTranscript(data, 3, KEY, 0);
    expect(out).toContain("User (turn 1): question 1");
    expect(out).toContain("### Your Response (turn 1):");
    expect(out).toContain("### Peer Model: claude");
    expect(out).toContain("[PEER PERSPECTIVES - TURN 2]");
    expect(out).toContain("Consensus synthesis (turn 1):");
    // Small responses are not truncated at tier 0
    expect(out).toContain("-ENDMARKER1");
    expect(out).toContain("-ENDMARKER2");
  });

  it("caps oversized responses at 6000 chars at tier 0", () => {
    const data = makeData(2, 7000);
    const out = buildPromptTranscript(data, 2, KEY, 0);
    expect(out).not.toContain("-ENDMARKER1");
    expect(out).toContain("[truncated]");
  });
});

describe("buildCompactedTranscript", () => {
  it("keeps tier 0 while the transcript fits the budget", () => {
    const data = makeData(3, 1000);
    const r = buildCompactedTranscript(data, 3, KEY, 0);
    expect(r.tier).toBe(0);
    expect(r.text).toContain("-ENDMARKER2");
  });

  it("uses tier 1 for long discussions, condensing older turns only", () => {
    // 8 turns × 4 models × ~3050 chars + consensus ≈ 122k chars > budget
    const data = makeData(8, 3000);
    const r = buildCompactedTranscript(data, 9, KEY, 0);
    expect(r.tier).toBe(1);
    expect(r.text.length).toBeLessThanOrEqual(PROMPT_BUDGET_CHARS);
    expect(r.originalChars).toBeGreaterThan(PROMPT_BUDGET_CHARS);
    // most recent prior turn stays full detail
    expect(r.text).toContain("-ENDMARKER8");
    // older turns are condensed
    expect(r.text).not.toContain("-ENDMARKER1");
    expect(r.text).not.toContain("-ENDMARKER7");
    expect(r.text).toContain("[truncated]");
    // structure survives compaction
    expect(r.text).toContain("User (turn 1):");
    expect(r.text).toContain("### Peer Model:");
    expect(r.text).toContain("Consensus synthesis (turn 3):");
  });

  it("falls back to tier 2 when even tier 1 exceeds the budget", () => {
    const data = makeData(10, 3000);
    const r = buildCompactedTranscript(data, 11, KEY, 0);
    expect(r.tier).toBe(2);
    expect(r.text.length).toBeLessThanOrEqual(PROMPT_BUDGET_CHARS);
    // every prior turn is condensed, including the most recent
    expect(r.text).not.toContain("-ENDMARKER10");
    expect(r.text).toContain("User (turn 10):");
    expect(r.text).toContain("### Peer Model:");
  });

  it("shrinks the transcript budget by the prompt size already used", () => {
    const data = makeData(8, 3000);
    const r = buildCompactedTranscript(data, 9, KEY, 60_000);
    // budget floors at 15k, so even tier 1 (~61k) cannot fit
    expect(r.tier).toBe(2);
    expect(r.text.length).toBeLessThanOrEqual(PROMPT_BUDGET_CHARS);
  });

  it("produces compact output when a huge RAG context leaves only the floor", () => {
    const data = makeData(6, 3000);
    const r = buildCompactedTranscript(data, 7, KEY, 1_000_000);
    expect(r.tier).toBe(2);
    expect(r.text.length).toBeLessThanOrEqual(PROMPT_BUDGET_CHARS);
  });
});
