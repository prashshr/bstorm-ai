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
  import { recoverDiscussionState } from "./lib/utils/helpers";

  let initializing = $state(true);
  let hashHandled = false;

  async function loadDiscussionFromHash(): Promise<void> {
    const match = window.location.hash.match(/^#discussion\/(\d+)/);
    if (!match) return;
    const discussionId = parseInt(match[1], 10);
    try {
      const res = await api.getDiscussion(discussionId);
      const state = recoverDiscussionState(
        JSON.parse(res.state_json || "{}"),
      ) as Record<string, any>;
      const hasRounds = state.rounds && Object.keys(state.rounds).length > 0;
      const hasRagContext = !!res.retrieved_context;

      // discussion.load() expects a parsed DiscussionState (rounds,
      // userMessages, … at the top level) — pass the parsed state_json,
      // overlaid with the response envelope fields. Passing the raw
      // response would reset rounds to {} and wipe server state via
      // load()'s persist().
      discussion.load({
        ...state,
        id: res.id,
        title: res.title || state.title || "",
        question: res.question || state.question || "",
        status: res.status || state.status,
        retrieved_context: res.retrieved_context ?? state.retrieved_context ?? null,
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

  onMount(async () => {
    theme.init();
    await auth.init();
    // A #discussion/N deep link must win over the localStorage-restored
    // discussion: capture it before restore() syncs the URL from local
    // state (otherwise the incoming hash gets rewritten and the wrong
    // discussion loads).
    const deepLink = /^#discussion\/\d+/.test(window.location.hash);
    discussion.restore({ syncUrl: !deepLink });
    if (auth.isAuthenticated) {
      models.restore();
      userSettings.fetchRemote();
      providers.load().then(() => providers.verifyAll());
      personas.load();
      history.load();
      folders.load();
    }
    initializing = false;
  });

  // Load the deep-linked discussion once authentication is ready — both on
  // a plain page load (already authenticated) and after a fresh login
  // (LoginPage flips auth.isAuthenticated without re-running onMount).
  // The one-shot must NOT be consumed while the hash is empty (e.g. right
  // after login) — otherwise a later same-document navigation to
  // #discussion/N silently does nothing.
  $effect(() => {
    if (initializing || !auth.isAuthenticated || hashHandled) return;
    if (!/^#discussion\/\d+/.test(window.location.hash)) return;
    hashHandled = true;
    void loadDiscussionFromHash();
  });

  // Same-document deep links (URL bar paste / fragment navigation) don't
  // reload the page, so listen for hash changes too. Internal writes from
  // #syncUrlFromState are ignored because they target the already-loaded id,
  // and an in-flight run is never interrupted.
  onMount(() => {
    const handleHashChange = () => {
      const match = window.location.hash.match(/^#discussion\/(\d+)/);
      if (!match) return;
      const id = parseInt(match[1], 10);
      const currentId = typeof discussion.data.id === "number" ? discussion.data.id : null;
      if (id === currentId) return;
      if (discussion.running) return;
      hashHandled = true;
      void loadDiscussionFromHash();
    };
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
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
