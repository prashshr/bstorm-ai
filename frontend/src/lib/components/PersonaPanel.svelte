<script lang="ts">
  import { personas } from "../stores/personas.svelte";
  import type { AgentPersona } from "../api/types";
  import Icon from "./Icon.svelte";
  import PersonaForm from "./PersonaForm.svelte";

  interface Props {
    open: boolean;
    onclose: () => void;
  }
  let { open, onclose }: Props = $props();

  let adding = $state(false);
  let editingPersona = $state<AgentPersona | null>(null);

  async function remove(p: AgentPersona) {
    if (confirm(`Delete persona "${p.name}"?`)) {
      await personas.remove(p.id);
      if (editingPersona?.id === p.id) editingPersona = null;
    }
  }
</script>

{#if open}
  <div class="backdrop" role="presentation" onclick={onclose}></div>
{/if}

<aside class="panel" class:open aria-hidden={!open}>
  <div class="p-head">
    <h2>Custom Agent Personas</h2>
    <button class="btn btn-ghost icon-btn" onclick={onclose} aria-label="Close panel">
      <Icon name="close" size="sm" />
    </button>
  </div>

  <div class="p-body">
    <div class="p-head-actions">
      <button
        class="btn btn-primary btn-sm"
        onclick={() => {
          adding = !adding;
          editingPersona = null;
        }}
      >
        <Icon name="plus" size="sm" /> Create Persona
      </button>
    </div>

    {#if adding}
      <div class="edit-pane">
        <PersonaForm ondone={() => (adding = false)} />
      </div>
    {/if}

    {#if personas.loading}
      <p class="muted">Loading personas…</p>
    {:else if personas.list.length === 0}
      <p class="muted">No custom agent personas yet. Click Create to make your first specialist agent.</p>
    {:else}
      <ul class="persona-list">
        {#each personas.list as p (p.id)}
          <li class="persona-row">
            <div class="row-main">
              <span class="avatar-badge">{p.avatar || "🤖"}</span>
              <div class="info">
                <span class="pname">{p.name}</span>
                {#if p.role_description}
                  <span class="prole">{p.role_description}</span>
                {/if}
              </div>
              <div class="row-actions">
                <button
                  class="btn btn-ghost btn-sm"
                  title="Edit persona"
                  onclick={() => {
                    editingPersona = editingPersona?.id === p.id ? null : p;
                    adding = false;
                  }}
                >
                  <Icon name="settings" size="sm" />
                </button>
                <button class="btn btn-ghost btn-sm danger" title="Delete" onclick={() => remove(p)}>
                  <Icon name="trash" size="sm" />
                </button>
              </div>
            </div>

            {#if editingPersona?.id === p.id}
              <div class="edit-pane">
                <PersonaForm initialPersona={p} ondone={() => (editingPersona = null)} />
              </div>
            {/if}
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</aside>

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
    width: 320px;
    max-width: 90vw;
    background: var(--bg-secondary);
    border-left: 1px solid var(--border);
    box-shadow: var(--shadow-md);
    transform: translateX(100%);
    transition: transform var(--transition);
    z-index: 50;
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
  }
  .panel.open {
    transform: translateX(0);
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
  .p-head-actions {
    margin-bottom: 10px;
  }
  .p-head-actions .btn {
    width: 100%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }
  .persona-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .persona-row {
    border-radius: var(--radius);
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    padding: 8px 10px;
  }
  .row-main {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .avatar-badge {
    font-size: 18px;
    flex-shrink: 0;
  }
  .info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .pname {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .prole {
    font-size: 11px;
    color: var(--text-tertiary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .row-actions {
    display: flex;
    gap: 2px;
    flex-shrink: 0;
  }
  .danger {
    color: var(--error);
  }
  .edit-pane {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid var(--border);
  }
  .muted {
    color: var(--text-tertiary);
    font-size: 12px;
    padding: 10px;
  }
</style>
