<script lang="ts" module>
  import type { ProgressPhase } from "../api/types";
  export const PHASES: { key: ProgressPhase; label: string }[] = [
    { key: "queued", label: "Queued" },
    { key: "searching", label: "Searching" },
    { key: "drafting", label: "Drafting" },
    { key: "synthesizing", label: "Synthesizing" },
  ];
</script>

<script lang="ts">
  import { discussion } from "../stores/discussion.svelte";

  interface Props {
    compact?: boolean;
  }
  let { compact = false }: Props = $props();

  const order: ProgressPhase[] = [
    "queued",
    "searching",
    "drafting",
    "synthesizing",
    "done",
  ];
  let activeIndex = $derived(order.indexOf(discussion.phase));
</script>

<div
  class="stepper"
  class:compact
  role="status"
  aria-live="polite"
  aria-label="Discussion progress: {discussion.phase}"
>
  {#each PHASES as phase, i (phase.key)}
    {@const state =
      i < activeIndex ? "done" : i === activeIndex ? "active" : "pending"}
    <div class="step {state}">
      <span class="dot"></span>
      {#if !compact}<span class="label">{phase.label}</span>{/if}
    </div>
    {#if i < PHASES.length - 1}
      <span class="bar {i < activeIndex ? 'done' : ''}"></span>
    {/if}
  {/each}
</div>

<style>
  .stepper {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .step {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--border);
    transition: background var(--transition);
  }
  .step.done .dot {
    background: var(--success);
  }
  .step.active .dot {
    background: var(--accent);
    animation: pulse 1.2s ease-in-out infinite;
  }
  .label {
    font-size: 12px;
    color: var(--text-tertiary);
  }
  .step.active .label {
    color: var(--accent);
    font-weight: 600;
  }
  .step.done .label {
    color: var(--text-secondary);
  }
  .bar {
    width: 24px;
    height: 2px;
    background: var(--border);
  }
  .bar.done {
    background: var(--success);
  }
  .compact .bar {
    width: 12px;
  }
</style>
