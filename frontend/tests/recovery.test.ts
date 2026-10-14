import { describe, it, expect, beforeEach } from "vitest";
import { recoverDiscussionState } from "../src/lib/utils/helpers";
import { discussion } from "../src/lib/stores/discussion.svelte";
import type { DiscussionState } from "../src/lib/api/types";

function originalState(): Record<string, unknown> {
  return {
    id: 201,
    timestamp: 1760000000000,
    title: "How do quantum computers break RSA?",
    question: "How do quantum computers break RSA?",
    instructions: "",
    models: ["openai::gpt-4o"],
    userMessages: { 1: "How do quantum computers break RSA?" },
    rounds: {
      1: {
        "openai::gpt-4o": {
          text: "Shor's algorithm runs in polynomial time…",
          status: "complete",
          stats: { outputTokens: 500, durationMs: 1200 },
        },
      },
    },
    consensus: "Quantum threat is real but timeline is debated.",
    consensuses: {},
    consensusEnabled: true,
    consensusError: "",
    endpoint: "",
    consensusModel: "openai::gpt-4o",
    timeout: 120,
    maxTokens: 6000,
    attachments: [],
    tokensUsed: 700,
    status: "completed",
    totalRounds: 1,
    use_rag: false,
    ragMode: "model-only",
    deep_research: false,
    retrieved_context: null,
  };
}

/** The exact shape the legacy hash-load bug persisted: envelope fields +
 *  emptyState defaults + the original state nested as a `state_json` string. */
function wipedWrapper(): Record<string, unknown> {
  const envelope = {
    id: 201,
    title: "How do quantum computers break RSA?",
    question: "How do quantum computers break RSA?",
    status: "completed",
    retrieved_context: null,
    created_at: "2026-10-05T18:00:00Z",
  };
  return {
    ...envelope,
    timestamp: null,
    instructions: "",
    models: [],
    rounds: {},
    userMessages: {},
    consensus: "",
    consensuses: {},
    consensusEnabled: false,
    endpoint: "",
    consensusModel: "",
    timeout: 120,
    maxTokens: 6000,
    attachments: [],
    tokensUsed: 0,
    status: envelope.status,
    totalRounds: 0,
    use_rag: false,
    ragMode: "model-only",
    deep_research: false,
    summaryFormat: "compact",
    responseFormat: "compact",
    topologyByRound: {},
    turnAnalysisByRound: {},
    retrievedContextByRound: {},
    state_json: JSON.stringify(originalState()),
  };
}

describe("recoverDiscussionState", () => {
  it("recovers rounds from a wiped wrapper", () => {
    const recovered = recoverDiscussionState(wipedWrapper()) as Record<string, any>;
    expect(Object.keys(recovered.rounds)).toEqual(["1"]);
    expect(recovered.rounds[1]["openai::gpt-4o"].text).toContain("Shor's");
    expect(recovered.consensus).toContain("Quantum threat");
    expect(recovered.userMessages[1]).toContain("quantum");
    expect(recovered.status).toBe("completed");
    expect(recovered.id).toBe(201);
    // stale keys must be dropped so future persists don't re-wrap
    expect("state_json" in recovered).toBe(false);
    expect("created_at" in recovered).toBe(false);
  });

  it("unwraps double-wiped states (wrapper inside wrapper)", () => {
    const doubleWrapped = { ...wipedWrapper(), rounds: {}, state_json: JSON.stringify(wipedWrapper()) };
    const recovered = recoverDiscussionState(doubleWrapped) as Record<string, any>;
    expect(Object.keys(recovered.rounds)).toEqual(["1"]);
    expect("state_json" in recovered).toBe(false);
  });

  it("unwraps deeply wrapped states (production observed 7 levels)", () => {
    let wrapped: Record<string, unknown> = originalState();
    for (let i = 0; i < 7; i++) {
      wrapped = { ...wipedWrapper(), rounds: {}, state_json: JSON.stringify(wrapped) };
    }
    const recovered = recoverDiscussionState(wrapped) as Record<string, any>;
    expect(Object.keys(recovered.rounds)).toEqual(["1"]);
    expect(recovered.rounds[1]["openai::gpt-4o"].text).toContain("Shor's");
    expect("state_json" in recovered).toBe(false);
  });

  it("strips a leftover valid nested state_json even when rounds are present", () => {
    const withRounds = { ...originalState(), state_json: JSON.stringify(originalState()) } as object;
    const recovered = recoverDiscussionState(withRounds) as Record<string, any>;
    expect("state_json" in recovered).toBe(false);
    expect(Object.keys(recovered.rounds)).toEqual(["1"]);
  });

  it("returns a healthy state untouched", () => {
    const healthy = originalState() as object;
    expect(recoverDiscussionState(healthy)).toBe(healthy);
  });

  it("ignores an empty or invalid state_json string", () => {
    const empty = { ...originalState(), rounds: {}, state_json: "" };
    expect(recoverDiscussionState(empty)).toBe(empty);
    const invalid = { ...originalState(), rounds: {}, state_json: "{not json" };
    expect(recoverDiscussionState(invalid)).toBe(invalid);
    const notAnObject = { ...originalState(), rounds: {}, state_json: '"just a string"' };
    expect(recoverDiscussionState(notAnObject)).toBe(notAnObject);
  });

  it("keeps envelope identity fields when the inner state lacks them", () => {
    const inner = { ...originalState(), title: "", question: "", status: undefined };
    const wrapper = { ...wipedWrapper(), state_json: JSON.stringify(inner) };
    const recovered = recoverDiscussionState(wrapper) as Record<string, any>;
    expect(recovered.title).toBe("How do quantum computers break RSA?");
    expect(recovered.question).toBe("How do quantum computers break RSA?");
    expect(recovered.status).toBe("completed");
  });
});

describe("discussion.load() recovery", () => {
  beforeEach(() => {
    discussion.reset();
  });

  it("restores wiped server state and marks mid-flight models as skipped", () => {
    const inner = originalState();
    (inner.rounds as any)[1]["openai::gpt-4o"].status = "connecting";
    const wrapper = { ...wipedWrapper(), state_json: JSON.stringify(inner) };

    discussion.load(wrapper as unknown as DiscussionState);

    const data = discussion.data as any;
    expect(Object.keys(data.rounds)).toEqual(["1"]);
    expect(data.rounds[1]["openai::gpt-4o"].status).toBe("skipped");
    expect(data.consensus).toContain("Quantum threat");
    expect(data.id).toBe(201);
    // self-heal: the persisted copy must be clean (no nested wrapper)
    const persisted = JSON.parse(localStorage.getItem("aiEnsembleDiscussionState")!);
    expect(persisted.rounds[1]["openai::gpt-4o"].text).toContain("Shor's");
    expect("state_json" in persisted).toBe(false);
  });
});
