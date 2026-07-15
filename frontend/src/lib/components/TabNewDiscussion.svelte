<script lang="ts">
  import { models } from "../stores/models.svelte";
  import { providers } from "../stores/providers.svelte";
  import { discussion } from "../stores/discussion.svelte";
  import { nav } from "../stores/nav.svelte";
  import { debug } from "../stores/debug.svelte";
  import type { AttachedFile } from "../api/types";
  import { splitModelKey } from "../utils/helpers";
  import ModelSelector from "./ModelSelector.svelte";
  import ActiveEnsemble from "./ActiveEnsemble.svelte";
  import Icon from "./Icon.svelte";

  let question = $state("");
  let instructions = $state("");
  let useRag = $state(false);
  let deepResearch = $state(false);
  let responseFormat = $state("default");
  let summaryFormat = $state<"default" | "compact" | "elaborate">("default");
  let summaryInstructions = $state("");
  let totalRounds = $state(2);
  let timeout = $state(120);
  let maxTokens = $state(6000);
  let consensusModel = $state("");
  let advancedOpen = $state(false);
  let attachments = $state<AttachedFile[]>([]);
  let dragover = $state(false);
  let starting = $state(false);
  let error = $state<string | null>(null);

  let consensusOptions = $derived(models.selected);

  $effect(() => {
    if (!consensusModel && models.selected.length > 0) {
      consensusModel = models.selected[0];
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
  <ModelSelector />
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
          <select id="nd-format" bind:value={responseFormat}>
            <option value="default">Default</option>
            <option value="markdown">Markdown</option>
            <option value="bullet points">Bullet points</option>
            <option value="essay">Essay</option>
            <option value="JSON">JSON</option>
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

      <label for="nd-instructions">Custom instructions</label>
      <textarea
        id="nd-instructions"
        bind:value={instructions}
        placeholder="Optional guidance for all models"
        rows="2"
      ></textarea>

      <div class="row">
        <div class="field">
          <label for="nd-summaryfmt">Summary format</label>
          <select id="nd-summaryfmt" bind:value={summaryFormat}>
            <option value="default">Default</option>
            <option value="compact">Compact</option>
            <option value="elaborate">Elaborate</option>
          </select>
        </div>
        <div class="field">
          <label for="nd-consensus">Consensus model</label>
          <select id="nd-consensus" bind:value={consensusModel}>
            {#each consensusOptions as key (key)}
              {@const { model } = splitModelKey(key)}
              <option value={key}>{model}</option>
            {/each}
          </select>
        </div>
      </div>

      <label for="nd-summaryinstr">Summary instructions</label>
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
    </section>
  {/if}

  {#if error}
    <div class="error" role="alert">{error}</div>
  {/if}

  <button
    class="btn btn-primary start"
    data-testid="start-discussion-btn"
    onclick={start}
    disabled={starting || discussion.running}
  >
    <Icon name="play" size="sm" />
    {starting ? "Starting…" : "Start Discussion"}
  </button>
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
  @media (max-width: 640px) {
    .advanced .row {
      grid-template-columns: 1fr;
    }
  }
</style>
