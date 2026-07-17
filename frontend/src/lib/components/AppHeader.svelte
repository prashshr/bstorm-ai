<script lang="ts">
  import { theme } from "../stores/theme.svelte";
  import { discussion } from "../stores/discussion.svelte";
  import Icon from "./Icon.svelte";
  import ProgressStepper from "./ProgressStepper.svelte";

  interface Props {
    onTogglePanel: () => void;
    onToggleSessions?: () => void;
  }
  let { onTogglePanel, onToggleSessions }: Props = $props();
</script>

<header class="app-header">
  <div class="left">
    <button
      class="btn btn-ghost btn-sm icon-btn burger"
      onclick={() => onToggleSessions?.()}
      aria-label="Toggle chat list"
    >
      <Icon name="menu" />
    </button>
    <button
      class="btn btn-ghost btn-sm icon-btn"
      onclick={() => theme.toggle()}
      aria-label="Toggle theme"
    >
      <Icon name={theme.theme === "dark" ? "sun" : "moon"} />
    </button>
  </div>

  <div class="title-wrap">
    <button class="title" onclick={() => discussion.reset()} aria-label="New chat">
      <span class="logo" aria-hidden="true"></span>
      AI-Ensemble
    </button>
  </div>

  <div class="right">
    {#if discussion.running}
      <ProgressStepper compact />
    {/if}
    <button
      class="providers-btn"
      onclick={onTogglePanel}
      aria-label="Toggle providers panel"
    >
      <Icon name="panel" />
      <span>Providers</span>
    </button>
  </div>
</header>

<style>
  .app-header {
    position: relative;
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
    position: relative;
    z-index: 2;
  }
  .right {
    justify-content: flex-end;
  }
  .title-wrap {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    bottom: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    pointer-events: none;
    z-index: 1;
  }
  .title-wrap .title {
    pointer-events: auto;
  }
  .logo {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    border: 4px solid var(--accent);
    position: relative;
    flex-shrink: 0;
  }
  .logo::after {
    content: "";
    position: absolute;
    inset: 5px;
    background: var(--accent);
    border-radius: 50%;
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
  .icon-btn {
    padding: 6px;
  }
  .providers-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    height: 32px;
    padding: 0 12px;
    background: none;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-secondary);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: background var(--transition), color var(--transition), border-color var(--transition);
  }
  .providers-btn:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border-color: var(--accent);
  }
  .burger {
    display: none;
  }
  @media (max-width: 768px) {
    .burger {
      display: inline-flex;
    }
    .providers-btn span {
      display: none;
    }
    .providers-btn {
      padding: 0 10px;
    }
    .title {
      font-size: 22px;
      gap: 8px;
    }
    .logo {
      width: 26px;
      height: 26px;
      border-width: 3px;
    }
  }
</style>
