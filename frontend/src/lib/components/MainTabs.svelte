<script lang="ts">
  import { nav, type Tab } from "../stores/nav.svelte";
  import { discussion } from "../stores/discussion.svelte";

  const tabs: { key: Tab; label: string; alwaysShow: boolean }[] = [
    { key: "provider", label: "Provider", alwaysShow: true },
    { key: "new", label: "New Discussion", alwaysShow: true },
    { key: "current", label: "Current Discussion", alwaysShow: false },
    { key: "history", label: "History", alwaysShow: true },
  ];

  let showCurrent = $derived(
    discussion.data.status !== "new" || discussion.running,
  );
</script>

<nav class="main-tabs" aria-label="Workspace sections">
  {#each tabs as tab (tab.key)}
    {#if tab.alwaysShow || showCurrent}
      <button
        class="main-tab"
        class:active={nav.tab === tab.key}
        aria-current={nav.tab === tab.key ? "page" : undefined}
        onclick={() => nav.go(tab.key)}
      >
        {tab.label}
        {#if tab.key === "current" && discussion.running}
          <span class="live-dot" aria-label="live"></span>
        {/if}
      </button>
    {/if}
  {/each}
</nav>

<style>
  .main-tabs {
    display: flex;
    gap: 2px;
    padding: 8px 16px 0;
    border-bottom: 1px solid var(--border);
    background: var(--bg-secondary);
    overflow-x: auto;
  }
  .main-tab {
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--text-secondary);
    padding: 10px 14px;
    font-size: 14px;
    font-weight: 600;
    white-space: nowrap;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .main-tab:hover {
    color: var(--text-primary);
  }
  .main-tab.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }
  .live-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--accent);
    animation: pulse 1.2s infinite;
  }
</style>
