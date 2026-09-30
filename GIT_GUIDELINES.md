# Git Guidelines

## Commits
`<type>: <imperative description>`

Types: `feat` / `fix` / `refactor` / `docs` / `chore`  
First line ≤ 72 chars. Body explains why (not what).

## Semver and Release Tags
`vMAJOR.MINOR.PATCH`
- MAJOR: breaking API/DB change
- MINOR: new feature, backward compat
- PATCH: bug fix, backward compat

Release tags must be annotated and pushed explicitly:
```bash
git tag -a v3.1.0 -m "summary since v3.0.0"
git push origin main --tags
```
Always use annotated tags (`-a`). The tag message should summarise the user-visible deltas since the previous release.

For GitHub releases, the tag should match the repo version exactly and the release notes should map to the same semver plan.

## GitHub Labeling / Tagging Standards
Use a concise, consistent GitHub label taxonomy so issues and pull requests are easy to filter and triage.

Preferred labels:
- `type:bug`, `type:feature`, `type:docs`, `type:refactor`, `type:chore`
- `area:backend`, `area:frontend`, `area:infra`, `area:docs`, `area:security`
- `priority:P0`, `priority:P1`, `priority:P2`, `priority:P3`
- `status:blocked`, `status:needs-info`, `status:ready`
- `release:major`, `release:minor`, `release:patch`

Use the narrowest label set that describes the issue. Avoid duplicating labels that already imply the same meaning.

## Branches
- `main` — always deployable
- `feat/*` / `fix/*` — short-lived, squash-merged
- No merge commits on main (rebase)

## .gitignore
Ignore: `node_modules/`, `__pycache__/`, `*.pyc`, `.env`, `dist/`, `build/`, `*.log`, `*.key`, `.idea/`, `.vscode/`, `.DS_Store`
Commit: Dockerfiles, K8s manifests, CI, `.env.example`, `package.json`

## History
One commit per logical change. No fixup/squash in permanent history.
