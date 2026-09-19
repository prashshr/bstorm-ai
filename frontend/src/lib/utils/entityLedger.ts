/**
 * Entity & Recommendation Ledger for AI-Ensemble discussions.
 *
 * Tracks entities (companies, stock tickers, technologies, products) proposed,
 * evaluated, or ranked across discussion turns. Enforces conversational memory
 * and negative constraints when users ask for new / next / alternative options.
 */

import type { ModelResult } from "../api/types";

// Financial and technical acronyms that appear in parentheses but are not company tickers
const NON_ENTITY_ABBREVIATIONS = new Set([
  "AI", "ML", "LLM", "GPU", "CPU", "ASIC", "NPU", "DSP", "AEC", "AOC", "CPO",
  "FCF", "CAGR", "EBITDA", "EBIT", "GAAP", "NON-GAAP", "P/E", "P/S", "P/B", "EV/EBITDA",
  "ROIC", "ROE", "ROA", "EPS", "TAM", "SAM", "DCF", "WACC", "IRR", "ROI",
  "LTM", "NTM", "TTM", "YOY", "QOQ", "MTD", "YTD",
  "FY23", "FY24", "FY25", "FY26", "FY27", "FY28", "Q1", "Q2", "Q3", "Q4",
  "HVAC", "CDU", "DLC", "RDHX", "UPS", "BESS", "PDU", "SMPS", "VRM", "PMIC",
  "HBM", "DDR5", "PCI", "PCIE", "CXL", "SERDES", "PAM4", "COWOS", "TSV",
  "US", "USA", "UK", "EU", "APAC", "EMEA", "ROW", "SEC", "IPO", "SPAC", "ETF",
  "CEO", "CFO", "CTO", "COO", "R&D", "CAPEX", "OPEX", "M&A", "SGA", "COGS",
  "USD", "EUR", "GBP", "JPY", "CNY", "CHF", "CAD", "AUD", "SEK",
  "LSE", "NYSE", "NASDAQ", "TSX", "ASX", "HKEX", "TSE",
]);

/**
 * Extracts candidate entities (company names, tickers) mentioned in prior rounds.
 */
export function extractDiscussedEntities(
  rounds: Record<number, Record<string, ModelResult>>,
  consensuses: Record<number, string> = {},
  maxRoundExclusive?: number,
): string[] {
  const entityMap = new Map<string, string>(); // canonical key -> display label

  // Helper to add entity safely
  function addEntity(rawName: string, rawTicker?: string) {
    let name = rawName.trim().replace(/^[*#_`]+|[*#_`]+$/g, "").trim();
    let ticker = rawTicker?.trim().replace(/^[*#_`$]+|[*#_`]+$/g, "").toUpperCase();

    // Check if ticker is a known non-entity abbreviation
    if (ticker && NON_ENTITY_ABBREVIATIONS.has(ticker)) {
      ticker = undefined;
    }

    // Clean ticker formatting (e.g., AWE.L, MTRS.ST, NASDAQ:CRDO, or AWE, LSE)
    if (ticker) {
      if (ticker.includes(":")) {
        const parts = ticker.split(":");
        ticker = parts[parts.length - 1];
      }
      ticker = ticker.split(/[,;\s]/)[0];
      // Normalize exchange dot suffix like AWE.L -> AWE
      const baseTicker = ticker.split(".")[0];
      if (baseTicker && baseTicker.length >= 1 && baseTicker.length <= 5) {
        ticker = baseTicker;
      }
    }

    if (!name && !ticker) return;

    // Discard single generic words without ticker
    if (!ticker && (name.length < 3 || /^(the|and|for|top|first|five|companies|overview|conclusion)$/i.test(name))) {
      return;
    }

    // If name has "(TICKER)" embedded, split it
    const parenMatch = name.match(/^([A-Za-z0-9\s&.,'/-]+?)\s*\(([A-Za-z0-9.:]+)(?:,\s*[^)]+)?\)$/);
    if (parenMatch) {
      name = parenMatch[1].trim();
      const extractedTicker = parenMatch[2].trim().toUpperCase().split(/[,:\s]/)[0];
      if (!NON_ENTITY_ABBREVIATIONS.has(extractedTicker)) {
        ticker = ticker || extractedTicker;
      }
    }

    // Strip leading conversational phrases, verbs, and conjunctions from name
    name = name.replace(/^(and|or|vs|versus|with|also|as\s+well\s+as|revisiting|considering|evaluating|analyzing|excluding|including|recommending|reviewing|noting|regarding|avoiding|buy|hold|sell|top|next|new)\s+/i, "");

    // Normalize name
    name = name.replace(/\s+/g, " ").trim();
    if (name.length > 50) name = name.slice(0, 50).trim();

    const canonicalKey = ticker || name.toUpperCase();
    let display = name;
    if (ticker) {
      if (!name || name.toUpperCase() === ticker) {
        display = ticker;
      } else if (!name.includes(`(${ticker})`)) {
        display = `${name} (${ticker})`;
      } else {
        display = name;
      }
    }

    if (!entityMap.has(canonicalKey)) {
      entityMap.set(canonicalKey, display);
    } else {
      const existing = entityMap.get(canonicalKey)!;
      // If new one has both name and ticker while existing is just ticker, upgrade
      if (ticker && display.includes(`(${ticker})`) && !existing.includes(`(${ticker})`)) {
        entityMap.set(canonicalKey, display);
      } else if (ticker && display.includes(`(${ticker})`) && existing.includes(`(${ticker})`)) {
        // If both include ticker, prefer the cleaner/shorter company name
        if (display.length < existing.length && display.length >= 5) {
          entityMap.set(canonicalKey, display);
        }
      }
    }
  }

  // Iterate over rounds
  const roundEntries = Object.entries(rounds)
    .map(([r, models]) => [Number(r), models] as const)
    .sort(([a], [b]) => a - b);

  for (const [rNum, models] of roundEntries) {
    if (maxRoundExclusive !== undefined && rNum >= maxRoundExclusive) {
      continue;
    }

    // Scan consensus for this round
    const cons = consensuses[rNum];
    if (cons) {
      scanTextForEntities(cons, addEntity);
    }

    // Scan completed model responses for this round
    for (const res of Object.values(models)) {
      if (res.status === "complete" && res.text) {
        scanTextForEntities(res.text, addEntity);
      }
    }
  }

  return Array.from(entityMap.values()).filter((e) => e && e.length >= 2);
}

/**
 * Scans markdown text for company names, tickers, numbered lists, and consensus rankings.
 */
function scanTextForEntities(text: string, addEntity: (name: string, ticker?: string) => void) {
  const lines = text.split("\n");

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    // Strip markdown formatting symbols like ** and __ to normalize matching
    const unformatted = trimmed.replace(/[*_`]/g, "").trim();

    // Check if line is a numbered item or bullet
    const bulletMatch = unformatted.match(/^\s*(?:\d+\.|[-*•])\s+(.+)$/);
    if (bulletMatch) {
      const itemBody = bulletMatch[1].trim();
      // Match "Company Name (TICKER) - Description" or "Company Name (TICKER)"
      const itemParenMatch = itemBody.match(/^([A-Za-z0-9\s&.,'/-]+?)\s*\(([A-Za-z0-9.:]+)(?:,\s*[^)]+)?\)/);
      if (itemParenMatch) {
        addEntity(itemParenMatch[1], itemParenMatch[2]);
      } else {
        // Match "Company Name - Description" without parentheses
        const itemSepMatch = itemBody.match(/^([A-Za-z0-9\s&.,'/-]{2,40})(?:\s*[-–—:]\s+.+)?$/);
        if (itemSepMatch) {
          const raw = itemSepMatch[1].trim();
          if (!/^(note|summary|pros|cons|verdict|risk|avoid|valuation|common ground|key|recommendation)\b/i.test(raw)) {
            addEntity(raw);
          }
        }
      }
    }

    // Also scan for explicit Company (TICKER) anywhere in line
    // Allowing lowercase leading letters like nVent
    const parenRegex = /([a-zA-Z0-9][A-Za-z0-9\s&.,'/-]{1,35})\s*\(([A-Z]{1,5}(?:\.[A-Z]{1,4}|:[A-Z]{1,4})?)(?:,\s*[^)]+)?\)/g;
    let pMatch: RegExpExecArray | null;
    while ((pMatch = parenRegex.exec(unformatted)) !== null) {
      let name = pMatch[1].trim();
      const ticker = pMatch[2].trim();
      name = name.replace(/^(revisiting|considering|evaluating|analyzing|excluding|including|recommending|reviewing|noting|regarding|avoiding|buy|hold|sell|top|next|new)\s+/i, "");
      if (!/^(figure|table|section|turn|round|source|basis|as of)\b/i.test(name)) {
        addEntity(name, ticker);
      }
    }

    // Scan for cash tags like $CLS or $NVT
    const cashTagRegex = /\$([A-Z]{1,5})\b/g;
    let cMatch: RegExpExecArray | null;
    while ((cMatch = cashTagRegex.exec(unformatted)) !== null) {
      const ticker = cMatch[1];
      if (!NON_ENTITY_ABBREVIATIONS.has(ticker)) {
        addEntity(ticker, ticker);
      }
    }
  }
}


/**
 * Detects whether the user follow-up prompt is asking for NEW, ADDITIONAL, NEXT, or ALTERNATIVE items/recommendations.
 */
export function detectNewItemsIntent(userMessage: string): boolean {
  if (!userMessage) return false;
  const msg = userMessage.toLowerCase();

  // Explicit phrases:
  // "recommend next new 5 companies", "next 5", "new companies", "other options",
  // "give me 5 more", "different companies", "second batch", "continue research and recommend"
  const patterns = [
    /\b(next|new|another|additional|other|fresh|further|more|different|besides|what else)\b.*\b(companies|stocks|names|picks|candidates|options|alternatives|ideas|firms|tickers|recommendations|batch)\b/i,
    /\b(recommend|give|provide|suggest|find|show|list)\b.*\b(next|new|more|another|additional|other|fresh|alternative)\b/i,
    /\b(next\s+new|\bnew\s+\d+|\bnext\s+\d+)\b/i,
    /\b(continue\s+(your\s+)?research\s+and\s+recommend)\b/i,
    /\b(second\s+batch|next\s+batch|next\s+round\s+of|more\s+names|other\s+names)\b/i,
    /\b(beyond\s+(the\s+)?(prior|previous|above|initial))\b/i,
    /\b(excluding\s+(the\s+)?(prior|previous|above|initial))\b/i,
    // Multilingual support (German, etc.)
    /\b(weitere|andere|neue|nächste)\b.*\b(aktien|firmen|unternehmen|kandidaten|optionen)\b/i,
  ];

  return patterns.some((p) => p.test(msg));
}

/**
 * Checks if a turn message is an internal automated deliberation directive
 * (e.g., generated by deliberation topology) vs. an authentic user prompt.
 */
export function isAutomatedDeliberationDirective(message: string): boolean {
  if (!message) return false;
  const trimmed = message.trim();
  return (
    trimmed.startsWith("[COUNCIL DELIBERATION DIRECTIVE") ||
    trimmed.startsWith("[ENSEMBLE DELIBERATION DIRECTIVE") ||
    trimmed.startsWith("Deliberation Round") ||
    trimmed.includes("[END COUNCIL DELIBERATION DIRECTIVE]")
  );
}

/**
 * Formats a clean, prominent Negative Constraint / Exclusion Ledger block
 * for injection into model and consensus prompts.
 */
export function buildExclusionLedgerDirective(entities: string[]): string {
  if (!entities || entities.length === 0) return "";

  // Deduplicate and cap to avoid token bloat
  const cleanList = Array.from(new Set(entities)).slice(0, 40);
  const itemsFormatted = cleanList.map((e) => `• ${e}`).join("\n");

  return (
    `[ACTIVE EXCLUSION LEDGER - DO NOT REPEAT PREVIOUSLY ANALYZED ITEMS]\n` +
    `The following entities/companies have ALREADY been proposed, evaluated, or settled in earlier turns of this discussion:\n` +
    `${itemsFormatted}\n\n` +
    `CRITICAL MANDATE FOR THIS TURN:\n` +
    `- The user is requesting NEW, NEXT, or ADDITIONAL recommendations.\n` +
    `- You MUST NOT re-propose, repeat, or re-rank ANY of the previously discussed entities listed above.\n` +
    `- Every candidate you recommend must be completely fresh, new, and distinct from all prior turns.\n` +
    `[END ACTIVE EXCLUSION LEDGER]\n\n`
  );
}
