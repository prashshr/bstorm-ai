<script lang="ts">
  import { discussion } from "../stores/discussion.svelte";
  import { userSettings } from "../stores/settings.svelte";
  import { safeRenderMarkdown } from "../utils/markdown";
  import { copyToClipboard } from "../utils/helpers";
  import { parseModelThinking } from "../utils/thinking";
  import ContributionBars from "./ContributionBars.svelte";
  import Icon from "./Icon.svelte";

  interface Props {
    roundNum?: number;
    text?: string;
  }
  let { roundNum = 0, text = "" }: Props = $props();

  // Show this round's own consensus. Never fall back to the global/latest
  // consensus, otherwise a round without its own synthesis would display the
  // previous turn's consensus (e.g. an old consensus appearing below a new
  // follow-up question).
  let rawConsensus = $derived(
    text || (roundNum ? discussion.data.consensuses[roundNum] ?? "" : discussion.data.consensus),
  );
  let parsed = $derived(parseModelThinking(rawConsensus));
  let consensus = $derived(parsed.finalText || rawConsensus);
  let rendered = $derived(safeRenderMarkdown(consensus));
  let topology = $derived(
    roundNum ? discussion.data.topologyByRound?.[roundNum] : undefined,
  );
  let generating = $derived(
    discussion.phase === "synthesizing" &&
      (roundNum === 0 || roundNum === discussion.currentRound),
  );

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
      <h2><Icon name="star" size="sm" /> Consensus</h2>
      <div class="c-head-right">
        {#if topology}
          <span
            class="topology-pill"
            class:dissent={topology.has_disagreement}
            title={topology.rationale}
          >
            <span class="topo-dot"></span>
            {#if topology.has_disagreement}
              Dissent: {topology.dissenting_model ? topology.dissenting_model.split("::").pop() : "Divergence"} ({topology.primary_divergence.replace(/_/g, " ")})
            {:else}
              Consensus: {topology.consensus_percent}%
            {/if}
          </span>
        {/if}
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

    {#if topology?.has_disagreement && topology.dissenting_model}
      <div class="dissent-banner">
        <Icon name="alert-triangle" size="sm" />
        <span class="dissent-text">
          <strong>Deliberation Focus:</strong> Model <code>{topology.dissenting_model.split("::").pop()}</code> raised an alternative view on <em>{topology.primary_divergence.replace(/_/g, " ")}</em>.
        </span>
      </div>
    {/if}

    {#if generating}
     <div class="generating">
       <span class="spinner"></span> Synthesizing consensus…
     </div>
   {:else if discussion.data.consensusError}
     <div class="consensus-error">{discussion.data.consensusError}</div>
    {:else if consensus}
      {#if userSettings.data.showThinking && parsed.thinking}
        <details class="thinking-block">
          <summary class="thinking-summary">
            <Icon name="lightbulb" size="sm" /> Thinking
          </summary>
          <div class="thinking-body">{@html safeRenderMarkdown(parsed.thinking)}</div>
        </details>
      {/if}
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
    border-left: 3px solid var(--accent-light);
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
    font-size: 13px;
    font-weight: 600;
    color: var(--accent-light);
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
    font-size: 13px;
    line-height: 1.6;
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
  .consensus-error {
    color: var(--error);
    background: var(--error-bg);
    border: 1px solid color-mix(in srgb, var(--error) 40%, transparent);
    border-radius: var(--radius);
    padding: 8px 12px;
    font-size: 13px;
  }
  .thinking-block {
    margin-bottom: 12px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-tertiary);
  }
  .thinking-summary {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 10px;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-tertiary);
    cursor: pointer;
    user-select: none;
  }
  .thinking-summary:hover {
    color: var(--text-secondary);
  }
  .thinking-body {
    padding: 0 10px 10px;
    font-size: 12px;
    line-height: 1.5;
    color: var(--text-tertiary);
    max-height: 250px;
    overflow-y: auto;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  .topology-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 12px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    color: var(--text-secondary);
  }
  .topology-pill.dissent {
    border-color: #f59e0b;
    background: rgba(245, 158, 11, 0.1);
    color: #d97706;
  }
  .topo-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #10b981;
  }
  .topology-pill.dissent .topo-dot {
    background: #f59e0b;
  }
  .dissent-banner {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(245, 158, 11, 0.08);
    border: 1px solid rgba(245, 158, 11, 0.25);
    border-radius: var(--radius);
    padding: 8px 12px;
    margin-bottom: 12px;
    font-size: 0.82rem;
    color: var(--text-primary);
  }
  .dissent-banner code {
    background: rgba(0, 0, 0, 0.06);
    padding: 1px 4px;
    border-radius: 4px;
    font-size: 0.78rem;
  }
</style>
