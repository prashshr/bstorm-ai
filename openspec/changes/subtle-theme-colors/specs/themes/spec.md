# Specification: Themes

## Purpose
Specifies the 50% more desaturated matte orange and green design tokens for an easy-on-the-eyes, dim, minimalistic dark theme.

## MODIFIED Requirements

### Requirement: Subtle Matte Brand Accent Tokens
The system SHALL use low-saturation matte orange (`#b35d25`) and soft sage green (`#2b7a4d`) design tokens in place of bright saturated accents.

#### Scenario: Rendering accent borders and success badges
- **GIVEN** dark theme active in `app.css`
- **WHEN** active model chips, focus rings, or success badges render
- **THEN** the system applies the ultra-subtle matte orange (`--accent: #b35d25`) or matte green (`--success: #2b7a4d`)
