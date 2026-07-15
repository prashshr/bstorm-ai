import { marked } from "marked";
import DOMPurify from "dompurify";

marked.setOptions({ breaks: true, gfm: true });

function escapeHtml(str: string): string {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Render markdown to sanitized HTML. Falls back to escaped plaintext
 * if marked/DOMPurify are unavailable or throw.
 */
export function safeRenderMarkdown(text: string | null | undefined): string {
  if (!text) return "";
  try {
    const raw = marked.parse(text, { async: false }) as string;
    return DOMPurify.sanitize(raw);
  } catch {
    return escapeHtml(String(text)).replace(/\n/g, "<br>");
  }
}

export { escapeHtml };
