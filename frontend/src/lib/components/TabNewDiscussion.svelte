<script lang="ts">
  import { models } from "../stores/models.svelte";
  import { providers } from "../stores/providers.svelte";
  import { discussion } from "../stores/discussion.svelte";
  import { nav } from "../stores/nav.svelte";
  import { debug } from "../stores/debug.svelte";
  import type { AttachedFile } from "../api/types";
  import { splitModelKey } from "../utils/helpers";
  import ActiveEnsemble from "./ActiveEnsemble.svelte";
  import Icon from "./Icon.svelte";

  const RESPONSE_PRESETS: Record<string, string> = {
    compact:
      "Provide a COMPACT response:\n- Use bullet points\n- Be concise and precise\n- Limit to 3-5 key points\n- No lengthy explanations\n- Use short sentences",
    elaborate:
      "Provide an ELABORATE response:\n- Include thorough explanations and reasoning\n- Cover multiple perspectives\n- Provide examples and evidence where relevant\n- Structure with clear sections\n- Be comprehensive but well-organized",
  };
  const SUMMARY_PRESETS: Record<string, string> = {
    compact:
      "Provide a COMPACT consensus summary:\n- Start with a 1-sentence verdict\n- Use a weighted score table for the model answers\n- Keep paragraphs under 3 sentences\n- Focus strictly on core agreement points",
    elaborate:
      "Provide an ELABORATE consensus summary:\n- Full synthesis of alternative viewpoints and reasoning\n- Explicitly trace points of divergence and conflicts between models\n- Grade consensus strength across categories\n- Detail background context and recommended next steps",
  };

  let question = $state("");
  let responseFormat = $state<"default" | "compact" | "elaborate">("default");
  let summaryFormat = $state<"default" | "compact" | "elaborate">("default");
  let instructions = $state("");
  let summaryInstructions = $state("");
  let useRag = $state(false);
  let deepResearch = $state(false);

  function applyResponseFormat() {
    instructions =
      responseFormat in RESPONSE_PRESETS
        ? RESPONSE_PRESETS[responseFormat]
        : "";
  }

  function applySummaryFormat() {
    summaryInstructions =
      summaryFormat in SUMMARY_PRESETS ? SUMMARY_PRESETS[summaryFormat] : "";
  }
  let totalRounds = $state(2);
  let timeout = $state(120);
  let maxTokens = $state(6000);
  let consensusModel = $state("");
  let advancedOpen = $state(false);
  let attachments = $state<AttachedFile[]>([]);
  let dragover = $state(false);
  let starting = $state(false);
  let summarizing = $state(false);
  let error = $state<string | null>(null);

  let consensusOptions = $derived(models.all);

  $effect(() => {
    if (!consensusModel && models.all.length > 0) {
      consensusModel = models.all[0];
    }
  });

  async function handleFiles(fileList: FileList | null) {
    if (!fileList) return;
    for (const file of Array.from(fileList)) {
      if (file.size > 10 * 1024 * 1024) {
        error = `${file.name} exceeds 10MB`;
        continue;
      }
      const content = await file.text();
      attachments = [
        ...attachments,
        { name: file.name, size: file.size, type: file.type, content },
      ];
    }
  }

  function removeFile(name: string) {
    attachments = attachments.filter((f) => f.name !== name);
  }

  async function stopAndSummarize() {
    summarizing = true;
    try {
      nav.go("current");
      await discussion.stopAndSummarize();
    } catch (e) {
      debug.log(`Stop & summarize failed: ${e}`, "error");
    } finally {
      summarizing = false;
    }
  }

  function closeDiscussion() {
    discussion.stop();
    discussion.reset();
  }

  async function start() {
    error = null;
    if (!question.trim()) {
      error = "Please enter a question";
      return;
    }
    if (models.selected.length === 0) {
      error = "Please select at least one model";
      return;
    }
    starting = true;
    const endpoint = providers.active
      ? (providers.find(providers.active)?.endpoint ?? "")
      : "";

    let fullQuestion = question;
    if (attachments.length > 0) {
      const attachText = attachments
        .map((a) => `\n\n--- Attached: ${a.name} ---\n${a.content}`)
        .join("");
      fullQuestion += attachText;
    }

    try {
      nav.go("current");
      await discussion.start({
        question: fullQuestion,
        models: models.selected,
        instructions,
        endpoint,
        consensusModel: consensusModel || models.selected[0],
        totalRounds,
        timeout,
        maxTokens,
        useRag,
        deepResearch,
        responseFormat,
        summaryFormat,
        summaryInstructions,
      });
    } catch (e) {
      debug.log(`Failed to start discussion: ${e}`, "error");
      error = "Failed to start discussion";
    } finally {
      starting = false;
    }
  }
</script>

<div class="new-discussion">
  <ActiveEnsemble />

  <section class="form-section">
    <label for="nd-question">Question</label>
    <textarea
      id="nd-question"
      data-testid="question-input"
      bind:value={question}
      placeholder="What should the ensemble discuss?"
      rows="4"
    ></textarea>

    <div
      class="drop-zone"
      class:dragover
      role="button"
      tabindex="0"
      ondragover={(e) => {
        e.preventDefault();
        dragover = true;
      }}
      ondragleave={() => (dragover = false)}
      ondrop={(e) => {
        e.preventDefault();
        dragover = false;
        handleFiles(e.dataTransfer?.files ?? null);
      }}
      onclick={() => document.getElementById("nd-file")?.click()}
      onkeydown={(e) =>
        e.key === "Enter" && document.getElementById("nd-file")?.click()}
    >
      <Icon name="upload" size="sm" /> Attach files (max 10MB each)
    </div>
    <input
      id="nd-file"
      type="file"
      multiple
      style="display:none"
      onchange={(e) => handleFiles((e.target as HTMLInputElement).files)}
    />
    {#if attachments.length > 0}
      <div class="files">
        {#each attachments as f (f.name)}
          <div class="file">
            <Icon name="file" size="sm" />
            <span>{f.name}</span>
            <button
              class="rm"
              onclick={() => removeFile(f.name)}
              aria-label="Remove {f.name}">×</button
            >
          </div>
        {/each}
      </div>
    {/if}

    <div class="toggles">
      <label class="switch">
        <input type="checkbox" data-testid="rag-toggle" bind:checked={useRag} />
        <span>RAG (web search context)</span>
      </label>
      <label class="switch">
        <input type="checkbox" bind:checked={deepResearch} />
        <span>Deep Research (between rounds)</span>
      </label>
    </div>
  </section>

  <button
    class="btn btn-secondary toggle-adv"
    onclick={() => (advancedOpen = !advancedOpen)}
    aria-expanded={advancedOpen}
  >
    <Icon name={advancedOpen ? "chevron-up" : "chevron-down"} size="sm" />
    Advanced settings
  </button>

  {#if advancedOpen}
    <section class="form-section advanced">
      <div class="row">
        <div class="field">
          <label for="nd-format">Response format</label>
          <select
            id="nd-format"
            bind:value={responseFormat}
            onchange={applyResponseFormat}
          >
            <option value="default">Default — Let the model decide</option>
            <option value="compact">Compact — Precise, bullet points, short</option>
            <option value="elaborate"
              >Elaborate — Detailed with explanations & reasoning</option
            >
          </select>
        </div>
        <div class="field">
          <label for="nd-rounds">Rounds</label>
          <select id="nd-rounds" bind:value={totalRounds}>
            <option value={2}>2 rounds</option>
            <option value={3}>3 rounds</option>
          </select>
        </div>
      </div>

      <label for="nd-instructions"
        >Custom instructions (overrides format above)</label
      >
      <textarea
        id="nd-instructions"
        bind:value={instructions}
        placeholder="Optional guidance for all models"
        rows="2"
      ></textarea>

      <div class="row">
        <div class="field">
          <label for="nd-summaryfmt">Summary format</label>
          <select
            id="nd-summaryfmt"
            bind:value={summaryFormat}
            onchange={applySummaryFormat}
          >
            <option value="elaborate"
              >Elaborate — Full synthesis with reasoning</option
            >
            <option value="compact"
              >Compact — Quick verdict with weighted scores</option
            >
            <option value="default">Default — Let consensus model decide</option>
          </select>
        </div>
      </div>

      <label for="nd-summaryinstr"
        >Summary instructions (overrides format above)</label
      >
      <textarea
        id="nd-summaryinstr"
        bind:value={summaryInstructions}
        placeholder="Optional guidance for the consensus synthesis"
        rows="2"
      ></textarea>

      <div class="row">
        <div class="field">
          <label for="nd-timeout">Timeout (s)</label>
          <input id="nd-timeout" type="number" bind:value={timeout} min="10" />
        </div>
        <div class="field">
          <label for="nd-maxtokens">Max tokens</label>
          <input
            id="nd-maxtokens"
            type="number"
            bind:value={maxTokens}
            min="256"
          />
        </div>
      </div>

      <div class="field consensus-field">
        <label for="nd-consensus">Consensus model</label>
        <select id="nd-consensus" bind:value={consensusModel}>
          {#each consensusOptions as key (key)}
            {@const { provider, model } = splitModelKey(key)}
            <option value={key}>{provider}::{model}</option>
          {/each}
        </select>
      </div>
    </section>
  {/if}

  {#if error}
    <div class="error" role="alert">{error}</div>
  {/if}

  {#if discussion.running}
    <div class="running-actions">
      <button
        class="btn btn-primary start"
        data-testid="stop-summarize-btn"
        onclick={stopAndSummarize}
        disabled={summarizing}
      >
        <Icon name="stop" size="sm" />
        {summarizing ? "Summarizing…" : "Stop Discussion and Summarize"}
      </button>
      <button
        class="btn btn-secondary close-btn"
        data-testid="close-discussion-btn"
        onclick={closeDiscussion}
      >
        <Icon name="close" size="sm" /> Close
      </button>
    </div>
  {:else}
    <button
      class="btn btn-primary start"
      data-testid="start-discussion-btn"
      onclick={start}
      disabled={starting}
    >
      <Icon name="play" size="sm" />
      {starting ? "Starting…" : "Start Discussion"}
    </button>
  {/if}
</div>

<style>
  .new-discussion {
    max-width: 900px;
    margin: 0 auto;
  }
  .form-section {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 18px;
    margin-top: 16px;
  }
  .form-section textarea {
    width: 100%;
    box-sizing: border-box;
  }
  #nd-question {
    min-height: 160px;
    resize: both;
  }
  .drop-zone {
    border: 2px dashed var(--border);
    border-radius: var(--radius);
    padding: 14px;
    text-align: center;
    color: var(--text-tertiary);
    font-size: 13px;
    margin-top: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    cursor: pointer;
    transition: all var(--transition);
  }
  .drop-zone:hover,
  .drop-zone.dragover {
    border-color: var(--accent);
    color: var(--accent);
  }
  .files {
    margin-top: 8px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .file {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    background: var(--bg-tertiary);
    border-radius: var(--radius);
    font-size: 12px;
  }
  .file .rm {
    margin-left: auto;
    background: none;
    border: none;
    color: var(--error);
    font-weight: bold;
    font-size: 16px;
  }
  .toggles {
    display: flex;
    gap: 20px;
    margin-top: 14px;
    flex-wrap: wrap;
  }
  .switch {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    font-size: 13px;
    color: var(--text-primary);
    font-weight: 400;
    cursor: pointer;
  }
  .switch input {
    accent-color: var(--accent);
    width: auto;
  }
  .toggle-adv {
    margin-top: 16px;
    width: 100%;
  }
  .advanced .row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }
  .advanced label {
    margin-top: 12px;
  }
  .field {
    display: flex;
    flex-direction: column;
  }
  .field input,
  .field select {
    width: 100%;
  }
  .consensus-field {
    max-width: 320px;
  }
  .error {
    margin-top: 14px;
    padding: 8px 12px;
    background: var(--error-bg);
    color: var(--error);
    border-radius: var(--radius);
    font-size: 13px;
  }
  .start {
    margin-top: 18px;
    width: 100%;
    padding: 12px;
    font-size: 15px;
  }
  .running-actions {
    display: flex;
    gap: 10px;
    align-items: stretch;
  }
  .running-actions .start {
    flex: 1;
  }
  .close-btn {
    margin-top: 18px;
    padding: 12px 18px;
    font-size: 15px;
    white-space: nowrap;
  }
  @media (max-width: 640px) {
    .advanced .row {
      grid-template-columns: 1fr;
    }
  }
</style>
