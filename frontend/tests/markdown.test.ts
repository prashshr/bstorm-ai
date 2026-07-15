import { describe, it, expect } from "vitest";
import { safeRenderMarkdown, escapeHtml } from "../src/lib/utils/markdown";

describe("safeRenderMarkdown", () => {
  it("returns empty string for empty input", () => {
    expect(safeRenderMarkdown("")).toBe("");
    expect(safeRenderMarkdown(null)).toBe("");
    expect(safeRenderMarkdown(undefined)).toBe("");
  });

  it("renders basic markdown to HTML", () => {
    const html = safeRenderMarkdown("# Title\n\n**bold**");
    expect(html).toContain("<h1");
    expect(html).toContain("<strong>bold</strong>");
  });

  it("strips dangerous script tags (XSS)", () => {
    const html = safeRenderMarkdown("hi <script>alert('x')</script>");
    expect(html).not.toContain("<script>");
  });

  it("strips inline event handlers", () => {
    const html = safeRenderMarkdown('<img src=x onerror="alert(1)">');
    expect(html.toLowerCase()).not.toContain("onerror");
  });
});

describe("escapeHtml", () => {
  it("escapes angle brackets and ampersands", () => {
    expect(escapeHtml("<b>&</b>")).toBe("&lt;b&gt;&amp;&lt;/b&gt;");
  });
});
