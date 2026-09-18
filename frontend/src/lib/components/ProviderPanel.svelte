<script lang="ts">
  import { providers } from "../stores/providers.svelte";
  import { models } from "../stores/models.svelte";
  import Icon from "./Icon.svelte";
  import ProviderForm from "./ProviderForm.svelte";
  import ModelSelector from "./ModelSelector.svelte";
  import OAuthModal from "./OAuthModal.svelte";
  import { providerDisplayName, splitModelKey } from "../utils/helpers";

  interface Props {
    open: boolean;
    onclose: () => void;
  }
  let { open, onclose }: Props = $props();

  let adding = $state(false);
  let editing = $state<string | null>(null);
  let favoritesOpen = $state(true);
  let oauthModal = $state<"codex" | "copilot" | "openrouter" | null>(null);

  let codexAccount = $derived(providers.oauthAccountFor("codex"));
  let openrouterAccount = $derived(providers.oauthAccountFor("openrouter"));
  let copilotAccount = $derived(providers.oauthAccountFor("copilot"));
  let paneWidth = $state<number>(
    typeof window !== "undefined"
      ? Math.min(
          Math.max(Number(localStorage.getItem("aiEnsembleProviderPanelWidth")) || 380, 280),
          Math.floor(window.innerWidth * 0.92),
        )
      : 380,
  );
  let dragging = $state(false);

  function startResize(e: PointerEvent) {
    if (!open) return;
    dragging = true;
    document.body.classList.add("resizing");
    window.addEventListener("pointermove", onResize);
    window.addEventListener("pointerup", endResize);
    window.addEventListener("pointercancel", endResize);
    try {
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
    e.preventDefault();
    e.stopPropagation();
  }

  function onResize(e: PointerEvent) {
    if (!dragging) return;
    const maxW = Math.min(850, Math.floor(window.innerWidth * 0.92));
    const next = Math.min(Math.max(window.innerWidth - e.clientX, 280), maxW);
    paneWidth = next;
    localStorage.setItem("aiEnsembleProviderPanelWidth", String(next));
  }

  function endResize(e?: PointerEvent) {
    if (!dragging) return;
    dragging = false;
    document.body.classList.remove("resizing");
    window.removeEventListener("pointermove", onResize);
    window.removeEventListener("pointerup", endResize);
    window.removeEventListener("pointercancel", endResize);
    if (e && e.pointerId != null) {
      try {
        (e.target as HTMLElement).releasePointerCapture(e.pointerId);
      } catch {
        /* ignore */
      }
    }
  }

  let sortedProviders = $derived(
    [...providers.list].sort((a, b) => {
      const ac = a.provider.toLowerCase().startsWith("custom");
      const bc = b.provider.toLowerCase().startsWith("custom");
      if (ac !== bc) return ac ? 1 : -1;
      return a.provider.localeCompare(b.provider);
    }),
  );

  let allFavoritesSelected = $derived(
    models.favorites.length > 0 &&
      models.favorites.every((k) => models.isSelected(k)),
  );

  function toggleAllFavorites() {
    if (allFavoritesSelected) {
      for (const k of models.favorites) {
        if (models.isSelected(k)) models.toggle(k);
      }
    } else {
      for (const k of models.favorites) {
        if (!models.isSelected(k)) models.toggle(k);
      }
    }
  }

  async function selectProvider(key: string) {
    providers.select(key);
    try {
      await models.discover(key);
    } catch {
      /* handled in store */
    }
  }

  async function remove(key: string) {
    const p = providers.find(key);
    const name = p ? providerDisplayName(key, p.label) : key;
    if (confirm(`Remove provider "${name}"? Saved credentials will be deleted.`)) {
      await providers.remove(key);
      if (editing === key) editing = null;
    }
  }

  async function handleDisconnect(provider: string, label: string) {
    if (confirm(`Disconnect ${label}? Your saved session will be removed.`)) {
      await providers.disconnectOAuth(provider);
      if (editing === provider) editing = null;
    }
  }

  function toggleEdit(key: string) {
    editing = editing === key ? null : key;
    adding = false;
    if (editing === key && providers.isVerified(key)) {
      selectProvider(key);
    }
  }
</script>

{#if open}
  <div
    class="backdrop"
    role="presentation"
    onclick={() => {
      if (!dragging) onclose();
    }}
  ></div>
{/if}

<aside
  class="panel"
  class:open
  aria-hidden={!open}
  style={open ? `width: ${paneWidth}px; max-width: 95vw;` : ""}
>
  <!-- Left-Edge Vertical Draggable Resizer Handle -->
  <div
    class="resizer-left"
    role="separator"
    aria-orientation="vertical"
    aria-label="Resize providers panel width"
    class:dragging
    onpointerdown={startResize}
    onpointermove={onResize}
    onpointerup={endResize}
    onpointercancel={endResize}
    title="Drag left/right to resize panel width"
  ></div>

  <div class="p-head">
    <h2>Subscriptions</h2>
    <button class="btn btn-ghost icon-btn" onclick={onclose} aria-label="Close panel">
      <Icon name="close" size="sm" />
    </button>
  </div>

  <div class="p-body">
    <!-- Top Section: Subscriptions (ChatGPT, GitHub Copilot, OpenRouter) -->
    <div class="section-block oauth-section">
      <div class="oauth-cards-stack">
        <!-- ChatGPT Row -->
        <div class="oauth-card" class:is-connected={Boolean(codexAccount)}>
          <div class="oauth-card-left">
            <div class="oauth-icon-badge brand-chatgpt" aria-hidden="true">
              <Icon name="chatgpt" size="sm" />
            </div>
            <div class="oauth-meta">
              <div class="oauth-name-row">
                <span class="oauth-name">ChatGPT</span>
                {#if codexAccount}
                  <span class="oauth-status-badge connected" title="Connected: {codexAccount}">
                    <span class="status-indicator-dot"></span>
                    <span>Active</span>
                  </span>
                {:else}
                  <span class="oauth-status-badge disconnected">
                    <span>Not linked</span>
                  </span>
                {/if}
              </div>
              <div class="oauth-detail-row" title={codexAccount || "Sign-in with ChatGPT subscription"}>
                {#if codexAccount}
                  <span class="oauth-account-id">{codexAccount}</span>
                {:else}
                  <span class="oauth-hint-text">Plus &bull; Team &bull; Pro login</span>
                {/if}
              </div>
            </div>
          </div>
          <div class="oauth-card-right">
            {#if codexAccount}
              <div class="oauth-btn-group">
                <button
                  class="btn btn-ghost btn-sm oauth-action-btn"
                  aria-label="Switch ChatGPT"
                  title="Switch account (currently {codexAccount})"
                  onclick={() => (oauthModal = "codex")}
                >
                  <Icon name="refresh" size="sm" />
                  <span>Switch</span>
                </button>
                <button
                  class="btn btn-ghost btn-sm oauth-action-btn oauth-disconnect-btn"
                  aria-label="Disconnect ChatGPT"
                  title="Disconnect account ({codexAccount})"
                  onclick={() => handleDisconnect("codex", "ChatGPT")}
                >
                  <Icon name="trash" size="sm" />
                  <span>Disconnect</span>
                </button>
              </div>
            {:else}
              <button
                class="btn btn-primary btn-sm oauth-action-btn"
                aria-label="Connect ChatGPT"
                title="Connect ChatGPT"
                onclick={() => (oauthModal = "codex")}
              >
                Connect
              </button>
            {/if}
          </div>
        </div>

        <!-- GitHub Copilot Row -->
        <div class="oauth-card" class:is-connected={Boolean(copilotAccount)}>
          <div class="oauth-card-left">
            <div class="oauth-icon-badge brand-copilot" aria-hidden="true">
              <Icon name="github" size="sm" />
            </div>
            <div class="oauth-meta">
              <div class="oauth-name-row">
                <span class="oauth-name">GitHub Copilot</span>
                {#if copilotAccount}
                  <span class="oauth-status-badge connected" title="Connected: @{copilotAccount}">
                    <span class="status-indicator-dot"></span>
                    <span>Active</span>
                  </span>
                {:else}
                  <span class="oauth-status-badge disconnected">
                    <span>Not linked</span>
                  </span>
                {/if}
              </div>
              <div class="oauth-detail-row" title={copilotAccount ? `@${copilotAccount}` : "Claude 3.5, GPT-4o, and o1 via GitHub authorization"}>
                {#if copilotAccount}
                  <span class="oauth-account-id">@{copilotAccount}</span>
                {:else}
                  <span class="oauth-hint-text">Claude 3.5 &bull; GPT-4o &bull; o1</span>
                {/if}
              </div>
            </div>
          </div>
          <div class="oauth-card-right">
            {#if copilotAccount}
              <div class="oauth-btn-group">
                <button
                  class="btn btn-ghost btn-sm oauth-action-btn"
                  aria-label="Switch GitHub Copilot"
                  title="Switch account (currently @{copilotAccount})"
                  onclick={() => (oauthModal = "copilot")}
                >
                  <Icon name="refresh" size="sm" />
                  <span>Switch</span>
                </button>
                <button
                  class="btn btn-ghost btn-sm oauth-action-btn oauth-disconnect-btn"
                  aria-label="Disconnect GitHub Copilot"
                  title="Disconnect account (@{copilotAccount})"
                  onclick={() => handleDisconnect("copilot", "GitHub Copilot")}
                >
                  <Icon name="trash" size="sm" />
                  <span>Disconnect</span>
                </button>
              </div>
            {:else}
              <button
                class="btn btn-primary btn-sm oauth-action-btn"
                aria-label="Connect Copilot"
                title="Connect GitHub Copilot"
                onclick={() => (oauthModal = "copilot")}
              >
                Connect
              </button>
            {/if}
          </div>
        </div>

        <!-- OpenRouter Row -->
        <div class="oauth-card" class:is-connected={Boolean(openrouterAccount)}>
          <div class="oauth-card-left">
            <div class="oauth-icon-badge brand-openrouter" aria-hidden="true">
              <Icon name="openrouter" size="sm" />
            </div>
            <div class="oauth-meta">
              <div class="oauth-name-row">
                <span class="oauth-name">OpenRouter</span>
                {#if openrouterAccount}
                  <span class="oauth-status-badge connected" title="Connected: {openrouterAccount}">
                    <span class="status-indicator-dot"></span>
                    <span>Active</span>
                  </span>
                {:else}
                  <span class="oauth-status-badge disconnected">
                    <span>Not linked</span>
                  </span>
                {/if}
              </div>
              <div class="oauth-detail-row" title={openrouterAccount || "Multi-model PKCE browser authorization"}>
                {#if openrouterAccount}
                  <span class="oauth-account-id">{openrouterAccount}</span>
                {:else}
                  <span class="oauth-hint-text">Unified catalog &bull; PKCE login</span>
                {/if}
              </div>
            </div>
          </div>
          <div class="oauth-card-right">
            {#if openrouterAccount}
              <div class="oauth-btn-group">
                <button
                  class="btn btn-ghost btn-sm oauth-action-btn"
                  aria-label="Switch OpenRouter"
                  title="Switch key (currently {openrouterAccount})"
                  onclick={() => (oauthModal = "openrouter")}
                >
                  <Icon name="refresh" size="sm" />
                  <span>Switch</span>
                </button>
                <button
                  class="btn btn-ghost btn-sm oauth-action-btn oauth-disconnect-btn"
                  aria-label="Disconnect OpenRouter"
                  title="Disconnect OpenRouter"
                  onclick={() => handleDisconnect("openrouter", "OpenRouter")}
                >
                  <Icon name="trash" size="sm" />
                  <span>Disconnect</span>
                </button>
              </div>
            {:else}
              <button
                class="btn btn-primary btn-sm oauth-action-btn"
                aria-label="Connect OpenRouter"
                title="Connect OpenRouter"
                onclick={() => (oauthModal = "openrouter")}
              >
                Connect
              </button>
            {/if}
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom Section: API Providers & Models -->
    <div class="section-block custom-section">
      <div class="section-header split">
        <div class="section-title-wrap">
          <h3 class="section-title">API Providers</h3>
        </div>
        <button
          class="btn {adding ? 'btn-secondary' : 'btn-outline'} btn-sm add-custom-btn"
          onclick={() => {
            adding = !adding;
            editing = null;
          }}
        >
          <Icon name={adding ? "close" : "plus"} size="sm" />
          <span>{adding ? "Cancel" : "Add Provider"}</span>
        </button>
      </div>

      {#if adding}
        <div class="edit-pane add-pane">
          <ProviderForm ondone={() => (adding = false)} />
        </div>
      {/if}

      {#if providers.loading}
        <p class="muted">Loading…</p>
      {:else if providers.list.length === 0}
        <div class="empty-state">
          <p class="muted">No API providers configured yet. Connect a subscription above or click <strong>Add Provider</strong>.</p>
        </div>
      {:else}
        <ul class="provider-list">
          {#each sortedProviders as p (p.provider)}
            <li class="provider-row" class:active={providers.active === p.provider}>
              <div class="row-main">
                <button
                  class="provider-item"
                  class:active={providers.active === p.provider}
                  class:open={editing === p.provider}
                  aria-expanded={editing === p.provider}
                  onclick={() => toggleEdit(p.provider)}
                >
                  <Icon
                    name={editing === p.provider ? "chevron-down" : "chevron-right"}
                    size="sm"
                  />
                  <span class="pname" title={providers.oauthAccountFor(p.provider) ?? undefined}
                    >{providerDisplayName(p.provider, p.label)}{#if providers.oauthAccountFor(p.provider)} (OAuth){/if}</span
                  >
                  {#if providers.isVerified(p.provider) || providers.oauthAccountFor(p.provider)}
                    <span
                      class="verified"
                      title={providers.oauthAccountFor(p.provider)
                        ? `OAuth connected: ${providers.oauthAccountFor(p.provider)}`
                        : "Models discovered"}
                    ></span>
                  {/if}
                </button>
                <div class="row-actions">
                  <button class="btn btn-ghost btn-sm" title="Select & discover models" onclick={() => selectProvider(p.provider)}>
                    <Icon name="refresh" size="sm" />
                  </button>
                  <button class="btn btn-ghost btn-sm danger" title="Remove" onclick={() => remove(p.provider)}>
                    <Icon name="trash" size="sm" />
                  </button>
                </div>
              </div>
              {#if editing === p.provider}
                <div class="edit-pane">
                  <details class="settings-details" open>
                    <summary>Settings</summary>
                    <ProviderForm initialProvider={p.provider} ondone={() => (editing = null)} />
                  </details>
                  {#if providers.isVerified(p.provider) && providers.active === p.provider}
                    <details class="settings-details" open>
                      <summary>Models</summary>
                      <ModelSelector />
                    </details>
                  {/if}
                </div>
              {/if}
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  </div>

  <!-- Bottom Foldable Favorite Models Section -->
  <div class="p-foot-favorites">
    <div class="fav-head">
      <button
        type="button"
        class="fav-toggle-main"
        onclick={() => (favoritesOpen = !favoritesOpen)}
        aria-expanded={favoritesOpen}
        title="Toggle favorite models list"
      >
        <span class="fav-star-icon">
          <Icon name="star" size="sm" />
        </span>
        <span class="fav-title">Favorite Models</span>
        {#if models.favorites.length > 0}
          <span class="count-pill">{models.favorites.length}</span>
        {/if}
      </button>
      <div class="fav-toggle-right">
        {#if models.favorites.length > 0}
          <button
            type="button"
            class="fav-select-all-btn"
            onclick={toggleAllFavorites}
          >
            {allFavoritesSelected ? "Unselect all" : "Select all"}
          </button>
        {/if}
        <button
          type="button"
          class="btn btn-ghost btn-sm fav-chevron-btn"
          onclick={() => (favoritesOpen = !favoritesOpen)}
          aria-label={favoritesOpen ? "Collapse favorites" : "Unfold favorites"}
        >
          <Icon name={favoritesOpen ? "chevron-down" : "chevron-up"} size="sm" />
        </button>
      </div>
    </div>

    {#if favoritesOpen}
      <div class="fav-content">
        {#if models.favorites.length === 0}
          <p class="fav-empty">
            Click the <span class="star-hint">★</span> star icon next to any model above to add it to your favorites.
          </p>
        {:else}
          <div class="fav-list">
            {#each models.favorites as key (key)}
              {@const { provider, model } = splitModelKey(key)}
              {@const p = providers.find(provider)}
              {@const provLabel = p ? providerDisplayName(provider, p.label) : provider}
              {@const isSelected = models.isSelected(key)}
              <div class="fav-row" class:selected={isSelected}>
                <button
                  type="button"
                  class="fav-star-action active"
                  title="Remove from favorites"
                  aria-label="Remove {model} from favorites"
                  onclick={() => models.toggleFavorite(key)}
                >
                  <Icon name="star" size="sm" />
                </button>
                <button
                  type="button"
                  class="fav-chip-btn"
                  onclick={() => models.toggle(key)}
                  title={key}
                >
                  <span class="fav-mname">{model}</span>
                  <span class="fav-pname" title="Provider: {provLabel}">{provLabel}</span>
                </button>
                <input
                  type="checkbox"
                  class="fav-check"
                  checked={isSelected}
                  onchange={() => models.toggle(key)}
                  aria-label="Select {model}"
                />
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/if}
  </div>
</aside>

{#if oauthModal}
  <OAuthModal provider={oauthModal} onclose={() => (oauthModal = null)} />
{/if}

<style>
  .backdrop {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 40;
  }
  .panel {
    position: absolute;
    top: 0;
    bottom: 0;
    right: 0;
    height: 100%;
    width: 380px;
    max-width: 95vw;
    background: var(--bg-secondary);
    border-left: 1px solid var(--border);
    box-shadow: var(--shadow-md);
    transform: translateX(100%);
    transition: transform var(--transition), visibility var(--transition);
    z-index: 50;
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
    pointer-events: none;
    visibility: hidden;
  }
  .panel.open {
    transform: translateX(0);
    pointer-events: auto;
    visibility: visible;
  }
  .panel:not(.open) .resizer-left {
    display: none;
  }
  .resizer-left {
    position: absolute;
    top: 0;
    left: -8px;
    width: 16px;
    height: 100%;
    cursor: col-resize;
    z-index: 70;
    background: transparent;
    display: flex;
    justify-content: center;
    touch-action: none;
  }
  .resizer-left::after {
    content: "";
    width: 3px;
    height: 100%;
    background: transparent;
    transition: background 0.15s ease;
  }
  .resizer-left:hover::after,
  .resizer-left.dragging::after {
    background: var(--accent);
    opacity: 0.9;
  }
  @media (max-width: 768px) {
    .panel {
      width: 100vw;
      max-width: 100vw;
    }
  }
  .p-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 14px 8px;
    border-bottom: 1px solid var(--border);
  }
  .p-head h2 {
    margin: 0;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-tertiary);
  }
  .p-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 10px;
  }
  /* Section layouts */
  .section-block {
    margin-bottom: 16px;
  }
  .oauth-section {
    padding-bottom: 14px;
    border-bottom: 1px solid var(--border);
  }
  .section-header {
    margin-bottom: 10px;
  }
  .section-header.split {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .section-title-wrap {
    min-width: 0;
  }
  .section-title {
    margin: 0;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-tertiary);
    line-height: 1.3;
  }
  .add-custom-btn {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    font-size: 11px;
  }

  /* OAuth Cards Stack: each in a row */
  .oauth-cards-stack {
    display: flex;
    flex-direction: column;
    gap: 7px;
  }
  .oauth-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 8px 10px;
    background: var(--bg-primary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    transition: all var(--transition);
  }
  .oauth-card:hover {
    border-color: var(--border-hover);
    background: var(--bg-tertiary);
  }
  .oauth-card.is-connected {
    border-color: rgba(43, 122, 77, 0.35);
    background: rgba(43, 122, 77, 0.04);
  }
  .oauth-card.is-connected:hover {
    border-color: rgba(43, 122, 77, 0.55);
  }

  .oauth-card-left {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
    flex: 1;
  }
  .oauth-icon-badge {
    width: 30px;
    height: 30px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .oauth-icon-badge.brand-chatgpt {
    background: rgba(16, 163, 127, 0.12);
    color: #10a37f;
  }
  .oauth-icon-badge.brand-copilot {
    background: rgba(88, 101, 242, 0.12);
    color: #5865f2;
  }
  .oauth-icon-badge.brand-openrouter {
    background: rgba(99, 102, 241, 0.12);
    color: #6366f1;
  }

  .oauth-meta {
    min-width: 0;
    flex: 1;
  }
  .oauth-name-row {
    display: flex;
    align-items: center;
    gap: 6px;
    line-height: 1.2;
  }
  .oauth-name {
    font-size: 12.5px;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
  }
  .oauth-status-badge {
    font-size: 10px;
    font-weight: 500;
    padding: 1px 5px;
    border-radius: 4px;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    line-height: 1;
  }
  .oauth-status-badge.connected {
    color: #34d399;
    background: rgba(16, 185, 129, 0.12);
  }
  .oauth-status-badge.disconnected {
    color: var(--text-tertiary);
    background: rgba(255, 255, 255, 0.05);
  }
  .status-indicator-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #10b981;
    display: inline-block;
  }

  .oauth-detail-row {
    font-size: 11px;
    color: var(--text-secondary);
    margin-top: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .oauth-account-id {
    color: var(--text-primary);
    font-family: var(--font-mono);
    font-size: 10.5px;
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .oauth-hint-text {
    color: var(--text-tertiary);
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .oauth-card-right {
    flex-shrink: 0;
    display: flex;
    align-items: center;
  }
  .oauth-btn-group {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
  .oauth-action-btn {
    font-size: 11px;
    padding: 2px 8px;
    height: 24px;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    white-space: nowrap;
    transition: all var(--transition);
  }
  .oauth-disconnect-btn {
    color: var(--text-tertiary);
  }
  .oauth-disconnect-btn:hover {
    color: var(--danger, #ef4444);
    border-color: rgba(239, 68, 68, 0.4);
    background: rgba(239, 68, 68, 0.08);
  }

  .add-pane {
    margin-bottom: 10px;
  }
  .empty-state {
    padding: 12px 6px;
    color: var(--text-secondary);
  }
  .edit-pane {
    padding: 8px 8px 14px;
    border-bottom: 1px solid var(--border);
  }
  .provider-list {
    list-style: none;
    margin: 0;
    padding: 6px;
  }
  .provider-row {
    border-radius: var(--radius);
  }
  .provider-row.active {
    background: var(--bg-tertiary);
  }
  .row-main {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .provider-item {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 9px 10px;
    border: none;
    background: none;
    color: var(--text-primary);
    border-radius: var(--radius);
    text-align: left;
    font-size: 13px;
  }
  .provider-item:hover {
    background: var(--bg-tertiary);
  }
  .provider-item.active {
    color: var(--accent);
  }
  .pname {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    text-transform: capitalize;
  }
  .verified {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--success);
  }
  .row-actions {
    display: flex;
    gap: 2px;
    flex-shrink: 0;
  }
  .btn.danger {
    color: var(--error);
  }
  .muted {
    color: var(--text-tertiary);
    font-size: 12px;
    padding: 10px 14px;
    list-style: none;
  }
  .settings-details {
    border-top: 1px solid var(--border);
    padding-top: 8px;
    margin-bottom: 12px;
  }
  .settings-details summary {
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 4px 0;
  }

  /* Bottom Foldable Favorite Models Drawer */
  .p-foot-favorites {
    flex-shrink: 0;
    border-top: 1px solid var(--border);
    background: var(--bg-primary);
    display: flex;
    flex-direction: column;
    max-height: 48vh;
  }
  .fav-head {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    box-sizing: border-box;
  }
  .fav-toggle-main {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 8px;
    background: none;
    border: none;
    cursor: pointer;
    padding: 2px 0;
    text-align: left;
  }
  .fav-star-icon {
    color: #f59e0b;
    display: inline-flex;
    align-items: center;
  }
  .fav-star-icon :global(svg) {
    fill: #f59e0b;
    stroke: #f59e0b;
  }
  .fav-title {
    font-size: 12.5px;
    font-weight: 700;
    color: var(--text-primary);
  }
  .count-pill {
    font-size: 11px;
    color: var(--text-tertiary);
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 1px 7px;
  }
  .fav-toggle-right {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .fav-select-all-btn {
    background: none;
    border: none;
    padding: 2px 6px;
    font-size: 11px;
    color: var(--accent);
    cursor: pointer;
    border-radius: var(--radius);
  }
  .fav-select-all-btn:hover {
    text-decoration: underline;
  }
  .fav-chevron-btn {
    padding: 4px;
    color: var(--text-tertiary);
  }
  .fav-content {
    overflow-y: auto;
    max-height: 38vh;
    padding: 4px 10px 12px;
    border-top: 1px solid var(--border);
  }
  .fav-empty {
    margin: 8px 0;
    font-size: 12px;
    color: var(--text-tertiary);
    line-height: 1.4;
    text-align: center;
    padding: 8px 12px;
    background: var(--bg-tertiary);
    border-radius: var(--radius);
  }
  .star-hint {
    color: #f59e0b;
    font-size: 14px;
  }
  .fav-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-top: 4px;
  }
  .fav-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 8px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    transition: border-color var(--transition), background var(--transition);
  }
  .fav-row:hover {
    border-color: var(--border-hover);
  }
  .fav-row.selected {
    border-color: var(--accent);
    background: var(--bg-tertiary);
  }
  .fav-star-action {
    background: transparent;
    border: none;
    padding: 2px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: #f59e0b;
    border-radius: var(--radius);
    flex-shrink: 0;
    transition: transform var(--transition);
  }
  .fav-star-action :global(svg) {
    fill: #f59e0b;
    stroke: #f59e0b;
  }
  .fav-star-action:hover {
    transform: scale(1.2);
  }
  .fav-chip-btn {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    background: none;
    border: none;
    padding: 0;
    color: var(--text-primary);
    font-size: 12.5px;
    text-align: left;
    cursor: pointer;
  }
  .fav-mname {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 500;
  }
  .fav-pname {
    font-size: 10.5px;
    color: var(--text-tertiary);
    background: var(--bg-primary);
    border: 1px solid var(--border);
    padding: 1px 6px;
    border-radius: 4px;
    white-space: nowrap;
    flex-shrink: 0;
    opacity: 0.9;
  }
  .fav-check {
    accent-color: var(--accent);
    cursor: pointer;
    margin: 0;
    flex-shrink: 0;
  }
</style>

