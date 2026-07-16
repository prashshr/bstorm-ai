<script lang="ts">
  import { discussion } from "../stores/discussion.svelte";
  import ModelCard from "./ModelCard.svelte";
  import Icon from "./Icon.svelte";

  let rounds = $derived(
    Object.entries(discussion.data.rounds)
      .map(([num, models]) => ({ num: Number(num), models }))
      .sort((a, b) => a.num - b.num),
  );

  let open = $state<Set<number>>(new Set([rounds[0]?.num].filter(Boolean)));

  function toggle(num: number) {
    const next = new Set(open);
    if (next.has(num)) next.delete(num);
    else next.add(num);
    open = next;
  }
</script>

<div class="timeline">
  {#each rounds as round (round.num)}
    {@const isOpen = open.has(round.num)}
    <section class="round">
      <button
        class="round-header"
        class:open={isOpen}
        onclick={() => toggle(round.num)}
        aria-expanded={isOpen}
      >
        <span class="rh-left">
          <Icon
            name={isOpen ? "chevron-down" : "chevron-right"}
            size="sm"
          />
          <h3>Round {round.num}</h3>
        </span>
        <span class="round-meta">
          {Object.values(round.models).filter((m) => m.status === "complete")
            .length}/{Object.keys(round.models).length} complete
        </span>
      </button>
      {#if isOpen}
        <div class="cards">
          {#each Object.entries(round.models) as [modelKey, result] (modelKey)}
            <ModelCard {modelKey} roundNum={round.num} {result} />
          {/each}
        </div>
      {/if}
    </section>
  {/each}
</div>

<style>
  .timeline {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .round-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: 8px 12px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    cursor: pointer;
    color: var(--text-primary);
    font: inherit;
    text-align: left;
  }
  .round-header.open {
    border-color: var(--accent);
  }
  .rh-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .round-header h3 {
    margin: 0;
    font-size: 14px;
  }
  .round-meta {
    font-size: 12px;
    color: var(--text-tertiary);
  }
  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 14px;
    padding-top: 12px;
  }
  @media (max-width: 640px) {
    .cards {
      grid-template-columns: 1fr;
    }
  }
</style>
