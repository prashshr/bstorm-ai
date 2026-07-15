<script lang="ts">
  import { discussion } from "../stores/discussion.svelte";
  import { splitModelKey } from "../utils/helpers";

  let contributions = $derived(discussion.contributions);

  function highlight(modelKey: string) {
    document
      .querySelectorAll(".model-card.highlight")
      .forEach((el) => el.classList.remove("highlight"));
    const cards = document.querySelectorAll(
      `[id^="card-"][id$="-${CSS.escape(modelKey)}"]`,
    );
    cards.forEach((el) => el.classList.add("highlight"));
    cards[0]?.scrollIntoView({ behavior: "smooth", block: "center" });
  }
</script>

{#if contributions.length > 0}
  <div class="contributions">
    <h4>Contribution breakdown</h4>
    <div class="stacked" role="img" aria-label="Model contribution proportions">
      {#each contributions as c (c.model)}
        <div
          class="seg"
          style="width:{c.weight}%;background:{c.color}"
          title="{splitModelKey(c.model).model}: {c.weight}%"
        ></div>
      {/each}
    </div>
    <ul class="legend">
      {#each contributions as c (c.model)}
        <li>
          <button
            class="legend-item"
            onclick={() => highlight(c.model)}
            title="Jump to {splitModelKey(c.model).model}"
          >
            <span class="dot" style="background:{c.color}"></span>
            <span class="lname">{splitModelKey(c.model).model}</span>
            <span class="pct">{c.weight}%</span>
          </button>
        </li>
      {/each}
    </ul>
  </div>
{/if}

<style>
  .contributions {
    margin-top: 16px;
  }
  .contributions h4 {
    font-size: 13px;
    margin: 0 0 8px;
    color: var(--text-secondary);
  }
  .stacked {
    display: flex;
    height: 14px;
    border-radius: 999px;
    overflow: hidden;
    background: var(--bg-tertiary);
  }
  .seg {
    height: 100%;
    transition: width var(--transition);
  }
  .legend {
    list-style: none;
    margin: 10px 0 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .legend-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 999px;
    font-size: 12px;
    cursor: pointer;
    color: var(--text-primary);
  }
  .legend-item:hover {
    border-color: var(--accent);
  }
  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }
  .pct {
    color: var(--text-tertiary);
    font-variant-numeric: tabular-nums;
  }
</style>
