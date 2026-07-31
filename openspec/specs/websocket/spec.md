# Specification: WebSocket

## Purpose
Specifies real-time event transport mechanics, comparing Server-Sent Events (SSE) over HTTP/2 with WebSockets, and stream line buffering.

## Requirements

### Requirement: SSE Protocol Frame Formatting
Stream frames SHALL be transmitted as single or multi-line strings starting with `data: ` and terminated by `\n\n`.

#### Scenario: Backend emits stream event
- **GIVEN** active model stream
- **WHEN** delta chunk is ready
- **THEN** backend formats frame `data: {"type":"delta","content":"text"}\n\n`

### Requirement: Client Line Buffer Reassembly
The client `TextDecoder` reader SHALL buffer incoming bytes, split on newlines, and parse complete `data:` payloads.

#### Scenario: Stream bytes arrive fragmented
- **GIVEN** incoming byte chunks split across TCP packets
- **WHEN** client reader processes buffer
- **THEN** lines are reassembled cleanly before JSON parsing
