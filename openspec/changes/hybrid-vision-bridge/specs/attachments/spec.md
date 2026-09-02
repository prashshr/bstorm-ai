# Specification: Attachments

## Purpose
Specifies multimodal file and image processing, document text extraction, and hybrid vision bridging for text-only LLMs.

## ADDED Requirements

### Requirement: Hybrid Vision Bridging for Text-Only Models
When an image attachment or pasted screenshot is included in a discussion involving both vision-capable and text-only models, the system SHALL extract a structured transcription using a vision model and supply that transcription into the prompt of text-only models, while omitting the raw `image_url` block from the text-only model's request.

#### Scenario: User queries DeepSeek (text-only) and GPT-4o (vision) with a chart screenshot
- **GIVEN** a discussion containing `openrouter::openai/gpt-4o` and `openrouter::deepseek/deepseek-chat`
- **WHEN** user submits a prompt with an attached PNG chart
- **THEN** `gpt-4o` receives the native image attachment
- **AND** `deepseek-chat` receives the prompt with structured transcription of the chart's data and visual breakdown
- **AND** both models complete successfully without HTTP 400 rejection
