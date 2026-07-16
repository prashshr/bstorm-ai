<script lang="ts">
  import { history } from "../stores/history.svelte";
  import { discussion } from "../stores/discussion.svelte";
  import { nav } from "../stores/nav.svelte";
  import type { DiscussionResponse } from "../api/types";
  import { formatDate, splitModelKey, copyToClipboard } from "../utils/helpers";
  import { safeRenderMarkdown } from "../utils/markdown";
  import Icon from "./Icon.svelte";

  let expanded = $state<number | null>(null);
  let copiedId = $state<number | null>(null);
  let selected = $state<Set<number>>(new Set());
  let anchor = $state<number | null>(null);

  let allSelected = $derived(
    history.visible.length > 0 &&
      history.visible.every((d) => selected.has(d.id)),
  );
  let someSelected = $derived(
    history.visible.some((d) => selected.has(d.id)),
  );

  function toggleExpand(id: number) {
    expanded = expanded === id ? null : id;
  }

  function toggleSelect(id: number, shiftKey = false) {
    const ids = history.visible.map((d) => d.id);
    if (shiftKey && anchor !== null) {
      const a = ids.indexOf(anchor);
      const b = ids.indexOf(id);
      if (a !== -1 && b !== -1) {
        const [lo, hi] = a < b ? [a, b] : [b, a];
        const next = new Set(selected);
        const turnOn = !next.has(id);
        for (let i = lo; i <= hi; i++) {
          if (turnOn) next.add(ids[i]);
          else next.delete(ids[i]);
        }
        selected = next;
        return;
      }
    }
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    anchor = id;
    selected = next;
  }

  function toggleSelectAll() {
    if (allSelected) selected = new Set();
    else selected = new Set(history.visible.map((d) => d.id));
  }

  function download(filename: string, content: string) {
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function exportOne(d: DiscussionResponse) {
    const slug = (d.title || d.question || "discussion")
      .replace(/[^a-z0-9]+/gi, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60) || "discussion";
    download(`discussion-${d.id}-${slug}.md`, transcriptFor(d));
  }

  function exportSelected() {
    const items = history.visible.filter((d) => selected.has(d.id));
    if (items.length === 1) {
      exportOne(items[0]);
      return;
    }
    const bundle = items
      .map((d) => `---\n# Discussion ${d.id}\n${transcriptFor(d)}`)
      .join("\n\n");
    download(`discussions-export-${items.length}.md`, bundle);
  }

  async function deleteSelected() {
    for (const id of selected) {
      await history.remove(id);
    }
    selected = new Set();
  }

  function transcriptFor(d: DiscussionResponse): string {
    try {
      const state = JSON.parse(d.state_json) as {
        question?: string;
        rounds?: Record<string, Record<string, { text?: string }>>;
        consensus?: string;
      };
      const parts: string[] = [];
      parts.push(`# ${state.question ?? d.question}`);
      const rounds = state.rounds ?? {};
      for (const rn of Object.keys(rounds).sort((a, b) => Number(a) - Number(b))) {
        const body = Object.entries(rounds[rn])
          .filter(([, r]) => r.text)
          .map(([m, r]) => `### ${splitModelKey(m).model}\n\n${r.text}`)
          .join("\n\n");
        if (body) parts.push(`## Round ${rn}\n\n${body}`);
      }
      if (state.consensus) parts.push(`## Consensus\n\n${state.consensus}`);
      return parts.join("\n\n");
    } catch {
      return d.question ?? "";
    }
  }

  async function copyItem(d: DiscussionResponse) {
    if (await copyToClipboard(transcriptFor(d))) {
      copiedId = d.id;
      setTimeout(() => (copiedId = null), 1500);
    }
  }

  async function restore(d: DiscussionResponse) {
    try {
      const state = JSON.parse(d.state_json) as Parameters<
        typeof discussion.load
      >[0];
      const safeState = { ...state };
      if (safeState.status !== "completed" && safeState.status !== "closed") {
        safeState.status = "stopped";
      }
      discussion.load(safeState);
      nav.go("current");
    } catch (e) {
      console.error("Failed to restore", e);
    }
  }

  function preview(d: DiscussionResponse): string {
    try {
      const state = JSON.parse(d.state_json) as {
        question?: string;
        rounds?: Record<string, Record<string, { text?: string }>>;
        consensus?: string;
        models?: string[];
      };
      const parts: string[] = [];
      parts.push(`# ${state.question ?? d.question}`);
      const rounds = state.rounds ?? {};
      for (const rn of Object.keys(rounds).sort(
        (a, b) => Number(a) - Number(b),
      )) {
        const body = Object.entries(rounds[rn])
          .filter(([, r]) => r.text)
          .map(([m, r]) => `### ${splitModelKey(m).model}\n\n${r.text}`)
          .join("\n\n");
        if (body) parts.push(`## Round ${rn}\n\n${body}`);
      }
      if (state.consensus) parts.push(`## Consensus\n\n${state.consensus}`);
      return safeRenderMarkdown(parts.join("\n\n"));
    } catch {
      return safeRenderMarkdown(d.question ?? "");
    }
  }

  function metaCounts(d: DiscussionResponse): { models: number; rounds: number } {
    try {
      const state = JSON.parse(d.state_json) as {
        rounds?: Record<string, unknown>;
        models?: unknown[];
      };
      return {
        models: state.models?.length ?? 0,
        rounds: Object.keys(state.rounds ?? {}).length,
      };
    } catch {
      return { models: 0, rounds: 0 };
    }
  }
</script>

<div class="history-list" data-testid="history-list">
  <div class="bulk-bar" class:show={someSelected}>
    <label class="select-all">
      <input type="checkbox" checked={allSelected} onchange={toggleSelectAll} />
      Select all
    </label>
    <span class="count">{selected.size} selected</span>
    <div class="bulk-actions">
      <button class="btn btn-ghost btn-sm" onclick={exportSelected}>
        <Icon name="download" size="sm" /> Export{selected.size > 1 ? " (" + selected.size + ")" : ""}
      </button>
      <button class="btn btn-ghost btn-sm danger" onclick={deleteSelected}>
        <Icon name="trash" size="sm" /> Delete{selected.size > 1 ? " (" + selected.size + ")" : ""}
      </button>
    </div>
  </div>

  {#each history.visible as d (d.id)}
    {@const counts = metaCounts(d)}
    <article class="item" class:selected={selected.has(d.id)} data-testid="history-item">
      <div class="row">
        <label class="select-cell" title="Select">
          <input
            type="checkbox"
            checked={selected.has(d.id)}
            onclick={(e) => {
              e.preventDefault();
              toggleSelect(d.id, e.shiftKey);
            }}
          />
        </label>
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
            onclick={() => copyItem(d)}
            title="Copy discussion"
          >
            <Icon name={copiedId === d.id ? "check" : "copy"} size="sm" />
          </button>
          <button
            class="btn btn-ghost btn-sm"
            onclick={() => exportOne(d)}
            title="Export as Markdown"
          >
            <Icon name="download" size="sm" />
          </button>
          <button
            class="btn btn-ghost btn-sm"
            onclick={() => restore(d)}
            title="View Discussion">View Discussion</button
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
        {#if counts.models}
          <span class="tag">{counts.models} models</span>
        {/if}
        {#if counts.rounds}
          <span class="tag">{counts.rounds} rounds</span>
        {/if}
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
  .bulk-bar {
    display: none;
    align-items: center;
    gap: 12px;
    padding: 8px 12px;
    background: var(--bg-secondary);
    border: 1px solid var(--accent);
    border-radius: var(--radius);
  }
  .bulk-bar.show {
    display: flex;
  }
  .select-all {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: var(--text-secondary);
    cursor: pointer;
  }
  .bulk-bar .count {
    font-size: 12px;
    color: var(--text-tertiary);
  }
  .bulk-actions {
    display: flex;
    gap: 6px;
    margin-left: auto;
  }
  .item {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 14px;
  }
  .item.selected {
    border-color: var(--accent);
  }
  .row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  .select-cell {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    cursor: pointer;
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
    max-height: 60vh;
    overflow-y: auto;
  }
</style>
