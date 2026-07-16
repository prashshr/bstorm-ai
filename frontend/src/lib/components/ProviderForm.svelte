<script lang="ts">
  import { providers } from "../stores/providers.svelte";
  import { models } from "../stores/models.svelte";
  import { PROVIDER_PRESETS } from "../utils/helpers";
  import Icon from "./Icon.svelte";

  interface Props {
    initialProvider?: string;
    ondone?: () => void;
  }
  let { initialProvider = "", ondone }: Props = $props();

  const presetOptions = [...PROVIDER_PRESETS].sort((a, b) => {
    if (a.key === "custom") return 1;
    if (b.key === "custom") return -1;
    return 0;
  });

  let presetKey = $state(initialProvider || "openrouter");
  let apiKey = $state("");
  let endpoint = $state(
    PROVIDER_PRESETS.find((p) => p.key === (initialProvider || "openrouter"))
      ?.endpoint ?? "",
  );
  let showKey = $state(false);
  let saving = $state(false);
  let message = $state<{ type: "ok" | "err"; text: string } | null>(null);

  function onPresetChange() {
    const preset = PROVIDER_PRESETS.find((p) => p.key === presetKey);
    if (preset && preset.key !== "custom") endpoint = preset.endpoint;
  }

  async function save() {
    if (!apiKey.trim()) {
      message = { type: "err", text: "API key is required" };
      return;
    }
    saving = true;
    message = null;
    const ok = await providers.save(presetKey, apiKey, endpoint);
    if (ok) {
      try {
        await models.discover(presetKey);
        message = { type: "ok", text: "Saved and verified" };
      } catch {
        message = {
          type: "err",
          text: "Saved, but model discovery failed. Check the key/endpoint.",
        };
      }
      apiKey = "";
      ondone?.();
    } else {
      message = { type: "err", text: "Failed to save provider" };
    }
    saving = false;
  }
</script>

<div class="provider-form">
  <label for="pf-preset">Provider</label>
  <select id="pf-preset" bind:value={presetKey} onchange={onPresetChange}>
    {#each presetOptions as preset (preset.key)}
      <option value={preset.key}>{preset.name}</option>
    {/each}
  </select>

  <label for="pf-endpoint">Endpoint</label>
  <input
    id="pf-endpoint"
    type="url"
    bind:value={endpoint}
    placeholder="https://api.example.com/v1"
  />

  <label for="pf-key">API Key</label>
  <div class="key-row">
    {#if showKey}
      <input id="pf-key" type="text" bind:value={apiKey} placeholder="sk-…" />
    {:else}
      <input
        id="pf-key"
        type="password"
        bind:value={apiKey}
        placeholder="sk-…"
      />
    {/if}
    <button
      type="button"
      class="btn btn-ghost btn-sm"
      onclick={() => (showKey = !showKey)}
      aria-label={showKey ? "Hide key" : "Show key"}
    >
      <Icon name={showKey ? "eye-off" : "eye"} size="sm" />
    </button>
  </div>

  {#if message}
    <div class="msg {message.type}" role="status">{message.text}</div>
  {/if}

  <div class="actions">
    <button class="btn btn-primary btn-sm" onclick={save} disabled={saving}>
      <Icon name="save" size="sm" />
      {saving ? "Saving…" : "Save & Discover"}
    </button>
  </div>
</div>

<style>
  .provider-form {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .provider-form label {
    margin-top: 10px;
  }
  .key-row {
    display: flex;
    gap: 6px;
  }
  .key-row input {
    flex: 1;
  }
  .actions {
    margin-top: 14px;
  }
  .msg {
    margin-top: 10px;
    padding: 6px 10px;
    border-radius: var(--radius);
    font-size: 12px;
  }
  .msg.ok {
    background: var(--success-bg);
    color: var(--success);
  }
  .msg.err {
    background: var(--error-bg);
    color: var(--error);
  }
</style>
