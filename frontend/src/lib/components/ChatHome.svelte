<script lang="ts">
  import ChatInput from "./ChatInput.svelte";
  import { models } from "../stores/models.svelte";
  import Icon from "./Icon.svelte";

  interface Props {
    onEditModels?: () => void;
  }
  let { onEditModels }: Props = $props();
</script>

<div class="home">
  <div class="hero">
    <p class="tagline">Ask multiple AI models at once and get a consensus synthesis.</p>
  </div>

  <div class="composer">
    {#if models.selected.length === 0}
      <div class="hint" data-testid="no-models-hint">
        <Icon name="bot" size="sm" />
        Select one or more models from the providers panel to begin.
      </div>
    {/if}
    <ChatInput autofocus placeholder="What would you like to ask multiple AI models today?" {onEditModels} />
  </div>
</div>

<style>
  .home {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    min-width: 0;
    width: 100%;
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
  .tagline {
    margin: 0;
    color: var(--text-secondary);
    font-size: 15px;
    text-align: center;
    max-width: 420px;
  }
  .composer {
    flex-shrink: 0;
    max-width: 720px;
    width: 100%;
    margin: 0 auto;
    padding: 0 16px 24px;
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
  @media (max-width: 768px) {
    .hero {
      padding: 16px;
    }
    .composer {
      padding: 0 12px 16px;
    }
  }
</style>
