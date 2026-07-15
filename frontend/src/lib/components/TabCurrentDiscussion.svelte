<script lang="ts">
  import { discussion } from "../stores/discussion.svelte";
  import { nav } from "../stores/nav.svelte";
  import ProgressStepper from "./ProgressStepper.svelte";
  import RoundTimeline from "./RoundTimeline.svelte";
  import ConsensusSection from "./ConsensusSection.svelte";
  import Icon from "./Icon.svelte";

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
      {#if discussion.running}
        <button class="btn btn-ghost" onclick={() => discussion.stop()}>
          <Icon name="stop" size="sm" /> Stop
        </button>
      {:else if discussion.data.status === "completed" || discussion.data.status === "stopped"}
        <button class="btn btn-secondary" onclick={newDiscussion}>
          <Icon name="plus" size="sm" /> New
        </button>
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

<style>
  .empty-state {
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
    margin-bottom: 16px;
  }
  .q-wrap {
    flex: 1;
    min-width: 0;
  }
  .question {
    margin: 0 0 12px;
    font-size: 18px;
    line-height: 1.4;
    word-break: break-word;
  }
  .controls {
    flex-shrink: 0;
  }
  .scroll-area {
    position: relative;
    overflow-y: auto;
    max-height: calc(100vh - 220px);
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
