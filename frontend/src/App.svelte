<script lang="ts">
  import { onMount } from "svelte";
  import { auth } from "./lib/stores/auth.svelte";
  import { theme } from "./lib/stores/theme.svelte";
  import { providers } from "./lib/stores/providers.svelte";
  import { models } from "./lib/stores/models.svelte";
  import { history } from "./lib/stores/history.svelte";
  import { folders } from "./lib/stores/folders.svelte";
  import { discussion } from "./lib/stores/discussion.svelte";
  import { personas } from "./lib/stores/personas.svelte";
  import LoginPage from "./lib/components/LoginPage.svelte";
  import AppContainer from "./lib/components/AppContainer.svelte";

  onMount(async () => {
    theme.init();
    await auth.init();
    discussion.restore();
    if (auth.isAuthenticated) {
      models.restore();
      providers.load().then(() => providers.verifyAll());
      personas.load();
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
