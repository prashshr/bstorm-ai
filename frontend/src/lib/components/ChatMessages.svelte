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
      <div class="turn">
        <div class="user-msg" data-testid="user-message-{rn}">
          <span class="user-label">You</span>
          <p>{discussion.data.userMessages[rn] ?? ""}</p>
        </div>

        <div class="model-row">
          {#each Object.entries(discussion.data.rounds[rn]) as [modelKey, result] (modelKey)}
            <ModelCard {modelKey} roundNum={rn} result={result} />
          {/each}
        </div>

        {#if rn === roundNums[roundNums.length - 1]}
          <ConsensusSection />
        {/if}
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

  <ChatInput />
</div>

<style>
  .chat {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
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
