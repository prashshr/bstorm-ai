<script lang="ts">
  import { providers } from "../stores/providers.svelte";
  import { models } from "../stores/models.svelte";
  import { nav } from "../stores/nav.svelte";
  import Icon from "./Icon.svelte";
  import ProviderForm from "./ProviderForm.svelte";

  let adding = $state(false);

  async function selectProvider(key: string) {
    providers.select(key);
    try {
      await models.discover(key);
    } catch {
      /* handled in store */
    }
  }
</script>

<aside class="sidebar" class:collapsed={nav.sidebarCollapsed}>
  {#if nav.sidebarCollapsed}
    <button
      class="btn btn-ghost expand-btn"
      onclick={() => nav.toggleSidebar()}
      aria-label="Expand sidebar"
    >
      <Icon name="chevron-right" />
    </button>
  {:else}
    <div class="sidebar-head">
      <h2>Providers</h2>
      <button
        class="btn btn-ghost btn-sm"
        onclick={() => (adding = !adding)}
        aria-label="Add provider"
      >
        <Icon name="plus" size="sm" />
      </button>
    </div>

    {#if adding}
      <div class="add-form">
        <ProviderForm ondone={() => (adding = false)} />
      </div>
    {/if}

    <ul class="provider-list" data-testid="provider-list">
      {#if providers.loading}
        <li class="empty">Loading…</li>
      {:else if providers.list.length === 0}
        <li class="empty">No providers yet. Click + to add one.</li>
      {:else}
        {#each providers.list as p (p.provider)}
          <li>
            <button
              class="provider-item"
              class:active={providers.active === p.provider}
              onclick={() => selectProvider(p.provider)}
            >
              <Icon name="plug" size="sm" />
              <span class="pname">{p.provider}</span>
              {#if providers.isVerified(p.provider)}
                <span class="verified" title="Models discovered"></span>
              {/if}
            </button>
          </li>
        {/each}
      {/if}
    </ul>

    {#if providers.active && models.available.length > 0}
      <div class="model-count">
        {models.selected.length}/{models.available.length} models selected
      </div>
    {/if}
  {/if}
</aside>

<style>
  .sidebar {
    width: var(--sidebar-width);
    flex-shrink: 0;
    border-right: 1px solid var(--border);
    background: var(--bg-secondary);
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    transition: width var(--transition);
  }
  .sidebar.collapsed {
    width: var(--sidebar-collapsed);
    align-items: center;
  }
  .expand-btn {
    margin-top: 10px;
    padding: 8px;
  }
  .sidebar-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 14px 8px;
  }
  .sidebar-head h2 {
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-tertiary);
    margin: 0;
  }
  .add-form {
    padding: 8px 14px 14px;
    border-bottom: 1px solid var(--border);
  }
  .provider-list {
    list-style: none;
    margin: 0;
    padding: 6px;
    flex: 1;
  }
  .provider-item {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 9px 10px;
    border: none;
    background: none;
    color: var(--text-primary);
    border-radius: var(--radius);
    text-align: left;
    font-size: 13px;
  }
  .provider-item:hover {
    background: var(--bg-tertiary);
  }
  .provider-item.active {
    background: var(--bg-tertiary);
    color: var(--accent);
  }
  .pname {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .verified {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--success);
  }
  .empty {
    color: var(--text-tertiary);
    font-size: 12px;
    padding: 10px 14px;
    list-style: none;
  }
  .model-count {
    padding: 10px 14px;
    font-size: 12px;
    color: var(--text-tertiary);
    border-top: 1px solid var(--border);
  }
  @media (max-width: 768px) {
    .sidebar {
      width: 100%;
      max-height: 40vh;
      border-right: none;
      border-bottom: 1px solid var(--border);
    }
  }
</style>
