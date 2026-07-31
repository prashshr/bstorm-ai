# Specification: Homepage UI & Layout

# Purpose
The Homepage subsystem defines the layout structure and initial landing experience when a user opens AI-Ensemble or starts a new discussion. It enforces a 3-section layout separating the top header, centered hero messaging, and the bottom-docked prompt composer.

# Responsibilities
- Display the application brand header fixed at the top of the viewport.
- Render the hero tagline ("*Ask multiple AI models at once and get a consensus synthesis.*") fixed in the vertical/horizontal center of the main area.
- Present a model selection hint pill when no models are currently selected.
- Anchor the single-card prompt composer (`ChatInput.svelte`) to the bottom of the viewport.
- Ensure 100% layout independence so resizing or dragging the bottom composer does not shift or move the centered hero text.

# Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│ [Fixed Top Header: Burger | Theme | AI-Ensemble Logo | Providers ⚙]    │
├──────────────┬─────────────────────────────────────────────────────────┤
│ [Collapsible │                                                         │
│  Sessions    │                   (Fixed Hero Text)                     │
│  Sidebar]    │     Ask multiple AI models at once and get a            │
│              │                   consensus synthesis.                  │
│              │                                                         │
│              │      [Dashed Hint: Select models to begin]              │
│              │  ┌───────────────────────────────────────────────────┐  │
│              │  │ ::: (Top Drag Handle)                           _ │  │
│              │  │ What would you like to ask multiple AI models?  │ │  │
│              │  │ [Paperclip] [Advanced ⚙]               [Send ➔]   │ │  │
│              │  └───────────────────────────────────────────────────┘  │
└──────────────┴─────────────────────────────────────────────────────────┘
```

# Data Flow
- Mounts `ChatHome.svelte` when `discussion.data.id == null && discussion.data.question === ""`.
- On prompt submission, `discussion.start()` initializes the conversation state and transitions the view from `ChatHome.svelte` to `ChatMessages.svelte`.

# Internal Components
- `ChatHome.svelte`: Root homepage component rendering `.hero`, `.hint`, and `<ChatInput>`.
- `ChatInput.svelte`: Single-card bottom-docked composer component.

# Public Interfaces
- Component: `<ChatHome onEditModels={() => void} />`

# Dependencies
- `models.svelte.ts` (monitors `models.selected.length` to toggle model selection hint).
- `discussion.svelte.ts` (triggers conversation state transitions).

# Configuration
- Hero position: `top: 35%` / `left: 50%` (`transform: translate(-50%, -50%)`).
- Hint width: `width: calc(100% - 32px); max-width: 760px; margin: 0 auto 8px;` (matches `ChatInput.svelte` width exactly across desktop, mobile, and Android).

# Current Behaviour
When the user visits the home view, the header, hero text, and bottom composer are rendered. The hero text remains completely static and unaffected when the composer height is adjusted via dragging.

# Constraints
- The hero text is marked `pointer-events: auto` and `z-index: 1`, ensuring it sits behind the composer (`z-index: 10`) if the composer is expanded upwards.

# Future Considerations
- Quick-start prompt template cards (e.g. "Compare Python vs Rust", "Summarize Market News") displayed below the hero tagline.

# Related Specs
- [Frontend Spec](frontend.md)
- [Prompt Composer Spec](prompt-composer.md)
- [Chat Spec](chat.md)
