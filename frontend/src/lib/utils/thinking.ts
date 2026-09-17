export interface ParsedThinkingResult {
  thinking: string;
  finalText: string;
  isThinkingOnly: boolean;
}

/**
 * Extracts internal reasoning/thinking tokens and tags from model output.
 * Handles both streaming (unclosed tags) and completed responses,
 * combining tag-based thinking with upstream thinking deltas.
 */
export function parseModelThinking(
  rawText: string = "",
  upstreamThinking: string = "",
): ParsedThinkingResult {
  const upstream = (upstreamThinking ?? "").trim();
  const text = rawText ?? "";

  if (!text) {
    return {
      thinking: upstream,
      finalText: "",
      isThinkingOnly: Boolean(upstream),
    };
  }

  // Regex to match closed thinking tags
  const closedTagRegex = /<(think|thought|reasoning|thinking)>([\s\S]*?)<\/\1>/gi;
  const extractedThinking: string[] = upstream ? [upstream] : [];

  let remaining = text.replace(closedTagRegex, (_, _tag, content) => {
    const trimmed = content.trim();
    if (trimmed) {
      extractedThinking.push(trimmed);
    }
    return "";
  });

  // Check for an unclosed opening tag at the end (active streaming)
  const openTagMatch = remaining.match(/<(think|thought|reasoning|thinking)>([\s\S]*)$/i);
  let isThinkingOnly = false;

  if (openTagMatch) {
    const unclosedContent = openTagMatch[2]?.trim();
    if (unclosedContent) {
      extractedThinking.push(unclosedContent);
    }
    remaining = remaining.slice(0, openTagMatch.index);
    isThinkingOnly = remaining.trim().length === 0;
  } else if (!remaining.trim() && extractedThinking.length > 0) {
    isThinkingOnly = true;
  }

  return {
    thinking: extractedThinking.join("\n\n").trim(),
    finalText: remaining.trimStart(),
    isThinkingOnly,
  };
}
