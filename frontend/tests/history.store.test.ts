import { describe, it, expect, beforeEach, vi } from "vitest";

vi.mock("../src/lib/api/client", () => ({
  api: {
    listDiscussions: vi.fn(async () => [
      {
        id: 1,
        title: "Alpha topic",
        question: "What is alpha?",
        status: "completed",
        use_rag: false,
        deep_research: false,
        state_json: "{}",
        retrieved_context: null,
        created_at: "2026-01-01T00:00:00Z",
      },
      {
        id: 2,
        title: "Beta topic",
        question: "How does beta work?",
        status: "in_progress",
        use_rag: true,
        deep_research: false,
        state_json: "{}",
        retrieved_context: null,
        created_at: "2026-02-01T00:00:00Z",
      },
    ]),
    deleteDiscussion: vi.fn(async () => {}),
  },
}));

import { history } from "../src/lib/stores/history.svelte";

describe("history store", () => {
  beforeEach(async () => {
    history.setFilter("all");
    history.setSort("newest");
    history.setSearch("");
    await history.load();
  });

  it("loads discussions", () => {
    expect(history.items.length).toBe(2);
  });

  it("sorts newest first by default", () => {
    expect(history.visible[0].id).toBe(2);
  });

  it("sorts oldest first", () => {
    history.setSort("oldest");
    expect(history.visible[0].id).toBe(1);
  });

  it("filters by completed status", () => {
    history.setFilter("completed");
    expect(history.visible.every((d) => d.status === "completed")).toBe(true);
    expect(history.visible.length).toBe(1);
  });

  it("filters running/new discussions", () => {
    history.setFilter("running");
    expect(history.visible.map((d) => d.id)).toEqual([2]);
  });

  it("fuzzy searches question and title", () => {
    history.setSearch("beta");
    expect(history.visible.map((d) => d.id)).toEqual([2]);
  });

  it("removes an item locally", async () => {
    await history.remove(1);
    expect(history.items.find((d) => d.id === 1)).toBeUndefined();
  });
});
