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
   let ragMode = $state<"model-self" | "model-only">("model-only");
   let deepResearch = $state(false);
   let attachments = $state<AttachedFile[]>([]);
   let dragover = $state(false);
   let sending = $state(false);
   let editorEl = $state<HTMLDivElement | null>(null);
   let showAdvanced = $state(false);
   let consensusEnabled = $state(false);
   let instructions = $state("");
   let responseFormatText = $state("");
   let summaryFormatText = $state(
     "Simply get information from all responses. Do not add any more information from your side or elsewhere. analyze all the responses, get the common points and the not common points and share in very short precise format a best consensus. No additional explanations.",
   );
   let summaryInstructions = $state("");
   let timeout = $state(120);
   let maxTokens = $state(6000);
   let consensusModel = $state("");
    let totalRounds = $state(1);
   let showInfo = $state(false);
   let chatHeight = $state<number | null>(null);
   let dragging = $state(false);
   let dragStartY = $state(0);
   let dragStartH = $state(300);

   function startDrag(e: MouseEvent) {
     dragging = true;
     dragStartY = e.clientY;
     dragStartH = chatHeight ?? 300;
     e.preventDefault();
   }

   $effect(() => {
     if (!dragging) return;
     const onMove = (e: MouseEvent) => {
       const delta = dragStartY - e.clientY;
       chatHeight = Math.max(100, Math.min(600, dragStartH + delta));
     };
     const onUp = () => { dragging = false; };
     window.addEventListener("mousemove", onMove);
     window.addEventListener("mouseup", onUp);
     return () => {
       window.removeEventListener("mousemove", onMove);
       window.removeEventListener("mouseup", onUp);
     };
   });

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

   let responseFormat = $state<"none" | "compact" | "elaborate" | "custom">("none");
   let summaryFormat = $state<"none" | "compact" | "elaborate" | "custom">("compact");

   // Selecting a preset auto-fills the (editable) text field. "custom" leaves
   // the current text untouched so the user can write their own.
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
     if (autofocus && editorEl) editorEl.focus();
   });

   const running = $derived(discussion.running);

   function autoGrow() {
    if (!editorEl) return;
    editorEl.style.height = "auto";
    editorEl.style.height = Math.min(editorEl.scrollHeight, 250) + "px";
    text = readText();
  }

  function readText(): string {
    if (!editorEl) return "";
    return (editorEl.innerText ?? "").replace(/ /g, " ").trim();
  }

  const MAX_FILE_SIZE = 100 * 1024 * 1024;

  async function handleFiles(fileList: FileList | null) {
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
    // Attachments handed to the backend as multimodal content (images) and/or
    // appended text. Images are sent via the `attachments` field; text files
    // are also added inline so the model can read them.
    const chatAttachments = attach.map((a) => ({ name: a.name, type: a.type, content: a.content }));
    // Only genuine text files and extracted document content are inlined into
    // the prompt; images are sent as multimodal content (never as base64 text,
    // which would render as garbage).
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
    // Capture pasted files (images copied to clipboard) as attachments.
    // Check .files first (standard), then .items for apps like monosnap
    // that put image blobs in items rather than files.
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
          handleFiles(new FileList(blobs as FileList));
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
    // If it explicitly matches a text-only pattern, assume no vision.
    if (TEXT_ONLY_RE.test(key) && !VISION_RE.test(key)) return false;
    return VISION_RE.test(key);
  }

  const hasImageAttachment = $derived(attachments.some((a) => a.type.startsWith("image/")));
  const selectionHasVision = $derived(
    models.selected.length > 0 && models.selected.some(modelSupportsVision)
  );
  const imageButNoVision = $derived(hasImageAttachment && !selectionHasVision);
</script>

<div class="chat-input-bar" style={chatHeight != null ? "height:" + chatHeight + "px" : ""}>
  <div class="resize-handle left" onmousedown={startDrag}></div>
  <div class="resize-handle right" onmousedown={startDrag}></div>
  <div class="attach-row">
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
        Image attached, but the selected model(s) may not support vision (e.g. DeepSeek is text-only). Use a vision-capable model — GPT-4o, Gemini, Claude 3.5+ — to let it see the image.
      </div>
    {/if}
  </div>

  <div
    class="input-wrap"
    class:dragover
    ondragover={onDragOver}
    ondragleave={onDragLeave}
    ondrop={onDrop}
  >
    <div
      class="editor"
      bind:this={editorEl}
      contenteditable="true"
      role="textbox"
      aria-multiline="true"
      aria-label="Message"
      {placeholder}
      data-testid="chat-input"
      oninput={autoGrow}
      onkeydown={onKeydown}
      onpaste={onPaste}
    ></div>

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

    <div class="advanced">
       <button
        type="button"
        class="adv-toggle"
        onclick={() => (showAdvanced = !showAdvanced)}
        aria-expanded={showAdvanced}
      >
        <Icon name={showAdvanced ? "chevron-down" : "chevron-right"} size="sm" />
        Advanced settings
      </button>
      <span
        class="info-wrap"
        role="note"
        tabindex="0"
        onmouseenter={() => (showInfo = true)}
        onmouseleave={() => (showInfo = false)}
        onfocus={() => (showInfo = true)}
        onblur={() => (showInfo = false)}
        aria-label="Advanced settings help"
      >
        <Icon name="info" size="sm" />
        {#if showInfo}
          <span class="info-pop">
            <strong>Consensus</strong> — when enabled, all model responses are synthesized into a single consensus summary. Disable to see each model's raw reply side by side without a final synthesis.<br />
            <strong>Consensus Model</strong> — model that writes the final synthesis (defaults to the first selected model).<br />
            <strong>Number of Rounds</strong> — how many discussion passes run before a final consensus.<br />
            <strong>Response Format</strong> — instruction each model follows when answering. Pick Compact/Elaborate to auto-fill, or Custom to write your own (all editable).<br />
            <strong>Discussion / Summary Format</strong> — instruction the consensus model follows when synthesizing. Same Compact/Elaborate/Custom options.<br />
            <strong>Custom Instructions</strong> — global rule applied to every model on every turn.<br />
            <strong>Response Timeout</strong> — seconds to wait per model before giving up.<br />
            <strong>Max Tokens / Response</strong> — cap on each model's output length.<br />
            <strong>RAG Retrieval Mode</strong> — Model/Self retrieves context from your knowledge base; Model-Only skips it.<br />
            <strong>Deep Research</strong> — lets models run web search between rounds for fresh information.
          </span>
        {/if}
      </span>

       {#if showAdvanced}
          <div class="adv-panel">
            <div class="adv-panel-grid">
              <div class="adv-field adv-inline">
                <label class="switch inline" class:on={consensusEnabled} title="When enabled, all model responses are synthesized into a consensus summary. When disabled, each model replies individually.">
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
                <label for="pf-rounds" class:disabled={!consensusEnabled}>Number of Rounds</label>
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
                  placeholder="Instruction sent to the consensus model about how to synthesize…"
                ></textarea>
              </div>

              <div class="adv-field span-2">
                <label for="pf-instructions">Custom Instructions (optional — applies to every model & turn)</label>
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

              <div class="adv-field adv-inline">
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
  </div>
</div>

<style>
  .chat-input-bar {
    border-top: 1px solid var(--border);
    background: var(--bg-secondary);
    padding: 10px 16px;
    max-height: 60vh;
    overflow-y: auto;
    position: relative;
  }
  .resize-handle {
    position: absolute;
    top: 0;
    width: 60px;
    height: 6px;
    cursor: ns-resize;
    z-index: 10;
  }
  .resize-handle::after {
    content: "";
    display: block;
    width: 32px;
    height: 2px;
    background: var(--border);
    border-radius: 2px;
    margin: 2px auto 0;
  }
  .resize-handle.left {
    left: 0;
  }
  .resize-handle.right {
    right: 0;
  }
  .resize-handle:hover::after {
    background: var(--accent);
  }
  .chat-controls-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 6px 0 4px;
    gap: 8px;
  }
  .attach-btn {
    display: inline-flex;
  }
  .advanced {
    margin-bottom: 8px;
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
    padding: 5px 10px;
    transition: border-color var(--transition), color var(--transition);
    width: 100%;
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
    width: 18px;
    height: 18px;
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
    left: 0;
    z-index: 50;
    width: min(360px, 80vw);
    padding: 10px 12px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-elevated, #fff);
    color: var(--text-secondary);
    font-size: 11.5px;
    line-height: 1.5;
    font-weight: 400;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
    text-align: left;
  }
  .info-pop strong {
    color: var(--text-primary);
  }
  .adv-panel {
    margin-top: 8px;
    padding: 12px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-tertiary);
    max-height: 46vh;
    overflow-y: auto;
    flex-basis: 100%;
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
  .adv-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 10px;
  }
  .adv-grid-2 {
    grid-template-columns: 1fr 1fr;
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
  .adv-field.disabled label {
    color: var(--text-tertiary);
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
    color: #b45309;
    background: color-mix(in srgb, #f59e0b 14%, transparent);
    border: 1px solid color-mix(in srgb, #f59e0b 40%, transparent);
    border-radius: var(--radius);
    padding: 7px 10px;
    margin-bottom: 8px;
  }
  .vision-warn :global(svg) {
    flex-shrink: 0;
    margin-top: 1px;
  }
  .selected-models {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 8px;
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
    padding: 3px 6px 3px 8px;
  }
  .chip.model-chip :global(svg) {
    color: var(--accent);
  }
  .edit-models {
    font-size: 11px;
    padding: 3px 8px;
    color: var(--text-tertiary);
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
    padding: 14px 16px;
    min-height: 132px;
    display: flex;
    flex-direction: column;
    transition: border-color var(--transition);
  }
  .input-wrap:focus-within {
    border-color: var(--accent);
  }
  .input-wrap.dragover {
    border-color: var(--accent);
    border-style: dashed;
    background: var(--accent-bg, rgba(255, 92, 0, 0.06));
  }
  .editor {
    flex: 1;
    width: 100%;
    border: none;
    background: none;
    padding: 0;
    outline: none;
    resize: none;
    min-height: 86px;
    max-height: 260px;
    overflow-y: auto;
    line-height: 1.6;
    color: var(--text-primary);
    font-size: 14px;
  }
  .editor:empty::before {
    content: attr(placeholder);
    color: var(--text-tertiary);
    pointer-events: none;
  }
  .editor:focus {
    outline: none;
  }
  .editor :global(b),
  .editor :global(strong) {
    font-weight: 700;
  }
  .editor :global(i),
  .editor :global(em) {
    font-style: italic;
  }
  .editor :global(ul),
  .editor :global(ol) {
    margin: 4px 0;
    padding-left: 22px;
  }
  .editor :global(a) {
    color: var(--accent);
    text-decoration: underline;
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
  .switch:hover {
    border-color: var(--accent);
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
  .rag-select {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 32px;
    padding: 0 10px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }
  .rag-select:hover {
    border-color: var(--accent);
  }
  .rag-label {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
  }
  .rag-select select {
    font-size: 12px;
    font-weight: 500;
    height: 100%;
    line-height: 1;
    padding: 4px 4px;
    color: var(--text-secondary);
    background: none;
    border: none;
    outline: none;
    cursor: pointer;
  }
  .rag-select select:focus {
    border: none;
    outline: none;
  }
  .switch.inline {
    height: auto;
    padding: 4px 10px;
    align-self: flex-start;
  }
  .dr-label {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
  }
  .send {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 32px;
    padding: 0 14px;
  }
  .icon-btn {
    padding: 6px;
    height: 32px;
  }
  @media (max-width: 768px) {
    .chat-controls-row {
      flex-wrap: wrap;
    }
    .send {
      margin-left: auto;
    }
    .input-wrap {
      min-height: 96px;
      padding: 12px 14px;
    }
    .editor {
      min-height: 60px;
    }
  }
  @media (max-width: 420px) {
    .chat-controls-row {
      gap: 6px;
    }
    .rag-select,
    .switch {
      flex: 1 1 auto;
    }
    .send {
      flex: 1 1 100%;
      justify-content: center;
    }
  }
</style>
