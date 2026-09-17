import { describe, it, expect } from "vitest";
import { parseModelThinking } from "../src/lib/utils/thinking";

describe("parseModelThinking", () => {
  it("returns raw text when no thinking tags or upstream thinking exist", () => {
    const res = parseModelThinking("Hello world!");
    expect(res.finalText).toBe("Hello world!");
    expect(res.thinking).toBe("");
    expect(res.isThinkingOnly).toBe(false);
  });

  it("extracts closed <think> tags from text", () => {
    const raw = "<think>Let me calculate 2+2.\nIt is 4.</think>The answer is 4.";
    const res = parseModelThinking(raw);
    expect(res.thinking).toBe("Let me calculate 2+2.\nIt is 4.");
    expect(res.finalText).toBe("The answer is 4.");
    expect(res.isThinkingOnly).toBe(false);
  });

  it("handles streaming unclosed <think> tag", () => {
    const raw = "<think>Calculating the result step by step...";
    const res = parseModelThinking(raw);
    expect(res.thinking).toBe("Calculating the result step by step...");
    expect(res.finalText).toBe("");
    expect(res.isThinkingOnly).toBe(true);
  });

  it("combines upstream thinking with inline thinking tags", () => {
    const res = parseModelThinking(
      "<thought>Tag thought</thought>Response text",
      "Upstream thought",
    );
    expect(res.thinking).toBe("Upstream thought\n\nTag thought");
    expect(res.finalText).toBe("Response text");
    expect(res.isThinkingOnly).toBe(false);
  });

  it("recognizes thinking-only state when upstream thinking is present and text is empty", () => {
    const res = parseModelThinking("", "Deep model reasoning in progress...");
    expect(res.thinking).toBe("Deep model reasoning in progress...");
    expect(res.finalText).toBe("");
    expect(res.isThinkingOnly).toBe(true);
  });

  it("handles multiple thinking blocks and tags", () => {
    const raw = "<think>Part 1</think>Intermediate<thought>Part 2</thought>Final answer";
    const res = parseModelThinking(raw);
    expect(res.thinking).toBe("Part 1\n\nPart 2");
    expect(res.finalText).toBe("IntermediateFinal answer");
    expect(res.isThinkingOnly).toBe(false);
  });
});
