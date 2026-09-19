import { describe, it, expect } from "vitest";
import {
  extractDiscussedEntities,
  detectNewItemsIntent,
  isAutomatedDeliberationDirective,
  buildExclusionLedgerDirective,
} from "../src/lib/utils/entityLedger";
import type { ModelResult } from "../src/lib/api/types";

describe("entityLedger utility", () => {
  describe("detectNewItemsIntent", () => {
    it("detects turn 5 user phrasing: continue your research and recommend next new 5 companies on same lines.", () => {
      expect(
        detectNewItemsIntent("continue your research and recommend next new 5 companies on same lines."),
      ).toBe(true);
    });

    it("detects other common variations requesting new or next items", () => {
      expect(detectNewItemsIntent("give me next 5 companies")).toBe(true);
      expect(detectNewItemsIntent("recommend 5 new names")).toBe(true);
      expect(detectNewItemsIntent("what are other options?")).toBe(true);
      expect(detectNewItemsIntent("provide alternative picks")).toBe(true);
      expect(detectNewItemsIntent("give me a second batch of candidates")).toBe(true);
      expect(detectNewItemsIntent("continue research and suggest new ones")).toBe(true);
      expect(detectNewItemsIntent("excluding the prior companies, who else?")).toBe(true);
    });

    it("does not trigger on refinement, comparison, or clarification queries", () => {
      expect(detectNewItemsIntent("compare CLS and NVT in terms of valuation")).toBe(false);
      expect(detectNewItemsIntent("review in these lines with the latest live verified snapshot")).toBe(false);
      expect(detectNewItemsIntent("what is the free cash flow margin of Fabrinet?")).toBe(false);
      expect(detectNewItemsIntent("explain why Credo is risky")).toBe(false);
    });
  });

  describe("isAutomatedDeliberationDirective", () => {
    it("identifies deliberation directives", () => {
      expect(
        isAutomatedDeliberationDirective(
          "[COUNCIL DELIBERATION DIRECTIVE - TURN 2]\nIn Round 1, Model X raised...",
        ),
      ).toBe(true);
      expect(
        isAutomatedDeliberationDirective(
          "[ENSEMBLE DELIBERATION DIRECTIVE - TURN 3]\nYou are now in deliberation turn 3...",
        ),
      ).toBe(true);
    });

    it("does not flag regular user prompts", () => {
      expect(isAutomatedDeliberationDirective("Hello, can you help me?")).toBe(false);
      expect(
        isAutomatedDeliberationDirective("continue your research and recommend next new 5 companies on same lines."),
      ).toBe(false);
    });
  });

  describe("extractDiscussedEntities", () => {
    it("extracts entities from model responses and consensus rankings across rounds", () => {
      const rounds: Record<number, Record<string, ModelResult>> = {
        1: {
          "openai::gpt-4o": {
            status: "complete",
            text: `Top candidates:
1. **Celestica (CLS)** - Leading EMS manufacturer for AI clusters.
2. **Credo Technology (CRDO)** - High speed connectivity.
3. **Alphawave IP (AWE.L)** - Silicon IP provider.
4. **Astera Labs (ALAB)** - PCIe retimers.
5. **Onto Innovation (ONTO)** - Semiconductor metrology.`,
          },
          "deepseek::deepseek-chat": {
            status: "complete",
            text: `My recommendations:
- **nVent Electric (NVT)**: Liquid cooling enclosures.
- **Fabrinet (FN)**: Optical packaging.
- **Munters (MTRS)**: Air treatment and data centre cooling.
- **Comfort Systems (FIX)**: HVAC installation.`,
          },
        },
        2: {
          "openai::gpt-4o": {
            status: "complete",
            text: `Revisiting Astera Labs (ALAB) and Modine Manufacturing (MOD). Vertiv (VRT) also noted.`,
          },
        },
      };

      const consensuses: Record<number, string> = {
        1: `## Consensus
1. Celestica (CLS)
2. nVent Electric (NVT)
3. Credo Technology (CRDO)
4. Onto Innovation (ONTO)
5. Fabrinet (FN)`,
      };

      const entities = extractDiscussedEntities(rounds, consensuses);
      expect(entities).toContain("Celestica (CLS)");
      expect(entities).toContain("Credo Technology (CRDO)");
      expect(entities).toContain("Alphawave IP (AWE)");
      expect(entities).toContain("Astera Labs (ALAB)");
      expect(entities).toContain("Onto Innovation (ONTO)");
      expect(entities).toContain("nVent Electric (NVT)");
      expect(entities).toContain("Fabrinet (FN)");
      expect(entities).toContain("Munters (MTRS)");
      expect(entities).toContain("Comfort Systems (FIX)");
      expect(entities).toContain("Modine Manufacturing (MOD)");
      expect(entities).toContain("Vertiv (VRT)");

      // Should not contain non-entity financial acronyms
      expect(entities).not.toContain("FCF");
      expect(entities).not.toContain("CAGR");
      expect(entities).not.toContain("EBITDA");
    });

    it("respects maxRoundExclusive parameter", () => {
      const rounds: Record<number, Record<string, ModelResult>> = {
        1: {
          "m::1": { status: "complete", text: "1. Celestica (CLS)" },
        },
        2: {
          "m::1": { status: "complete", text: "1. Monolithic Power Systems (MPWR)" },
        },
      };

      const entitiesRound1Only = extractDiscussedEntities(rounds, {}, 2);
      expect(entitiesRound1Only).toContain("Celestica (CLS)");
      expect(entitiesRound1Only).not.toContain("Monolithic Power Systems (MPWR)");
    });
  });

  describe("buildExclusionLedgerDirective", () => {
    it("generates a clear negative constraint block", () => {
      const directive = buildExclusionLedgerDirective(["Celestica (CLS)", "nVent Electric (NVT)"]);
      expect(directive).toContain("[ACTIVE EXCLUSION LEDGER - DO NOT REPEAT PREVIOUSLY ANALYZED ITEMS]");
      expect(directive).toContain("• Celestica (CLS)");
      expect(directive).toContain("• nVent Electric (NVT)");
      expect(directive).toContain("MUST NOT re-propose");
      expect(directive).toContain("[END ACTIVE EXCLUSION LEDGER]");
    });

    it("returns empty string if entity list is empty", () => {
      expect(buildExclusionLedgerDirective([])).toBe("");
    });
  });
});
