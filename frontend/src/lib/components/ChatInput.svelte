<script lang="ts">
  import { discussion } from "../stores/discussion.svelte";
  import { models } from "../stores/models.svelte";
  import type { AttachedFile } from "../api/types";
  import Icon from "./Icon.svelte";

  interface Props {
    autofocus?: boolean;
    placeholder?: string;
  }
  let { autofocus = false, placeholder = "Ask your question…" }: Props = $props();

  let text = $state("");
  let ragMode = $state<"model-only" | "model-self">("model-self");
  let deepResearch = $state(false);
  let attachments = $state<AttachedFile[]>([]);
  let dragover = $state(false);
  let sending = $state(false);
  let textareaEl = $state<HTMLTextAreaElement | null>(null);

  $effect(() => {
    if (autofocus && textareaEl) textareaEl.focus();
  });

  const running = $derived(discussion.running);

  function autoGrow() {
    if (!textareaEl) return;
    textareaEl.style.height = "auto";
    textareaEl.style.height = Math.min(textareaEl.scrollHeight, 200) + "px";
  }

  async function handleFiles(fileList: FileList | null) {
    if (!fileList) return;
    for (const file of Array.from(fileList)) {
      if (file.size > 10 * 1024 * 1024) continue;
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

  async function send() {
    if (!text.trim() || sending) return;
    if (models.selected.length === 0) return;
    const question = text;
    const attach = attachments;
    text = "";
    attachments = [];
    sending = true;
    try {
      if (discussion.data.id == null) {
        await discussion.start({
          question,
          models: models.selected,
          instructions: "",
          endpoint: "",
          consensusModel: models.selected[0],
          totalRounds: 1,
          timeout: 120,
          maxTokens: 6000,
          ragMode,
          deepResearch: deepResearch,
          responseFormat: "default",
          summaryFormat: "default",
          summaryInstructions: "",
        });
      } else {
        let full = question;
        if (attach.length > 0) {
          full += attach
            .map((a) => `\n\n--- Attached: ${a.name} ---\n${a.content}`)
            .join("");
        }
        await discussion.nextTurn(full);
      }
    } finally {
      sending = false;
    }
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }
</script>

<div class="chat-input-bar">
  <div class="attach-row">
    {#if attachments.length > 0}
      <div class="files">
        {#each attachments as f (f.name)}
          <span class="chip">
            <Icon name="file" size="sm" />
            {f.name}
            <button class="rm" onclick={() => removeFile(f.name)} aria-label="Remove {f.name}">×</button>
          </span>
        {/each}
      </div>
    {/if}
  </div>

  <div class="input-wrap">
    <textarea
      bind:this={textareaEl}
      bind:value={text}
      {placeholder}
      rows="2"
      oninput={autoGrow}
      onkeydown={onKeydown}
      data-testid="chat-input"
    ></textarea>

    <div class="controls">
      <label class="switch" title="Attach files">
        <button
          class="btn btn-ghost btn-sm icon-btn"
          type="button"
          onclick={() => document.getElementById("chat-file")?.click()}
          aria-label="Attach files"
        >
          <Icon name="paperclip" size="sm" />
        </button>
        <input
          id="chat-file"
          type="file"
          multiple
          style="display:none"
          onchange={(e) => handleFiles((e.target as HTMLInputElement).files)}
        />
      </label>

      <div class="rag-select" title="Retrieval mode">
        <select bind:value={ragMode} data-testid="rag-mode-select" aria-label="Retrieval mode">
          <option value="model-self">Model/Self (Default)</option>
          <option value="model-only">Model-Only</option>
        </select>
      </div>

      <label class="switch" title="Deep Research">
        <input type="checkbox" bind:checked={deepResearch} />
        <Icon name="search" size="sm" />
      </label>

      <button
        class="btn btn-primary send"
        data-testid="chat-send"
        onclick={send}
        disabled={!text.trim() || running || sending || models.selected.length === 0}
      >
        <Icon name={running ? "stop" : "arrow-right"} size="sm" />
        {running ? "Running…" : "Send"}
      </button>
    </div>
  </div>
</div>

<style>
  .chat-input-bar {
    flex-shrink: 0;
    border-top: 1px solid var(--border);
    background: var(--bg-secondary);
    padding: 12px 16px 14px;
  }
  .files {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 8px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: 999px;
    font-size: 12px;
    color: var(--text-secondary);
  }
  .chip .rm {
    background: none;
    border: none;
    color: var(--error);
    font-size: 15px;
    line-height: 1;
    padding: 0 2px;
  }
  .input-wrap {
    border: 1px solid var(--input-border);
    border-radius: var(--radius-lg);
    background: var(--input-bg);
    padding: 10px 12px;
    transition: border-color var(--transition);
  }
  .input-wrap:focus-within {
    border-color: var(--accent);
  }
  textarea {
    width: 100%;
    border: none;
    background: none;
    padding: 0;
    resize: none;
    min-height: 24px;
    line-height: 1.5;
    color: var(--text-primary);
  }
  textarea:focus {
    border: none;
    outline: none;
  }
  .controls {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 8px;
  }
  .switch {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    color: var(--text-secondary);
    cursor: pointer;
  }
  .switch input {
    accent-color: var(--accent);
    width: auto;
    padding: 0;
  }
  .rag-select {
    display: inline-flex;
    align-items: center;
  }
  .rag-select select {
    font-size: 12px;
    padding: 6px 8px;
    color: var(--text-secondary);
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }
  .rag-select select:focus {
    border-color: var(--accent);
  }
  .send {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .icon-btn {
    padding: 6px;
  }
</style>
