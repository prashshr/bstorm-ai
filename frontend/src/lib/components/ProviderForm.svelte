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
  let projectId = $state("");
  let region = $state("global");
  let adcJson = $state("");
  let showKey = $state(false);
  let saving = $state(false);
  let message = $state<{ type: "ok" | "err"; text: string } | null>(null);

  const isVertex = $derived(
    presetKey === "google-vertex" || presetKey === "vertex",
  );

  // Prefill project/region/adc when editing an existing provider.
  if (initialProvider) {
    const existing = providers.find(initialProvider);
    if (existing?.project_id) projectId = existing.project_id;
    if (existing?.region) region = existing.region;
  }

  function onPresetChange() {
    const preset = PROVIDER_PRESETS.find((p) => p.key === presetKey);
    if (preset && preset.key !== "custom") endpoint = preset.endpoint;
    if (isVertex) {
      projectId = "";
      region = "global";
      adcJson = "";
    }
  }

  async function save() {
    // Vertex uses Application Default Credentials (no static API key needed).
    if (!isVertex && !apiKey.trim()) {
      message = { type: "err", text: "API key is required" };
      return;
    }
    if (isVertex && !projectId.trim()) {
      message = { type: "err", text: "GCP Project ID is required for Vertex AI" };
      return;
    }
    if (adcJson.trim()) {
      try {
        JSON.parse(adcJson);
      } catch {
        message = {
          type: "err",
          text: "ADC credentials must be valid JSON (a service-account key or gcloud application_default_credentials.json).",
        };
        return;
      }
    }
    saving = true;
    message = null;
    const ok = await providers.save(presetKey, apiKey, endpoint, {
      project_id: isVertex ? projectId.trim() : "",
      region: isVertex ? region.trim() : "",
      adc_json: isVertex ? adcJson.trim() : "",
    });
    if (ok) {
      try {
        await models.discover(presetKey);
        message = { type: "ok", text: "Saved and verified" };
      } catch {
        message = {
          type: "err",
          text: "Saved, but model discovery failed. Check the project/region.",
        };
      }
      apiKey = "";
      projectId = "";
      adcJson = "";
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

  {#if isVertex}
    <label class="with-help" for="pf-project">
      GCP Project ID
      <span class="help" title="The Google Cloud project that has the Vertex AI API enabled. Find it in the GCP Console (Home → Project info), or run `gcloud config get-value project`. Your ADC identity must have the 'Vertex AI User' role on this project.">
        <Icon name="alert" size="sm" />
      </span>
    </label>
    <input
      id="pf-project"
      type="text"
      bind:value={projectId}
      placeholder="my-gcp-project"
    />

    <label class="with-help" for="pf-region">
      Region
      <span class="help" title="Vertex AI location. Use 'global' to auto-route, or a specific region such as us-east5, europe-west1, asia-southeast1. The model set available depends on the region your project is enabled in.">
        <Icon name="alert" size="sm" />
      </span>
    </label>
    <input
      id="pf-region"
      type="text"
      bind:value={region}
      placeholder="global"
    />

    <label class="with-help" for="pf-adc">
      ADC Credentials (JSON)
      <span class="help" title="Paste the contents of a Google Cloud service-account key JSON, or your gcloud application_default_credentials.json (typically at ~/.config/gcloud/application_default_credentials.json). This is stored encrypted per user and used to authenticate Vertex AI. A service-account key is durable; a gcloud user-ADC refresh token can expire or be revoked.">
        <Icon name="alert" size="sm" />
      </span>
    </label>
    <textarea
      id="pf-adc"
      rows="5"
      bind:value={adcJson}
      placeholder={'{ "type": "service_account", "project_id": "...", "private_key": "...", "client_email": "..." }'}
      spellcheck="false"
    ></textarea>

    <p class="vertex-note">
      Vertex AI authenticates via Application Default Credentials (ADC). Paste a
      service-account key JSON above (durable), or your gcloud
      <code>application_default_credentials.json</code> (may expire). If left
      empty, the backend uses environment-level ADC — no API key required.
    </p>
  {/if}

  <label for="pf-key">API Key</label>
  <div class="key-row">
    {#if showKey}
      <input id="pf-key" type="text" bind:value={apiKey} placeholder={isVertex ? "(optional)" : "sk-…"} disabled={isVertex} />
    {:else}
      <input
        id="pf-key"
        type="password"
        bind:value={apiKey}
        placeholder={isVertex ? "(optional)" : "sk-…"}
        disabled={isVertex}
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
  .with-help {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .help {
    display: inline-flex;
    color: var(--text-tertiary);
    cursor: help;
  }
  .help :global(svg) {
    width: 13px;
    height: 13px;
  }
  .vertex-note {
    margin: 6px 0 0;
    font-size: 12px;
    color: var(--text-tertiary);
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 8px 10px;
    line-height: 1.5;
  }
  .vertex-note code {
    font-family: var(--mono, monospace);
    font-size: 11px;
    color: var(--text-secondary);
  }
  textarea#pf-adc {
    resize: vertical;
    font-family: var(--mono, monospace);
    font-size: 11px;
    line-height: 1.4;
    min-height: 92px;
    width: 100%;
    box-sizing: border-box;
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
