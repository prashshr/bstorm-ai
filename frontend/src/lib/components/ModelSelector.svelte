<script lang="ts">
  import { models } from "../stores/models.svelte";
  import { providers } from "../stores/providers.svelte";
  import Icon from "./Icon.svelte";

  let compositeKeys = $derived(
    models.available.map((m) => `${providers.active}::${m}`),
  );

  async function retestAll() {
    await models.checkAllHealth(compositeKeys);
  }
</script>

<div class="model-selector">
  <div class="head">
    <h3>Models {providers.active ? `· ${providers.active}` : ""}</h3>
    {#if models.available.length > 0}
      <button class="btn btn-ghost btn-sm" onclick={retestAll}>
        <Icon name="refresh" size="sm" /> Test all
      </button>
    {/if}
  </div>

  {#if models.discovering}
    <div class="hint">Discovering models…</div>
  {:else if !providers.active}
    <div class="hint">Select a provider from the sidebar to load models.</div>
  {:else if models.available.length === 0}
    <div class="hint">No models found for this provider.</div>
  {:else}
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
  .hint {
    color: var(--text-tertiary);
    font-size: 13px;
    padding: 12px;
    background: var(--bg-tertiary);
    border-radius: var(--radius);
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
</style>
