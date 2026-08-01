# Specification: Themes

## Purpose
Specifies the toned-down matte orange and green design tokens for an easy-on-the-eyes, dim, minimalistic dark theme.

## MODIFIED Requirements

### Requirement: Subtle Matte Brand Accent Tokens
The system SHALL use muted matte orange (`#d96b27`) and soft forest green (`#38a169`) design tokens in place of high-saturation neon accents.

#### Scenario: Rendering accent borders and success badges
- **GIVEN** dark theme active in `app.css`
- **WHEN** active model chips, focus rings, or success badges render
- **THEN** the system applies the subtle matte orange (`--accent: #d96b27`) or matte green (`--success: #38a169`)
