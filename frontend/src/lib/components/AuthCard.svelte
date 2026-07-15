<script lang="ts">
  import { auth } from "../stores/auth.svelte";
  import { providers } from "../stores/providers.svelte";
  import { history } from "../stores/history.svelte";
  import Icon from "./Icon.svelte";

  let identifier = $state("");
  let password = $state("");
  let showPassword = $state(false);
  let mode = $state<"login" | "register">("login");

  async function submit(e: Event) {
    e.preventDefault();
    const ok =
      mode === "login"
        ? await auth.login(identifier, password)
        : await auth.register(identifier, password);
    if (ok) {
      await Promise.all([providers.load(), history.load()]);
    }
  }
</script>

<div class="auth-wrap" data-testid="login-page">
  <form class="auth-card" onsubmit={submit} aria-labelledby="auth-title">
    <div class="brand">
      <span class="logo" aria-hidden="true"></span>
      <h1 id="auth-title">AI-Ensemble</h1>
    </div>
    <p class="subtitle">Multi-provider AI discussion platform</p>

    <label for="auth-id">Email</label>
    <input
      id="auth-id"
      type="email"
      autocomplete="username"
      bind:value={identifier}
      placeholder="you@example.com"
      required
    />

    <label for="auth-pw">Password</label>
    <div class="pw-row">
      {#if showPassword}
        <input
          id="auth-pw"
          type="text"
          autocomplete="current-password"
          bind:value={password}
          placeholder="••••••••"
          required
        />
      {:else}
        <input
          id="auth-pw"
          type="password"
          autocomplete="current-password"
          bind:value={password}
          placeholder="••••••••"
          required
        />
      {/if}
      <button
        type="button"
        class="btn btn-ghost btn-sm pw-toggle"
        onclick={() => (showPassword = !showPassword)}
        aria-label={showPassword ? "Hide password" : "Show password"}
      >
        <Icon name={showPassword ? "eye-off" : "eye"} size="sm" />
      </button>
    </div>

    {#if auth.error}
      <div class="auth-error" role="alert">{auth.error}</div>
    {/if}

    <button type="submit" class="btn btn-primary submit" disabled={auth.loading}>
      {#if auth.loading}
        Please wait…
      {:else}
        {mode === "login" ? "Log in" : "Create account"}
      {/if}
    </button>

    <p class="switch">
      {#if mode === "login"}
        No account?
        <button type="button" class="linkbtn" onclick={() => (mode = "register")}>
          Register
        </button>
      {:else}
        Already have an account?
        <button type="button" class="linkbtn" onclick={() => (mode = "login")}>
          Log in
        </button>
      {/if}
    </p>
  </form>
</div>

<style>
  .auth-wrap {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }
  .auth-card {
    width: 100%;
    max-width: 380px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 32px;
    box-shadow: var(--shadow-md);
    display: flex;
    flex-direction: column;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    justify-content: center;
  }
  .logo {
    width: 26px;
    height: 26px;
    border-radius: 6px;
    border: 2.5px solid var(--accent);
    position: relative;
  }
  .logo::after {
    content: "";
    position: absolute;
    inset: 8px;
    background: var(--accent);
    border-radius: 50%;
  }
  h1 {
    font-size: 22px;
    margin: 0;
  }
  .subtitle {
    text-align: center;
    color: var(--text-tertiary);
    font-size: 13px;
    margin: 4px 0 24px;
  }
  label {
    margin-top: 14px;
  }
  .pw-row {
    display: flex;
    gap: 6px;
    align-items: stretch;
  }
  .pw-row input {
    flex: 1;
  }
  .pw-toggle {
    border: 1px solid var(--input-border);
  }
  .submit {
    margin-top: 22px;
    width: 100%;
  }
  .auth-error {
    margin-top: 14px;
    padding: 8px 12px;
    background: var(--error-bg);
    color: var(--error);
    border-radius: var(--radius);
    font-size: 13px;
  }
  .switch {
    text-align: center;
    font-size: 13px;
    color: var(--text-tertiary);
    margin: 16px 0 0;
  }
  .linkbtn {
    background: none;
    border: none;
    color: var(--accent);
    font-weight: 600;
    padding: 0;
  }
  .linkbtn:hover {
    text-decoration: underline;
  }
</style>
