# Specification: Coding Standards & Git Conventions

# Purpose
This document specifies project-wide coding standards, language conventions for Python 3.12 and Svelte 5, type safety requirements, formatting rules, git branch/commit guidelines, and semantic versioning rules for AI-Ensemble.

# Responsibilities
- Define Python 3.12 code formatting, PEP 8 compliance, and type annotation expectations (`mypy` / `ruff`).
- Define Svelte 5 Runes idioms (`$state`, `$derived`, `$effect`) and TypeScript strict mode rules.
- Enforce git commit message formatting and semantic release tagging (`vX.Y.Z`).
- Enforce security best practices (no plaintext secrets in code or commits).

# Python 3.12 Conventions
- **Code Style**: PEP 8 compliance using 4-space indentation.
- **Type Annotations**: All function signatures must include explicit parameter and return type hints:
  ```python
  def encrypt_string(data: str, uek: str) -> str:
      ...
  ```
- **Async First**: Use `async`/`await` for all FastAPI route handlers and HTTP requests (`httpx`).
- **Dependencies**: Manage requirements in `backend/requirements.txt`. Do not introduce unapproved libraries.
- **Comments**: Focus comments on *why* complex logic is implemented, not *what* is done.

# Svelte 5 & TypeScript Conventions
- **Runes State**: Use class-based Svelte 5 Runes stores (`.svelte.ts`) with `$state`, `$derived`, and `$effect`:
  ```typescript
  class DiscussionStore {
    data = $state<DiscussionData>(initialData);
    running = $derived(this.data.running);
  }
  ```
- **Component Props**: Use `$props()` rune interface definitions:
  ```typescript
  interface Props {
    autofocus?: boolean;
    placeholder?: string;
  }
  let { autofocus = false, placeholder = "Ask..." }: Props = $props();
  ```
- **Svelte Check**: Zero errors allowed in `npm run check`.
- **Absolute Imports**: Prefer relative imports within component modules (`../stores/discussion.svelte`).

# Git & Release Conventions
- **Semantic Versioning**: Use `vMAJOR.MINOR.PATCH` format (e.g. `v4.2.0`).
- **Commit Message Format**:
  - `feat(scope): ...` for new capabilities.
  - `fix(scope): ...` for bug or UI fixes.
  - `deploy(scope): ...` for deployment or image updates.
  - `docs(scope): ...` for documentation additions.
- **Pre-commit Checklist**:
  1. Run `npm run check` (0 errors).
  2. Run `npm test` (37 tests pass).
  3. Run `python3 testing/scripts/run-tests.py` (128 tests pass).
  4. Tag release `git tag vX.Y.Z`.

# Dependencies
- Python 3.12, Svelte 5, TypeScript 5, Ruff, Svelte-Check, Git.

# Current Behaviour
Codebase complies with PEP 8 and Svelte 5 Runes patterns. Version `v4.2.0` is tagged and verified.

# Related Specs
- [Testing Spec](testing.md)
- [Deployment Spec](deployment.md)
