<script lang="ts">
  import { models } from "../stores/models.svelte";
  import { splitModelKey } from "../utils/helpers";
  import Icon from "./Icon.svelte";
</script>

{#if models.selected.length > 0}
  <div class="ensemble">
    <span class="lbl">Active ensemble:</span>
    <div class="pills">
      {#each models.selected as key (key)}
        {@const { model } = splitModelKey(key)}
        <span class="pill">
          {model}
          <button
            class="rm"
            onclick={() => models.remove(key)}
            aria-label="Remove {model}"
          >
            <Icon name="close" size="sm" />
          </button>
        </span>
      {/each}
    </div>
  </div>
{/if}

<style>
  .ensemble {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin: 12px 0;
    flex-wrap: wrap;
  }
  .lbl {
    font-size: 12px;
    color: var(--text-tertiary);
    font-weight: 600;
    padding-top: 5px;
  }
  .pills {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 6px 4px 10px;
    background: var(--bg-tertiary);
    border: 1px solid var(--accent);
    border-radius: 999px;
    font-size: 12px;
    color: var(--accent);
  }
  .rm {
    display: inline-flex;
    background: none;
    border: none;
    color: var(--accent);
    padding: 2px;
    border-radius: 50%;
  }
  .rm:hover {
    background: var(--accent);
    color: #fff;
  }
</style>
