<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import { api } from "../api/client";
  import { providers } from "../stores/providers.svelte";
  import { models } from "../stores/models.svelte";
  import { copyToClipboard } from "../utils/helpers";
  import Icon from "./Icon.svelte";

  interface Props {
    provider: "codex" | "copilot" | "openrouter";
    onclose: () => void;
  }
  let { provider, onclose }: Props = $props();

  const POLL_INTERVAL_MS = 3000;
  const POLL_TIMEOUT_MS = 15 * 60 * 1000;

  let title = $derived(
    provider === "codex"
      ? "Connect ChatGPT"
      : provider === "copilot"
        ? "Connect GitHub Copilot"
        : "Connect OpenRouter"
  );
  // Model-discovery key after a successful connect.
  let discoverKey = $derived(
    provider === "codex" ? "codex" : provider === "copilot" ? "copilot" : "openrouter"
  );

  let loading = $state(true);
  let error = $state("");
  let verificationUrl = $state("");
  let userCode = $state("");
  let expiresIn = $state(0);
  let authUrl = $state("");
  let popupBlocked = $state(false);
  let success = $state(false);
  let account = $state("");
  let copied = $state(false);

  // Memory only — never persisted.
  let pollToken: string | null = null;
  let pollTimer: ReturnType<typeof setInterval> | null = null;
  let polling = false;
  let deadline = 0;
  let popup: Window | null = null;
  let destroyed = false;
  let listening = false;

  function stopPolling(): void {
    if (pollTimer !== null) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function closePopup(): void {
    try {
      popup?.close();
    } catch {
      /* ignore */
    }
    popup = null;
  }

  async function handleOk(resAccount?: string): Promise<void> {
    if (destroyed || success) return;
    stopPolling();
    success = true;
    if (resAccount) account = resAccount;
    closePopup();
    try {
      await providers.load();
      await providers.loadOAuth();
      const acc =
        providers.oauthAccountFor(discoverKey) ??
        providers.oauthAccountFor(provider);
      if (acc) account = acc;
    } catch {
      /* stores log internally */
    }
    try {
      await models.discover(discoverKey);
    } catch {
      /* handled in store */
    }
  }

  async function pollOnce(): Promise<void> {
    if (polling || !pollToken || destroyed || success) return;
    if (Date.now() > deadline) {
      stopPolling();
      error = "Connection timed out. Please try again.";
      loading = false;
      return;
    }
    polling = true;
    try {
      const res = await api.oauthPoll(provider, pollToken);
      if (destroyed || success) return;
      if (res.status === "ok") {
        await handleOk(res.account);
      } else if (res.status === "error") {
        stopPolling();
        error = res.error || "Connection failed. Please try again.";
        loading = false;
      }
      // "pending" -> keep polling silently until the deadline.
    } catch {
      /* transient poll errors: keep polling until the deadline */
    } finally {
      polling = false;
    }
  }

  function startPolling(): void {
    stopPolling();
    deadline = Date.now() + POLL_TIMEOUT_MS;
    pollTimer = setInterval(() => {
      void pollOnce();
    }, POLL_INTERVAL_MS);
  }

  function openPopup(url: string): void {
    try {
      popup = window.open(url, "_blank", "width=480,height=640");
    } catch {
      popup = null;
    }
    popupBlocked = !popup || popup.closed;
  }

  function onMessage(ev: MessageEvent): void {
    const data = ev.data as {
      provider?: string;
      ok?: boolean;
      account?: string;
    } | null;
    if (!data || typeof data !== "object") return;
    if (data.provider !== provider) return;
    if (data.ok) {
      void handleOk(data.account);
    }
  }

  async function start(): Promise<void> {
    loading = true;
    error = "";
    success = false;
    try {
      const res = await api.oauthStart(provider);
      if (destroyed) return;
      if ((provider === "codex" || provider === "copilot") && "verification_url" in res) {
        verificationUrl = res.verification_url;
        userCode = res.user_code;
        expiresIn = res.expires_in;
        pollToken = res.poll_token;
      } else if (provider === "openrouter" && "auth_url" in res) {
        authUrl = res.auth_url;
        pollToken = res.poll_token;
        openPopup(authUrl);
        if (!listening) {
          window.addEventListener("message", onMessage);
          listening = true;
        }
      } else {
        throw new Error("Unexpected response from server");
      }
      loading = false;
      startPolling();
    } catch (e) {
      if (destroyed) return;
      error = e instanceof Error ? e.message : String(e);
      loading = false;
    }
  }

  function retry(): void {
    stopPolling();
    verificationUrl = "";
    userCode = "";
    expiresIn = 0;
    authUrl = "";
    popupBlocked = false;
    pollToken = null;
    void start();
  }

  async function copyCode(): Promise<void> {
    if (await copyToClipboard(userCode)) {
      copied = true;
      setTimeout(() => (copied = false), 1500);
    }
  }

  async function disconnect(): Promise<void> {
    try {
      await api.oauthDisconnect(provider);
    } catch {
      /* surface via reload below regardless */
    }
    await providers.loadOAuth();
    onclose();
  }

  onMount(() => {
    void start();
  });
  onDestroy(() => {
    destroyed = true;
    stopPolling();
    if (listening) {
      window.removeEventListener("message", onMessage);
      listening = false;
    }
  });
</script>

<div class="modal-backdrop" onclick={onclose} aria-hidden="true"></div>

<div class="modal-card" role="dialog" aria-label={title}>
  <div class="modal-header">
    <div class="title-row">
      <h2>{title}</h2>
    </div>
    <button class="btn btn-ghost btn-sm close-btn" onclick={onclose} aria-label="Close">
      <Icon name="close" size="sm" />
    </button>
  </div>

  <div class="modal-body">
    {#if loading && !verificationUrl && !authUrl}
      <p class="hint">Starting connection…</p>
    {:else if success}
      <span class="badge badge-ok">Connected{#if account} · {account}{/if}</span>
      <p class="hint">Provider connected successfully. Models have been refreshed.</p>
      <div class="row">
        <button class="btn btn-ghost btn-sm" onclick={disconnect}>Disconnect</button>
        <button class="btn btn-primary btn-sm" onclick={onclose}>Close</button>
      </div>
    {:else if provider === "codex" || provider === "copilot"}
      <p class="hint">Open the verification page and enter this code:</p>
      <div class="user-code">{userCode}</div>
      <div class="row">
        <button class="btn btn-ghost btn-sm" onclick={copyCode}>
          <Icon name={copied ? "check" : "copy"} size="sm" />
          {copied ? "Copied" : "Copy"}
        </button>
        <a class="btn btn-ghost btn-sm" href={verificationUrl} target="_blank" rel="noreferrer">Open link</a>
        <button class="btn btn-primary btn-sm" onclick={() => openPopup(verificationUrl)}>
          Open verification page
        </button>
      </div>
      {#if expiresIn > 0}
        <p class="hint">Code expires in {Math.max(1, Math.round(expiresIn / 60))} min. Waiting for approval…</p>
      {:else}
        <p class="hint">Waiting for approval…</p>
      {/if}
      <span class="badge badge-testing">Waiting</span>
      {#if popupBlocked}
        <p class="hint">Popup was blocked — use the link above.</p>
      {/if}
      {#if error}
        <p class="hint">{error}</p>
        <div class="row">
          <button class="btn btn-ghost btn-sm" onclick={retry}>Retry</button>
          <button class="btn btn-primary btn-sm" onclick={onclose}>Close</button>
        </div>
      {/if}
    {:else}
      <p class="hint">A sign-in popup was opened. Complete sign-in there; this dialog completes automatically.</p>
      <div class="row">
        <button class="btn btn-primary btn-sm" onclick={() => openPopup(authUrl)}>Reopen sign-in</button>
        <a class="btn btn-ghost btn-sm" href={authUrl} target="_blank" rel="noreferrer">Open link</a>
      </div>
      <span class="badge badge-testing">Waiting</span>
      {#if popupBlocked}
        <p class="hint">Popup was blocked — use the link above.</p>
      {/if}
      {#if error}
        <p class="hint">{error}</p>
        <div class="row">
          <button class="btn btn-ghost btn-sm" onclick={retry}>Retry</button>
          <button class="btn btn-primary btn-sm" onclick={onclose}>Close</button>
        </div>
      {/if}
    {/if}
  </div>
</div>

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.65);
    backdrop-filter: blur(4px);
    z-index: 100;
  }

  .modal-card {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: min(480px, 92vw);
    max-height: 85vh;
    overflow-y: auto;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
    z-index: 101;
    display: flex;
    flex-direction: column;
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 18px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-primary);
  }

  .title-row h2 {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .close-btn {
    padding: 4px;
  }

  .modal-body {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 18px;
  }

  .hint {
    margin: 0;
    font-size: 12px;
    color: var(--text-tertiary);
    line-height: 1.5;
    word-break: break-word;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .user-code {
    font-family: var(--font-mono);
    font-size: 28px;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-align: center;
    padding: 12px;
    background: var(--bg-primary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-primary);
  }
</style>
