import { api } from "../api/client";
import type {
  Contribution,
  DiscussionState,
  ModelResult,
  ProgressPhase,
  StreamEvent,
} from "../api/types";
import { debug } from "./debug.svelte";
import { providers } from "./providers.svelte";
import { colorForModel, splitModelKey } from "../utils/helpers";

const STATE_KEY = "aiEnsembleDiscussionState";
const MAX_CONCURRENT = 3;
const STAGGER_MS = 500;

function emptyState(): DiscussionState {
  return {
    id: null,
    timestamp: null,
    title: "",
    question: "",
    instructions: "",
    models: [],
    rounds: {},
    userMessages: {},
    consensus: "",
    endpoint: "",
    consensusModel: "",
    timeout: 120,
    maxTokens: 6000,
    attachments: [],
    stats: {
      totalInputTokens: 0,
      totalOutputTokens: 0,
      totalTokens: 0,
      avgDurationMs: 0,
      peakContext: 0,
      modelCount: 0,
    },
    status: "new",
    totalRounds: 0,
    use_rag: false,
    ragMode: "model-self",
    deep_research: false,
    retrieved_context: null,
    summaryFormat: "default",
    summaryInstructions: "",
    responseFormat: "default",
  };
}

class DiscussionStore {
  #data = $state<DiscussionState>(emptyState());
  #running = $state(false);
  #currentRound = $state(0);
  #phase = $state<ProgressPhase>("idle");
  #abort: AbortController | null = null;

  get data() {
    return this.#data;
  }
  get running() {
    return this.#running;
  }
  get currentRound() {
    return this.#currentRound;
  }
  get phase() {
    return this.#phase;
  }

  /** Build a plain-text transcript of the whole discussion for copy/export. */
  buildTranscript(): string {
    const d = this.#data;
    const parts: string[] = [];
    const heading = d.title || d.question;
    parts.push(`# ${heading}`);
    if (d.instructions) parts.push(`## Instructions\n\n${d.instructions}`);
    const roundNums = Object.keys(d.rounds)
      .map(Number)
      .sort((a, b) => a - b);
    for (const rn of roundNums) {
      const userMsg = d.userMessages[rn];
      if (userMsg) parts.push(`## You (turn ${rn})\n\n${userMsg}`);
      const models = d.rounds[rn];
      const body = Object.entries(models)
        .filter(([, r]) => r.text)
        .map(([m, r]) => `### ${splitModelKey(m).model}\n\n${r.text}`)
        .join("\n\n");
      if (body) parts.push(`## Model responses (turn ${rn})\n\n${body}`);
    }
    if (d.consensus) parts.push(`## Consensus\n\n${d.consensus}`);
    return parts.join("\n\n");
  }

  /** Contribution weights derived from output token counts per model. */
  get contributions(): Contribution[] {
    const totals: Record<string, number> = {};
    for (const round of Object.values(this.#data.rounds)) {
      for (const [model, res] of Object.entries(round)) {
        const w = res.stats?.outputTokens ?? res.text.length;
        totals[model] = (totals[model] ?? 0) + w;
      }
    }
    const sum = Object.values(totals).reduce((a, b) => a + b, 0) || 1;
    return Object.entries(totals)
      .map(([model, w]) => ({
        model,
        weight: Math.round((w / sum) * 100),
        color: colorForModel(model),
      }))
      .sort((a, b) => b.weight - a.weight);
  }

  restore(): void {
    try {
      const raw = localStorage.getItem(STATE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as DiscussionState;
        const restored = { ...emptyState(), ...parsed };
        if (restored.status !== "completed" && restored.status !== "closed") {
          restored.status = "stopped";
        }
        for (const round of Object.values(restored.rounds)) {
          for (const r of Object.values(round)) {
            if (r.status === "waiting" || r.status === "connecting") {
              r.status = "skipped";
            }
          }
        }
        this.#data = restored;
        this.#running = false;
        this.#phase = "done";
      }
    } catch (e) {
      debug.log(`Failed to restore discussion state: ${e}`, "warn");
    }
  }

  persist(): void {
    try {
      localStorage.setItem(STATE_KEY, JSON.stringify(this.#data));
    } catch (e) {
      debug.log(`Failed to persist discussion state: ${e}`, "warn");
    }
    if (typeof this.#data.id === "number") {
      api
        .updateDiscussion(this.#data.id, {
          status: this.#data.status,
          state_json: JSON.stringify(this.#data),
        })
        .catch((e) => debug.log(`Backend state sync failed: ${e}`, "warn"));
    }
  }

  reset(): void {
    this.#abort?.abort();
    this.#data = emptyState();
    this.#running = false;
    this.#currentRound = 0;
    this.#phase = "idle";
    localStorage.removeItem(STATE_KEY);
  }

  configure(partial: Partial<DiscussionState>): void {
    this.#data = { ...this.#data, ...partial };
  }

  async start(opts: {
    question: string;
    models: string[];
    instructions: string;
    endpoint: string;
    consensusModel: string;
    totalRounds: number;
    timeout: number;
    maxTokens: number;
    ragMode: DiscussionState["ragMode"];
    deepResearch: boolean;
    responseFormat: string;
    summaryFormat: DiscussionState["summaryFormat"];
    summaryInstructions: string;
  }): Promise<void> {
    this.#abort = new AbortController();
    this.#running = true;
    const useRag = opts.ragMode === "model-self";
    this.#phase = useRag ? "searching" : "queued";

    const title = opts.question.slice(0, 60);
    this.#data = {
      ...emptyState(),
      question: opts.question,
      title,
      userMessages: { 1: opts.question },
      instructions: opts.instructions,
      models: [...opts.models],
      endpoint: opts.endpoint,
      consensusModel: opts.consensusModel,
      totalRounds: opts.totalRounds,
      timeout: opts.timeout,
      maxTokens: opts.maxTokens,
      use_rag: useRag,
      ragMode: opts.ragMode,
      deep_research: opts.deepResearch,
      responseFormat: opts.responseFormat,
      summaryFormat: opts.summaryFormat,
      summaryInstructions: opts.summaryInstructions,
      status: "in_progress",
      timestamp: Date.now(),
      stats: { ...emptyState().stats, modelCount: opts.models.length },
    };

    try {
      const created = await api.createDiscussion({
        question: opts.question,
        title,
        use_rag: useRag,
        deep_research: opts.deepResearch,
      });
      this.#data.id = created.id;
      this.#data.retrieved_context = created.retrieved_context;
      debug.log(`Created discussion ${created.id}`);
    } catch (e) {
      this.#data.id = `disc_${Date.now()}`;
      debug.log(`Discussion create failed, using local id: ${e}`, "warn");
    }

    this.persist();
    await this.runRound(1);
  }

  /** Append a follow-up user message and run the next chat turn. */
  async nextTurn(followUp: string): Promise<void> {
    if (!followUp.trim()) return;
    if (!this.#running) {
      this.#abort = new AbortController();
      this.#running = true;
    }
    const roundNum = Object.keys(this.#data.rounds).length + 1;
    this.#data.userMessages = { ...this.#data.userMessages, [roundNum]: followUp };
    if (!this.#data.title) this.#data.title = followUp.slice(0, 60);
    this.#data = { ...this.#data };
    this.persist();
    await this.runRound(roundNum);
  }

  async runRound(roundNum: number): Promise<void> {
    if (!this.#running) return;
    this.#currentRound = roundNum;
    this.#phase = "drafting";
    this.#data.rounds[roundNum] = {};
    for (const model of this.#data.models) {
      this.#data.rounds[roundNum][model] = { text: "", status: "waiting" };
    }
    this.#data = { ...this.#data };

    // Bounded concurrency with stagger
    const queue = [...this.#data.models];
    const workers: Promise<void>[] = [];
    let index = 0;

    const runNext = async (): Promise<void> => {
      const model = queue[index++];
      if (!model) return;
      await new Promise((r) => setTimeout(r, STAGGER_MS * (index % MAX_CONCURRENT)));
      await this.queryModel(model, roundNum);
      if (index < queue.length && this.#running) await runNext();
    };

    for (let i = 0; i < Math.min(MAX_CONCURRENT, queue.length); i++) {
      workers.push(runNext());
    }
    await Promise.all(workers);

    this.persist();

    // Multi-turn: only the final round synthesizes a consensus, then stop.
    // The UI drives follow-ups via nextTurn().
    await this.generateConsensus();
    this.finish();
  }

  async queryModel(compositeKey: string, roundNum: number): Promise<void> {
    if (!this.#running) return;
    const { provider, model } = splitModelKey(compositeKey);
    const cred = providers.find(provider);
    const started = Date.now();

    this.#updateModel(roundNum, compositeKey, { status: "connecting", text: "" });

    const prompt = this.#buildPrompt(compositeKey, roundNum);

    try {
      const onEvent = (ev: StreamEvent) => {
        if (ev.type === "delta" && ev.content) {
          const prev = this.#data.rounds[roundNum][compositeKey];
          this.#updateModel(roundNum, compositeKey, {
            status: "streaming",
            text: prev.text + ev.content,
          });
        } else if (ev.type === "error") {
          throw new Error(ev.detail ?? "stream error");
        }
      };

      const full = await api.chatStream(
        {
          provider,
          model,
          prompt,
          endpoint: cred?.endpoint ?? this.#data.endpoint,
          max_tokens: this.#data.maxTokens,
          temperature: 0.7,
          discussion_id: typeof this.#data.id === "number" ? this.#data.id : null,
          include_rag_context: this.#data.use_rag && roundNum === 1,
        },
        onEvent,
        this.#abort?.signal,
      );

      const durationMs = Date.now() - started;
      const outputTokens = Math.round(full.length / 4);
      this.#updateModel(roundNum, compositeKey, {
        status: "complete",
        text: full,
        stats: { outputTokens, durationMs, totalTokens: outputTokens },
      });
      this.#recomputeStats();
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      // Fallback to non-streaming
      try {
        const res = await api.chat({
          provider,
          model,
          prompt,
          endpoint: cred?.endpoint ?? this.#data.endpoint,
          max_tokens: this.#data.maxTokens,
          temperature: 0.7,
          discussion_id: typeof this.#data.id === "number" ? this.#data.id : null,
          include_rag_context: this.#data.use_rag && roundNum === 1,
        });
        this.#updateModel(roundNum, compositeKey, {
          status: "complete",
          text: res.output,
          stats: { outputTokens: Math.round(res.output.length / 4) },
        });
        this.#recomputeStats();
      } catch (e2) {
        const m2 = e2 instanceof Error ? e2.message : String(e2);
        this.#updateModel(roundNum, compositeKey, {
          status: "error",
          text: "",
          error: m2 || msg,
        });
        debug.log(`Model ${compositeKey} failed: ${m2}`, "error");
      }
    }
  }

  async retryModel(compositeKey: string, roundNum: number): Promise<void> {
    this.#running = true;
    await this.queryModel(compositeKey, roundNum);
    this.persist();
  }

  skipModel(compositeKey: string, roundNum: number): void {
    this.#updateModel(roundNum, compositeKey, { status: "skipped", text: "" });
    this.persist();
  }

  async generateConsensus(): Promise<void> {
    this.#phase = "synthesizing";
    const model = this.#data.consensusModel || this.#data.models[0];
    if (!model) return;
    const { provider, model: modelId } = splitModelKey(model);
    const cred = providers.find(provider);

    const allResponses = Object.entries(this.#data.rounds)
      .map(([round, models]) => {
        const parts = Object.entries(models)
          .filter(([, r]) => r.status === "complete")
          .map(([m, r]) => `### ${m}\n${r.text}`)
          .join("\n\n");
        return `## Round ${round}\n${parts}`;
      })
      .join("\n\n");

    const prompt = `You are synthesizing a consensus from multiple AI models discussing:\n\n"${this.#data.question}"\n\nHere are all responses:\n\n${allResponses}\n\nProvide a clear, well-structured consensus synthesis${
      this.#data.summaryInstructions
        ? ` following these instructions: ${this.#data.summaryInstructions}`
        : "."
    }`;

    try {
      const res = await api.chat({
        provider,
        model: modelId,
        prompt,
        endpoint: cred?.endpoint ?? this.#data.endpoint,
        max_tokens: this.#data.maxTokens,
        temperature: 0.5,
      });
      this.#data.consensus = res.output;
      this.#data = { ...this.#data };
    } catch (e) {
      debug.log(`Consensus generation failed: ${e}`, "error");
    }
  }

  stop(): void {
    this.#running = false;
    this.#abort?.abort();
    this.#data.status = "stopped";
    this.#phase = "done";
    this.#data = { ...this.#data };
    this.persist();
  }

  /**
   * Stop the running rounds immediately and synthesize a consensus from
   * whatever responses have been collected so far (mirrors the legacy
   * "Stop Discussion and Summarize" action).
   */
  async stopAndSummarize(): Promise<void> {
    this.#running = false;
    this.#abort?.abort();
    this.#data.status = "stopped";
    this.#data = { ...this.#data };
    const hasResponses = Object.values(this.#data.rounds).some((round) =>
      Object.values(round).some((r) => r.status === "complete" && r.text),
    );
    if (hasResponses) {
      await this.generateConsensus();
    }
    this.#phase = "done";
    this.#data = { ...this.#data };
    this.persist();
  }

  finish(): void {
    this.#running = false;
    this.#data.status = "completed";
    this.#phase = "done";
    this.#data = { ...this.#data };
    this.persist();
  }

  load(state: DiscussionState): void {
    const loaded = { ...emptyState(), ...state };
    // A loaded (e.g. history) discussion must never auto-resume. Coerce any
    // non-terminal status to a terminal one and freeze any models that were
    // mid-flight so the LLM is never prompted again when the discussion is
    // merely viewed.
    if (loaded.status !== "completed" && loaded.status !== "closed") {
      loaded.status = "stopped";
    }
    for (const round of Object.values(loaded.rounds)) {
      for (const r of Object.values(round)) {
        if (r.status === "waiting" || r.status === "connecting") {
          r.status = "skipped";
        }
      }
    }
    this.#data = loaded;
    this.#abort?.abort();
    this.#running = false;
    this.#currentRound = 0;
    this.#phase = "done";
    // Persist so a page reload restores the currently-viewed discussion
    // instead of dropping to a blank "New Discussion" screen.
    this.persist();
  }

  #buildPrompt(compositeKey: string, roundNum: number): string {
    const today = new Date().toISOString().slice(0, 10);
    let prompt = `Today's date: ${today}\n\n`;

    if (this.#data.instructions) {
      prompt += `Global instructions: ${this.#data.instructions}\n\n`;
    }

    // Build the full chat transcript up to (but not including) this turn.
    const turnCount = roundNum;
    prompt += `The following is the conversation so far:\n\n`;
    for (let i = 1; i < turnCount; i++) {
      const userMsg = this.#data.userMessages[i];
      if (userMsg) {
        prompt += `User (turn ${i}): ${userMsg}\n\n`;
      }
      const prevRound = this.#data.rounds[i] ?? {};
      const parts = Object.entries(prevRound)
        .filter(([m, r]) => m !== compositeKey && r.status === "complete" && r.text)
        .map(([m, r]) => `### ${splitModelKey(m).model}\n${r.text}`)
        .join("\n\n");
      if (parts) {
        prompt += `Model responses (turn ${i}):\n${parts}\n\n`;
      }
    }

    // Current user turn
    const currentMsg = this.#data.userMessages[roundNum] ?? this.#data.question;
    prompt += `User (turn ${roundNum}): ${currentMsg}\n\n`;

    if (turnCount > 1) {
      prompt += `Building on the previous responses above, continue the discussion with your own analysis. Refine or challenge earlier views where useful.\n`;
    }

    if (this.#data.responseFormat && this.#data.responseFormat !== "default") {
      prompt += `\nRespond in ${this.#data.responseFormat} format.\n`;
    }
    return prompt;
  }

  #updateModel(
    roundNum: number,
    compositeKey: string,
    patch: Partial<ModelResult>,
  ): void {
    const round = this.#data.rounds[roundNum] ?? {};
    const prev = round[compositeKey] ?? { text: "", status: "waiting" };
    this.#data.rounds[roundNum] = {
      ...round,
      [compositeKey]: { ...prev, ...patch },
    };
    this.#data = { ...this.#data };
  }

  #recomputeStats(): void {
    let outTok = 0;
    let dur = 0;
    let count = 0;
    for (const round of Object.values(this.#data.rounds)) {
      for (const res of Object.values(round)) {
        if (res.stats?.outputTokens) outTok += res.stats.outputTokens;
        if (res.stats?.durationMs) {
          dur += res.stats.durationMs;
          count++;
        }
      }
    }
    this.#data.stats = {
      ...this.#data.stats,
      totalOutputTokens: outTok,
      totalTokens: outTok,
      avgDurationMs: count ? Math.round(dur / count) : 0,
    };
  }
}

export const discussion = new DiscussionStore();
