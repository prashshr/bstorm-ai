<script lang="ts">
  import { discussion } from "../stores/discussion.svelte";
import { userSettings } from "../stores/settings.svelte";
  import { copyToClipboard, findResumableRound } from "../utils/helpers";
  import Icon from "./Icon.svelte";
  import ModelCard from "./ModelCard.svelte";
  import ConsensusSection from "./ConsensusSection.svelte";
  import ChatInput from "./ChatInput.svelte";
  import ChatExport from "./ChatExport.svelte";
  import ProgressStepper from "./ProgressStepper.svelte";

  let scrollEl = $state<HTMLElement | null>(null);
  let atBottom = $state(true);
  let showJump = $derived(!atBottom && discussion.running);

  // Edit-question (branch) UI: scoped to the discussion id it was opened on,
  // so switching discussions hides the editor without extra effects.
  let editingQuestion = $state(false);
  let editingQuestionForId = $state<string | number | null>(null);
  let editQuestionText = $state("");

  interface Props {
    onEditModels?: () => void;
  }
  let { onEditModels }: Props = $props();

  function onScroll() {
    if (!scrollEl) return;
    const gap = scrollEl.scrollHeight - scrollEl.scrollTop - scrollEl.clientHeight;
    atBottom = gap < 80;
  }

  $effect(() => {
    discussion.data;
    // Perf: autoscroll only when already near the bottom, and jump instantly
    // (behavior:"auto") while a run is in flight — smooth scrolling per delta
    // janks and fights the user. Jump button logic below is unchanged.
    if (atBottom && scrollEl) {
      scrollEl.scrollTo({
        top: scrollEl.scrollHeight,
        behavior: discussion.running ? "auto" : "smooth",
      });
    }
  });

  function jumpToLatest() {
    scrollEl?.scrollTo({
      top: scrollEl.scrollHeight,
      behavior: discussion.running ? "auto" : "smooth",
    });
  }

  const editingActive = $derived(
    editingQuestion && editingQuestionForId === discussion.data.id,
  );

  function startEditQuestion(rn: number) {
    editingQuestion = true;
    editingQuestionForId = discussion.data.id ?? null;
    editQuestionText = cleanUserMessage(discussion.data.userMessages[rn] ?? "");
  }

  async function branchFromEditedQuestion() {
    const q = editQuestionText.trim();
    if (!q) return;
    editingQuestion = false;
    await discussion.branch({ question: q });
  }

  const roundNums = $derived(
    Object.keys(discussion.data.rounds)
      .map(Number)
      .sort((a, b) => a - b),
  );

  // A round with models that never finished (reload/offline/timeout/error)
  // can be resumed without redoing completed work.
  const resumable = $derived(findResumableRound(discussion.data));

  function cleanUserMessage(msg: string): string {
    if (!msg) return "";
    let clean = msg;
    const markerIndex = clean.search(/\n\n--- (?:Attached File|Attachment):/);
    if (markerIndex !== -1) {
      clean = clean.slice(0, markerIndex).trim();
    }
    const directiveMatch = clean.match(
      /\[COUNCIL DELIBERATION DIRECTIVE(?: - TURN \d+)?\]\n([\s\S]*?)\n\[END COUNCIL DELIBERATION DIRECTIVE\]/,
    );
    if (directiveMatch) {
      return directiveMatch[1].trim();
    }
    return clean;
  }

  function getAttachmentsForRound(rn: number): { name: string; type: string; content?: string }[] {
    const list = discussion.attachmentsForRound(rn);
    if (list && list.length > 0) return list;
    const msg = discussion.data.userMessages[rn] ?? "";
    const regex = /\n\n--- (?:Attached File|Attachment): ([^\n]+) ---\n/g;
    const legacyAttachments: { name: string; type: string }[] = [];
    let match: RegExpExecArray | null;
    while ((match = regex.exec(msg)) !== null) {
      const name = match[1].trim();
      legacyAttachments.push({
        name,
        type: name.endsWith(".png") || name.endsWith(".jpg") || name.endsWith(".jpeg") || name.endsWith(".webp")
          ? "image/png"
          : "text/plain",
      });
    }
    return legacyAttachments;
  }

  function formatSize(bytes?: number): string {
    if (!bytes || bytes <= 0) return "";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
</script>

<div class="chat">
  <div class="chat-header">
    <div class="ch-left">
      <h2 class="title" title={discussion.data.title || discussion.data.question}>
        {discussion.data.title || discussion.data.question}
      </h2>
      {#if discussion.running}
        <ProgressStepper compact />
        <span class="round-indicator">Round {discussion.currentRound} of {discussion.data.totalRounds || 1}</span>
      {/if}
      {#if discussion.data.use_rag || discussion.data.retrieved_context}
        <div
          class="rag-status"
          class:ok={!!discussion.data.retrieved_context}
          class:fail={discussion.data.use_rag && !discussion.data.retrieved_context && !discussion.running}
          class:loading={discussion.phase === "searching"}
        >
          <span class="rag-dot"></span>
          <span class="rag-text">
            {#if discussion.phase === "searching"}
              Searching the web…
            {:else if discussion.data.retrieved_context}
              Web Search: {Math.max(1, Math.round(discussion.data.retrieved_context.length / 1000))} KB live data active
            {:else if discussion.data.use_rag}
              Web Search: No context retrieved
            {/if}
          </span>
        </div>
      {/if}
    </div>
<div class="ch-right">
      {#if discussion.running}
        <div class="stop-group">
          <button class="btn btn-ghost btn-sm" onclick={() => discussion.stop()}>
            <Icon name="stop" size="sm" /> Stop
          </button>
          <button class="btn btn-ghost btn-sm" onclick={() => discussion.stopAndSummarize()}>
            <Icon name="star" size="sm" /> Stop & Summarize
          </button>
        </div>
      {/if}
      <div class="top-toolbar">
        {#if !discussion.running}
          {#if resumable}
            <button
              class="btn btn-ghost btn-sm"
              data-testid="resume-round-btn"
              title="Re-run only the models that did not finish — completed answers are kept"
              onclick={() => discussion.resumeRound(resumable.round)}
            >
              <Icon name="refresh" size="sm" /> Resume round {resumable.round}
            </button>
          {/if}
          <button class="btn btn-ghost btn-sm" onclick={() => discussion.reset()} title="New discussion">
            <Icon name="plus" size="sm" /> New
          </button>
          <button class="btn btn-ghost btn-sm" onclick={() => userSettings.openModal()} title="Settings">
            <Icon name="settings" size="sm" />
          </button>
        {/if}
        <button class="btn btn-ghost btn-sm" onclick={() => window.print()} title="Print discussion">
          <Icon name="file" size="sm" />
        </button>
      </div>
      <ChatExport />
    </div>
</div>

  <div class="scroll-area" bind:this={scrollEl} onscroll={onScroll}>
    {#each roundNums as rn (rn)}
      <div class="turn" class:followup={rn > 1}>
        {#if rn > 1 && !(discussion.data.userMessages[rn] ?? "").includes("COUNCIL DELIBERATION DIRECTIVE")}
          <div class="followup-divider">
            <span class="followup-badge">
              <Icon name="corner-down-right" size="sm" />
              {#if discussion.data.turnAnalysisByRound?.[rn]?.needs_fresh_entities}
                Follow-up (turn {rn}) — fresh recommendations requested (exclusion ledger active)
              {:else}
                Follow-up (turn {rn}) — building on the previous consensus
              {/if}
            </span>
          </div>
        {/if}
        <div class="user-msg" data-testid="user-message-{rn}">
          {#if rn === 1 && discussion.data.branchOf}
            <a
              class="branch-chip"
              data-testid="branch-chip"
              href="#discussion/{discussion.data.branchOf}"
              onclick={(e) => {
                e.preventDefault();
                const parent = discussion.data.branchOf;
                if (parent) discussion.openDiscussion(parent);
              }}
            >
              <Icon name="git-branch" size="sm" />
              Branched from #{discussion.data.branchOf}{discussion.data.branchFromTitle
                ? `: ${discussion.data.branchFromTitle}`
                : ""}
            </a>
          {/if}
          <span class="user-label">
            {rn === 1
              ? "You"
              : (discussion.data.userMessages[rn] ?? "").includes("COUNCIL DELIBERATION DIRECTIVE") || (discussion.data.userMessages[rn] ?? "").includes("Council Deliberation")
                ? `Council Deliberation · Turn ${rn}`
                : (discussion.data.userMessages[rn] ?? "").startsWith("Continue refining the analysis")
                  ? "Auto-continue"
                  : "You · follow-up"}
          </span>
          {#if editingActive && rn === 1}
            <div class="question-edit" data-testid="question-edit">
              <textarea
                class="question-edit-input"
                rows="4"
                bind:value={editQuestionText}
                data-testid="question-edit-input"
              ></textarea>
              <div class="question-edit-actions">
                <button
                  class="btn btn-primary btn-xs"
                  data-testid="branch-create-btn"
                  disabled={!editQuestionText.trim()}
                  onclick={branchFromEditedQuestion}
                >
                  <Icon name="git-branch" size="sm" /> Create branch
                </button>
                <button class="btn btn-ghost btn-xs" data-testid="branch-cancel-btn" onclick={() => (editingQuestion = false)}>
                  Cancel
                </button>
                <span class="question-edit-hint">
                  Starts a new discussion with this question — this one stays unchanged.
                </span>
              </div>
            </div>
          {:else if cleanUserMessage(discussion.data.userMessages[rn] ?? "")}
            <p>{cleanUserMessage(discussion.data.userMessages[rn] ?? "")}</p>
            <div class="user-msg-actions">
              <button class="btn btn-ghost btn-xs copy-msg" title="Copy" onclick={(e) => {
                e.stopPropagation();
                navigator.clipboard.writeText(cleanUserMessage(discussion.data.userMessages[rn] ?? ""));
              }}>
                <Icon name="copy" size="sm" />
              </button>
              {#if rn === 1 && !discussion.running && discussion.data.userMessages[rn]}
                <button
                  class="btn btn-ghost btn-xs edit-msg"
                  title="Edit question (creates a new branch)"
                  data-testid="edit-question-btn"
                  onclick={(e) => {
                    e.stopPropagation();
                    startEditQuestion(rn);
                  }}
                >
                  <Icon name="pencil" size="sm" /> Edit
                </button>
              {/if}
              <button class="btn btn-ghost btn-xs delete-msg" title="Delete" onclick={(e) => {
                e.stopPropagation();
                if (confirm("Delete this user message?")) {
                  discussion.configure({
                    userMessages: Object.fromEntries(
                      Object.entries(discussion.data.userMessages).filter(([k]) => k !== String(rn)),
                    ) as Record<number, string>,
                  });
                }
              }}>
                <Icon name="trash" size="sm" />
              </button>
            </div>
          {/if}
          {#if getAttachmentsForRound(rn).length > 0}
            <div class="user-attachments-grid">
              {#each getAttachmentsForRound(rn) as att (att.name)}
                {#if att.type.startsWith("image/") && att.content}
                  <div class="att-image-preview">
                    <img
                      class="att-thumb"
                      src={"data:" + att.type + ";base64," + att.content}
                      alt={att.name}
                      title={att.name}
                    />
                    <span class="att-image-name" title={att.name}>{att.name}</span>
                  </div>
                {:else}
                  <div class="att-file-card" title={att.name}>
                    <div class="att-file-icon">
                      <Icon name="file" size="sm" />
                    </div>
                    <div class="att-file-info">
                      <span class="att-file-name" title={att.name}>{att.name}</span>
                      {#if att.content}
                        <span class="att-file-meta">{formatSize(att.content.length)}</span>
                      {:else}
                        <span class="att-file-meta">Attached</span>
                      {/if}
                    </div>
                  </div>
                {/if}
              {/each}
            </div>
          {/if}
        </div>

        <div class="model-row">
          {#each Object.entries(discussion.data.rounds[rn]) as [modelKey, result] (modelKey)}
            <ModelCard {modelKey} roundNum={rn} result={result} />
          {/each}
        </div>

        <ConsensusSection roundNum={rn} />
      </div>
    {/each}

    {#if roundNums.length === 0}
      {#if discussion.data.status === "in_progress" || discussion.data.status === "new"}
        <div class="pending">
          <span class="spinner"></span> Preparing models…
        </div>
      {:else if discussion.data.retrieved_context}
        <div class="empty-state">
          <p>RAG context was retrieved but no responses were generated yet.</p>
        </div>
      {:else}
        <div class="empty-state">
          <p>No responses yet. Submit a prompt to start the discussion.</p>
        </div>
      {/if}
    {/if}
  </div>

  {#if showJump}
    <button class="jump" onclick={jumpToLatest}>
      <Icon name="arrow-down" size="sm" /> Jump to latest
    </button>
  {/if}

  <div class="composer-wrap">
    <ChatInput {onEditModels} />
  </div>
</div>

<style>
  .chat {
    flex: 1;
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    min-width: 0;
    width: 100%;
    position: relative;
    overflow: hidden;
  }
  .chat-header {
    flex-shrink: 0;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-secondary);
  }
  .ch-left {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .title {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .rag-status {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--text-tertiary);
  }
  .rag-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--text-tertiary);
    flex-shrink: 0;
  }
  .rag-status.loading .rag-dot {
    background: var(--accent);
    animation: rag-pulse 1.2s ease-in-out infinite;
  }
  .rag-status.ok .rag-dot {
    background: #22c55e;
  }
  .rag-status.ok .rag-text {
    color: #16a34a;
  }
  .rag-status.fail .rag-dot {
    background: #ef4444;
  }
  .rag-status.fail .rag-text {
    color: #dc2626;
  }
  .round-indicator {
    font-size: 11px;
    font-weight: 600;
    color: var(--accent-light);
    background: color-mix(in srgb, var(--accent-light) 14%, transparent);
    border: 1px solid color-mix(in srgb, var(--accent-light) 30%, transparent);
    border-radius: 999px;
    padding: 2px 8px;
    white-space: nowrap;
    flex-shrink: 0;
  }
  @keyframes rag-pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.8); }
  }
  @media (prefers-reduced-motion: reduce) {
    .rag-status.loading .rag-dot { animation: none; }
  }
  .ch-right {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }
  .stop-group {
    display: flex;
    gap: 4px;
  }
  .scroll-area {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 16px 16px 20px;
  }
  .turn {
    margin-bottom: 18px;
  }
  .followup-divider {
    display: flex;
    align-items: center;
    margin: 4px 0 14px;
  }
  .followup-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--accent-light);
    background: color-mix(in srgb, var(--accent-light) 12%, transparent);
    border: 1px solid color-mix(in srgb, var(--accent-light) 35%, transparent);
    border-radius: 999px;
    padding: 4px 10px;
  }
  .user-msg {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 10px;
  }
  .user-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--accent);
  }
  .user-msg p {
    margin: 0;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 12px 14px;
    font-size: 14px;
    line-height: 1.5;
    color: var(--text-primary);
    white-space: pre-wrap;
    word-break: break-word;
  }
  .user-msg-actions {
    display: flex;
    gap: 6px;
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px solid var(--border);
  }
  .user-msg-actions .btn {
    padding: 4px 8px;
    font-size: 10px;
    opacity: 0.8;
  }
  .user-msg-actions .btn:hover {
    opacity: 1;
  }
  .branch-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    margin-bottom: 6px;
    padding: 3px 9px;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: color-mix(in srgb, var(--accent) 8%, transparent);
    color: var(--accent);
    font-size: 11px;
    text-decoration: none;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .branch-chip:hover {
    background: color-mix(in srgb, var(--accent) 16%, transparent);
    border-color: var(--accent);
  }
  .question-edit {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .question-edit-input {
    width: 100%;
    resize: vertical;
    font: inherit;
    min-height: 72px;
  }
  .question-edit-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .question-edit-hint {
    font-size: 11px;
    opacity: 0.65;
  }
  .user-attachments-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 6px;
  }
  .att-file-card {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: var(--bg-primary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    max-width: 320px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  }
  .att-file-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border-radius: 4px;
    background: var(--bg-tertiary);
    color: var(--accent);
    flex-shrink: 0;
  }
  .att-file-info {
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .att-file-name {
    font-size: 12.5px;
    font-weight: 500;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 220px;
  }
  .att-file-meta {
    font-size: 10.5px;
    color: var(--text-tertiary);
  }
  .att-image-preview {
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-width: 260px;
  }
  .att-thumb {
    display: block;
    max-width: 260px;
    max-height: 200px;
    border-radius: var(--radius);
    border: 1px solid var(--border);
    object-fit: cover;
  }
  .att-image-name {
    font-size: 11px;
    color: var(--text-tertiary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .model-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 12px;
    align-items: stretch;
  }
  .model-card {
    display: flex;
    flex-direction: column;
    min-height: 320px;
  }
  .top-toolbar {
    display: flex;
    gap: 6px;
    margin-bottom: 8px;
  }
  .top-toolbar .btn {
    padding: 4px 8px;
    font-size: 11px;
  }
  .empty-state {
    padding: 40px 20px;
    text-align: center;
    color: var(--text-tertiary);
    font-size: 14px;
  }
  .empty-state p {
    margin: 0;
  }
  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  .jump {
    position: absolute;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%);
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 600;
    box-shadow: var(--shadow-md);
    cursor: pointer;
    z-index: 20;
  }
  .composer-wrap {
    flex-shrink: 0;
    width: 100%;
    z-index: 10;
    position: relative;
    bottom: 0;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
