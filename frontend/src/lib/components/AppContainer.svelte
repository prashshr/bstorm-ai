<script lang="ts">
  import { nav } from "../stores/nav.svelte";
  import { discussion } from "../stores/discussion.svelte";
  import AppHeader from "./AppHeader.svelte";
  import LeftSidebar from "./LeftSidebar.svelte";
  import MainTabs from "./MainTabs.svelte";
  import TabNewDiscussion from "./TabNewDiscussion.svelte";
  import TabCurrentDiscussion from "./TabCurrentDiscussion.svelte";
  import TabHistory from "./TabHistory.svelte";
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
        {#if nav.tab === "current"}
          <TabCurrentDiscussion />
        {:else if nav.tab === "new"}
          <div class="tab-scroll">
            <TabNewDiscussion />
          </div>
        {:else if nav.tab === "history"}
          <div class="tab-scroll">
            <TabHistory />
          </div>
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
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .tab-scroll {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 20px;
  }
  @media (max-width: 768px) {
    .body {
      flex-direction: column;
    }
    .tab-scroll {
      padding: 14px;
    }
  }
</style>
