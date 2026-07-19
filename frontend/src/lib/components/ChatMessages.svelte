<script lang="ts">
  import { discussion } from "../stores/discussion.svelte";
  import { copyToClipboard } from "../utils/helpers";
  import Icon from "./Icon.svelte";
  import ModelCard from "./ModelCard.svelte";
  import ConsensusSection from "./ConsensusSection.svelte";
  import ChatInput from "./ChatInput.svelte";
  import ChatExport from "./ChatExport.svelte";
  import ProgressStepper from "./ProgressStepper.svelte";

  let scrollEl = $state<HTMLElement | null>(null);
  let atBottom = $state(true);
  let showJump = $derived(!atBottom && discussion.running);

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
    if (atBottom && scrollEl) {
      scrollEl.scrollTo({ top: scrollEl.scrollHeight, behavior: "smooth" });
    }
  });

  function jumpToLatest() {
    scrollEl?.scrollTo({ top: scrollEl.scrollHeight, behavior: "smooth" });
  }

  const roundNums = $derived(
    Object.keys(discussion.data.rounds)
      .map(Number)
      .sort((a, b) => a - b),
  );
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
              RAG: {Math.round(discussion.data.retrieved_context.length / 1000)} KB context retrieved
            {:else if discussion.data.use_rag}
              RAG: No context retrieved (search failed)
            {/if}
          </span>
        </div>
      {/if}
    </div>
    <div class="ch-right">
      {#if discussion.running}
        <button class="btn btn-ghost btn-sm" onclick={() => discussion.stop()}>
          <Icon name="stop" size="sm" /> Stop
        </button>
      {/if}
      <ChatExport />
    </div>
  </div>

   <div class="scroll-area" bind:this={scrollEl} onscroll={onScroll}>
    {#each roundNums as rn (rn)}
      <div class="turn" class:followup={rn > 1}>
        {#if rn > 1}
          <div class="followup-divider">
            <span class="followup-badge">
              <Icon name="corner-down-right" size="sm" /> Follow-up (turn {rn}) — building on the previous consensus
            </span>
          </div>
        {/if}
        <div class="user-msg" data-testid="user-message-{rn}">
          <span class="user-label">{rn === 1 ? "You" : (discussion.data.userMessages[rn] ?? "").startsWith("Continue refining the analysis") ? "Auto-continue" : "You · follow-up"}</span>
          <p>{discussion.data.userMessages[rn] ?? ""}</p>
          {#each discussion.attachmentsForRound(rn) as att (att.name)}
            {#if att.type.startsWith("image/")}
              <img
                class="att-thumb"
                src={"data:" + att.type + ";base64," + att.content}
                alt={att.name}
                title={att.name}
              />
            {:else}
              <span class="att-chip">
                <Icon name="file" size="sm" /> {att.name}
              </span>
            {/if}
          {/each}
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
      <div class="pending">
        <span class="spinner"></span> Preparing models…
      </div>
    {/if}
  </div>

  {#if showJump}
    <button class="jump" onclick={jumpToLatest}>
      <Icon name="arrow-down" size="sm" /> Jump to latest
    </button>
  {/if}

  <ChatInput {onEditModels} />
</div>

<style>
  .chat {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    min-width: 0;
    width: 100%;
    position: relative;
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
  .scroll-area {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 16px;
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
  .att-thumb {
    display: block;
    max-width: 280px;
    max-height: 280px;
    margin-top: 8px;
    border-radius: var(--radius);
    border: 1px solid var(--border);
  }
  .att-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 8px;
    padding: 4px 10px;
    font-size: 12px;
    color: var(--text-secondary);
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 999px;
  }
  .model-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 12px;
  }
  .pending {
    display: flex;
    align-items: center;
    gap: 10px;
    color: var(--text-secondary);
    font-size: 14px;
    padding: 20px;
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
    bottom: 110px;
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
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
