<script lang="ts">
  import { discussion } from "../stores/discussion.svelte";
  import AppHeader from "./AppHeader.svelte";
  import ChatSessions from "./ChatSessions.svelte";
  import ChatHome from "./ChatHome.svelte";
  import ChatMessages from "./ChatMessages.svelte";
  import ProviderPanel from "./ProviderPanel.svelte";
  import DebugPanel from "./DebugPanel.svelte";

  let panelOpen = $state(false);

  const hasActive = $derived(
    discussion.data.id != null || discussion.data.question !== "" || discussion.running,
  );
</script>

<div class="shell">
  <AppHeader onToggleSessions={() => {}} onTogglePanel={() => (panelOpen = !panelOpen)} />
  <div class="body">
    <ChatSessions />
    <main class="main-area">
      {#if hasActive}
        <ChatMessages />
      {:else}
        <ChatHome />
      {/if}
    </main>
  </div>
  <ProviderPanel open={panelOpen} onclose={() => (panelOpen = false)} />
  <DebugPanel />
</div>

<style>
  .shell {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .body {
    flex: 1;
    display: flex;
    min-height: 0;
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
  }
</style>
