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
    question: "",
    instructions: "",
    models: [],
    rounds: {},
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
        this.#data = { ...emptyState(), ...parsed };
        if (this.#data.status === "in_progress") {
          this.#data.status = "stopped";
        }
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
    useRag: boolean;
    deepResearch: boolean;
    responseFormat: string;
    summaryFormat: DiscussionState["summaryFormat"];
    summaryInstructions: string;
  }): Promise<void> {
    this.#abort = new AbortController();
    this.#running = true;
    this.#phase = opts.useRag ? "searching" : "queued";

    this.#data = {
      ...emptyState(),
      question: opts.question,
      instructions: opts.instructions,
      models: [...opts.models],
      endpoint: opts.endpoint,
      consensusModel: opts.consensusModel,
      totalRounds: opts.totalRounds,
      timeout: opts.timeout,
      maxTokens: opts.maxTokens,
      use_rag: opts.useRag,
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
        title: opts.question.slice(0, 60),
        use_rag: opts.useRag,
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

    if (this.#running && roundNum < this.#data.totalRounds) {
      await this.runRound(roundNum + 1);
    } else if (this.#running) {
      await this.generateConsensus();
      this.finish();
    }
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

  finish(): void {
    this.#running = false;
    this.#data.status = "completed";
    this.#phase = "done";
    this.#data = { ...this.#data };
    this.persist();
  }

  load(state: DiscussionState): void {
    this.#data = { ...emptyState(), ...state };
    this.#running = false;
    this.#phase = "done";
  }

  #buildPrompt(compositeKey: string, roundNum: number): string {
    const today = new Date().toISOString().slice(0, 10);
    let prompt = `Today's date: ${today}\n\nQuestion: ${this.#data.question}\n`;
    if (this.#data.instructions) {
      prompt += `\nInstructions: ${this.#data.instructions}\n`;
    }
    if (roundNum > 1) {
      const prev = this.#data.rounds[roundNum - 1] ?? {};
      const others = Object.entries(prev)
        .filter(([m, r]) => m !== compositeKey && r.status === "complete")
        .map(([m, r]) => `### ${m}\n${r.text}`)
        .join("\n\n");
      if (others) {
        prompt += `\nOther models said in the previous round:\n\n${others}\n\nRefine or challenge these views with your own analysis.\n`;
      }
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
