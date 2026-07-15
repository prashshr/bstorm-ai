<script lang="ts">
  import { nav } from "../stores/nav.svelte";
  import { discussion } from "../stores/discussion.svelte";
  import AppHeader from "./AppHeader.svelte";
  import LeftSidebar from "./LeftSidebar.svelte";
  import MainTabs from "./MainTabs.svelte";
  import TabNewDiscussion from "./TabNewDiscussion.svelte";
  import TabCurrentDiscussion from "./TabCurrentDiscussion.svelte";
  import TabHistory from "./TabHistory.svelte";
  import TabProviderConfig from "./TabProviderConfig.svelte";
  import DebugPanel from "./DebugPanel.svelte";
</script>

<div class="shell">
  <AppHeader />
  <div class="body" class:focus={nav.focusMode}>
    {#if !nav.focusMode}
      <LeftSidebar />
    {/if}
    <main class="main-area">
      <MainTabs />
      <div class="tab-content">
        {#if nav.tab === "new"}
          <TabNewDiscussion />
        {:else if nav.tab === "current"}
          <TabCurrentDiscussion />
        {:else if nav.tab === "history"}
          <TabHistory />
        {:else if nav.tab === "provider"}
          <TabProviderConfig />
        {/if}
      </div>
    </main>
  </div>
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
  .tab-content {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
  }
  @media (max-width: 768px) {
    .body {
      flex-direction: column;
    }
    .tab-content {
      padding: 14px;
    }
  }
</style>
