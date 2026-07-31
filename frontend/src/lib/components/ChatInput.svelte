<script lang="ts">
  import { discussion } from "../stores/discussion.svelte";
  import { models } from "../stores/models.svelte";
  import { splitModelKey, VISION_RE, TEXT_ONLY_RE } from "../utils/helpers";
  import DOMPurify from "dompurify";
  import { isSupportedDocument, extractDocumentText } from "../utils/extractDocument";
  import type { AttachedFile } from "../api/types";
  import Icon from "./Icon.svelte";

  interface Props {
    autofocus?: boolean;
    placeholder?: string;
    onEditModels?: () => void;
  }
  let {
    autofocus = false,
    placeholder = "Ask your question…",
    onEditModels,
  }: Props = $props();

  let text = $state("");
  let ragMode = $state<"model-self" | "model-only">(discussion.data?.ragMode ?? "model-only");
  let deepResearch = $state(discussion.data?.deep_research ?? false);
  let attachments = $state<AttachedFile[]>([]);
  let dragover = $state(false);
  let sending = $state(false);
  let editorEl = $state<HTMLDivElement | null>(null);
  let showAdvanced = $state(false);
  let isCollapsed = $state(false);
  let consensusEnabled = $state(discussion.data?.consensusEnabled ?? false);
  let instructions = $state(discussion.data?.instructions ?? "");
  let responseFormatText = $state(discussion.data?.responseFormatText ?? "");
  let summaryFormatText = $state(
    discussion.data?.summaryFormatText ??
      "Simply get information from all responses. Do not add any more information from your side or elsewhere. analyze all the responses, get the common points and the not common points and share in very short precise format a best consensus. No additional explanations.",
  );
  let summaryInstructions = $state(discussion.data?.summaryInstructions ?? "");
  let timeout = $state(discussion.data?.timeout ?? 120);
  let maxTokens = $state(discussion.data?.maxTokens ?? 6000);
  let consensusModel = $state(discussion.data?.consensusModel ?? "");
  let totalRounds = $state(discussion.data?.totalRounds ?? 1);
  let showInfo = $state(false);

  // Dock Height Resizing Bounded strictly UPWARDS
  let dockHeight = $state<number | null>(null);
  let draggingHeight = $state(false);
  let dragStartY = $state(0);
  let dragStartH = $state(160);

  // Auto-minimize on Android / Mobile when discussion is active/running
  $effect(() => {
    if (discussion.running) {
      isCollapsed = true;
    }
  });

  function startDragHeight(e: PointerEvent) {
    if (isCollapsed) return;
    draggingHeight = true;
    dragStartY = e.clientY;
    dragStartH = dockHeight ?? 160;
    try {
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    } catch { /* fallback */ }
    e.preventDefault();
  }

  function onPointerMoveHeight(e: PointerEvent) {
    if (!draggingHeight || isCollapsed) return;
    const delta = dragStartY - e.clientY;
    // Bounds: Min 130px, Max min(380px, 42vh).
    const minH = 130;
    const maxH = Math.min(380, Math.floor(window.innerHeight * 0.42));
    dockHeight = Math.max(minH, Math.min(maxH, dragStartH + delta));
  }

  function endPointerUpHeight(e: PointerEvent) {
    if (!draggingHeight) return;
    draggingHeight = false;
    try {
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch { /* fallback */ }
  }

  function toggleCollapse() {
    isCollapsed = !isCollapsed;
  }

  const RESPONSE_PRESETS: Record<string, string> = {
    none: "",
    compact:
      "Simply get information from all responses. Do not add any more information from your side or elsewhere. analyze all the responses, get the common points and the not common points and share in very short precise format a best consensus. No additional explanations.",
    elaborate:
      "Respond in detail with thorough reasoning, examples where helpful, and a clear structure. Explore nuance and trade-offs.",
  };
  const SUMMARY_PRESETS: Record<string, string> = {
    none: "",
    compact:
      "Simply get information from all responses. Do not add any more information from your side or elsewhere. analyze all the responses, get the common points and the not common points and share in very short precise format a best consensus. No additional explanations.",
    elaborate:
      "Provide an elaborate synthesis: a full structured write-up covering each model's position, points of consensus, and remaining disagreements.",
  };

  let responseFormat = $state<"none" | "compact" | "elaborate" | "custom">(discussion.data?.responseFormat ?? "none");
  let summaryFormat = $state<"none" | "compact" | "elaborate" | "custom">(discussion.data?.summaryFormat ?? "compact");

  function applyResponsePreset(preset: string) {
    responseFormat = preset as "none" | "compact" | "elaborate" | "custom";
    if (preset !== "custom" && RESPONSE_PRESETS[preset] !== undefined) {
      responseFormatText = RESPONSE_PRESETS[preset];
    }
  }
  function applySummaryPreset(preset: string) {
    summaryFormat = preset as "none" | "compact" | "elaborate" | "custom";
    if (preset !== "custom" && SUMMARY_PRESETS[preset] !== undefined) {
      summaryFormatText = SUMMARY_PRESETS[preset];
    }
  }

  $effect(() => {
    if (autofocus && editorEl && !isCollapsed) editorEl.focus();
  });

  const running = $derived(discussion.running);

  function autoGrow() {
    if (!editorEl) return;
    text = readText();
  }

  function readText(): string {
    if (!editorEl) return "";
    return (editorEl.innerText ?? "").replace(/\u00a0/g, " ").trim();
  }

  const MAX_FILE_SIZE = 100 * 1024 * 1024;

  async function handleFiles(fileList: FileList | File[] | null) {
    if (!fileList) return;
    for (const file of Array.from(fileList)) {
      if (file.size > MAX_FILE_SIZE) {
        alert(`${file.name} exceeds the 100 MB limit.`);
        continue;
      }
      const isImage = file.type.startsWith("image/");
      let content: string;
      if (isImage) {
        content = await blobToBase64(file);
      } else if (isSupportedDocument(file.type)) {
        const extracted = await extractDocumentText(file);
        content = extracted ?? "[Could not extract text from this file format]";
      } else {
        content = await file.text();
      }
      attachments = [
        ...attachments,
        { name: file.name, size: file.size, type: file.type, content },
      ];
    }
  }

  function blobToBase64(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const result = reader.result as string;
        resolve(result.split(",")[1] ?? result);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  function removeFile(name: string) {
    attachments = attachments.filter((f) => f.name !== name);
  }

  function onDragOver(e: DragEvent) {
    if (!e.dataTransfer?.types.includes("Files")) return;
    e.preventDefault();
    dragover = true;
  }
  function onDragLeave(e: DragEvent) {
    if ((e.relatedTarget as Node | null) && (e.currentTarget as HTMLElement).contains(e.relatedTarget as Node)) return;
    dragover = false;
  }
  function onDrop(e: DragEvent) {
    e.preventDefault();
    dragover = false;
    if (e.dataTransfer?.files?.length) handleFiles(e.dataTransfer.files);
  }

  async function send() {
    const question = readText();
    if (!question || sending) return;
    if (models.selected.length === 0) return;
    const attach = attachments;
    const chatAttachments = attach.map((a) => ({ name: a.name, type: a.type, content: a.content }));
    const textAttachments = attach.filter((a) => !a.type.startsWith("image/"));
    if (editorEl) editorEl.innerHTML = "";
    text = "";
    attachments = [];
    sending = true;
    try {
      if (discussion.data.id == null) {
        await discussion.start({
          question,
          models: models.selected,
          instructions,
          consensusEnabled,
          endpoint: "",
          consensusModel: consensusModel || models.selected[0],
          totalRounds,
          timeout,
          maxTokens,
          ragMode,
          deepResearch: deepResearch,
          responseFormat,
          responseFormatText,
          summaryFormat,
          summaryFormatText,
          summaryInstructions,
          attachments: chatAttachments,
        });
      } else {
        let full = question;
        if (textAttachments.length > 0) {
          full += textAttachments
            .map((a) => `\n\n--- Attached: ${a.name} ---\n${a.content}`)
            .join("");
        }
        await discussion.nextTurn(full, models.selected, chatAttachments, {
          instructions,
          consensusModel: consensusModel || models.selected[0],
          totalRounds,
          timeout,
          maxTokens,
          ragMode,
          deepResearch,
          responseFormat,
          responseFormatText,
          summaryFormat,
          summaryFormatText,
          summaryInstructions,
          consensusEnabled,
        });
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

  function onPaste(e: ClipboardEvent) {
    const files = e.clipboardData?.files;
    if (files && files.length > 0) {
      e.preventDefault();
      handleFiles(files);
      return;
    }
    const items = e.clipboardData?.items;
    if (items && items.length > 0) {
      const imageItems = Array.from(items).filter((it) => it.type.startsWith("image/"));
      if (imageItems.length > 0) {
        e.preventDefault();
        const blobs = imageItems
          .map((it) => it.getAsFile())
          .filter((f): f is File => f !== null);
        if (blobs.length > 0) {
          handleFiles(blobs);
        }
        return;
      }
    }
    e.preventDefault();
    const html = e.clipboardData?.getData("text/html");
    const textPlain = e.clipboardData?.getData("text/plain") ?? "";
    if (html && editorEl) {
      const clean = stripDangerous(html);
      document.execCommand("insertHTML", false, clean);
    } else if (editorEl) {
      document.execCommand("insertText", false, textPlain);
    }
    text = readText();
    autoGrow();
  }

  function stripDangerous(html: string): string {
    return DOMPurify.sanitize(html, {
      ALLOWED_TAGS: ["b", "i", "em", "strong", "a", "p", "br", "ul", "ol", "li", "code", "pre"],
      ALLOWED_ATTR: ["href", "target", "rel"],
    });
  }

  function modelSupportsVision(key: string): boolean {
    if (TEXT_ONLY_RE.test(key) && !VISION_RE.test(key)) return false;
    return VISION_RE.test(key);
  }

  const hasImageAttachment = $derived(attachments.some((a) => a.type.startsWith("image/")));
  const selectionHasVision = $derived(
    models.selected.length > 0 && models.selected.some(modelSupportsVision)
  );
  const imageButNoVision = $derived(hasImageAttachment && !selectionHasVision);
</script>

<!-- Single Bottom-Docked Chatbox Component (No nested boxes/outer wrappers) -->
<div
  class="chat-input-bar"
  class:collapsed={isCollapsed}
  class:dragover
  style={!isCollapsed && dockHeight != null ? "height:" + dockHeight + "px;" : ""}
  ondragover={onDragOver}
  ondragleave={onDragLeave}
  ondrop={onDrop}
  role="region"
  aria-label="Chat input"
>
  <!-- Full-width top height drag handle -->
  <div
    class="resize-handle top-bar"
    role="slider"
    aria-label="Resize chat box height"
    aria-valuenow={dockHeight ?? 160}
    tabindex="0"
    onpointerdown={startDragHeight}
    onpointermove={onPointerMoveHeight}
    onpointerup={endPointerUpHeight}
    ondblclick={toggleCollapse}
    title="Drag up/down to resize height, double-click to collapse/expand"
  >
    <div class="drag-indicator"></div>
  </div>

  {#if isCollapsed}
    <!-- Collapsed Compact Bar -->
    <div class="compact-bar">
      <button
        class="compact-expand-btn"
        onclick={toggleCollapse}
        data-testid="chat-input-expand"
        aria-label="Expand chat box"
      >
        <span class="compact-placeholder">
          {#if discussion.running}
            <span class="running-indicator">
              <span class="pulse-dot"></span>
              <span>Models responding… Pull up to reply</span>
            </span>
          {:else}
            <Icon name="message-square" size="sm" />
            <span>Ask a follow-up or refine discussion…</span>
          {/if}
        </span>
        <span class="compact-right">
          <span class="compact-models-pill">
            {models.selected.length} model{models.selected.length === 1 ? "" : "s"}
          </span>
          <Icon name="chevron-up" size="sm" />
        </span>
      </button>
    </div>
  {:else}
    <!-- Single Unified Chat Card Contents -->
    <div class="attach-row">
      <div class="attach-left">
        {#if models.selected.length > 0}
          <div class="selected-models">
            <span class="sm-label">Models</span>
            {#each models.selected as key (key)}
              {@const { provider, model } = splitModelKey(key)}
              <span class="chip model-chip" title={key}>
                <Icon name="bot" size="sm" />
                {model}
                <button
                  class="rm"
                  onclick={() => models.toggle(key)}
                  aria-label="Remove {model}"
                >×</button>
              </span>
            {/each}
            <button
              class="btn btn-ghost btn-sm edit-models"
              onclick={() => onEditModels?.()}
              title="Edit model selection"
            >edit</button>
          </div>
        {/if}
      </div>

      <div class="attach-right">
        <button
          type="button"
          class="btn btn-ghost btn-sm collapse-btn"
          onclick={toggleCollapse}
          data-testid="chat-input-collapse"
          title="Minimize composer"
          aria-label="Minimize composer"
        >
          <Icon name="chevron-down" size="sm" />
        </button>
      </div>
    </div>

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

    {#if imageButNoVision}
      <div class="vision-warn" role="status">
        <Icon name="alert" size="sm" />
        Image attached, but selected model(s) may not support vision. Use GPT-4o, Gemini, Claude 3.5+.
      </div>
    {/if}

    <!-- Direct Editor Area (Flex 1 fills all height directly inside card without empty gaps) -->
    <div
      class="editor"
      bind:this={editorEl}
      contenteditable="true"
      role="textbox"
      tabindex="0"
      aria-multiline="true"
      aria-label="Message"
      {placeholder}
      data-testid="chat-input"
      oninput={autoGrow}
      onkeydown={onKeydown}
      onpaste={onPaste}
    ></div>

    <!-- Controls Row (Contained neatly inside single card at bottom) -->
    <div class="chat-controls-row">
      <label class="attach-btn" title="Attach files">
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

      <div class="advanced-wrap">
        <button
          type="button"
          class="adv-toggle"
          onclick={() => (showAdvanced = !showAdvanced)}
          aria-expanded={showAdvanced}
        >
          <Icon name="settings" size="sm" />
          Advanced
          <Icon name={showAdvanced ? "chevron-down" : "chevron-right"} size="sm" />
        </button>
        <span
          class="info-wrap"
          role="note"
          onmouseenter={() => (showInfo = true)}
          onmouseleave={() => (showInfo = false)}
          onfocus={() => (showInfo = true)}
          onblur={() => (showInfo = false)}
          aria-label="Advanced settings help"
        >
          <Icon name="info" size="sm" />
          {#if showInfo}
            <span class="info-pop">
              <strong>Consensus</strong> — synthesized consensus summary.<br />
              <strong>Consensus Model</strong> — model that writes final synthesis.<br />
              <strong>Rounds</strong> — discussion passes.<br />
              <strong>Response & Summary Format</strong> — custom format instructions.<br />
              <strong>RAG Mode</strong> — context retrieval from web/knowledge base.<br />
              <strong>Deep Research</strong> — web search between rounds.
            </span>
          {/if}
        </span>

        {#if showAdvanced}
          <div class="adv-panel">
            <div class="adv-panel-header">
              <span class="adv-title">Advanced Configuration</span>
              <button
                type="button"
                class="btn btn-ghost btn-sm adv-close"
                onclick={() => (showAdvanced = false)}
                aria-label="Close advanced settings"
              >×</button>
            </div>
            <div class="adv-panel-grid">
              <div class="adv-field adv-inline">
                <label class="switch inline" class:on={consensusEnabled} title="Enable consensus synthesis">
                  <input type="checkbox" bind:checked={consensusEnabled} />
                  <span class="track" aria-hidden="true"><span class="thumb"></span></span>
                  <span>Consensus</span>
                </label>
              </div>

              <div class="adv-field" class:disabled={!consensusEnabled}>
                <label for="pf-consensus" class:disabled={!consensusEnabled}>Consensus Model</label>
                <select id="pf-consensus" bind:value={consensusModel} disabled={!consensusEnabled}>
                  <option value="">Auto (first selected model)</option>
                  {#each models.selected as m (m)}
                    <option value={m}>{m.split("::")[1] ?? m}</option>
                  {/each}
                </select>
              </div>

              <div class="adv-field" class:disabled={!consensusEnabled}>
                <label for="pf-rounds" class:disabled={!consensusEnabled}>Rounds</label>
                <select id="pf-rounds" bind:value={totalRounds} disabled={!consensusEnabled}>
                  <option value={1}>1 Round</option>
                  <option value={2}>2 Rounds</option>
                  <option value={3}>3 Rounds</option>
                </select>
              </div>

              <div class="adv-field">
                <label for="pf-rag">RAG Retrieval Mode</label>
                <select id="pf-rag" bind:value={ragMode} data-testid="rag-mode-select" aria-label="RAG mode">
                  <option value="model-self">Model/Self (Default)</option>
                  <option value="model-only">Model-Only</option>
                </select>
              </div>

              <div class="adv-field span-2">
                <label for="pf-response-preset">Response Format</label>
                <select
                  id="pf-response-preset"
                  value={responseFormat}
                  onchange={(e) => applyResponsePreset((e.currentTarget as HTMLSelectElement).value)}
                >
                  <option value="none">None</option>
                  <option value="compact">Compact</option>
                  <option value="elaborate">Elaborate</option>
                  <option value="custom">Custom</option>
                </select>
                <textarea
                  id="pf-response-text"
                  rows="2"
                  bind:value={responseFormatText}
                  placeholder="Instruction sent to each model about how to format its response…"
                ></textarea>
              </div>

              <div class="adv-field span-2">
                <label for="pf-summary-preset">Discussion / Summary Format</label>
                <select
                  id="pf-summary-preset"
                  value={summaryFormat}
                  onchange={(e) => applySummaryPreset((e.currentTarget as HTMLSelectElement).value)}
                >
                  <option value="none">None</option>
                  <option value="compact">Compact (default)</option>
                  <option value="elaborate">Elaborate</option>
                  <option value="custom">Custom</option>
                </select>
                <textarea
                  id="pf-summary-text"
                  rows="2"
                  bind:value={summaryFormatText}
                  placeholder="Instruction sent to consensus model…"
                ></textarea>
              </div>

              <div class="adv-field span-2">
                <label for="pf-instructions">Custom Instructions</label>
                <textarea id="pf-instructions" rows="2" bind:value={instructions}
                  placeholder="E.g., Always cite your sources…"></textarea>
              </div>

              <div class="adv-field">
                <label for="pf-timeout">Response Timeout (sec)</label>
                <input id="pf-timeout" type="number" min="10" max="300" bind:value={timeout} />
              </div>

              <div class="adv-field">
                <label for="pf-maxtok">Max Tokens / Response</label>
                <input id="pf-maxtok" type="number" min="500" max="16000" step="500" bind:value={maxTokens} />
              </div>

              <div class="adv-field adv-inline span-2">
                <label class="switch inline" class:on={deepResearch} title="Deep Research (web search between rounds)">
                  <input type="checkbox" bind:checked={deepResearch} />
                  <span class="track" aria-hidden="true"><span class="thumb"></span></span>
                  <Icon name="search" size="sm" />
                  <span class="dr-label">Deep Research</span>
                </label>
              </div>
            </div>
          </div>
        {/if}
      </div>

      <button
        class="btn btn-primary send"
        data-testid="chat-send"
        onclick={running ? () => discussion.stop() : send}
        disabled={!text.trim() && !running || sending || models.selected.length === 0}
      >
        <Icon name={running ? "stop" : "arrow-right"} size="sm" />
        {running ? "Stop" : "Send"}
      </button>
    </div>
  {/if}
</div>

<style>
  /* Single Unified Bottom Dock Component - Complete 4-sided rectangular outline */
  .chat-input-bar {
    border: 1px solid var(--input-border, #1f1f23);
    border-radius: var(--radius-lg);
    background: var(--input-bg, #16161a);
    padding: 10px 14px 12px;
    width: calc(100% - 32px);
    max-width: 760px;
    margin: 0 auto 8px;
    position: relative;
    bottom: 0;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    min-height: 130px;
    max-height: min(380px, 42vh);
    transition: border-color var(--transition), max-height var(--transition), padding var(--transition);
  }

  .chat-input-bar:focus-within {
    border-color: var(--accent);
  }

  .chat-input-bar.dragover {
    border-color: var(--accent);
    border-style: dashed;
    background: var(--accent-bg, rgba(255, 92, 0, 0.06));
  }

  .chat-input-bar.collapsed {
    padding: 6px 12px 6px;
    height: 44px !important;
    min-height: 44px !important;
    max-height: 44px !important;
    overflow: hidden;
  }

  /* Full-width top height drag handle - Positioned exactly on top border of chatbox */
  .resize-handle.top-bar {
    position: absolute;
    top: -6px;
    left: 0;
    right: 0;
    height: 12px;
    cursor: ns-resize;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 20;
    touch-action: none;
  }

  .drag-indicator {
    width: 38px;
    height: 3px;
    background: var(--border-hover, #2e2e33);
    border-radius: 999px;
    transition: background var(--transition), width var(--transition);
  }

  .resize-handle.top-bar:hover .drag-indicator {
    background: var(--accent);
    width: 48px;
  }

  /* Direct Editor Area (Fills space directly inside single card - NO empty gap) */
  .editor {
    flex: 1;
    width: 100%;
    border: none;
    background: none;
    padding: 2px 0;
    outline: none;
    resize: none;
    min-height: 50px;
    overflow-y: auto;
    line-height: 1.5;
    color: var(--text-primary);
    font-size: 14px;
    box-sizing: border-box;
  }

  .editor:empty::before {
    content: attr(placeholder);
    color: var(--text-tertiary);
    pointer-events: none;
  }

  /* Compact collapsed view */
  .compact-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 32px;
  }

  .compact-expand-btn {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0 12px;
    color: var(--text-secondary);
    font-size: 13px;
    cursor: pointer;
    transition: border-color var(--transition), color var(--transition);
  }

  .compact-expand-btn:hover {
    border-color: var(--accent);
    color: var(--text-primary);
  }

  .compact-placeholder {
    display: flex;
    align-items: center;
    gap: 8px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .running-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--accent-light);
    font-weight: 600;
  }

  .pulse-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent);
    animation: pulse 1.2s ease-in-out infinite;
  }

  .compact-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .compact-models-pill {
    font-size: 11px;
    color: var(--text-tertiary);
    background: var(--bg-secondary);
    padding: 2px 8px;
    border-radius: 999px;
    border: 1px solid var(--border);
  }

  /* Header row inside card */
  .attach-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 6px;
  }

  .attach-left {
    flex: 1;
    min-width: 0;
  }

  .attach-right {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .collapse-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 6px;
    color: var(--text-tertiary);
    border-radius: var(--radius);
    min-width: 28px;
    min-height: 28px;
  }

  .collapse-btn:hover {
    color: var(--text-primary);
    background: var(--bg-tertiary);
  }

  .chat-controls-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 8px;
    gap: 8px;
  }

  .attach-btn {
    display: inline-flex;
  }

  .advanced-wrap {
    position: relative;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .adv-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    padding: 6px 10px;
    min-height: 32px;
    transition: border-color var(--transition), color var(--transition);
  }

  .adv-toggle:hover {
    border-color: var(--accent);
    color: var(--text-primary);
  }

  .info-wrap {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    color: var(--text-tertiary);
    cursor: help;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
  }

  .info-wrap:hover,
  .info-wrap:focus {
    color: var(--text-secondary);
    outline: none;
    border-color: var(--accent);
  }

  .info-pop {
    position: absolute;
    bottom: calc(100% + 8px);
    right: 0;
    z-index: 60;
    width: min(320px, 80vw);
    padding: 10px 12px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-secondary);
    color: var(--text-secondary);
    font-size: 11.5px;
    line-height: 1.5;
    box-shadow: var(--shadow-md);
    text-align: left;
  }

  .info-pop strong {
    color: var(--text-primary);
  }

  /* Advanced Panel Overlay Sheet */
  .adv-panel {
    position: absolute;
    bottom: calc(100% + 8px);
    right: 0;
    width: min(520px, 92vw);
    padding: 14px;
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    background: var(--bg-secondary);
    box-shadow: var(--shadow-md);
    max-height: 52vh;
    overflow-y: auto;
    z-index: 50;
  }

  .adv-panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
  }

  .adv-title {
    font-size: 13px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .adv-close {
    font-size: 18px;
    padding: 2px 6px;
    line-height: 1;
  }

  .adv-panel-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px 14px;
    align-items: start;
  }

  .adv-panel-grid .span-2 {
    grid-column: 1 / -1;
  }

  .adv-field {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .adv-field label {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-tertiary);
  }

  .adv-field select,
  .adv-field input,
  .adv-field textarea {
    width: 100%;
    box-sizing: border-box;
  }

  .adv-field textarea {
    resize: vertical;
    font-size: 12px;
  }

  .adv-field.disabled {
    opacity: 0.45;
    pointer-events: none;
  }

  .files {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 8px;
  }

  .vision-warn {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    font-size: 12px;
    line-height: 1.4;
    color: var(--warning);
    background: var(--warning-bg);
    border: 1px solid color-mix(in srgb, var(--warning) 40%, transparent);
    border-radius: var(--radius);
    padding: 7px 10px;
    margin-bottom: 8px;
  }

  .selected-models {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
  }

  .sm-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-tertiary);
    margin-right: 2px;
  }

  .chip.model-chip {
    padding: 4px 8px;
  }

  .chip.model-chip :global(svg) {
    color: var(--accent);
  }

  .edit-models {
    font-size: 11px;
    padding: 4px 8px;
    color: var(--text-tertiary);
    min-height: 28px;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
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
    font-size: 16px;
    line-height: 1;
    padding: 4px;
    margin-right: -2px;
    cursor: pointer;
  }

  .switch {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    height: 32px;
    padding: 0 10px;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    cursor: pointer;
    white-space: nowrap;
    transition: border-color var(--transition), color var(--transition);
  }

  .switch.on {
    color: var(--text-primary);
    border-color: var(--accent);
  }

  .switch input {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
    margin: 0;
    pointer-events: none;
  }

  .track {
    position: relative;
    width: 30px;
    height: 16px;
    border-radius: 999px;
    background: var(--border-hover);
    transition: background var(--transition);
    flex-shrink: 0;
  }

  .thumb {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--text-secondary);
    transition: transform var(--transition), background var(--transition);
  }

  .switch.on .track {
    background: var(--accent);
  }

  .switch.on .thumb {
    transform: translateX(14px);
    background: #fff;
  }

  .send {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 36px;
    padding: 0 16px;
    font-size: 13px;
  }

  .icon-btn {
    padding: 8px;
    min-height: 36px;
    min-width: 36px;
  }

  /* Mobile and Touch-screen Ergonomics */
  @media (max-width: 768px) {
    .chat-input-bar {
      padding: 6px 10px max(10px, env(safe-area-inset-bottom, 0px));
      width: calc(100% - 16px);
    }

    .editor:focus {
      max-height: 25vh;
    }

    .send {
      min-height: 38px;
    }

    .adv-panel {
      width: calc(100vw - 24px);
      right: -10px;
    }

    /* Mobile optimization */
  }
</style>
