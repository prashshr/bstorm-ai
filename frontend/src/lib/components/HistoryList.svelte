<script lang="ts">
  import { history } from "../stores/history.svelte";
  import { discussion } from "../stores/discussion.svelte";
  import { nav } from "../stores/nav.svelte";
  import type { DiscussionResponse } from "../api/types";
  import { formatDate } from "../utils/helpers";
  import { safeRenderMarkdown } from "../utils/markdown";
  import Icon from "./Icon.svelte";

  let expanded = $state<number | null>(null);

  function toggleExpand(id: number) {
    expanded = expanded === id ? null : id;
  }

  async function restore(d: DiscussionResponse) {
    try {
      const state = JSON.parse(d.state_json) as Parameters<
        typeof discussion.load
      >[0];
      discussion.load(state);
      nav.go("current");
    } catch (e) {
      console.error("Failed to restore", e);
    }
  }

  function preview(d: DiscussionResponse): string {
    try {
      const state = JSON.parse(d.state_json) as {
        rounds?: Record<number, Record<string, { text: string }>>;
        consensus?: string;
      };
      const firstRound = Object.values(state.rounds ?? {})[0];
      const firstModel = firstRound ? Object.values(firstRound)[0] : null;
      const text = (firstModel?.text ?? state.consensus ?? "").slice(0, 400);
      return safeRenderMarkdown(text);
    } catch {
      return "";
    }
  }
</script>

<div class="history-list" data-testid="history-list">
  {#each history.visible as d (d.id)}
    <article class="item" data-testid="history-item">
      <div class="row">
        <button class="title-btn" onclick={() => toggleExpand(d.id)}>
          <Icon
            name={expanded === d.id ? "chevron-down" : "chevron-right"}
            size="sm"
          />
          <span class="title">{d.title || d.question}</span>
        </button>
        <div class="actions">
          <button
            class="btn btn-ghost btn-sm"
            onclick={() => restore(d)}
            title="Restore">Restore</button
          >
          <button
            class="btn btn-ghost btn-sm danger"
            onclick={() => history.remove(d.id)}
            title="Delete">Delete</button
          >
        </div>
      </div>
      <div class="meta">
        <span class="status status-{d.status}">{d.status}</span>
        <span class="date">{formatDate(d.created_at)}</span>
        {#if d.use_rag}<span class="tag">RAG</span>{/if}
        {#if d.deep_research}<span class="tag">Deep</span>{/if}
      </div>
      {#if expanded === d.id}
        <div class="details markdown">{@html preview(d)}</div>
      {/if}
    </article>
  {/each}
</div>

<style>
  .history-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .item {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 14px;
  }
  .row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  .title-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    background: none;
    border: none;
    color: var(--text-primary);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    flex: 1;
    text-align: left;
    padding: 0;
  }
  .title {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .actions {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
  }
  .btn.danger {
    color: var(--error);
  }
  .meta {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 8px;
    font-size: 12px;
    color: var(--text-tertiary);
  }
  .status {
    text-transform: capitalize;
    padding: 1px 8px;
    border-radius: 999px;
    background: var(--bg-tertiary);
  }
  .status-completed {
    color: var(--success);
  }
  .status-in_progress {
    color: var(--warning);
  }
  .tag {
    padding: 1px 8px;
    border-radius: 999px;
    background: var(--bg-tertiary);
    color: var(--accent);
  }
  .details {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid var(--border);
    font-size: 13px;
    max-height: 240px;
    overflow-y: auto;
  }
</style>
