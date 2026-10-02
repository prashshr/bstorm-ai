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

  let initializing = $state(true);

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
          const state = JSON.parse(res.state_json || "{}");
          const hasRounds = state.rounds && Object.keys(state.rounds).length > 0;
          const hasRagContext = !!res.retrieved_context;

          discussion.load({
            id: res.id,
            title: res.title,
            question: res.question,
            status: res.status,
            state_json: res.state_json,
            retrieved_context: res.retrieved_context,
            created_at: res.created_at,
          } as any);

          // If discussion has RAG context but no model responses, auto-start it
          if (!hasRounds && hasRagContext && res.status === "in_progress") {
            discussion.start({
              question: res.question,
              models: state.models || [],
              instructions: state.instructions || "",
              consensusEnabled: state.consensus_enabled || false,
              endpoint: state.endpoint || "",
              consensusModel: state.consensus_model || "",
              totalRounds: state.total_rounds || 1,
              timeout: state.timeout || 120,
              maxTokens: state.max_tokens || 6000,
              ragMode: state.rag_mode || "model-only",
              deepResearch: state.deep_research || false,
              responseFormat: state.response_format || "none",
              responseFormatText: state.response_format_text || "",
              summaryFormat: state.summary_format || "none",
              summaryFormatText: state.summary_format_text || "",
              summaryInstructions: state.summary_instructions || "",
            });
          }
        } catch (e) {
          console.warn("Failed to load discussion from URL:", e);
        }
      }
    }
    initializing = false;
  });
</script>

{#if initializing}
  <div class="app-loading">
    <div class="loading-spinner"></div>
    <span>Loading...</span>
  </div>
{:else if auth.isAuthenticated}
  <AppContainer />
  <UserSettingsModal />
{:else}
  <LoginPage />
{/if}

<style>
  .app-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    gap: 16px;
    color: var(--text-tertiary);
    font-size: 14px;
  }
  .loading-spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
