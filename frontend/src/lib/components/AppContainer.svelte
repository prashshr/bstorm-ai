<script lang="ts">
  import { onMount } from "svelte";
  import { discussion } from "../stores/discussion.svelte";
  import AppHeader from "./AppHeader.svelte";
  import Icon from "./Icon.svelte";
  import ChatSessions from "./ChatSessions.svelte";
  import ChatHome from "./ChatHome.svelte";
  import ChatMessages from "./ChatMessages.svelte";
  import ProviderPanel from "./ProviderPanel.svelte";
  import DebugPanel from "./DebugPanel.svelte";

  let panelOpen = $state(false);
  let sidebarCollapsed = $state(true);
  let sidebarMobileOpen = $state(false);
  let sidebarWidth = $state<number>(
    Number(localStorage.getItem("aiEnsembleSidebarWidth")) || 260,
  );
  let online = $state(typeof navigator === "undefined" ? true : navigator.onLine);

  onMount(() => {
    const handleOnline = () => {
      online = true;
      // Flush any state that failed to sync while offline.
      discussion.persist();
    };
    const handleOffline = () => (online = false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  });

  const hasActive = $derived(
    discussion.data.id != null || discussion.data.question !== "" || discussion.running,
  );

  const headerOffset = $derived(sidebarCollapsed ? 56 : sidebarWidth);
</script>

<div class="shell" style="--sidebar-w:{sidebarCollapsed ? 56 : sidebarWidth}px">
  <AppHeader
    onTogglePanel={() => (panelOpen = !panelOpen)}
    onToggleSessions={() => (sidebarMobileOpen = !sidebarMobileOpen)}
  />
  {#if !online}
    <div class="offline-banner" data-testid="offline-banner" role="status">
      <Icon name="alert" size="sm" />
      You're offline — completed responses are saved locally and sync automatically when you reconnect.
    </div>
  {/if}
  <div class="body">
    <ChatSessions
      bind:collapsed={sidebarCollapsed}
      bind:paneWidth={sidebarWidth}
      bind:mobileOpen={sidebarMobileOpen}
    />
    <main class="main-area">
      {#if hasActive}
        <ChatMessages onEditModels={() => (panelOpen = true)} />
      {:else}
        <ChatHome onEditModels={() => (panelOpen = true)} />
      {/if}
    </main>
  </div>
  <ProviderPanel open={panelOpen} onclose={() => (panelOpen = false)} />
  <DebugPanel />
</div>

<style>
  .offline-banner {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 6px 12px;
    font-size: 12px;
    color: var(--warning);
    background: var(--warning-bg);
    border-bottom: 1px solid var(--border);
  }
  .shell {
    position: relative;
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
  }
  .body {
    position: relative;
    flex: 1;
    display: flex;
    min-height: 0;
    overflow: hidden;
  }
  .main-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    overflow: hidden;
  }
  @media (max-width: 768px) {
    .body {
      flex-direction: column;
    }
    .shell {
      --sidebar-w: 0px;
    }
  }
</style>
