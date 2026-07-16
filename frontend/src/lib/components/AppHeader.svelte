<script lang="ts">
  import { theme } from "../stores/theme.svelte";
  import { discussion } from "../stores/discussion.svelte";
  import Icon from "./Icon.svelte";
  import ProgressStepper from "./ProgressStepper.svelte";

  interface Props {
    onToggleSessions: () => void;
    onTogglePanel: () => void;
  }
  let { onToggleSessions, onTogglePanel }: Props = $props();
</script>

<header class="app-header">
  <div class="left">
    <button
      class="btn btn-ghost btn-sm icon-btn"
      onclick={onToggleSessions}
      aria-label="Toggle chat list"
    >
      <Icon name="menu" />
    </button>
  </div>

  <button class="title" onclick={() => discussion.reset()} aria-label="New chat">
    <span class="logo" aria-hidden="true"></span>
    AI-Ensemble
  </button>

  <div class="right">
    {#if discussion.running}
      <ProgressStepper compact />
    {/if}
    <button
      class="btn btn-ghost btn-sm icon-btn"
      onclick={() => theme.toggle()}
      aria-label="Toggle theme"
    >
      <Icon name={theme.theme === "dark" ? "sun" : "moon"} />
    </button>
    <button
      class="btn btn-ghost btn-sm icon-btn"
      onclick={onTogglePanel}
      aria-label="Toggle providers panel"
    >
      <Icon name="settings" />
    </button>
  </div>
</header>

<style>
  .app-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 14px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-secondary);
    gap: 12px;
    flex-shrink: 0;
  }
  .left,
  .right {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
  }
  .right {
    justify-content: flex-end;
  }
  .title {
    display: flex;
    align-items: center;
    gap: 12px;
    background: none;
    border: none;
    color: var(--text-primary);
    font-size: 32px;
    font-weight: 700;
  }
  .logo {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    border: 4px solid var(--accent);
    position: relative;
  }
  .logo::after {
    content: "";
    position: absolute;
    inset: 5px;
    background: var(--accent);
    border-radius: 50%;
  }
  .icon-btn {
    padding: 6px;
  }
</style>
