<script lang="ts">
  import type { ModelResult } from "../api/types";
  import { discussion } from "../stores/discussion.svelte";
  import { safeRenderMarkdown } from "../utils/markdown";
  import { splitModelKey, copyToClipboard } from "../utils/helpers";
  import Icon from "./Icon.svelte";

  interface Props {
    modelKey: string;
    roundNum: number;
    result: ModelResult;
  }
  let { modelKey, roundNum, result }: Props = $props();

  let { model } = $derived(splitModelKey(modelKey));
  let rendered = $derived(safeRenderMarkdown(result.text));

  const statusLabel: Record<string, string> = {
    waiting: "Queued",
    connecting: "Connecting",
    streaming: "Streaming",
    complete: "Complete",
    error: "Error",
    timeout: "Timed out",
    skipped: "Skipped",
  };

  let copied = $state(false);
  async function copy() {
    if (await copyToClipboard(result.text)) {
      copied = true;
      setTimeout(() => (copied = false), 1500);
    }
  }
</script>

<article
  class="model-card {result.status}"
  id="card-{roundNum}-{modelKey}"
  aria-live={result.status === "streaming" ? "polite" : "off"}
>
  <header class="card-head">
    <span class="model-name" title={model}>
      <Icon name="bot" size="sm" />
      {model}
    </span>
    <div class="head-right">
      <span class="status status-{result.status}">
        {statusLabel[result.status] ?? result.status}
      </span>
      {#if (result.status === "complete" || result.status === "streaming") && result.text}
        <button
          class="btn btn-ghost btn-sm copy-btn"
          title="Copy response"
          onclick={copy}
        >
          <Icon name={copied ? "check" : "copy"} size="sm" />
        </button>
      {/if}
    </div>
  </header>

  {#if result.status === "connecting" || result.status === "waiting"}
    <div class="skeleton">
      <span></span><span></span><span></span>
    </div>
  {:else if result.status === "error" || result.status === "timeout"}
    <div class="err-body">
      <Icon name="alert" size="sm" />
      <span>{result.error ?? "Request failed"}</span>
    </div>
    <div class="card-actions">
      <button
        class="btn btn-secondary btn-sm"
        onclick={() => discussion.retryModel(modelKey, roundNum)}
      >
        <Icon name="refresh" size="sm" /> Retry
      </button>
      <button
        class="btn btn-ghost btn-sm"
        onclick={() => discussion.skipModel(modelKey, roundNum)}
      >
        <Icon name="skip" size="sm" /> Skip
      </button>
    </div>
  {:else if result.status === "skipped"}
    <div class="skipped-body">Skipped by user</div>
  {:else}
    <div class="markdown card-body">{@html rendered}</div>
    {#if result.stats && result.status === "complete"}
      <footer class="card-stats">
        {#if result.stats.outputTokens}
          <span><Icon name="zap" size="sm" />{result.stats.outputTokens} tok</span>
        {/if}
        {#if result.stats.durationMs}
          <span
            ><Icon name="clock" size="sm" />{(
              result.stats.durationMs / 1000
            ).toFixed(1)}s</span
          >
        {/if}
      </footer>
    {/if}
  {/if}
</article>

<style>
  .model-card {
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    background: var(--bg-secondary);
    padding: 14px;
    transition:
      border-color var(--transition),
      box-shadow var(--transition);
  }
  .model-card.streaming {
    border-color: var(--accent);
    box-shadow: 0 0 0 1px var(--accent);
  }
  .model-card.complete {
    border-color: var(--success);
  }
  .model-card.error,
  .model-card.timeout {
    border-color: var(--error);
  }
  .card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }
  .model-name {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
    font-size: 13px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .head-right {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }
  .copy-btn {
    padding: 6px 8px;
    min-height: 32px;
    min-width: 32px;
  }
  @media (hover: none) {
    .copy-btn {
      opacity: 0.9;
    }
  }
  .status {
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 999px;
  }
  .status-streaming {
    background: var(--warning-bg);
    color: var(--warning);
  }
  .status-complete {
    background: var(--success-bg);
    color: var(--success);
  }
  .status-error,
  .status-timeout {
    background: var(--error-bg);
    color: var(--error);
  }
  .status-connecting,
  .status-waiting {
    background: var(--bg-tertiary);
    color: var(--text-tertiary);
  }
  .card-body {
    font-size: 13px;
    line-height: 1.6;
    word-wrap: break-word;
  }
  .err-body {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--error);
    font-size: 13px;
  }
  .skipped-body {
    color: var(--text-tertiary);
    font-size: 13px;
    font-style: italic;
  }
  .card-actions {
    display: flex;
    gap: 8px;
    margin-top: 10px;
  }
  .card-stats {
    display: flex;
    gap: 14px;
    margin-top: 10px;
    padding-top: 8px;
    border-top: 1px solid var(--border);
    color: var(--text-tertiary);
    font-size: 11px;
  }
  .card-stats span {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
  .skeleton {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .skeleton span {
    height: 10px;
    border-radius: 4px;
    background: linear-gradient(
      90deg,
      var(--bg-tertiary) 25%,
      var(--border) 50%,
      var(--bg-tertiary) 75%
    );
    background-size: 400px 100%;
    animation: shimmer 1.4s infinite;
  }
  .skeleton span:nth-child(2) {
    width: 80%;
  }
  .skeleton span:nth-child(3) {
    width: 60%;
  }
</style>
