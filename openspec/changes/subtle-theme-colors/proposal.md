# Change Proposal: Subtle Matte Theme Color Accents

## Motivation
The current orange (`#ff5c00`) and green (`#22c55e`) brand accent lines and badges are bright and saturated. To create an easy-on-the-eyes, dim, matte, minimalistic dark design aesthetic, these accent colors should be toned down into more subtle matte shades.

## Proposed Changes

### 1. Design Token Color Adjustments (`app.css`)
- **Primary Accent Orange**: Toned down from bright `#ff5c00` to a subtle, dim matte orange `#d96b27` / `#c85a1b`.
- **Accent Light / Hover**: Adjusted from `#ff7e33` to a muted matte peach `#d87a43`.
- **Accent Dark**: Adjusted from `#cc5200` to `#a84500`.
- **Success Green**: Toned down from bright `#22c55e` to a soft matte forest green `#38a169` / `#2e8b57`.
- **Success Background**: Softened to `rgba(56, 161, 105, 0.12)`.
- **Active Focus Rings & Active Borders**: Focus outlines and active discussion borders updated to use the muted matte orange.

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
