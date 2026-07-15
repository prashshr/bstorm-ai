<script lang="ts">
  import { providers } from "../stores/providers.svelte";
  import { models } from "../stores/models.svelte";
  import ProviderForm from "./ProviderForm.svelte";
  import Icon from "./Icon.svelte";

  let editing = $state<string | null>(null);
  let addingNew = $state(false);

  async function discover(provider: string) {
    providers.select(provider);
    try {
      await models.discover(provider);
    } catch {
      // errors surfaced via debug store
    }
  }

  async function remove(provider: string) {
    if (confirm(`Remove provider "${provider}"? Saved credentials will be deleted.`)) {
      await providers.remove(provider);
    }
  }
</script>

<div class="provider-config">
  <div class="pc-head">
    <h2>Provider Configuration</h2>
    <button
      class="btn btn-primary btn-sm"
      data-testid="add-provider-btn"
      onclick={() => {
        addingNew = !addingNew;
        editing = null;
      }}
    >
      <Icon name="plus" size="sm" /> Add provider
    </button>
  </div>

  {#if addingNew}
    <div class="card add-card">
      <ProviderForm ondone={() => (addingNew = false)} />
    </div>
  {/if}

  {#if providers.list.length === 0 && !addingNew}
    <div class="hint">
      No providers configured yet. Add one to start running discussions.
    </div>
  {/if}

  <div class="list" data-testid="provider-list">
    {#each providers.list as p (p.provider)}
      <article class="card" class:active={providers.active === p.provider}>
        <div class="row">
          <div class="info">
            <span class="name">
              <Icon name="plug" size="sm" />
              {p.provider}
              {#if providers.isVerified(p.provider)}
                <span class="badge badge-ok">verified</span>
              {/if}
            </span>
            <span class="endpoint">{p.endpoint || "default endpoint"}</span>
            <span class="key-state">
              {p.has_key ? "API key stored" : "no key"}
            </span>
          </div>
          <div class="actions">
            <button
              class="btn btn-secondary btn-sm"
              onclick={() => discover(p.provider)}
            >
              <Icon name="refresh" size="sm" /> Discover
            </button>
            <button
              class="btn btn-ghost btn-sm"
              onclick={() =>
                (editing = editing === p.provider ? null : p.provider)}
            >
              <Icon name="settings" size="sm" /> Edit
            </button>
            <button
              class="btn btn-ghost btn-sm danger"
              onclick={() => remove(p.provider)}
            >
              <Icon name="trash" size="sm" />
            </button>
          </div>
        </div>
        {#if editing === p.provider}
          <div class="edit-form">
            <ProviderForm
              initialProvider={p.provider}
              ondone={() => (editing = null)}
            />
          </div>
        {/if}
      </article>
    {/each}
  </div>
</div>

<style>
  .provider-config {
    max-width: 800px;
    margin: 0 auto;
  }
  .pc-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }
  .pc-head h2 {
    margin: 0;
    font-size: 18px;
  }
  .hint {
    color: var(--text-tertiary);
    padding: 24px;
    text-align: center;
    background: var(--bg-secondary);
    border-radius: var(--radius);
  }
  .list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 10px;
  }
  .card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px;
  }
  .card.active {
    border-color: var(--accent);
  }
  .add-card {
    margin-bottom: 10px;
  }
  .row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }
  .info {
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }
  .name {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    font-size: 14px;
    text-transform: capitalize;
  }
  .endpoint {
    font-size: 12px;
    color: var(--text-tertiary);
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .key-state {
    font-size: 11px;
    color: var(--text-tertiary);
  }
  .actions {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
  }
  .btn.danger {
    color: var(--error);
  }
  .edit-form {
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid var(--border);
  }
  @media (max-width: 640px) {
    .row {
      flex-direction: column;
    }
  }
</style>
