<script lang="ts">
  import { providers } from "../stores/providers.svelte";
  import { models } from "../stores/models.svelte";
  import { nav } from "../stores/nav.svelte";
  import { auth } from "../stores/auth.svelte";
  import Icon from "./Icon.svelte";
  import ProviderForm from "./ProviderForm.svelte";
  import ModelSelector from "./ModelSelector.svelte";

  let adding = $state(false);
  let editing = $state<string | null>(null);

  let sortedProviders = $derived(
    [...providers.list].sort((a, b) => {
      const ac = a.provider.toLowerCase() === "custom";
      const bc = b.provider.toLowerCase() === "custom";
      if (ac !== bc) return ac ? 1 : -1;
      return a.provider.localeCompare(b.provider);
    }),
  );

  const MIN_W = 220;
  const MAX_W = 560;
  let width = $state<number>(
    Number(localStorage.getItem("aiEnsembleSidebarW")) || 260,
  );
  let resizing = $state(false);

  function startResize(e: PointerEvent) {
    resizing = true;
    const startX = e.clientX;
    const startW = width;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    const onMove = (ev: PointerEvent) => {
      const next = Math.min(MAX_W, Math.max(MIN_W, startW + ev.clientX - startX));
      width = next;
    };
    const onUp = () => {
      resizing = false;
      localStorage.setItem("aiEnsembleSidebarW", String(width));
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  }

  async function selectProvider(key: string) {
    providers.select(key);
    try {
      await models.discover(key);
    } catch {
      /* handled in store */
    }
  }

  async function discover(key: string) {
    await selectProvider(key);
  }

  async function remove(key: string) {
    if (
      confirm(`Remove provider "${key}"? Saved credentials will be deleted.`)
    ) {
      await providers.remove(key);
      if (editing === key) editing = null;
    }
  }

  async function toggleEdit(key: string) {
    editing = editing === key ? null : key;
    adding = false;
    if (editing === key && providers.isVerified(key)) {
      await selectProvider(key);
    }
  }
</script>

<aside
  class="sidebar"
  class:collapsed={nav.sidebarCollapsed}
  class:resizing
  style={nav.sidebarCollapsed ? "" : `width:${width}px`}
>
  {#if nav.sidebarCollapsed}
    <button
      class="btn btn-ghost expand-btn"
      onclick={() => nav.toggleSidebar()}
      aria-label="Expand sidebar"
    >
      <Icon name="chevron-right" />
    </button>
  {:else}
    <div class="sidebar-body">
    <div class="sidebar-head">
      <h2>Providers</h2>
      <button
        class="btn btn-primary btn-sm"
        data-testid="add-provider-btn"
        onclick={() => {
          adding = !adding;
          editing = null;
        }}
        aria-label="Add provider"
      >
        <Icon name="plus" size="sm" /> Add
      </button>
    </div>

    {#if adding}
      <div class="edit-pane">
        <ProviderForm ondone={() => (adding = false)} />
      </div>
    {/if}

    <ul class="provider-list" data-testid="provider-list">
      {#if providers.loading}
        <li class="empty">Loading…</li>
      {:else if providers.list.length === 0}
        <li class="empty">No providers yet. Click Add to create one.</li>
      {:else}
        {#each sortedProviders as p (p.provider)}
          <li class="provider-row" class:active={providers.active === p.provider}>
            <div class="row-main">
              <button
                class="provider-item"
                class:active={providers.active === p.provider}
                class:open={editing === p.provider}
                aria-expanded={editing === p.provider}
                onclick={() => toggleEdit(p.provider)}
              >
                <Icon
                  name={editing === p.provider ? "chevron-down" : "chevron-right"}
                  size="sm"
                />
                <span class="pname">{p.provider}</span>
                {#if providers.isVerified(p.provider)}
                  <span class="verified" title="Models discovered"></span>
                {/if}
              </button>
              <div class="row-actions">
                <button
                  class="btn btn-ghost btn-sm"
                  title="Select & discover models"
                  onclick={() => discover(p.provider)}
                >
                  <Icon name="refresh" size="sm" />
                </button>
                <button
                  class="btn btn-ghost btn-sm danger"
                  title="Remove"
                  onclick={() => remove(p.provider)}
                >
                  <Icon name="trash" size="sm" />
                </button>
              </div>
            </div>
            {#if editing === p.provider}
              <div class="edit-pane">
                {#if providers.isVerified(p.provider) && providers.active === p.provider}
                  <ModelSelector />
                {/if}
                <details class="settings-details">
                  <summary>Settings</summary>
                  <ProviderForm
                    initialProvider={p.provider}
                    ondone={() => (editing = null)}
                  />
                </details>
              </div>
            {/if}
          </li>
        {/each}
      {/if}
    </ul>

    <div
      class="resizer"
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize sidebar"
      title="Drag to resize"
      onpointerdown={startResize}
    ></div>
    </div>
  {/if}

  <div class="sidebar-footer">
    <span class="user" title={auth.user ?? ""}>{auth.user ?? "user"}</span>
    <button class="btn btn-ghost btn-sm" onclick={() => auth.logout()}>
      <Icon name="logout" size="sm" /> Logout
    </button>
  </div>
</aside>

<style>
  .sidebar {
    position: relative;
    width: var(--sidebar-width);
    flex-shrink: 0;
    border-right: 1px solid var(--border);
    background: var(--bg-secondary);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transition: width var(--transition);
  }
  .sidebar-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
  }
  .sidebar-footer {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 10px 14px;
    border-top: 1px solid var(--border);
    background: var(--bg-secondary);
  }
  .sidebar-footer .user {
    font-size: 13px;
    color: var(--text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .sidebar.resizing {
    transition: none;
    user-select: none;
    cursor: col-resize;
  }
  .resizer {
    position: absolute;
    top: 0;
    right: 0;
    width: 1.5px;
    height: 100%;
    cursor: col-resize;
    z-index: 5;
  }
  .resizer:hover,
  .sidebar.resizing .resizer {
    background: var(--accent);
    opacity: 0.5;
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
  .edit-pane {
    padding: 8px 14px 14px;
    border-bottom: 1px solid var(--border);
  }
  .provider-list {
    list-style: none;
    margin: 0;
    padding: 6px;
  }
  .provider-row {
    border-radius: var(--radius);
  }
  .provider-row.active {
    background: var(--bg-tertiary);
  }
  .row-main {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .provider-item {
    flex: 1;
    min-width: 0;
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
    color: var(--accent);
  }
  .pname {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    text-transform: capitalize;
  }
  .verified {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--success);
  }
  .row-actions {
    display: flex;
    gap: 2px;
    flex-shrink: 0;
    padding-right: 4px;
  }
  .btn.danger {
    color: var(--error);
  }
  .empty {
    color: var(--text-tertiary);
    font-size: 12px;
    padding: 10px 14px;
    list-style: none;
  }
  .settings-details {
    margin-top: 12px;
    border-top: 1px solid var(--border);
    padding-top: 8px;
  }
  .settings-details summary {
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 4px 0;
  }
  @media (max-width: 768px) {
    .sidebar {
      width: 100% !important;
      max-height: 50vh;
      border-right: none;
      border-bottom: 1px solid var(--border);
    }
    .resizer {
      display: none;
    }
  }
</style>
