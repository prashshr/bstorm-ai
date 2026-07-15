<script lang="ts">
  import { debug } from "../stores/debug.svelte";
  import { downloadFile } from "../utils/helpers";
  import Icon from "./Icon.svelte";

  function exportLogs() {
    const text = debug.logs
      .map(
        (l) =>
          `${new Date(l.ts).toISOString()} [${l.level.toUpperCase()}] ${l.message}`,
      )
      .join("\n");
    downloadFile("ai-ensemble-debug.log", text, "text/plain");
  }

  function fmt(ts: number): string {
    return new Date(ts).toLocaleTimeString();
  }
</script>

{#if debug.open}
  <div class="debug-panel" role="region" aria-label="Debug console">
    <div class="dp-head">
      <span class="dp-title"><Icon name="bug" size="sm" /> Debug console</span>
      <div class="dp-controls">
        <select
          value={debug.filter}
          onchange={(e) =>
            debug.setFilter(
              (e.target as HTMLSelectElement).value as typeof debug.filter,
            )}
        >
          <option value="all">All</option>
          <option value="info">Info</option>
          <option value="warn">Warn</option>
          <option value="error">Error</option>
        </select>
        <button class="btn btn-ghost btn-sm" onclick={exportLogs}>
          <Icon name="download" size="sm" /> Export
        </button>
        <button class="btn btn-ghost btn-sm" onclick={() => debug.clear()}>
          Clear
        </button>
        <button
          class="btn btn-ghost btn-sm"
          onclick={() => debug.toggle()}
          aria-label="Close debug console"
        >
          <Icon name="close" size="sm" />
        </button>
      </div>
    </div>
    <div class="dp-body">
      {#each debug.filtered as entry (entry.ts + entry.message)}
        <div class="log log-{entry.level}">
          <span class="log-ts">{fmt(entry.ts)}</span>
          <span class="log-lvl">{entry.level}</span>
          <span class="log-msg">{entry.message}</span>
        </div>
      {:else}
        <div class="empty">No log entries.</div>
      {/each}
    </div>
  </div>
{/if}

<style>
  .debug-panel {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 260px;
    background: var(--bg-secondary);
    border-top: 2px solid var(--border);
    display: flex;
    flex-direction: column;
    z-index: 50;
    box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.4);
  }
  .dp-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 14px;
    border-bottom: 1px solid var(--border);
  }
  .dp-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 600;
  }
  .dp-controls {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .dp-body {
    flex: 1;
    overflow-y: auto;
    padding: 8px 14px;
    font-family: var(--font-mono, monospace);
    font-size: 12px;
  }
  .log {
    display: flex;
    gap: 10px;
    padding: 2px 0;
    border-bottom: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.04));
  }
  .log-ts {
    color: var(--text-tertiary);
    flex-shrink: 0;
  }
  .log-lvl {
    text-transform: uppercase;
    font-weight: 600;
    width: 44px;
    flex-shrink: 0;
  }
  .log-warn .log-lvl {
    color: var(--warning);
  }
  .log-error .log-lvl {
    color: var(--error);
  }
  .log-info .log-lvl {
    color: var(--text-secondary);
  }
  .log-msg {
    word-break: break-word;
  }
  .empty {
    color: var(--text-tertiary);
    text-align: center;
    padding: 20px;
  }
</style>
