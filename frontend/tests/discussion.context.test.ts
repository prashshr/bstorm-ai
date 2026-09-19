import { describe, it, expect, beforeEach, vi } from "vitest";
import { discussion } from "../src/lib/stores/discussion.svelte";
import { api } from "../src/lib/api/client";

// Mock the API client
vi.mock("../src/lib/api/client", () => {
  return {
    api: {
      createDiscussion: vi.fn(async () => ({ id: 42, retrieved_context: null })),
      updateDiscussion: vi.fn(async () => ({})),
      chatStream: vi.fn(async (_body: unknown, onEvent: (e: { type: string; content?: string }) => void) => {
        onEvent({ type: "delta", content: "Model response content" });
        return "Model response content";
      }),
      chat: vi.fn(async () => ({ output: "Consensus summary content" })),
      deliberationTopology: vi.fn(async () => ({
        model_count: 2,
        consensus_score: 3.0,
        consensus_percent: 100,
        has_disagreement: false,
        primary_divergence: "unanimous",
        dissenting_model: null,
        should_deliberate_round_2: false,
        deliberation_directive: null,
        summary_badge: "Unanimous Consensus",
        rationale: "All models agreed.",
      })),
      triageDocument: vi.fn(async () => ({
        original_length: 100,
        triaged_length: 100,
        is_triaged: false,
        has_prompt_injection: false,
        triaged_content: "content",
      })),
      analyzeTurn: vi.fn(async (body: { query: string }) => {
        const isFresh = /next|new|second/i.test(body.query);
        return {
          needs_fresh_entities: isFresh,
          interaction_type: isFresh ? "fresh_recommendations" : "refinement_evaluation",
          confidence: 0.95,
          reasoning: "Test mock intent classification",
        };
      }),
      retrieveContext: vi.fn(async (body: { query: string }) => {
        return {
          retrieved_context: `Mocked live web search data for query: ${body.query}`,
          query: body.query,
          searched: true,
        };
      }),
    },
  };
});

describe("Multi-Turn Context & Entity Exclusion Ledger in DiscussionStore", () => {
  beforeEach(() => {
    discussion.reset();
    vi.clearAllMocks();
  });

  it("injects exclusion ledger and own past response into prompt when user asks for next/new items", async () => {
    // 1. Set up simulated Turn 1 with 2 models recommending initial companies
    await discussion.start({
      question: "Identify the five best small/mid-cap AI companies (<$50B) worldwide.",
      models: ["openai::gpt-4o", "anthropic::claude-3-5-sonnet"],
      instructions: "Be rigorous and factual.",
      consensusEnabled: true,
      endpoint: "",
      consensusModel: "openai::gpt-4o",
      totalRounds: 1,
      timeout: 120,
      maxTokens: 4000,
      ragMode: "model-only",
      deepResearch: false,
      responseFormat: "none",
      summaryFormat: "compact",
      summaryFormatText: "",
      responseFormatText: "",
      summaryInstructions: "",
    });

    // Populate simulated Turn 1 model answers with tickers and company names
    discussion.data.rounds[1]["openai::gpt-4o"] = {
      text: "1. Celestica (CLS)\n2. Credo Technology (CRDO)\n3. Astera Labs (ALAB)\n4. Fabrinet (FN)\n5. Modine Manufacturing (MOD)",
      status: "complete",
    };
    discussion.data.rounds[1]["anthropic::claude-3-5-sonnet"] = {
      text: "1. Celestica Inc (CLS)\n2. nVent Electric (NVT)\n3. Credo (CRDO)\n4. Onto Innovation (ONTO)\n5. Comfort Systems (FIX)",
      status: "complete",
    };
    discussion.data.consensuses[1] = "Turn 1 Consensus: 1. Celestica (CLS), 2. Credo Technology (CRDO), 3. Astera Labs (ALAB), 4. Fabrinet (FN), 5. nVent (NVT).";

    // 2. User initiates Turn 2: "continue your research and recommend next new 5 companies on same lines"
    await discussion.nextTurn(
      "continue your research and recommend next new 5 companies on same lines",
      ["openai::gpt-4o", "anthropic::claude-3-5-sonnet"],
    );

    // Call chatStream to see the generated prompt passed to api.chatStream
    const chatStreamMock = vi.mocked(api.chatStream);
    expect(chatStreamMock).toHaveBeenCalled();

    // Inspect the prompt sent to gpt-4o in Turn 2 (the latest call)
    const gptCall = chatStreamMock.mock.calls
      .filter((call) => (call[0] as { model: string }).model === "gpt-4o")
      .pop();
    expect(gptCall).toBeDefined();
    const gptPrompt = (gptCall![0] as { prompt: string }).prompt;

    // A. Model self-history: Must include gpt-4o's own Turn 1 response
    expect(gptPrompt).toContain("### Your Response (turn 1):");
    expect(gptPrompt).toContain("Celestica (CLS)");

    // B. Peer response: Must include claude-3-5-sonnet's response
    expect(gptPrompt).toContain("### Peer Model: claude-3-5-sonnet");
    expect(gptPrompt).toContain("Onto Innovation (ONTO)");

    // C. Exclusion Ledger: Must explicitly exclude prior Turn 1 entities
    expect(gptPrompt).toContain("[ACTIVE EXCLUSION LEDGER - DO NOT REPEAT PREVIOUSLY ANALYZED ITEMS]");
    expect(gptPrompt).toContain("Celestica (CLS)");
    expect(gptPrompt).toContain("Credo (CRDO)");
    expect(gptPrompt).toContain("Astera Labs");
    expect(gptPrompt).toContain("Fabrinet");
    expect(gptPrompt).toContain("nVent");
    expect(gptPrompt).toContain("[ACTIVE USER MANDATE - FRESH CANDIDATES REQUIRED]");
    expect(gptPrompt).toContain("Every entity you recommend must be NEW and NOT listed in the exclusion ledger");

    // D. Deliberation directive should NOT replace the fresh items mandate
    expect(gptPrompt).not.toContain("[ENSEMBLE DELIBERATION DIRECTIVE - TURN 2]");
  });

  it("formulates consensus prompt with separate prior context and strict new candidate mandate", async () => {
    discussion.data.question = "Identify 5 small/mid-cap AI companies (<$50B).";
    discussion.data.models = ["openai::gpt-4o", "anthropic::claude-3-5-sonnet"];
    discussion.data.consensusModel = "openai::gpt-4o";

    // Turn 1
    discussion.data.userMessages[1] = discussion.data.question;
    discussion.data.rounds[1] = {
      "openai::gpt-4o": {
        text: "Turn 1 GPT: Celestica (CLS), Credo (CRDO), Astera Labs (ALAB), Fabrinet (FN), Modine (MOD).",
        status: "complete",
      },
      "anthropic::claude-3-5-sonnet": {
        text: "Turn 1 Claude: Celestica (CLS), nVent (NVT), Credo (CRDO), Onto (ONTO), Comfort Systems (FIX).",
        status: "complete",
      },
    };
    discussion.data.consensuses[1] = "Turn 1 Consensus: CLS, CRDO, ALAB, FN, NVT.";

    // Turn 2
    discussion.data.userMessages[2] = "continue your research and recommend next new 5 companies on same lines";
    discussion.data.rounds[2] = {
      "openai::gpt-4o": {
        text: "Turn 2 Fresh Proposals: 1. Coherent (COHR), 2. Nova Ltd (NVMI), 3. Powell Industries (POWL), 4. Axcelis (ACLS), 5. Rambus (RMBS).",
        status: "complete",
      },
      "anthropic::claude-3-5-sonnet": {
        text: "Turn 2 Fresh Proposals: 1. Coherent Corp (COHR), 2. Nova (NVMI), 3. Sterling Infrastructure (STRL), 4. Rambus (RMBS), 5. Belden (BDC).",
        status: "complete",
      },
    };

    // Generate consensus for Turn 2
    await discussion.generateConsensus(2);

    const chatMock = vi.mocked(api.chat);
    expect(chatMock).toHaveBeenCalled();

    const lastCall = chatMock.mock.calls[chatMock.mock.calls.length - 1];
    const consensusPrompt = (lastCall[0] as { prompt: string }).prompt;

    // Consensus prompt must separate prior context and current turn proposals
    expect(consensusPrompt).toContain("[PRIOR CONVERSATION CONTEXT - TURNS 1 TO 1]");
    expect(consensusPrompt).toContain("Turn 1 Consensus: CLS, CRDO, ALAB, FN, NVT.");

    // Must have Critical Mandate for new items
    expect(consensusPrompt).toContain("[CRITICAL MANDATE - SYNTHESIZE NEW / NEXT RECOMMENDATIONS ONLY]");
    expect(consensusPrompt).toContain("user explicitly requested NEW / NEXT candidates");
    expect(consensusPrompt).toContain("STRICTLY EXCLUDED from re-ranking");
    expect(consensusPrompt).toContain("Celestica");
    expect(consensusPrompt).toContain("Credo (CRDO)");

    // Must present Turn 2 model responses under active synthesis block
    expect(consensusPrompt).toContain("[TURN 2 MODEL RESPONSES TO BE SYNTHESIZED]");
    expect(consensusPrompt).toContain("Coherent");
    expect(consensusPrompt).toContain("Nova");
    expect(consensusPrompt).toContain("Powell Industries");
    expect(consensusPrompt).toContain("Sterling Infrastructure");
  });

  it("handles non-fresh follow-up queries without injecting exclusion ledger", async () => {
    discussion.data.question = "Identify 5 small/mid-cap AI companies (<$50B).";
    discussion.data.models = ["openai::gpt-4o", "anthropic::claude-3-5-sonnet"];

    discussion.data.userMessages[1] = discussion.data.question;
    discussion.data.rounds[1] = {
      "openai::gpt-4o": {
        text: "Celestica (CLS) and Credo (CRDO)",
        status: "complete",
      },
    };

    // Follow-up query asking for comparison/refinement
    await discussion.nextTurn(
      "Compare the debt-to-equity and gross margin profiles of Celestica and Credo.",
      ["openai::gpt-4o"],
    );

    const chatStreamMock = vi.mocked(api.chatStream);
    const lastCall = chatStreamMock.mock.calls[chatStreamMock.mock.calls.length - 1];
    const prompt = (lastCall[0] as { prompt: string }).prompt;

    // Should NOT have exclusion ledger
    expect(prompt).not.toContain("[EXCLUSION LEDGER - DO NOT RE-RECOMMEND]");
    // Should have active user follow-up directive
    expect(prompt).toContain("[ACTIVE USER FOLLOW-UP DIRECTIVE - TURN 2]");
    expect(prompt).toContain("Compare the debt-to-equity and gross margin profiles");
  });

  it("records turnAnalysis in turnAnalysisByRound and respects semantic classification", async () => {
    discussion.data.question = "Name 3 leaders.";
    discussion.data.rounds[1] = {
      "openai::gpt-4o": {
        text: "1. Celestica (CLS)\n2. Credo (CRDO)",
        status: "complete",
      },
    };

    // User prompt uses phrasing where TypeSafe returns needs_fresh_entities: true
    await discussion.nextTurn("Give me the second wave candidates.", ["openai::gpt-4o"]);

    expect(discussion.data.turnAnalysisByRound?.[2]).toBeDefined();
    expect(discussion.data.turnAnalysisByRound?.[2]?.interaction_type).toBe("fresh_recommendations");
  });

  it("fetches fresh web research context on nextTurn and injects authoritative live grounding into prompt", async () => {
    discussion.data.question = "Latest small cap AI stocks 2026";
    discussion.data.use_rag = true;
    discussion.data.ragMode = "model-self";
    discussion.data.rounds[1] = {
      "openai::gpt-4o": {
        text: "1. Celestica (CLS)\n2. Credo (CRDO)",
        status: "complete",
      },
    };

    await discussion.nextTurn("recommend next new 5 companies on same lines", ["openai::gpt-4o"]);

    // Verify retrieveContext was called with the followUp query and topic_context
    expect(api.retrieveContext).toHaveBeenCalledWith({
      query: "recommend next new 5 companies on same lines",
      topic_context: "Latest small cap AI stocks 2026",
      deep_research: false,
    });

    // Verify retrievedContextByRound stored the round 2 context
    expect(discussion.data.retrievedContextByRound?.[2]).toContain("Mocked live web search data");

    // Verify the prompt sent to the model contains live online research context and grounding instructions
    const chatStreamMock = vi.mocked(api.chatStream);
    const lastCall = chatStreamMock.mock.calls[chatStreamMock.mock.calls.length - 1];
    const prompt = (lastCall[0] as { prompt: string }).prompt;

    expect(prompt).toContain("[LIVE ONLINE WEB RESEARCH CONTEXT - RETRIEVED AS OF TODAY]");
    expect(prompt).toContain("INSTRUCTION: Use the above live online research as your authoritative ground truth");
    expect(prompt).toContain("Do NOT apologize or claim you lack internet access");
    // Ensure the old disclaimer-forcing lines are gone
    expect(prompt).not.toContain("RAG data: [Used/Not Available]");
    expect(prompt).not.toContain("you must actively perform live internet search queries");
  });
});

