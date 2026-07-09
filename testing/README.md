# AI Ensemble — Testing Guide

## Directory Structure

```
testing/
├── backend/
│   ├── conftest.py              # Shared fixtures (TestClient, DB, auth, Playwright)
│   ├── pyproject.toml            # Pytest configuration
│   ├── requirements-dev.txt      # Test dependencies
│   ├── unit/                     # Unit tests (fast, isolated, mocked)
│   │   ├── test_auth.py          # Auth endpoints
│   │   ├── test_security.py      # Encryption, UEK, CORS
│   │   ├── test_domain_knowledge.py  # Topic classifier
│   │   └── test_rag.py           # RAG pipeline (mocked)
│   ├── integration/              # Integration tests (DB, API, external)
│   │   ├── test_discussions.py   # Discussion CRUD with RAG
│   │   ├── test_providers.py     # Provider credential management
│   │   └── test_proxy.py         # Proxy chat with RAG injection
│   └── e2e/                      # End-to-end browser tests (Playwright)
│       └── test_ui.py            # UI flows: auth, providers, discussions
├── scripts/
│   └── run-tests.py              # Test runner & report generator
├── infrastructure/               # Infrastructure tests (k8s, Docker)
└── reports/                      # Generated test reports (gitignored)
```

## Running Tests

```bash
# Run all backend tests (unit + integration)
python testing/scripts/run-tests.py

# With code coverage
python testing/scripts/run-tests.py --coverage

# Quick mode (skip slow external API tests)
python testing/scripts/run-tests.py --quick

# View latest test report
python testing/scripts/run-tests.py --view

# Run E2E browser tests (requires port-forwards + Playwright)
cd testing/backend && python -m pytest e2e/ -v

# Run infrastructure checks
python testing/scripts/run-tests.py --infra
```

## Report Format

Each run generates a markdown report at `testing/reports/test-report_{VERSION}_{YYYYMMDD}_{HHMM}.md` with:
- Executive summary (pass rate, totals)
- Environment info (OS, Python, git version)
- Functional area coverage table
- Per-module detailed results
- Failed tests root-cause analysis
- Raw test output

## Adding Tests

- **Unit tests** go in `testing/backend/unit/`. No DB, no network. Mock external calls.
- **Integration tests** go in `testing/backend/integration/`. Use `client` fixture for API calls.
- **E2E tests** go in `testing/backend/e2e/`. Require running K3s cluster and port-forwards.
