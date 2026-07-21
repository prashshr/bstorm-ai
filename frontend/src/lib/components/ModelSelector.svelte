<script lang="ts">
  import { models } from "../stores/models.svelte";
  import { providers } from "../stores/providers.svelte";
  import { providerDisplayName, modelSupportsVision } from "../utils/helpers";
  import Icon from "./Icon.svelte";

  let { collapsible = false } = $props<{ collapsible?: boolean }>();
  let collapsed = $state(false);

  let compositeKeys = $derived(
    models.available.map((m) => `${providers.active}::${m}`),
  );

  let allSelected = $derived(
    models.available.length > 0 &&
      compositeKeys.every((k) => models.isSelected(k)),
  );

  async function retestAll() {
    await models.checkAllHealth(compositeKeys);
  }

  function selectAll() {
    for (const key of compositeKeys) if (!models.isSelected(key)) models.toggle(key);
  }
  function clearAll() {
    for (const key of compositeKeys) if (models.isSelected(key)) models.toggle(key);
  }
</script>

<div class="model-selector">
  <div class="head">
    {#if collapsible}
      <button
        class="collapse-toggle"
        onclick={() => (collapsed = !collapsed)}
        aria-expanded={!collapsed}
      >
        <Icon name={collapsed ? "chevron-right" : "chevron-down"} size="sm" />
        <h3>Models {providers.active ? `· ${providers.active}` : ""}</h3>
        {#if models.available.length > 0}
          <span class="count-pill"
            >{models.selected.length}/{models.available.length}</span
          >
        {/if}
      </button>
    {:else}
      <h3>Models {providers.active ? `· ${providers.active}` : ""}</h3>
    {/if}
    {#if models.available.length > 0}
      <button class="btn btn-ghost btn-sm" onclick={retestAll}>
        <Icon name="refresh" size="sm" /> Test all
      </button>
    {/if}
  </div>

  {#if collapsible && collapsed}
    <!-- collapsed: list hidden -->
  {:else if models.discovering}
    <div class="hint searching">
      <span class="spinner"></span>
      Searching models for {providers.active ? providerDisplayName(providers.active) : "provider"}…
    </div>
  {:else if !providers.active}
    <div class="hint">Select a provider from the sidebar to load models.</div>
  {:else if models.available.length === 0}
    <div class="hint">No models found for this provider.</div>
  {:else}
    <div class="bulk">
      <button
        class="btn btn-ghost btn-sm"
        onclick={allSelected ? clearAll : selectAll}
      >
        {allSelected ? "Unselect all" : "Select all"}
      </button>
      {#if !allSelected && models.selected.length > 0}
        <button class="btn btn-ghost btn-sm" onclick={clearAll}>Clear</button>
      {/if}
    </div>
    <div class="grid" role="group" aria-label="Model selection">
      {#each models.available as model (model)}
        {@const key = `${providers.active}::${model}`}
        {@const health = models.healthOf(key)}
        <label class="model-chip" class:selected={models.isSelected(key)}>
          <input
            type="checkbox"
            checked={models.isSelected(key)}
            onchange={() => models.toggle(key)}
          />
          <span class="mname" title={model}>{model}</span>
          {#if modelSupportsVision(model)}
            <span class="badge badge-vision" title="Supports image attachments">vision</span>
          {/if}
          {#if health === "OK"}
            <span class="badge badge-ok">OK</span>
          {:else if health === "KO"}
            <span class="badge badge-ko">KO</span>
          {:else if health === "testing"}
            <span class="badge badge-testing">…</span>
          {/if}
        </label>
      {/each}
    </div>
  {/if}
</div>

<style>
  .model-selector {
    margin-top: 8px;
  }
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }
  .head h3 {
    font-size: 14px;
    margin: 0;
  }
  .collapse-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    color: var(--text-primary);
  }
  .count-pill {
    font-size: 11px;
    color: var(--text-tertiary);
    background: var(--bg-tertiary);
    border-radius: 999px;
    padding: 1px 7px;
  }
  .bulk {
    display: flex;
    gap: 6px;
    margin-bottom: 8px;
  }
  .hint {
    color: var(--text-tertiary);
    font-size: 13px;
    padding: 12px;
    background: var(--bg-tertiary);
    border-radius: var(--radius);
  }
  .hint.searching {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text-secondary);
  }
  .spinner {
    width: 14px;
    height: 14px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    flex-shrink: 0;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 8px;
  }
  .model-chip {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 9px 12px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-secondary);
    cursor: pointer;
    margin: 0;
    font-size: 13px;
    font-weight: 400;
    color: var(--text-primary);
    transition: border-color var(--transition);
  }
  .model-chip:hover {
    border-color: var(--border-hover);
  }
  .model-chip.selected {
    border-color: var(--accent);
    background: var(--bg-tertiary);
  }
  .model-chip input {
    accent-color: var(--accent);
    width: auto;
    padding: 0;
  }
  .mname {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .badge {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 1px 5px;
    border-radius: 3px;
    flex-shrink: 0;
  }
  .badge-vision {
    background: color-mix(in srgb, #8b5cf6 18%, transparent);
    color: #a78bfa;
  }
</style>
