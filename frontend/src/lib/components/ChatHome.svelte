<script lang="ts">
  import ChatInput from "./ChatInput.svelte";
  import { models } from "../stores/models.svelte";
  import Icon from "./Icon.svelte";
</script>

<div class="home">
  <div class="hero">
    <span class="logo" aria-hidden="true"></span>
    <h1>AI-Ensemble</h1>
    <p class="tagline">Ask multiple AI models at once and get a consensus synthesis.</p>
  </div>

  <div class="composer">
    {#if models.selected.length === 0}
      <div class="hint" data-testid="no-models-hint">
        <Icon name="bot" size="sm" />
        Select one or more models from the providers panel to begin.
      </div>
    {/if}
    <ChatInput autofocus placeholder="What would you like to ask multiple AI models today?" />
  </div>
</div>

<style>
  .home {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .hero {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 24px;
    gap: 6px;
  }
  .logo {
    width: 56px;
    height: 56px;
    border-radius: 14px;
    border: 5px solid var(--accent);
    position: relative;
    margin-bottom: 8px;
  }
  .logo::after {
    content: "";
    position: absolute;
    inset: 8px;
    background: var(--accent);
    border-radius: 50%;
  }
  h1 {
    margin: 0;
    font-size: 34px;
    font-weight: 700;
    letter-spacing: -0.01em;
  }
  .tagline {
    margin: 0;
    color: var(--text-secondary);
    font-size: 15px;
    max-width: 420px;
  }
  .composer {
    flex-shrink: 0;
    max-width: 720px;
    width: 100%;
    margin: 0 auto;
    padding-bottom: 24px;
    padding-left: 16px;
    padding-right: 16px;
  }
  .hint {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    color: var(--text-tertiary);
    font-size: 13px;
    padding: 10px;
    border: 1px dashed var(--border);
    border-radius: var(--radius);
    margin-bottom: 10px;
  }
</style>
