import { splitModelKey } from "./helpers";
import type { DiscussionState } from "../api/types";

/**
 * Context compaction for prompt transcripts.
 *
 * Long discussions used to ship every prior response (up to 6k chars each)
 * into every prompt, which overflows smaller context windows. This module
 * builds the transcript with tiered budgets:
 *
 * - Tier 0: full detail (legacy caps: 6000/response, 2500/consensus)
 * - Tier 1: older turns condensed (1500/500/1200); the most recent prior
 *   turn stays full so the model keeps full focus on its immediate context
 * - Tier 2: every prior turn condensed hard (500/300/400)
 *
 * Only the prompt is compacted — the UI keeps displaying complete responses.
 */

export const PROMPT_BUDGET_CHARS = 70_000;
const FLOOR_BUDGET_CHARS = 15_000;

const TIER_CAPS = {
  0: { resp: 6000, consensus: 2500, user: 0 },
  1: { resp: 1500, consensus: 600, user: 1200 },
  2: { resp: 500, consensus: 300, user: 400 },
} as const;

type TranscriptSource = Pick<
  DiscussionState,
  "userMessages" | "rounds" | "consensuses"
>;

function cap(text: string, limit: number): string {
  if (!limit || text.length <= limit) return text;
  return text.slice(0, limit) + "\n[truncated]";
}

/** Render turns 1..turnCount-1 for the prompt at a given compaction tier. */
export function buildPromptTranscript(
  data: TranscriptSource,
  turnCount: number,
  compositeKey: string,
  tier: 0 | 1 | 2,
): string {
  const condensed = TIER_CAPS[tier];
  const keepRecentFull = tier === 1;
  let out = "";

  for (let i = 1; i < turnCount; i++) {
    const fullDetail = tier === 0 || (keepRecentFull && i === turnCount - 1);
    const respCap = fullDetail ? TIER_CAPS[0].resp : condensed.resp;
    const consCap = fullDetail ? TIER_CAPS[0].consensus : condensed.consensus;
    const userCap = fullDetail ? TIER_CAPS[0].user : condensed.user;

    const userMsg = data.userMessages[i];
    if (userMsg) {
      out += `User (turn ${i}): ${cap(userMsg, userCap)}\n\n`;
    }
    const prevRound = data.rounds[i] ?? {};

    // Include this model's own response from turn i so it remembers what it
    // previously proposed.
    const ownResp = prevRound[compositeKey];
    if (ownResp && ownResp.status === "complete" && ownResp.text) {
      out += `### Your Response (turn ${i}):\n${cap(ownResp.text, respCap)}\n\n`;
    }

    const parts = Object.entries(prevRound)
      .filter(([m, r]) => m !== compositeKey && r.status === "complete" && r.text)
      .map(
        ([m, r]) =>
          `### Peer Model: ${splitModelKey(m).model}\n${cap(r.text, respCap)}`,
      )
      .join("\n\n");
    if (parts) {
      out +=
        `[PEER PERSPECTIVES - TURN ${i}]\nThe following are the complete analyses, reasoning steps, and conclusions from the other participating models in turn ${i}:\n\n` +
        `${parts}\n[END PEER PERSPECTIVES]\n\n`;
    }

    const prevConsensus = data.consensuses[i];
    if (prevConsensus) {
      out += `Consensus synthesis (turn ${i}):\n${cap(prevConsensus, consCap)}\n\n`;
    }
  }
  return out;
}

/**
 * Build the transcript with progressive compaction until it fits the budget.
 *
 * `promptLength` is the size of everything already in the prompt (headers,
 * RAG context, instructions); the transcript budget shrinks accordingly.
 * Returns the rendered text plus the tier used and the original (tier-0)
 * size for logging.
 */
export function buildCompactedTranscript(
  data: TranscriptSource,
  turnCount: number,
  compositeKey: string,
  promptLength: number,
): { text: string; tier: 0 | 1 | 2; originalChars: number } {
  const budget = Math.max(
    FLOOR_BUDGET_CHARS,
    PROMPT_BUDGET_CHARS - promptLength,
  );

  const tier0 = buildPromptTranscript(data, turnCount, compositeKey, 0);
  if (tier0.length <= budget) {
    return { text: tier0, tier: 0, originalChars: tier0.length };
  }
  const tier1 = buildPromptTranscript(data, turnCount, compositeKey, 1);
  if (tier1.length <= budget) {
    return { text: tier1, tier: 1, originalChars: tier0.length };
  }
  const tier2 = buildPromptTranscript(data, turnCount, compositeKey, 2);
  return { text: tier2, tier: 2, originalChars: tier0.length };
}
