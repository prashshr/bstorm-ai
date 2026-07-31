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
  <!-- Section 2: Fixed Center Content (Hero) - Always centered vertically and horizontally -->
  <div class="hero">
    <p class="tagline">Ask multiple AI models at once and get a consensus synthesis.</p>
  </div>

  <!-- Section 3: Bottom-Anchored Dock Container -->
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
    position: relative;
    flex: 1;
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    min-width: 0;
    width: 100%;
    overflow: hidden;
  }

  /* Fixed Center Content - Fixed at top: 35% */
  .hero {
    position: absolute;
    top: 35%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: calc(100% - 32px);
    max-width: 520px;
    text-align: center;
    pointer-events: auto;
    z-index: 1;
  }

  .tagline {
    margin: 0;
    color: var(--text-secondary);
    font-size: 15px;
    font-weight: 500;
    line-height: 1.5;
    text-align: center;
  }

  /* Bottom-Anchored Dock Container */
  .composer {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-end;
    z-index: 10;
    pointer-events: auto;
    box-sizing: border-box;
  }

  .hint {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    color: var(--text-tertiary);
    font-size: 13px;
    padding: 8px 14px;
    border: 1px dashed var(--border);
    border-radius: var(--radius);
    margin-bottom: 8px;
    background: var(--bg-secondary);
    max-width: 720px;
  }

  @media (max-width: 768px) {
    .hero {
      top: 30%;
    }
  }
</style>
