<script lang="ts">
  import { personas } from "../stores/personas.svelte";
  import { models } from "../stores/models.svelte";
  import type { AgentPersona } from "../api/types";
  import Icon from "./Icon.svelte";

  interface Props {
    initialPersona?: AgentPersona;
    ondone?: () => void;
  }
  let { initialPersona, ondone }: Props = $props();

  let name = $state(initialPersona?.name ?? "");
  let roleDescription = $state(initialPersona?.role_description ?? "");
  let systemPrompt = $state(initialPersona?.system_prompt ?? "");
  let model = $state(initialPersona?.model ?? (models.all[0] ?? ""));
  let avatar = $state(initialPersona?.avatar ?? "🤖");
  let saving = $state(false);

  const AVATAR_PRESETS = ["🤖", "🛡️", "⚡", "🧠", "🔍", "💻", "🔬", "⚖️", "🎨", "🚀"];

  async function save() {
    if (!name.trim() || !model.trim() || saving) return;
    saving = true;
    try {
      if (initialPersona) {
        await personas.update(initialPersona.id, {
          name: name.trim(),
          role_description: roleDescription.trim(),
          system_prompt: systemPrompt.trim(),
          model: model.trim(),
          avatar: avatar.trim() || "🤖",
        });
      } else {
        await personas.create({
          name: name.trim(),
          role_description: roleDescription.trim(),
          system_prompt: systemPrompt.trim(),
          model: model.trim(),
          avatar: avatar.trim() || "🤖",
        });
      }
      ondone?.();
    } finally {
      saving = false;
    }
  }
</script>

<form class="persona-form" onsubmit={(e) => { e.preventDefault(); save(); }}>
  <div class="field">
    <label for="pf-avatar">Avatar Icon</label>
    <div class="avatar-presets">
      {#each AVATAR_PRESETS as a (a)}
        <button
          type="button"
          class="avatar-chip"
          class:selected={avatar === a}
          onclick={() => (avatar = a)}
        >{a}</button>
      {/each}
      <input id="pf-avatar" class="avatar-input" bind:value={avatar} maxlength="4" placeholder="Custom" />
    </div>
  </div>

  <div class="field">
    <label for="pf-name">Agent Name *</label>
    <input id="pf-name" bind:value={name} placeholder="E.g. Security Auditor, System Architect" required />
  </div>

  <div class="field">
    <label for="pf-role">Role Description</label>
    <input id="pf-role" bind:value={roleDescription} placeholder="E.g. OWASP & Vulnerability Expert" />
  </div>

  <div class="field">
    <label for="pf-model">Assigned Model Provider *</label>
    <select id="pf-model" bind:value={model} required>
      <option value="" disabled>Select model…</option>
      {#each models.all as m (m)}
        <option value={m}>{m}</option>
      {/each}
    </select>
  </div>

  <div class="field">
    <label for="pf-prompt">Agent System Prompt / Role Instructions</label>
    <textarea
      id="pf-prompt"
      rows="3"
      bind:value={systemPrompt}
      placeholder="E.g. You are a senior security auditor. Critique all architecture proposals for security vulnerabilities…"
    ></textarea>
  </div>

  <div class="form-actions">
    <button type="submit" class="btn btn-primary" disabled={saving || !name.trim() || !model.trim()}>
      <Icon name="check" size="sm" />
      {initialPersona ? "Update Persona" : "Create Persona"}
    </button>
  </div>
</form>

<style>
  .persona-form {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 10px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .field label {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-tertiary);
  }
  .avatar-presets {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }
  .avatar-chip {
    width: 32px;
    height: 32px;
    border-radius: var(--radius);
    border: 1px solid var(--border);
    background: var(--bg-secondary);
    font-size: 16px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  .avatar-chip.selected {
    border-color: var(--accent);
    background: color-mix(in srgb, var(--accent) 20%, var(--bg-secondary));
  }
  .avatar-input {
    width: 60px;
    text-align: center;
    font-size: 14px;
  }
  .form-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 4px;
  }
</style>
