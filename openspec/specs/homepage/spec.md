# Specification: Homepage

## Purpose
Specifies the initial homepage landing interface layout, fixed header alignment, centered hero tagline, model selection hint pill, and bottom-docked composer layout.

## Requirements

### Requirement: Independent Vertical Layout Sections
The homepage SHALL maintain three completely independent vertical sections: fixed header at top, fixed centered hero text at `top: 35%`, and bottom-docked composer at `bottom: 0`.

#### Scenario: User resizes chatbox on homepage
- **GIVEN** the homepage interface with hero tagline
- **WHEN** the user resizes the chatbox height upwards
- **THEN** the chatbox height expands upwards while the hero tagline and top header remain strictly frozen in place

### Requirement: Width Alignment of Hint Pill and Chatbox
The model selection hint pill SHALL match the exact width, max-width, and margin parameters of the bottom chatbox card.

#### Scenario: Mobile viewport rendering on homepage
- **GIVEN** a mobile or Android screen width
- **WHEN** the homepage renders
- **THEN** both the hint pill and the chatbox card take `width: calc(100% - 16px)` with matching left and right edges
