<script lang="ts">
  import { auth } from "../stores/auth.svelte";
  import { theme } from "../stores/theme.svelte";
  import { nav } from "../stores/nav.svelte";
  import { discussion } from "../stores/discussion.svelte";
  import Icon from "./Icon.svelte";
  import ProgressStepper from "./ProgressStepper.svelte";

  function logout() {
    auth.logout();
  }
</script>

<header class="app-header">
  <div class="left">
    <button
      class="btn btn-ghost btn-sm icon-btn"
      onclick={() => nav.toggleSidebar()}
      aria-label="Toggle sidebar"
    >
      <Icon name="menu" />
    </button>
    <span class="user" data-testid="user-display" title={auth.user ?? ""}>
      {auth.user ?? "user"}
    </span>
    <button class="btn btn-ghost btn-sm" onclick={logout}>
      <Icon name="logout" size="sm" /> Logout
    </button>
  </div>

  <button class="title" onclick={() => nav.go("new")}>
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
  .user {
    font-size: 13px;
    color: var(--text-secondary);
    max-width: 160px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .title {
    display: flex;
    align-items: center;
    gap: 8px;
    background: none;
    border: none;
    color: var(--text-primary);
    font-size: 16px;
    font-weight: 700;
  }
  .logo {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid var(--accent);
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
  @media (max-width: 640px) {
    .user {
      display: none;
    }
  }
</style>
