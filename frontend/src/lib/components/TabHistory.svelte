<script lang="ts">
  import { history } from "../stores/history.svelte";
  import HistoryList from "./HistoryList.svelte";
  import Icon from "./Icon.svelte";

  let justLoaded = $state(false);
  $effect(() => {
    if (!justLoaded) {
      history.load();
      justLoaded = true;
    }
  });
</script>

<div class="history-tab">
  <div class="controls">
    <div class="search">
      <Icon name="search" size="sm" />
      <input
        type="search"
        placeholder="Search discussions…"
        value={history.search}
        oninput={(e) => history.setSearch((e.target as HTMLInputElement).value)}
      />
    </div>
    <div class="selects">
      <select
        value={history.filter}
        onchange={(e) =>
          history.setFilter(
            (e.target as HTMLSelectElement).value as typeof history.filter,
          )}
      >
        <option value="all">All</option>
        <option value="completed">Completed</option>
        <option value="running">Running</option>
      </select>
      <select
        value={history.sort}
        onchange={(e) =>
          history.setSort(
            (e.target as HTMLSelectElement).value as typeof history.sort,
          )}
      >
        <option value="newest">Newest</option>
        <option value="oldest">Oldest</option>
        <option value="az">A–Z</option>
      </select>
    </div>
  </div>

  {#if history.loading}
    <div class="hint">Loading…</div>
  {:else if history.error}
    <div class="hint error-hint">
      Failed to load history: {history.error}
    </div>
  {:else if history.visible.length === 0}
    <div class="hint">No discussions found.</div>
  {:else}
    <HistoryList />
  {/if}
</div>

<style>
  .history-tab {
    max-width: 900px;
    margin: 0 auto;
  }
  .controls {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }
  .search {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 12px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-tertiary);
  }
  .search input {
    flex: 1;
    border: none;
    background: none;
    padding: 10px 0;
    color: var(--text-primary);
  }
  .selects {
    display: flex;
    gap: 8px;
  }
  .hint {
    color: var(--text-tertiary);
    text-align: center;
    padding: 40px;
  }
  .error-hint {
    color: var(--error);
  }
</style>
