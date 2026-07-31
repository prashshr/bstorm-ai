<script lang="ts">
  import { history } from "../stores/history.svelte";
  import { folders } from "../stores/folders.svelte";
  import { discussion } from "../stores/discussion.svelte";
  import { auth } from "../stores/auth.svelte";
  import { models } from "../stores/models.svelte";
  import { providers } from "../stores/providers.svelte";
  import type { DiscussionResponse } from "../api/types";
  import Icon from "./Icon.svelte";

  let search = $state("");
  let { collapsed = $bindable(false), paneWidth = $bindable(260), mobileOpen = $bindable(false) } = $props();
  let expandedFolders = $state<Record<number, boolean>>({});
  let newFolderName = $state("");
  let addingFolder = $state(false);

  const activeId = $derived(
    typeof discussion.data.id === "number" ? discussion.data.id : null,
  );

  function groupByDate(items: DiscussionResponse[]): Record<string, DiscussionResponse[]> {
    const groups: Record<string, DiscussionResponse[]> = {};
    for (const d of items) {
      const date = new Date(d.created_at);
      const today = new Date();
      const yesterday = new Date();
      yesterday.setDate(today.getDate() - 1);
      const key =
        date.toDateString() === today.toDateString()
          ? "Today"
          : date.toDateString() === yesterday.toDateString()
            ? "Yesterday"
            : date.toLocaleDateString(undefined, {
                year: "numeric",
                month: "long",
                day: "numeric",
              });
      (groups[key] ??= []).push(d);
    }
    return groups;
  }

  const filtered = $derived(
    history.items.filter((d) =>
      search.trim()
        ? d.question.toLowerCase().includes(search.toLowerCase()) ||
          d.title.toLowerCase().includes(search.toLowerCase())
        : true,
    ),
  );

  const dateGroups = $derived(groupByDate(filtered.filter((d) => !folders.folderDiscussionIds.has(d.id))));
  const dateOrder = $derived(Object.keys(dateGroups));

  function selectDiscussion(d: DiscussionResponse) {
    mobileOpen = false;
    try {
      const state = JSON.parse(d.state_json || "{}") as typeof discussion.data;
      discussion.load(state);
    } catch {
      /* ignore */
    }
  }

  function newChat() {
    discussion.reset();
  }

  let dragging = $state(false);
  function startResize(e: PointerEvent) {
    if (collapsed) return;
    dragging = true;
    document.body.classList.add("resizing");
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }
  function onResize(e: PointerEvent) {
    if (!dragging) return;
    const next = Math.min(Math.max(e.clientX, 200), 520);
    paneWidth = next;
    localStorage.setItem("aiEnsembleSidebarWidth", String(next));
  }
  function endResize(e: PointerEvent) {
    dragging = false;
    document.body.classList.remove("resizing");
    try {
      (e.target as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
  }

  function toggleFolder(id: number) {
    expandedFolders = { ...expandedFolders, [id]: !expandedFolders[id] };
  }

  async function createFolder() {
    const name = newFolderName.trim();
    if (!name) return;
    await folders.create(name);
    newFolderName = "";
    addingFolder = false;
  }

  async function renameFolder(id: number, current: string) {
    const name = prompt("Rename folder", current);
    if (name && name.trim() && name !== current) {
      await folders.rename(id, name.trim());
    }
  }

  async function deleteFolder(id: number) {
    if (confirm("Delete this folder? Discussions inside are kept.")) {
      await folders.remove(id);
    }
  }

  async function removeFromFolder(folderId: number, discId: number) {
    await folders.removeDiscussion(folderId, discId);
  }

  const providerCount = $derived(providers.list.length);
  const modelCount = $derived(models.all.length);
</script>

<aside class="sessions" class:collapsed class:mobile-open={mobileOpen} style={collapsed ? "" : `width:${paneWidth}px`}>
  {#if collapsed}
    <button class="btn btn-ghost expand-btn" onclick={() => (collapsed = false)} aria-label="Expand chat list">
      <Icon name="chevron-right" />
    </button>
  {:else}
    <div class="s-head">
      <button class="btn btn-primary new-chat" onclick={newChat} data-testid="new-chat-btn">
        <Icon name="plus" size="sm" /> New Chat
      </button>
      <button class="btn btn-ghost icon-btn" onclick={() => (collapsed = true)} aria-label="Collapse chat list">
        <Icon name="chevron-left" />
      </button>
    </div>

    <div class="search-row">
      <Icon name="search" size="sm" />
      <input class="search" placeholder="Search chats…" bind:value={search} data-testid="session-search" />
    </div>

    <div class="scroll">
      {#if history.loading}
        <p class="muted">Loading…</p>
      {/if}

      {#each folders.list as folder (folder.id)}
        <div class="group">
          <div class="folder-head">
            <button class="folder-toggle" onclick={() => toggleFolder(folder.id)}>
              <Icon name={expandedFolders[folder.id] ? "chevron-down" : "chevron-right"} size="sm" />
              <span class="folder-name">{folder.name}</span>
              <span class="count">{folder.discussion_ids.length}</span>
            </button>
            <div class="folder-actions">
              <button class="btn btn-ghost btn-sm" title="Rename" onclick={() => renameFolder(folder.id, folder.name)}>
                <Icon name="settings" size="sm" />
              </button>
              <button class="btn btn-ghost btn-sm danger" title="Delete folder" onclick={() => deleteFolder(folder.id)}>
                <Icon name="trash" size="sm" />
              </button>
            </div>
          </div>
          {#if expandedFolders[folder.id]}
            {#each folder.discussion_ids as discId (discId)}
              {@const d = history.items.find((x) => x.id === discId)}
              {#if d}
                <div class="session" class:active={activeId === d.id}>
                  <button class="session-btn" onclick={() => selectDiscussion(d)} title={d.title || d.question}>
                    <Icon name="bot" size="sm" />
                    <span class="s-title">{d.title || d.question}</span>
                  </button>
                  <button class="btn btn-ghost btn-sm s-del" title="Remove from folder" onclick={() => removeFromFolder(folder.id, d.id)}>
                    <Icon name="close" size="sm" />
                  </button>
                </div>
              {/if}
            {/each}
          {/if}
        </div>
      {/each}

      {#each dateOrder as label (label)}
        <div class="group">
          <div class="date-label">{label}</div>
          {#each dateGroups[label] as d (d.id)}
            <div class="session" class:active={activeId === d.id}>
              <button class="session-btn" onclick={() => selectDiscussion(d)} title={d.title || d.question} data-testid="session-item">
                <Icon name="bot" size="sm" />
                <span class="s-title">{d.title || d.question}</span>
              </button>
              <button class="btn btn-ghost btn-sm s-del" title="Delete" onclick={() => history.remove(d.id)}>
                <Icon name="trash" size="sm" />
              </button>
            </div>
          {/each}
        </div>
      {/each}

      {#if dateOrder.length === 0 && folders.list.length === 0}
        <p class="muted empty">No chats yet. Start a new one.</p>
      {/if}
    </div>

    <div class="s-foot">
      <span class="user" title={auth.user ?? ""}>{auth.user ?? "user"}</span>
      <div class="foot-actions">
        <span class="stat" title="Providers / models">{providerCount}·{modelCount}</span>
        <button class="btn btn-ghost btn-sm" onclick={() => auth.logout()} aria-label="Logout">
          <Icon name="logout" size="sm" />
        </button>
      </div>
    </div>
  {/if}
  {#if !collapsed}
    <div
      class="resizer"
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize chat list"
      class:dragging
      onpointerdown={startResize}
      onpointermove={onResize}
      onpointerup={endResize}
    ></div>
  {/if}
</aside>

{#if mobileOpen}
  <div class="s-backdrop" onclick={() => (mobileOpen = false)} aria-hidden="true"></div>
{/if}

<style>
  .sessions {
    width: 260px;
    flex-shrink: 0;
    border-right: 1px solid var(--border);
    background: var(--bg-secondary);
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
  }
  .sessions.collapsed {
    width: 56px;
    align-items: center;
  }
  .resizer {
    position: absolute;
    top: 0;
    right: -5px;
    width: 10px;
    height: 100%;
    cursor: col-resize;
    z-index: 20;
    background: transparent;
  }
  .resizer:hover,
  .resizer.dragging {
    background: var(--accent);
    opacity: 0.6;
  }
  .sessions {
    position: relative;
  }
  :global(body.resizing) {
    cursor: col-resize;
    user-select: none;
  }
  .expand-btn {
    margin-top: 10px;
    padding: 8px;
  }
  .s-head {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 12px 14px 8px;
  }
  .new-chat {
    flex: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }
  .icon-btn {
    padding: 6px;
  }
  .search-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0 14px 10px;
    padding: 0 10px;
    border: 1px solid var(--input-border);
    border-radius: var(--radius);
    color: var(--text-tertiary);
  }
  .search-row:focus-within {
    border-color: var(--accent);
  }
  .search {
    border: none;
    background: none;
    padding: 8px 0;
    flex: 1;
  }
  .search:focus {
    border: none;
    outline: none;
  }
  .scroll {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 4px 8px;
  }
  .group {
    margin-bottom: 10px;
  }
  .date-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-tertiary);
    padding: 8px 8px 4px;
  }
  .folder-head {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 6px 6px;
    border-radius: var(--radius);
  }
  .folder-head:hover {
    background: var(--bg-tertiary);
  }
  .folder-toggle {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 6px;
    background: none;
    border: none;
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 600;
    text-align: left;
  }
  .folder-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .count {
    font-size: 11px;
    color: var(--text-tertiary);
  }
  .folder-actions {
    display: flex;
    gap: 2px;
    opacity: 0;
  }
  .folder-head:hover .folder-actions {
    opacity: 1;
  }
  .session {
    display: flex;
    align-items: center;
    gap: 2px;
    border-radius: var(--radius);
    margin: 1px 0;
  }
  .session:hover {
    background: var(--bg-tertiary);
  }
  .session.active {
    background: color-mix(in srgb, var(--accent) 16%, var(--bg-tertiary));
    box-shadow: inset 3px 0 0 var(--accent);
  }
  .session.active .session-btn {
    color: var(--text-primary);
    font-weight: 700;
  }
  .session.active .session-btn :global(svg) {
    color: var(--accent);
  }
  .session-btn {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    background: none;
    border: none;
    color: var(--text-primary);
    font-size: 13px;
    text-align: left;
  }
  .session-btn :global(svg) {
    color: var(--text-tertiary);
    flex-shrink: 0;
  }
  .s-title {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .s-del {
    opacity: 0;
    padding: 4px;
  }
  .session:hover .s-del,
  .session.active .s-del {
    opacity: 1;
  }
  .danger {
    color: var(--error);
  }
  .muted {
    color: var(--text-tertiary);
    font-size: 13px;
    padding: 12px 14px;
  }
  .empty {
    text-align: center;
    padding-top: 40px;
  }
  .s-foot {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 10px 14px;
    border-top: 1px solid var(--border);
  }
  .user {
    font-size: 13px;
    color: var(--text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .foot-actions {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .stat {
    font-size: 11px;
    color: var(--text-tertiary);
  }
  .s-backdrop {
    display: none;
  }

  /* ---- Mobile: sidebar becomes a slide-in overlay ---- */
  @media (max-width: 768px) {
    .sessions {
      position: absolute;
      top: 0;
      bottom: 0;
      left: 0;
      height: 100%;
      width: 280px;
      max-width: 85vw;
      z-index: 60;
      transform: translateX(-100%);
      transition: transform var(--transition);
      box-shadow: var(--shadow-md);
      box-sizing: border-box;
    }
    .sessions.mobile-open {
      transform: translateX(0);
    }
    .resizer {
      display: none;
    }
    .s-backdrop {
      display: block;
      position: absolute;
      inset: 0;
      background: rgba(0, 0, 0, 0.5);
      z-index: 55;
    }
    .folder-actions,
    .s-del {
      opacity: 1;
    }
  }
  @media (hover: none) {
    .folder-actions,
    .s-del {
      opacity: 1;
    }
  }
</style>
