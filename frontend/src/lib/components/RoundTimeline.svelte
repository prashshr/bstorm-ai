<script lang="ts">
  import { discussion } from "../stores/discussion.svelte";
  import ModelCard from "./ModelCard.svelte";

  let rounds = $derived(
    Object.entries(discussion.data.rounds)
      .map(([num, models]) => ({ num: Number(num), models }))
      .sort((a, b) => a.num - b.num),
  );
</script>

<div class="timeline">
  {#each rounds as round (round.num)}
    <section class="round">
      <div class="round-header">
        <h3>Round {round.num}</h3>
        <span class="round-meta">
          {Object.values(round.models).filter((m) => m.status === "complete")
            .length}/{Object.keys(round.models).length} complete
        </span>
      </div>
      <div class="cards">
        {#each Object.entries(round.models) as [modelKey, result] (modelKey)}
          <ModelCard {modelKey} roundNum={round.num} {result} />
        {/each}
      </div>
    </section>
  {/each}
</div>

<style>
  .timeline {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }
  .round-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    background: var(--bg-tertiary);
    border-radius: var(--radius);
    margin-bottom: 12px;
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
  }
  @media (max-width: 640px) {
    .cards {
      grid-template-columns: 1fr;
    }
  }
</style>
