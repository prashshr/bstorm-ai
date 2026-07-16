<script lang="ts">
  import { discussion } from "../stores/discussion.svelte";
  import { nav } from "../stores/nav.svelte";
  import ProgressStepper from "./ProgressStepper.svelte";
  import RoundTimeline from "./RoundTimeline.svelte";
  import ConsensusSection from "./ConsensusSection.svelte";
  import Icon from "./Icon.svelte";
  import { copyToClipboard } from "../utils/helpers";

  let copiedAll = $state(false);
  async function copyAll() {
    if (await copyToClipboard(discussion.buildTranscript())) {
      copiedAll = true;
      setTimeout(() => (copiedAll = false), 1500);
    }
  }

  let scrollEl = $state<HTMLElement | null>(null);
  let atBottom = $state(true);
  let showJump = $derived(!atBottom && discussion.running);

  function onScroll() {
    if (!scrollEl) return;
    const gap =
      scrollEl.scrollHeight - scrollEl.scrollTop - scrollEl.clientHeight;
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

  function newDiscussion() {
    discussion.reset();
    nav.go("new");
  }
</script>

<div class="cd">
{#if discussion.data.id == null && !discussion.running && discussion.data.question === ""}
  <div class="empty-state">
    <Icon name="bot" size="md" />
    <p>No active discussion yet.</p>
    <button class="btn btn-primary" onclick={() => nav.go("new")}>
      Start a new discussion
    </button>
  </div>
{:else}
  <div class="cd-header">
    <div class="q-wrap">
      <h2 class="question">{discussion.data.question}</h2>
      <ProgressStepper />
    </div>
    <div class="controls">
      <button
        class="btn btn-ghost"
        title="Copy entire discussion"
        onclick={copyAll}
      >
        <Icon name={copiedAll ? "check" : "copy"} size="sm" />
        {copiedAll ? "Copied" : "Copy all"}
      </button>
      {#if discussion.running}
        <button class="btn btn-ghost" onclick={() => discussion.stop()}>
          <Icon name="stop" size="sm" /> Stop
        </button>
      {:else}
        <div class="header-actions">
          <button
            class="btn btn-ghost"
            title="Close discussion"
            onclick={() => {
              discussion.reset();
              nav.go("new");
            }}
          >
            <Icon name="close" size="sm" /> Close
          </button>
          <button class="btn btn-secondary" onclick={newDiscussion}>
            <Icon name="plus" size="sm" /> New
          </button>
        </div>
      {/if}
    </div>
  </div>

  <div class="scroll-area" bind:this={scrollEl} onscroll={onScroll}>
    <RoundTimeline />
    <ConsensusSection />
  </div>

  {#if showJump}
    <button class="jump" onclick={jumpToLatest}>
      <Icon name="arrow-down" size="sm" /> Jump to latest
    </button>
  {/if}
{/if}
</div>

<style>
  .cd {
    height: 100%;
    display: flex;
    flex-direction: column;
    min-height: 0;
    padding: 20px;
  }
  .empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 14px;
    padding: 80px 20px;
    color: var(--text-tertiary);
  }
  .empty-state p {
    margin: 0;
    font-size: 15px;
  }
  .cd-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    padding-bottom: 12px;
    margin-bottom: 12px;
    border-bottom: 1px solid var(--border);
  }
  .q-wrap {
    flex: 1;
    min-width: 0;
  }
  .question {
    margin: 0 0 8px;
    font-size: 14px;
    font-weight: 600;
    line-height: 1.4;
    color: var(--text-primary);
    word-break: break-word;
  }
  .controls {
    flex-shrink: 0;
    display: flex;
    gap: 8px;
  }
  .header-actions {
    display: flex;
    gap: 8px;
  }
  .scroll-area {
    position: relative;
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding-right: 8px;
  }
  .jump {
    position: fixed;
    bottom: 24px;
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
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    cursor: pointer;
    z-index: 20;
  }
  @media (max-width: 640px) {
    .cd-header {
      flex-direction: column;
    }
  }
</style>
