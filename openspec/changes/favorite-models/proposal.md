# Change Proposal: Favorite Models Selection and Bottom Panel Drawer

## Motivation
Users frequently select a preferred subset of LLM models across multiple providers. Finding and reselecting these models across distinct provider tabs can be tedious. A single-click favorite star mechanism allows users to bookmark preferred models. Since different providers (e.g. OpenRouter, OpenCode, Vertex, Custom) may serve models with identical names (such as `gpt-4o` or `deepseek-chat`), the favorites list displayed at the bottom of the right drawer panel clearly annotates the provider name in a subtle, light tone and allows upwards unfold/collapse.

## Proposed Changes

### 1. Models Store (`models.svelte.ts`)
- Track `#favorites = $state<string[]>([])` storing composite keys (`${provider}::${model}`).
- Methods: `isFavorite(compositeKey: string): boolean`, `toggleFavorite(compositeKey: string): void`, `get favorites(): string[]`.
- LocalStorage persistence under `aiEnsembleModels` with graceful migration.

### 2. Model Chip Star Action (`ModelSelector.svelte`)
- Render an interactive star icon button to the left of each model chip in the model selector grid.
- Clicking the star toggles favorite state without interfering with the model selection checkbox.
- Visually indicate favorited state with golden/accent filled star.

### 3. Collapsible Bottom Favorites Section (`ProviderPanel.svelte`)
- Fixed or docked at the bottom of the right drawer panel with upwards unfold / collapse toggle.
- Header shows star icon, "Favorite Models", and active count badge.
- When unfolded, lists all favorited models with:
  - Star toggle icon.
  - Model name.
  - Subtle light-toned provider name badge / subtag to distinguish identical model names from different providers.
  - Quick checkbox / chip click to add/remove model from active discussion.

## Verification Plan
1. Validate OpenSpec change proposal via `openspec validate --all`.
2. Verify Svelte typechecking and test suite via `npm run check` and `npm test`.
3. Verify interactive starring, unfolding/collapsing, and discussion selection in browser.
4. Rebuild production assets, Docker images, and mobile APK.
