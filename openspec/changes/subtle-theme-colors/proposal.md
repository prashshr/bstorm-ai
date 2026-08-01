# Change Proposal: Subtle Matte Theme Color Accents

## Motivation
The orange and green brand accent lines and badges have been desaturated and dimmed 50% further into ultra-subtle, low-saturation matte shades (`#b35d25` orange and `#2b7a4d` sage green) for a dim, minimalistic, ultra-easy-on-the-eyes dark design aesthetic.

## Proposed Changes

### 1. Design Token Color Adjustments (`app.css`)
- **Primary Accent Orange**: Dimmed 50% further to ultra-subtle matte copper/terracotta `#b35d25`.
- **Accent Light**: Muted matte clay `#b86d38`.
- **Accent Dark**: Deep dim sienna `#823b00`.
- **Accent Hover**: Soft muted copper `#c2672d`.
- **Success Green**: Dimmed 50% further to soft muted sage green `#2b7a4d`.
- **Success Background**: Softened to `rgba(43, 122, 77, 0.10)`.

### 2. Affected Visual Components
- Active model selection chips and provider icons.
- Chatbox card border focus ring and top drag indicator hover.
- Round indicators and follow-up badges (`--accent-light`).
- RAG status dots and complete badges (`--success`).
- Progress stepper phase indicators.

## Verification Plan
1. Validate OpenSpec change proposal via `openspec validate --changes`.
2. Build frontend and verify CSS compilation via `npm run build`.
3. Execute backend/frontend test suite via `python testing/scripts/run-tests.py` and `npm test`.
4. Deploy web container image to live k3s cluster and compile Android APK.
