# Specification: Attachments

## Purpose
Specifies file attachment handling, multimodal base64 image encoding, client-side document text extraction (PDF, DOCX, XLSX, PPTX, RTF, TXT), and 100 MB upload limits.

## Requirements

### Requirement: Client-Side Document Text Extraction
The frontend SHALL extract raw text from supported document formats (PDF, DOCX, XLSX, PPTX, RTF, TXT) directly in the browser/app.

#### Scenario: User attaches a PDF document
- **GIVEN** a PDF file selected by the user
- **WHEN** `extractDocumentText(file)` executes
- **THEN** PDF.js extracts page text contents locally and inlines the text into the prompt context

### Requirement: Multimodal Base64 Image Processing
Image file attachments (`image/*`) SHALL be converted to base64 strings and passed in the `attachments` array for vision-capable models.

#### Scenario: User attaches a PNG image
- **GIVEN** a PNG image file
- **WHEN** the user submits a message to GPT-4o
- **THEN** the image is base64-encoded and sent as multimodal content to the provider
