# Specification: Prompt Composer Component

# Purpose
The Prompt Composer subsystem specifies the single-card bottom-docked input component (`ChatInput.svelte`). It manages user message entry, file attachments, drag height resizing, advanced execution settings, and mobile auto-minimization.

# Responsibilities
- Provide a `contenteditable` rich-text editor supporting multiline text, paste sanitization, and auto-growing height.
- Allow file attachments (images, PDFs, DOCX, XLSX, PPTX, RTF, TXT) via file chooser or drag-and-drop.
- Provide a full-width top drag handle for upward height adjustment bounded between `130px` and `min(380px, 42vh)`.
- Render a 4-sided rectangular outline card (`1px solid var(--input-border)`) with rounded corners and focus accent rings.
- House an Advanced Settings popover sheet (`adv-panel`) for consensus toggles, custom instructions, timeout, max tokens, RAG mode, and Deep Research.
- Auto-minimize to a compact 44px bar on mobile/Android during active model streaming with a 1-tap pull-up expand button.

# Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        ::: (Top Drag Handle)                           │
│  [Models: GPT-4o × | Claude 3.5 ×]                       (Minimize ˅)  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ What would you like to ask multiple AI models today?             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  [Paperclip]  [Advanced ⚙]                                 [Send ➔]    │
└────────────────────────────────────────────────────────────────────────┘
```

# Data Flow
1. User enters text in `editorEl` (`contenteditable="true"`).
2. Files dropped or attached via `<input type="file">` trigger `handleFiles()`.
3. Clicking Send invokes `send()`, collecting plaintext question and attachments, resetting editor state, and calling `discussion.start()` or `discussion.nextTurn()`.

# Internal Components
- `ChatInput.svelte`: Main composer component.
- `editorEl`: `contenteditable` DOM node receiving keyboard input and clipboard paste events.
- `adv-panel`: Floating popover sheet containing advanced configuration controls.
- `compact-bar`: Collapsed 44px pill bar displayed when minimized.

# Public Interfaces
- Component: `<ChatInput autofocus={boolean} placeholder={string} onEditModels={() => void} />`

# Dependencies
- `discussion.svelte.ts`, `models.svelte.ts`, `extractDocument.ts`, `DOMPurify`.

# Configuration
- Min dock height: `130px`.
- Max dock height: `min(380px, Math.floor(window.innerHeight * 0.42))`.
- Width: `width: calc(100% - 32px); max-width: 760px; margin: 0 auto 8px;` (desktop) / `width: calc(100% - 16px)` (mobile).

# Current Behaviour
The composer is permanently docked to `bottom: 0`. Dragging the top handle resizes height upwards into visible page space without moving the homepage hero text or header. On mobile, when `discussion.running` is true, it automatically collapses to a 44px bar.

# Constraints
- Paste handler sanitizes pasted HTML with DOMPurify to prevent XSS.

# Future Considerations
- Speech-to-Text audio recording button using browser MediaRecorder API.

# Related Specs
- [Homepage Spec](homepage.md)
- [Attachments Spec](attachments.md)
- [Settings Spec](settings.md)
