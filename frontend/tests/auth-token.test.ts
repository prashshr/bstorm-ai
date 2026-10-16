import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { auth } from "../src/lib/stores/auth.svelte";

const TOKEN_KEY = "aiEnsembleToken";

/**
 * A password change bumps the user's token version, which invalidates the
 * access token the client is holding. The backend hands back a replacement in
 * the change-password response and `adoptAccessToken` is what puts it in
 * place — without it the very next request 401s and the user is signed out of
 * the dialog they just used.
 */
describe("auth.adoptAccessToken", () => {
  beforeEach(() => {
    localStorage.clear();
  });
  afterEach(() => {
    localStorage.clear();
  });

  it("stores the replacement token and exposes it as the active one", async () => {
    localStorage.setItem(TOKEN_KEY, "stale-token");

    await auth.adoptAccessToken("replacement-token");

    expect(localStorage.getItem(TOKEN_KEY)).toBe("replacement-token");
    expect(auth.token).toBe("replacement-token");
  });

  it("does not touch the refresh token", async () => {
    localStorage.setItem("aiEnsembleRefresh", "my-refresh-token");

    await auth.adoptAccessToken("replacement-token");

    expect(localStorage.getItem("aiEnsembleRefresh")).toBe("my-refresh-token");
  });

  it("ignores empty or missing tokens instead of wiping the session", async () => {
    localStorage.setItem(TOKEN_KEY, "still-valid-token");

    await auth.adoptAccessToken(null);
    await auth.adoptAccessToken(undefined);
    await auth.adoptAccessToken("");

    expect(localStorage.getItem(TOKEN_KEY)).toBe("still-valid-token");
  });
});
