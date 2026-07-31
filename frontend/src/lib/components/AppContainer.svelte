<script lang="ts">
  import { discussion } from "../stores/discussion.svelte";
  import AppHeader from "./AppHeader.svelte";
  import ChatSessions from "./ChatSessions.svelte";
  import ChatHome from "./ChatHome.svelte";
  import ChatMessages from "./ChatMessages.svelte";
  import ProviderPanel from "./ProviderPanel.svelte";
  import DebugPanel from "./DebugPanel.svelte";

  let panelOpen = $state(false);
  let sidebarCollapsed = $state(false);
  let sidebarMobileOpen = $state(false);
  let sidebarWidth = $state<number>(
    Number(localStorage.getItem("aiEnsembleSidebarWidth")) || 260,
  );

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
