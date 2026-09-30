<script lang="ts">
  import { onMount } from "svelte";
  import { auth } from "./lib/stores/auth.svelte";
  import { theme } from "./lib/stores/theme.svelte";
  import { providers } from "./lib/stores/providers.svelte";
  import { models } from "./lib/stores/models.svelte";
  import { history } from "./lib/stores/history.svelte";
  import { folders } from "./lib/stores/folders.svelte";
  import { discussion } from "./lib/stores/discussion.svelte";
  import { api } from "./lib/api/client";
  import { personas } from "./lib/stores/personas.svelte";
  import { userSettings } from "./lib/stores/settings.svelte";
  import LoginPage from "./lib/components/LoginPage.svelte";
  import AppContainer from "./lib/components/AppContainer.svelte";
  import UserSettingsModal from "./lib/components/UserSettingsModal.svelte";

  onMount(async () => {
    theme.init();
    await auth.init();
    discussion.restore();
    if (auth.isAuthenticated) {
      models.restore();
      userSettings.fetchRemote();
      providers.load().then(() => providers.verifyAll());
      personas.load();
      history.load();
      folders.load();
      // Load discussion from URL hash if present (e.g., after browser refresh)
      const hash = window.location.hash;
      const match = hash.match(/^#discussion\/(\d+)/);
      if (match) {
        const discussionId = parseInt(match[1], 10);
        try {
          const res = await api.getDiscussion(discussionId);
          discussion.load({
            id: res.id,
            title: res.title,
            question: res.question,
            status: res.status,
            state_json: res.state_json,
            retrieved_context: res.retrieved_context,
            created_at: res.created_at,
          } as any);
        } catch (e) {
          console.warn("Failed to load discussion from URL:", e);
        }
      }
    }
  });
</script>

{#if auth.isAuthenticated}
  <AppContainer />
  <UserSettingsModal />
{:else}
  <LoginPage />
{/if}
