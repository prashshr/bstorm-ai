<script lang="ts">
  import { providers } from "../stores/providers.svelte";
  import { models } from "../stores/models.svelte";
  import Icon from "./Icon.svelte";
  import ProviderForm from "./ProviderForm.svelte";
  import ModelSelector from "./ModelSelector.svelte";
  import { providerDisplayName } from "../utils/helpers";

  interface Props {
    open: boolean;
    onclose: () => void;
  }
  let { open, onclose }: Props = $props();

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

  async function selectProvider(key: string) {
    providers.select(key);
    try {
      await models.discover(key);
    } catch {
      /* handled in store */
    }
  }

  async function remove(key: string) {
    if (confirm(`Remove provider "${key}"? Saved credentials will be deleted.`)) {
      await providers.remove(key);
      if (editing === key) editing = null;
    }
  }

  function toggleEdit(key: string) {
    editing = editing === key ? null : key;
    adding = false;
    if (editing === key && providers.isVerified(key)) {
      selectProvider(key);
    }
  }
</script>

{#if open}
  <div class="backdrop" role="presentation" onclick={onclose}></div>
{/if}

<aside class="panel" class:open aria-hidden={!open}>
  <div class="p-head">
    <h2>Providers & Models</h2>
    <button class="btn btn-ghost icon-btn" onclick={onclose} aria-label="Close panel">
      <Icon name="close" size="sm" />
    </button>
  </div>

  <div class="p-body">
    <div class="p-head-actions">
      <button
        class="btn btn-primary btn-sm"
        onclick={() => {
          adding = !adding;
          editing = null;
        }}
      >
        <Icon name="plus" size="sm" /> Add Provider
      </button>
    </div>

    {#if adding}
      <div class="edit-pane">
        <ProviderForm ondone={() => (adding = false)} />
      </div>
    {/if}

    {#if providers.loading}
      <p class="muted">Loading…</p>
    {:else if providers.list.length === 0}
      <p class="muted">No providers yet. Click Add to create one.</p>
    {:else}
      <ul class="provider-list">
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
                <span class="pname">{providerDisplayName(p.provider)}</span>
                {#if providers.isVerified(p.provider)}
                  <span class="verified" title="Models discovered"></span>
                {/if}
              </button>
              <div class="row-actions">
                <button class="btn btn-ghost btn-sm" title="Select & discover models" onclick={() => selectProvider(p.provider)}>
                  <Icon name="refresh" size="sm" />
                </button>
                <button class="btn btn-ghost btn-sm danger" title="Remove" onclick={() => remove(p.provider)}>
                  <Icon name="trash" size="sm" />
                </button>
              </div>
            </div>
            {#if editing === p.provider}
              <div class="edit-pane">
                <details class="settings-details" open>
                  <summary>Settings</summary>
                  <ProviderForm initialProvider={p.provider} ondone={() => (editing = null)} />
                </details>
                {#if providers.isVerified(p.provider) && providers.active === p.provider}
                  <details class="settings-details" open>
                    <summary>Models</summary>
                    <ModelSelector />
                  </details>
                {/if}
              </div>
            {/if}
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</aside>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 40;
  }
  .panel {
    position: fixed;
    top: 0;
    right: 0;
    height: 100%;
    width: 320px;
    max-width: 90vw;
    background: var(--bg-secondary);
    border-left: 1px solid var(--border);
    box-shadow: var(--shadow-md);
    transform: translateX(100%);
    transition: transform var(--transition);
    z-index: 50;
    display: flex;
    flex-direction: column;
  }
  .panel.open {
    transform: translateX(0);
  }
  @media (max-width: 768px) {
    .panel {
      width: 100vw;
      max-width: 100vw;
    }
  }
  .p-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 14px 8px;
    border-bottom: 1px solid var(--border);
  }
  .p-head h2 {
    margin: 0;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-tertiary);
  }
  .p-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 10px;
  }
  .p-head-actions {
    margin-bottom: 10px;
  }
  .p-head-actions .btn {
    width: 100%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }
  .edit-pane {
    padding: 8px 8px 14px;
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
  }
  .btn.danger {
    color: var(--error);
  }
  .muted {
    color: var(--text-tertiary);
    font-size: 12px;
    padding: 10px 14px;
    list-style: none;
  }
  .settings-details {
    border-top: 1px solid var(--border);
    padding-top: 8px;
    margin-bottom: 12px;
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
</style>
