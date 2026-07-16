<script lang="ts">
  import { onMount } from "svelte";
  import { auth } from "./lib/stores/auth.svelte";
  import { theme } from "./lib/stores/theme.svelte";
  import { providers } from "./lib/stores/providers.svelte";
  import { history } from "./lib/stores/history.svelte";
  import { folders } from "./lib/stores/folders.svelte";
  import { discussion } from "./lib/stores/discussion.svelte";
  import LoginPage from "./lib/components/LoginPage.svelte";
  import AppContainer from "./lib/components/AppContainer.svelte";

  onMount(() => {
    theme.init();
    auth.init();
    discussion.restore();
    if (auth.isAuthenticated) {
      providers.load().then(() => providers.verifyAll());
      history.load();
      folders.load();
    }
  });
</script>

{#if auth.isAuthenticated}
  <AppContainer />
{:else}
  <LoginPage />
{/if}
