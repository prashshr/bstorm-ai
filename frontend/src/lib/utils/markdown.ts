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
 *
 * All links open in a new tab with rel="noopener noreferrer" for security.
 */
export function safeRenderMarkdown(text: string | null | undefined): string {
  if (!text) return "";
  try {
    const raw = marked.parse(text, { async: false }) as string;
    const clean = DOMPurify.sanitize(raw, { ADD_ATTR: ["target", "rel"] });
    // Post-process: add target="_blank" to all links
    const div = document.createElement("div");
    div.innerHTML = clean;
    div.querySelectorAll("a").forEach((a) => {
      a.setAttribute("target", "_blank");
      a.setAttribute("rel", "noopener noreferrer");
    });
    return div.innerHTML;
  } catch {
    return escapeHtml(String(text)).replace(/\n/g, "<br>");
  }
}

export { escapeHtml };
