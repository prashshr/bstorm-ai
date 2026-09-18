import { api } from "../api/client";
import type {
  ChatAttachment,
  ChatRequest,
  Contribution,
  DiscussionState,
  ModelResult,
  ProgressPhase,
  StreamEvent,
} from "../api/types";
import { debug } from "./debug.svelte";
import { providers } from "./providers.svelte";
import { history } from "./history.svelte";
import { models } from "./models.svelte";
import { colorForModel, splitModelKey, modelSupportsVision } from "../utils/helpers";

const STATE_KEY = "aiEnsembleDiscussionState";
const MAX_CONCURRENT = 6;
const STAGGER_MS = 30;

function imageFingerprint(att: ChatAttachment): string {
  const content = att.content || "";
  const len = content.length;
  const sample = content.slice(0, 40) + content.slice(-40);
  return `${att.name}_${len}_${sample}`;
}

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
    consensuses: {},
    consensusEnabled: false,
    consensusError: "",
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
    ragMode: "model-only",
    deep_research: false,
    retrieved_context: null,
    summaryFormat: "compact",
    summaryFormatText:
      "STRICT COMPACT SUMMARY MANDATE: Simply get information from all responses. Do not add any more information from your side or elsewhere. Analyze all the responses, get the common points and the not common points and share in very short precise format a best consensus. Maximum 250 words total. No additional explanations.",
    summaryInstructions: "",
    responseFormat: "compact",
    responseFormatText:
      "STRICT COMPACT LENGTH & FORMAT MANDATE: Provide a direct, highly concise, and brief response. Maximum 150-250 words total (maximum 2-3 short paragraphs or bullet points). Eliminate all introductory filler, background summaries, conversational remarks, and repetitive restatements. Get straight to the point.",
  };
}

class DiscussionStore {
  #data = $state<DiscussionState>(emptyState());
  #running = $state(false);
  #currentRound = $state(0);
  #phase = $state<ProgressPhase>("idle");
  #abort: AbortController | null = null;
  // Attachments added on a given turn, keyed by round number. Only that round
  // sends them to the models (each new upload belongs to its own message).
  #attachmentsByRound: Record<number, ChatAttachment[]> = {};
  // Cached visual data transcriptions for text-only models, keyed by image attachment name.
  #imageTranscriptions: Record<string, string> = {};

  #isVisionModel(key: string): boolean {
    const { model } = splitModelKey(key);
    return models.visionOf(key) ?? modelSupportsVision(model);
  }

  #timeoutSecs(): number {
    const t = Number(this.#data.timeout);
    return Number.isFinite(t) && t > 0 ? t : 120;
  }

  /**
   * Build a linked AbortSignal combining the user-stop signal with a
   * per-request timeout. Callers must pass `signal` to the api call and
   * `cleanup()` in a finally block. `isTimeout()` is true when the timeout
   * signal fired (used to report status "timeout" vs user-stop).
   */
  #linkedTimeoutScope(): {
    signal: AbortSignal;
    isTimeout: () => boolean;
    cleanup: () => void;
    timeoutSecs: number;
  } {
    const timeoutSecs = this.#timeoutSecs();
    const timeoutSignal = AbortSignal.timeout(timeoutSecs * 1000);
    const linked = new AbortController();
    let timedOut = false;
    const userSignal = this.#abort?.signal;
    const onUserAbort = () => {
      if (!linked.signal.aborted) {
        try {
          linked.abort(userSignal?.reason);
        } catch {
          linked.abort();
        }
      }
    };
    const onTimeout = () => {
      timedOut = true;
      if (!linked.signal.aborted) {
        try {
          linked.abort(timeoutSignal.reason);
        } catch {
          linked.abort();
        }
      }
    };
    if (userSignal) {
      if (userSignal.aborted) onUserAbort();
      else userSignal.addEventListener("abort", onUserAbort, { once: true });
    }
    if (timeoutSignal.aborted) onTimeout();
    else timeoutSignal.addEventListener("abort", onTimeout, { once: true });
    const cleanup = () => {
      try {
        userSignal?.removeEventListener("abort", onUserAbort);
      } catch {
        /* ignore */
      }
      try {
        timeoutSignal.removeEventListener("abort", onTimeout);
      } catch {
        /* ignore */
      }
    };
    return {
      signal: linked.signal,
      isTimeout: () => timedOut || timeoutSignal.aborted,
      cleanup,
      timeoutSecs,
    };
  }

  async #ensureImageTranscriptions(roundNum: number): Promise<void> {
    const roundAttach = this.#attachmentsByRound[roundNum] || (roundNum === 1 ? this.#data.attachments : []);
    const images = roundAttach.filter((a) => a.type?.startsWith("image/"));
    if (images.length === 0) return;

    // Check if any active model in this round is text-only
    const hasTextOnly = this.#data.models.some((k) => !this.#isVisionModel(k));
    if (!hasTextOnly) return;

    // Find an available vision model to transcribe the visual data
    let bridgeKey = this.#data.models.find((k) => this.#isVisionModel(k));
    if (!bridgeKey) {
      bridgeKey = models.favorites.find((k) => this.#isVisionModel(k));
    }
    if (!bridgeKey) {
      bridgeKey = models.all.find((k) => this.#isVisionModel(k));
    }

    if (!bridgeKey) {
      debug.log("[Vision Bridge] No vision-capable model found for transcription fallback", "warn");
      return;
    }

    const { provider: vProvider, model: vModel } = splitModelKey(bridgeKey);
    const vCred = providers.find(vProvider);

    await Promise.all(
      images.map(async (img) => {
        const fp = imageFingerprint(img);
        if (this.#imageTranscriptions[fp]) return;
        try {
          debug.log(`[Vision Bridge] Transcribing visual data from "${img.name}" using ${vModel}...`);
          const bridgePrompt =
            `You are an expert AI Vision Data Transcriber. Analyze this image thoroughly and extract all visible content with 100% fidelity. ` +
            `Include all company names, stock tickers, strike prices, expiration dates, premiums, call/put warrant tables, column headers, numbers, metrics, charts, labels, and text in clean structured markdown tables. ` +
            `Be concise, complete, and strictly factual so a text-only AI model can analyze this exact data accurately without seeing the original pixels.`;

          const res = await api.chat({
            provider: vProvider,
            model: vModel,
            prompt: bridgePrompt,
            endpoint: vCred?.endpoint ?? "",
            max_tokens: 2000,
            temperature: 0.1,
            attachments: [img],
            timeout: this.#data.timeout,
          } as ChatRequest);

          if (res.output?.trim()) {
            this.#imageTranscriptions[fp] = res.output.trim();
            debug.log(`[Vision Bridge] Successfully transcribed "${img.name}" (${res.output.length} chars)`);
          }
        } catch (err) {
          debug.log(`[Vision Bridge] Transcription failed for "${img.name}": ${err}`, "warn");
        }
      }),
    );
  }

  /** Attachments uploaded on a given turn, for rendering in the chat UI. */
  attachmentsForRound(roundNum: number): ChatAttachment[] {
    return this.#attachmentsByRound[roundNum] ?? (roundNum === 1 ? (this.#data.attachments ?? []) : []);
  }

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
      const cons = d.consensuses[rn];
      if (cons) parts.push(`## Consensus (turn ${rn})\n\n${cons}`);
    }
    if (d.consensus) parts.push(`## Latest Consensus\n\n${d.consensus}`);
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
    this.#attachmentsByRound = {};
    this.#imageTranscriptions = {};
    localStorage.removeItem(STATE_KEY);
  }

  configure(partial: Partial<DiscussionState>): void {
    this.#data = { ...this.#data, ...partial };
  }

  async start(opts: {
    question: string;
    models: string[];
    instructions: string;
    consensusEnabled: boolean;
    endpoint: string;
    consensusModel: string;
    totalRounds: number;
    timeout: number;
    maxTokens: number;
    ragMode: DiscussionState["ragMode"];
    deepResearch: boolean;
    responseFormat: DiscussionState["responseFormat"];
    responseFormatText: string;
    summaryFormat: DiscussionState["summaryFormat"];
    summaryFormatText: string;
    summaryInstructions: string;
    attachments?: ChatAttachment[];
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
      responseFormatText: opts.responseFormatText,
      summaryFormat: opts.summaryFormat,
      summaryFormatText: opts.summaryFormatText,
      summaryInstructions: opts.summaryInstructions,
      consensusEnabled: opts.consensusEnabled,
      attachments: opts.attachments ? opts.attachments.map((a) => ({ name: a.name, size: 0, type: a.type, content: a.content })) : [],
      status: "in_progress",
      timestamp: Date.now(),
      stats: { ...emptyState().stats, modelCount: opts.models.length },
    };

    try {
      const created = await api.createDiscussion({
        question: opts.question,
        title,
        use_rag: useRag,
        rag_mode: opts.ragMode,
        deep_research: opts.deepResearch,
      });
      this.#data.id = created.id;
      this.#data.retrieved_context = created.retrieved_context;
      history.add(created);
      debug.log(`Created discussion ${created.id}`);
    } catch (e) {
      this.#data.id = `disc_${Date.now()}`;
      debug.log(`Discussion create failed, using local id: ${e}`, "warn");
    }

    this.persist();
    this.#imageTranscriptions = {};
    this.#attachmentsByRound = opts.attachments?.length
      ? { 1: opts.attachments }
      : {};
    await this.runRound(1);
  }

  /**
   * Append a follow-up user message and run the next chat turn.
   * `modelKeys` is the final model list after any add/remove happened since
   * the previous turn — the next round (and every round after it) uses exactly
   * this set, so mid-discussion model changes take effect immediately.
   * When omitted, the existing discussion model list is kept.
   */
  async nextTurn(
    followUp: string,
    modelKeys?: string[],
    attachments?: ChatAttachment[],
    settings?: {
      instructions?: string;
      consensusModel?: string;
      totalRounds?: number;
      timeout?: number;
      maxTokens?: number;
      ragMode?: DiscussionState["ragMode"];
      deepResearch?: boolean;
      responseFormat?: DiscussionState["responseFormat"];
      responseFormatText?: string;
      summaryFormat?: DiscussionState["summaryFormat"];
      summaryFormatText?: string;
      summaryInstructions?: string;
      consensusEnabled?: boolean;
    },
  ): Promise<void> {
    if (!followUp.trim()) return;
    if (!this.#running) {
      this.#abort = new AbortController();
      this.#running = true;
    }
    const roundNum = Object.keys(this.#data.rounds).length + 1;
    this.#data.userMessages = { ...this.#data.userMessages, [roundNum]: followUp };
    if (attachments && attachments.length > 0) {
      this.#data.attachments = attachments.map((a) => ({ name: a.name, size: 0, type: a.type, content: a.content }));
      this.#attachmentsByRound[roundNum] = attachments;
    }
    if (!this.#data.title) this.#data.title = followUp.slice(0, 60);
    // Adopt the latest model selection so the next turn reflects any
    // models added or removed since the discussion started / last turn.
    if (modelKeys && modelKeys.length > 0) {
      this.#data.models = [...modelKeys];
      this.#data.stats = {
        ...this.#data.stats,
        modelCount: modelKeys.length,
      };
    }
    if (settings) {
      if (settings.instructions !== undefined) this.#data.instructions = settings.instructions;
      if (settings.consensusModel !== undefined) this.#data.consensusModel = settings.consensusModel;
      if (settings.totalRounds !== undefined) this.#data.totalRounds = settings.totalRounds;
      if (settings.timeout !== undefined) this.#data.timeout = settings.timeout;
      if (settings.maxTokens !== undefined) this.#data.maxTokens = settings.maxTokens;
      if (settings.ragMode !== undefined) this.#data.ragMode = settings.ragMode;
      if (settings.deepResearch !== undefined) this.#data.deep_research = settings.deepResearch;
      if (settings.responseFormat !== undefined) this.#data.responseFormat = settings.responseFormat;
      if (settings.responseFormatText !== undefined) this.#data.responseFormatText = settings.responseFormatText;
      if (settings.summaryFormat !== undefined) this.#data.summaryFormat = settings.summaryFormat;
      if (settings.summaryFormatText !== undefined) this.#data.summaryFormatText = settings.summaryFormatText;
      if (settings.summaryInstructions !== undefined) this.#data.summaryInstructions = settings.summaryInstructions;
      if (settings.consensusEnabled !== undefined) this.#data.consensusEnabled = settings.consensusEnabled;
    }
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

    // Run Vision Bridge transcription for text-only models if image attachments are present
    await this.#ensureImageTranscriptions(roundNum);

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

    if (this.#data.consensusEnabled) {
      await this.generateConsensus(roundNum);
    }

    const total = this.#data.totalRounds || 1;
    if (roundNum < total) {
      // Auto-advance to the next round so the models can refine their
      // answers based on the previous round's results and consensus.
      const nextRound = roundNum + 1;
      this.#data.userMessages = {
        ...this.#data.userMessages,
        [nextRound]: `Continue refining the analysis. Review all previous rounds including their model responses and consensus. Provide a refined, enhanced response that builds on the best insights so far.`,
      };
      this.persist();
      await this.runRound(nextRound);
    } else {
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
    const isVision = this.#isVisionModel(compositeKey);
    const roundAttachments = this.#attachmentsByRound[roundNum] ?? (roundNum === 1 ? this.#data.attachments : []);
    const modelAttachments = isVision
      ? roundAttachments
      : roundAttachments.filter((a) => !a.type?.startsWith("image/"));

    const scope = this.#linkedTimeoutScope();

    // Streaming render batching: accumulate rapid deltas and flush to
    // #updateModel at most every ~100ms (trailing flush on done).
    let pendingText = "";
    let pendingThinking = "";
    let rafHandle: number | null = null;
    const cancelScheduledFlush = () => {
      if (rafHandle !== null) {
        if (typeof cancelAnimationFrame === "function") {
          cancelAnimationFrame(rafHandle);
        } else {
          clearTimeout(rafHandle);
        }
        rafHandle = null;
      }
    };
    const flushPending = () => {
      rafHandle = null;
      if (!pendingText && !pendingThinking) return;
      const prev = this.#data.rounds[roundNum]?.[compositeKey];
      if (!prev) {
        pendingText = "";
        pendingThinking = "";
        return;
      }
      const chunk = pendingText;
      const thinkChunk = pendingThinking;
      pendingText = "";
      pendingThinking = "";
      this.#updateModel(roundNum, compositeKey, {
        status: "streaming",
        text: prev.text + chunk,
        thinking: (prev.thinking ?? "") + thinkChunk,
      });
    };
    const scheduleFlush = () => {
      if (rafHandle !== null) return;
      if (typeof requestAnimationFrame === "function") {
        rafHandle = requestAnimationFrame(flushPending);
      } else {
        rafHandle = setTimeout(flushPending, 16) as unknown as number;
      }
    };

    try {
      const onEvent = (ev: StreamEvent) => {
        if (ev.type === "thinking_delta" && ev.content) {
          pendingThinking += ev.content;
          scheduleFlush();
        } else if (ev.type === "delta" && ev.content) {
          pendingText += ev.content;
          scheduleFlush();
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
          include_rag_context: false,
          attachments: modelAttachments.length ? modelAttachments : undefined,
          timeout: this.#data.timeout,
        } as ChatRequest,
        onEvent,
        scope.signal,
      );

      // Trailing flush on done: the authoritative full text already contains
      // every delta, so drop any unflushed remainder and set final text.
      cancelScheduledFlush();
      pendingText = "";
      pendingThinking = "";

      const durationMs = Date.now() - started;
      const outputTokens = Math.round(full.length / 4);
      this.#updateModel(roundNum, compositeKey, {
        status: "complete",
        text: full,
        stats: { outputTokens, durationMs, totalTokens: outputTokens },
      });
      this.#recomputeStats();
    } catch (e) {
      cancelScheduledFlush();
      // Timeout (timeout signal fired while still running) takes precedence
      // over the generic abort path; user-stop is running=false / #abort aborted.
      if (scope.isTimeout() && this.#running) {
        const prev = this.#data.rounds[roundNum]?.[compositeKey];
        const partial = (prev?.text ?? "") + pendingText;
        const partialThink = (prev?.thinking ?? "") + pendingThinking;
        pendingText = "";
        pendingThinking = "";
        this.#updateModel(roundNum, compositeKey, {
          status: "timeout",
          text: partial,
          thinking: partialThink,
          error: `Request timed out after ${scope.timeoutSecs}s`,
        });
        return;
      }
      pendingText = "";
      pendingThinking = "";
      const msg = e instanceof Error ? e.message : String(e);
      // Don't fall back if user initiated abort or discussion stopped
      if (this.#abort?.signal.aborted || !this.#running) {
        this.#updateModel(roundNum, compositeKey, {
          status: "error",
          text: "",
          error: "Stopped by user",
        });
        return;
      }
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
          include_rag_context: false,
          attachments: roundAttachments.length ? roundAttachments : undefined,
          timeout: this.#data.timeout,
        } as ChatRequest, scope.signal);
        if (scope.isTimeout() && this.#running) {
          this.#updateModel(roundNum, compositeKey, {
            status: "timeout",
            text: res.output ?? "",
            error: `Request timed out after ${scope.timeoutSecs}s`,
          });
          return;
        }
        // Guard: don't resurrect a stopped discussion
        if (!this.#running) {
          this.#updateModel(roundNum, compositeKey, {
            status: "error",
            text: "",
            error: "Stopped by user",
          });
          return;
        }
        this.#updateModel(roundNum, compositeKey, {
          status: "complete",
          text: res.output,
          stats: { outputTokens: Math.round(res.output.length / 4) },
        });
        this.#recomputeStats();
      } catch (e2) {
        if (scope.isTimeout() && this.#running) {
          const prev2 = this.#data.rounds[roundNum]?.[compositeKey];
          this.#updateModel(roundNum, compositeKey, {
            status: "timeout",
            text: prev2?.text ?? "",
            error: `Request timed out after ${scope.timeoutSecs}s`,
          });
          debug.log(`Model ${compositeKey} timed out after ${scope.timeoutSecs}s`, "error");
          return;
        }
        const m2 = e2 instanceof Error ? e2.message : String(e2);
        this.#updateModel(roundNum, compositeKey, {
          status: "error",
          text: "",
          error: m2 || msg,
        });
        debug.log(`Model ${compositeKey} failed: ${m2}`, "error");
      }
    } finally {
      scope.cleanup();
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

  async generateConsensus(roundNum: number): Promise<void> {
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
        const consensus = this.#data.consensuses[Number(round)];
        const consensusBlock = consensus
          ? `\n\n### Consensus (turn ${round})\n${consensus}`
          : "";
        return `## Round ${round}\n${parts}${consensusBlock}`;
      })
      .join("\n\n");

    const dateStr = new Date().toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
    const dateContext = `[System Notice: Today's date is ${dateStr}. Please synthesize a balanced consensus from all perspectives as of today's date.]`;

    let consensusFormat = "";
    const fmt = this.#data.summaryFormat || "compact";
    if (fmt === "none") {
      // No format instruction
    } else {
      const customText = this.#data.summaryInstructions?.trim() || this.#data.summaryFormatText?.trim();
      if (customText) {
        consensusFormat = `\n\n[MANDATORY CONSENSUS SUMMARY FORMAT DIRECTIVE - CRITICAL OVERRIDE]\n${customText}\n[END MANDATORY CONSENSUS FORMAT DIRECTIVE]\n`;
      } else if (fmt === "compact") {
        consensusFormat =
          "\n\n[MANDATORY COMPACT CONSENSUS FORMAT DIRECTIVE]\n" +
          "Provide a STRICTLY COMPACT, HIGHLY CONCISE consensus synthesis:\n" +
          "- Start with a 1-sentence verdict\n" +
          "- Short weighted score table (max 4 core metrics)\n" +
          "- Concise bullet points for key agreements and disagreements\n" +
          "- Max 3 priority recommendations as short numbered items\n" +
          "- Keep response under 250 words total. Eliminate fluff.\n" +
          "[END MANDATORY CONSENSUS FORMAT DIRECTIVE]\n";
      } else {
        consensusFormat =
          "\n\n[MANDATORY ELABORATE CONSENSUS FORMAT DIRECTIVE]\n" +
          "Provide an ELABORATE, FULLY DETAILED consensus synthesis:\n" +
          "- Start with an executive verdict (2-3 sentences)\n" +
          "- Full weighted scoring matrix with rationale for each model\n" +
          "- In-depth council alignment & friction matrix\n" +
          "- Detailed trade-off analysis and actionable next steps\n" +
          "[END MANDATORY CONSENSUS FORMAT DIRECTIVE]\n";
      }
    }

    const prompt = `${dateContext}\n\nSynthesize a balanced consensus from all perspectives.\n\n"${this.#data.question}"\n\nAll model responses:\n\n${allResponses}${consensusFormat}`;

    const scope = this.#linkedTimeoutScope();
    try {
      const res = await api.chat(
        {
          provider,
          model: modelId,
          prompt,
          endpoint: cred?.endpoint ?? this.#data.endpoint,
          max_tokens: this.#data.maxTokens,
          temperature: 0.5,
          timeout: this.#data.timeout,
        } as ChatRequest,
        scope.signal,
      );
      // Persist the consensus for this specific round so each turn keeps its
      // own synthesis and the conversation reads top-to-bottom in order.
      this.#data.consensuses = {
        ...this.#data.consensuses,
        [roundNum]: res.output,
      };
      this.#data.consensus = res.output;
      this.#data.consensusError = "";
      this.#data = { ...this.#data };
    } catch (e: any) {
      if (scope.isTimeout() && this.#running) {
        this.#data.consensusError = `Consensus generation timed out after ${scope.timeoutSecs}s`;
        this.#data = { ...this.#data };
        debug.log(`Consensus generation timed out after ${scope.timeoutSecs}s`, "error");
        return;
      }
      if (e?.name === "AbortError") return;
      this.#data.consensusError = `Consensus generation failed: ${e}`;
      this.#data = { ...this.#data };
      debug.log(`Consensus generation failed: ${e}`, "error");
    } finally {
      scope.cleanup();
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
      await this.generateConsensus(this.#currentRound || 1);
    }
    this.#phase = "done";
    this.#data = { ...this.#data };
    this.persist();
  }

  finish(): void {
    this.#running = false;
    if (this.#data.status !== "stopped") {
      this.#data.status = "completed";
    }
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
    this.#imageTranscriptions = {};
    this.#attachmentsByRound = loaded.attachments?.length ? { 1: loaded.attachments } : {};
    // Persist so a page reload restores the currently-viewed discussion
    // instead of dropping to a blank "New Discussion" screen.
    this.persist();
  }

  #buildPrompt(compositeKey: string, roundNum: number): string {
    const now = new Date();
    const dateStr = now.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
    const dateContext =
      `[SYSTEM NOTICE: Today's date is ${dateStr}. Treat today as the absolute present ` +
      `moment for your temporal grounding. If you have search, browsing, or real-time ` +
      `web-access capabilities, you must actively perform live internet search queries ` +
      `to retrieve and incorporate the latest, up-to-the-minute information from the ` +
      `most authoritative, reliable, and primary online sources before formulating your ` +
      `analysis or recommendations. Do not work on pre-training cutoff or stale offline data.]`;

    let prompt = `${dateContext}\n\n`;

    const respInstr = this.#data.responseFormatText?.trim();
    if (respInstr) {
      prompt += `[PRIMARY RESPONSE FORMAT DIRECTIVE - ENFORCE STRICTLY]\n${respInstr}\n[END PRIMARY RESPONSE FORMAT DIRECTIVE]\n\n`;
    }

    if (this.#data.use_rag) {
      prompt += `# Data Source Status\n`;
      if (!this.#data.retrieved_context) {
        prompt += `Note: Web research (RAG) was enabled but did not return results.\n`;
      }
      prompt += `Start your response with EXACTLY ONE LINE:\n`;
      prompt += `RAG data: [Used/Not Available] | Self Websearch: [Used/Not Available] | Training Data: [Used/Not Available]\n`;
      prompt += `Then proceed to answer.\n\n`;
    }
    if (this.#data.retrieved_context) {
      const ctx = this.#data.retrieved_context;
      const budgeted = ctx.length > 12000 ? `${ctx.slice(0, 12000)}\n[truncated]` : ctx;
      prompt += `# Retrieved Web Search Context\n${budgeted}\n\n`;
    }

    if (this.#data.instructions) {
      prompt += `Global instructions: ${this.#data.instructions}\n\n`;
    }

    // Build the full chat transcript up to (but not including) this turn.
    const turnCount = roundNum;
    prompt += `The following is the full conversation so far (from the beginning). Use ALL of it as context — do not treat this as a fresh query:\n\n`;
    for (let i = 1; i < turnCount; i++) {
      const userMsg = this.#data.userMessages[i];
      if (userMsg) {
        prompt += `User (turn ${i}): ${userMsg}\n\n`;
      }
      const prevRound = this.#data.rounds[i] ?? {};
      const parts = Object.entries(prevRound)
        .filter(([m, r]) => m !== compositeKey && r.status === "complete" && r.text)
        .map(([m, r]) => `### Peer Model: ${splitModelKey(m).model}\n${r.text.length > 6000 ? r.text.slice(0, 6000) + "\n[truncated]" : r.text}`)
        .join("\n\n");
      if (parts) {
        prompt += `[PEER PERSPECTIVES - TURN ${i}]\nThe following are the complete analyses, reasoning steps, and conclusions from the other participating models in turn ${i}:\n\n${parts}\n[END PEER PERSPECTIVES]\n\n`;
      }
      const prevConsensus = this.#data.consensuses[i];
      if (prevConsensus) {
        const capped = prevConsensus.length > 2500 ? prevConsensus.slice(0, 2500) : prevConsensus;
        prompt += `Consensus synthesis (turn ${i}):\n${capped}\n\n`;
      }
    }

    // Current user turn
    const currentMsg = this.#data.userMessages[roundNum] ?? this.#data.question;
    prompt += `User (turn ${roundNum}): ${currentMsg}\n\n`;

    if (roundNum > 1) {
      prompt += `[ENSEMBLE DELIBERATION DIRECTIVE - TURN ${roundNum}]\n` +
        `You are now in deliberation turn ${roundNum}. Review the peer model responses above with an analytical eye:\n` +
        `1. Integrate the valid points, edge cases, and distinct angles raised by other models (e.g. if another model noticed a constraint, bug, or nuance you did not emphasize).\n` +
        `2. Respectfully point out and correct any flaws, misconceptions, or false assumptions in their arguments.\n` +
        `3. Provide your synthesis and enhanced final judgment for this turn.\n` +
        `[END ENSEMBLE DELIBERATION DIRECTIVE]\n\n`;
    }

    const isVision = this.#isVisionModel(compositeKey);
    const roundAttach = this.#attachmentsByRound[roundNum]?.length
      ? this.#attachmentsByRound[roundNum]
      : (this.#data.attachments ?? []);
    if (roundAttach && roundAttach.length > 0) {
      for (const att of roundAttach) {
        if (att.content) {
          if (att.type?.startsWith("image/")) {
            if (!isVision) {
              const fp = imageFingerprint(att);
              const transcription = this.#imageTranscriptions[fp];
              if (transcription) {
                prompt += `--- [Visual Data Transcription of Attached Image: ${att.name}] ---\n${transcription}\n[End Visual Data Transcription]\n\n`;
              } else {
                prompt += `[Attached image: ${att.name} (Image attached by user — analyzed in text-only mode)]\n\n`;
              }
            }
          } else {
            const header = `--- Attached File: ${att.name} ---`;
            if (!prompt.includes(header)) {
              prompt += `${header}\n${att.content}\n[End Attached File: ${att.name}]\n\n`;
            }
          }
        }
      }
    }

    if (turnCount > 1) {
      if (this.#data.responseFormat === "compact") {
        prompt += `Review the previous turn(s) above and provide a concise, direct contribution focusing strictly on key points, agreements/disagreements, or new insights without repeating what other models already stated. Keep it strictly brief and compact.\n\n`;
      } else {
        prompt += `Review all previous responses above and provide your refined analysis building upon what has been discussed. Focus on areas where you can add value or offer a different perspective.\n\n`;
      }
    }

    if (respInstr) {
      prompt += `[FINAL RESPONSE FORMAT & LENGTH OVERRIDE - COMPLIANCE MANDATORY]\n${respInstr}\n[END FINAL RESPONSE FORMAT & LENGTH OVERRIDE]\n\n`;
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
