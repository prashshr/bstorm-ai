<script lang="ts">
  import { discussion } from "../stores/discussion.svelte";
  import { safeRenderMarkdown } from "../utils/markdown";
  import ContributionBars from "./ContributionBars.svelte";
  import Icon from "./Icon.svelte";

  let consensus = $derived(discussion.data.consensus);
  let rendered = $derived(safeRenderMarkdown(consensus));
  let generating = $derived(discussion.phase === "synthesizing");
</script>

<section class="consensus" aria-live="polite">
  <div class="c-head">
    <h2><Icon name="star" size="sm" /> Consensus Synthesis</h2>
    {#if discussion.data.consensusModel}
      <span class="c-model"
        >via {discussion.data.consensusModel.split("::")[1]}</span
      >
    {/if}
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
    border: 1px solid var(--accent);
    border-radius: var(--radius-lg);
    padding: 18px;
    margin-top: 20px;
  }
  .c-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }
  .c-head h2 {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    font-size: 16px;
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
