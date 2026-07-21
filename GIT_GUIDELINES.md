# Git Guidelines

## Commits
`<type>: <imperative description>`

Types: `feat` / `fix` / `refactor` / `docs` / `chore`  
First line ≤ 72 chars. Body explains why (not what).

## Semver
`vMAJOR.MINOR.PATCH`
- MAJOR: breaking API/DB change
- MINOR: new feature, backward compat
- PATCH: bug fix, backward compat

## Tagging
```bash
git tag -a v3.1.0 -m "summary since v3.0.0"
git push origin main --tags
```
Always annotated (`-a`). Tag message summarises deltas.

## Branches
- `main` — always deployable
- `feat/*` / `fix/*` — short-lived, squash-merged
- No merge commits on main (rebase)

## .gitignore
Ignore: `node_modules/`, `__pycache__/`, `*.pyc`, `.env`, `dist/`, `build/`, `*.log`, `*.key`, `.idea/`, `.vscode/`, `.DS_Store`
Commit: Dockerfiles, K8s manifests, CI, `.env.example`, `package.json`

## History
One commit per logical change. No fixup/squash in permanent history.
