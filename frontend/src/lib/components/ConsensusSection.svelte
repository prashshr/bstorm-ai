<script lang="ts">
  import { discussion } from "../stores/discussion.svelte";
  import { safeRenderMarkdown } from "../utils/markdown";
  import { copyToClipboard } from "../utils/helpers";
  import ContributionBars from "./ContributionBars.svelte";
  import Icon from "./Icon.svelte";

  let consensus = $derived(discussion.data.consensus);
  let rendered = $derived(safeRenderMarkdown(consensus));
  let generating = $derived(discussion.phase === "synthesizing");

  let copied = $state(false);
  async function copy() {
    if (await copyToClipboard(consensus)) {
      copied = true;
      setTimeout(() => (copied = false), 1500);
    }
  }
</script>

<section class="consensus" aria-live="polite">
  <div class="c-head">
    <h2><Icon name="star" size="sm" /> Consensus Synthesis</h2>
    <div class="c-head-right">
      {#if discussion.data.consensusModel}
        <span class="c-model"
          >via {discussion.data.consensusModel.split("::")[1]}</span
        >
      {/if}
      {#if consensus}
        <button
          class="btn btn-ghost btn-sm"
          title="Copy consensus"
          onclick={copy}
        >
          <Icon name={copied ? "check" : "copy"} size="sm" />
        </button>
      {/if}
    </div>
  </div>

  {#if generating}
    <div class="generating">
      <span class="spinner"></span> Synthesizing consensus…
    </div>
  {:else if consensus}
    <div class="markdown c-body">{@html rendered}</div>
    <ContributionBars />
  {:else if discussion.data.status === "completed"}
    <div class="empty">No consensus was generated.</div>
  {/if}
</section>

<style>
  .consensus {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: var(--radius);
    padding: 14px 16px;
    margin-top: 16px;
  }
  .c-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }
  .c-head h2 {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    font-size: 15px;
  }
  .c-head-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .c-model {
    font-size: 12px;
    color: var(--text-tertiary);
  }
  .c-body {
    font-size: 14px;
    line-height: 1.7;
  }
  .generating {
    display: flex;
    align-items: center;
    gap: 10px;
    color: var(--text-secondary);
    font-size: 14px;
  }
  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  .empty {
    color: var(--text-tertiary);
    font-size: 13px;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
