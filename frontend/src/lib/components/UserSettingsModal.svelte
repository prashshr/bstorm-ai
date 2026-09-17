<script lang="ts">
  import { userSettings } from "../stores/settings.svelte";
  import { auth } from "../stores/auth.svelte";
  import { history } from "../stores/history.svelte";
  import { theme } from "../stores/theme.svelte";
  import Icon from "./Icon.svelte";

  let activeTab = $state<"preferences" | "appearance" | "account" | "data">("preferences");

  // Local state for editing form
  let currentPassword = $state("");
  let newPassword = $state("");
  let passwordMsg = $state("");
  let passwordError = $state("");
  let changingPassword = $state(false);

  const ACCENT_OPTIONS = [
    { name: "Terracotta", hex: "#b35d25" },
    { name: "Sage Green", hex: "#2b7a4d" },
    { name: "Slate Blue", hex: "#2563eb" },
    { name: "Muted Amber", hex: "#d97706" },
  ];

  async function handlePasswordChange() {
    if (!currentPassword || !newPassword) {
      passwordError = "Please enter current and new password.";
      return;
    }
    if (newPassword.length < 8) {
      passwordError = "New password must be at least 8 characters.";
      return;
    }

    changingPassword = true;
    passwordMsg = "";
    passwordError = "";

    try {
      const res = await fetch("/api/user/change-password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${auth.token}`,
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      const data = await res.json();
      if (res.ok) {
        passwordMsg = "Password changed successfully!";
        currentPassword = "";
        newPassword = "";
      } else {
        passwordError = data.detail || "Failed to change password.";
      }
    } catch {
      passwordError = "Network error. Please try again.";
    } finally {
      changingPassword = false;
    }
  }

  function exportHistoryJSON() {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(history.items, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `ai_ensemble_history_${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  }

  function closeModal() {
    userSettings.closeModal();
  }
</script>

{#if userSettings.modalOpen}
  <div class="modal-backdrop" onclick={closeModal} aria-hidden="true"></div>

  <div class="modal-card" role="dialog" aria-label="User settings">
    <div class="modal-header">
      <div class="title-row">
        <Icon name="settings" size="sm" />
        <h2>User Settings</h2>
      </div>
      <button class="btn btn-ghost btn-sm close-btn" onclick={closeModal} aria-label="Close settings">
        <Icon name="close" size="sm" />
      </button>
    </div>

    <div class="modal-body">
      <!-- Left Navigation Tabs -->
      <nav class="settings-nav">
        <button
          class="nav-tab"
          class:active={activeTab === "preferences"}
          onclick={() => (activeTab = "preferences")}
        >
          <Icon name="settings" size="sm" /> Preferences
        </button>
        <button
          class="nav-tab"
          class:active={activeTab === "appearance"}
          onclick={() => (activeTab = "appearance")}
        >
          <Icon name="sun" size="sm" /> Appearance
        </button>
        <button
          class="nav-tab"
          class:active={activeTab === "account"}
          onclick={() => (activeTab = "account")}
        >
          <Icon name="bot" size="sm" /> Account & Security
        </button>
        <button
          class="nav-tab"
          class:active={activeTab === "data"}
          onclick={() => (activeTab = "data")}
        >
          <Icon name="file" size="sm" /> Data & Privacy
        </button>
      </nav>

      <!-- Right Tab Content Panel -->
      <div class="settings-content">
        {#if activeTab === "preferences"}
          <div class="tab-section">
            <h3>Discussion & Execution Defaults</h3>
            <p class="section-desc">Default parameters loaded when creating new chats.</p>

            <div class="field-grid">
              <div class="field">
                <label for="set-rag">Default RAG Mode</label>
                <select
                  id="set-rag"
                  value={userSettings.data.defaultRagMode}
                  onchange={(e) => userSettings.update({ defaultRagMode: (e.currentTarget as HTMLSelectElement).value as any })}
                >
                  <option value="model-self">Model/Self (Default - Search Enabled)</option>
                  <option value="model-only">Model-Only (Search Disabled)</option>
                </select>
              </div>

              <div class="field">
                <label for="set-consensus">Default Consensus State</label>
                <select
                  id="set-consensus"
                  value={userSettings.data.defaultConsensusEnabled ? "enabled" : "disabled"}
                  onchange={(e) => userSettings.update({ defaultConsensusEnabled: (e.currentTarget as HTMLSelectElement).value === "enabled" })}
                >
                  <option value="disabled">Disabled (Default)</option>
                  <option value="enabled">Enabled</option>
                </select>
              </div>

              <div class="field">
                <label for="set-resp-fmt">Default Response Format</label>
                <select
                  id="set-resp-fmt"
                  value={userSettings.data.defaultResponseFormat}
                  onchange={(e) => userSettings.update({ defaultResponseFormat: (e.currentTarget as HTMLSelectElement).value as any })}
                >
                  <option value="none">None (Default)</option>
                  <option value="compact">Compact</option>
                  <option value="elaborate">Elaborate</option>
                </select>
              </div>

              <div class="field">
                <label for="set-sum-fmt">Default Summary Format</label>
                <select
                  id="set-sum-fmt"
                  value={userSettings.data.defaultSummaryFormat}
                  onchange={(e) => userSettings.update({ defaultSummaryFormat: (e.currentTarget as HTMLSelectElement).value as any })}
                >
                  <option value="compact">Compact (Default)</option>
                  <option value="elaborate">Elaborate</option>
                  <option value="none">None</option>
                </select>
              </div>

              <div class="field">
                <label for="set-timeout">Response Timeout (seconds)</label>
                <input
                  id="set-timeout"
                  type="number"
                  min="10"
                  max="300"
                  value={userSettings.data.defaultTimeout}
                  onchange={(e) => userSettings.update({ defaultTimeout: parseInt((e.currentTarget as HTMLInputElement).value, 10) || 120 })}
                />
              </div>

              <div class="field">
                <label for="set-max-tokens">Max Tokens / Response</label>
                <input
                  id="set-max-tokens"
                  type="number"
                  min="500"
                  max="16000"
                  step="500"
                  value={userSettings.data.defaultMaxTokens}
                  onchange={(e) => userSettings.update({ defaultMaxTokens: parseInt((e.currentTarget as HTMLInputElement).value, 10) || 6000 })}
                />
              </div>

              <div class="field">
                <label for="set-show-thinking">Model Thinking & Reasoning</label>
                <select
                  id="set-show-thinking"
                  value={userSettings.data.showThinking ? "enabled" : "disabled"}
                  onchange={(e) => userSettings.update({ showThinking: (e.currentTarget as HTMLSelectElement).value === "enabled" })}
                >
                  <option value="disabled">Hide Thinking (Default - Final response only)</option>
                  <option value="enabled">Show Thinking (Display reasoning process)</option>
                </select>
                <span class="field-hint">When disabled, model windows display only the clean final response. Enable to view the thought process.</span>
              </div>
            </div>
          </div>
        {:else if activeTab === "appearance"}
          <div class="tab-section">
            <h3>Appearance & Aesthetics</h3>
            <p class="section-desc">Customize theme palette and layout behavior.</p>

            <div class="field">
              <label>Theme Mode</label>
              <div class="theme-buttons">
                <button
                  class="btn btn-ghost theme-opt"
                  class:active={theme.theme === "dark"}
                  onclick={() => theme.toggle()}
                >
                  <Icon name="moon" size="sm" /> Dark Mode
                </button>
                <button
                  class="btn btn-ghost theme-opt"
                  class:active={theme.theme === "light"}
                  onclick={() => theme.toggle()}
                >
                  <Icon name="sun" size="sm" /> Light Mode
                </button>
              </div>
            </div>

            <div class="field">
              <label>Accent Color Palette</label>
              <div class="palette-grid">
                {#each ACCENT_OPTIONS as opt (opt.hex)}
                  <button
                    class="palette-chip"
                    class:selected={userSettings.data.themeAccent === opt.hex}
                    onclick={() => userSettings.update({ themeAccent: opt.hex })}
                  >
                    <span class="swatch" style="background:{opt.hex}"></span>
                    <span>{opt.name}</span>
                  </button>
                {/each}
              </div>
            </div>

            <div class="field">
              <label class="switch-row">
                <input
                  type="checkbox"
                  checked={userSettings.data.autoMinimizeComposer}
                  onchange={(e) => userSettings.update({ autoMinimizeComposer: (e.currentTarget as HTMLInputElement).checked })}
                />
                <span>Auto-minimize chatbox composer when discussion starts</span>
              </label>
            </div>
          </div>
        {:else if activeTab === "account"}
          <div class="tab-section">
            <h3>Account & Security</h3>
            <p class="section-desc">Manage your account credentials and security keys.</p>

            <div class="account-info-box">
              <div class="info-row">
                <span class="lbl">Account Email:</span>
                <span class="val">{auth.user ?? "Local User"}</span>
              </div>
              <div class="info-row">
                <span class="lbl">User Encryption Key (UEK):</span>
                <span class="val status-ok">Active & Encrypted</span>
              </div>
            </div>

            <hr class="divider" />

            <h4>Change Password</h4>
            {#if passwordMsg}
              <div class="alert alert-success">{passwordMsg}</div>
            {/if}
            {#if passwordError}
              <div class="alert alert-danger">{passwordError}</div>
            {/if}

            <form class="password-form" onsubmit={(e) => { e.preventDefault(); handlePasswordChange(); }}>
              <div class="field">
                <label for="cur-pw">Current Password</label>
                <input id="cur-pw" type="password" bind:value={currentPassword} required />
              </div>
              <div class="field">
                <label for="new-pw">New Password</label>
                <input id="new-pw" type="password" bind:value={newPassword} required minlength="8" />
              </div>
              <button class="btn btn-primary" type="submit" disabled={changingPassword}>
                {changingPassword ? "Updating…" : "Update Password"}
              </button>
            </form>
          </div>
        {:else if activeTab === "data"}
          <div class="tab-section">
            <h3>Data & Export</h3>
            <p class="section-desc">Manage your saved discussion data and local storage.</p>

            <div class="data-actions">
              <div class="action-card">
                <div class="action-desc">
                  <strong>Export Discussion History</strong>
                  <p>Download all your encrypted discussion histories as JSON.</p>
                </div>
                <button class="btn btn-primary" onclick={exportHistoryJSON}>
                  <Icon name="download" size="sm" /> Export JSON
                </button>
              </div>

              <div class="action-card">
                <div class="action-desc">
                  <strong>Session Logout</strong>
                  <p>Sign out from this browser session.</p>
                </div>
                <button class="btn btn-ghost danger-btn" onclick={() => { closeModal(); auth.logout(); }}>
                  <Icon name="logout" size="sm" /> Sign Out
                </button>
              </div>
            </div>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.65);
    backdrop-filter: blur(4px);
    z-index: 100;
  }

  .modal-card {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: min(720px, 92vw);
    max-height: 85vh;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
    z-index: 101;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 18px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-primary);
  }

  .title-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .title-row h2 {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .close-btn {
    padding: 4px;
  }

  .modal-body {
    display: flex;
    flex: 1;
    min-height: 380px;
    overflow: hidden;
  }

  .settings-nav {
    width: 200px;
    flex-shrink: 0;
    border-right: 1px solid var(--border);
    background: var(--bg-tertiary);
    padding: 12px 8px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .nav-tab {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    border: none;
    border-radius: var(--radius);
    background: transparent;
    color: var(--text-secondary);
    font-size: 13px;
    font-weight: 600;
    text-align: left;
    cursor: pointer;
    transition: background var(--transition), color var(--transition);
  }

  .nav-tab:hover {
    background: var(--bg-secondary);
    color: var(--text-primary);
  }

  .nav-tab.active {
    background: color-mix(in srgb, var(--accent) 18%, var(--bg-secondary));
    color: var(--text-primary);
    border-left: 3px solid var(--accent);
  }

  .settings-content {
    flex: 1;
    padding: 18px 22px;
    overflow-y: auto;
  }

  .tab-section h3 {
    margin: 0 0 4px;
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .section-desc {
    margin: 0 0 16px;
    font-size: 12px;
    color: var(--text-tertiary);
  }

  .field-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 12px;
  }

  .field label {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
  }

  .field select,
  .field input {
    padding: 8px 10px;
    border: 1px solid var(--input-border);
    border-radius: var(--radius);
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 13px;
  }

  .field-hint {
    font-size: 11px;
    color: var(--text-tertiary);
    margin-top: -2px;
  }

  .theme-buttons {
    display: flex;
    gap: 8px;
  }

  .theme-opt {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    border: 1px solid var(--border);
    padding: 8px;
  }

  .theme-opt.active {
    border-color: var(--accent);
    color: var(--text-primary);
  }

  .palette-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .palette-chip {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-primary);
    color: var(--text-secondary);
    font-size: 12px;
    cursor: pointer;
  }

  .palette-chip.selected {
    border-color: var(--accent);
    color: var(--text-primary);
    font-weight: 700;
  }

  .swatch {
    width: 14px;
    height: 14px;
    border-radius: 50%;
  }

  .switch-row {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    font-size: 13px;
    color: var(--text-primary);
  }

  .account-info-box {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 14px;
    margin-bottom: 16px;
  }

  .info-row {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    padding: 4px 0;
  }

  .info-row .lbl {
    color: var(--text-tertiary);
  }

  .info-row .val {
    color: var(--text-primary);
    font-weight: 600;
  }

  .status-ok {
    color: var(--success, #2b7a4d);
  }

  .divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 16px 0;
  }

  .password-form {
    display: flex;
    flex-direction: column;
    gap: 10px;
    max-width: 320px;
  }

  .alert {
    padding: 8px 12px;
    border-radius: var(--radius);
    font-size: 12px;
    margin-bottom: 10px;
  }

  .alert-success {
    background: rgba(43, 122, 77, 0.15);
    border: 1px solid #2b7a4d;
    color: var(--text-primary);
  }

  .alert-danger {
    background: rgba(220, 38, 38, 0.15);
    border: 1px solid #dc2626;
    color: var(--text-primary);
  }

  .data-actions {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .action-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }

  .action-desc strong {
    display: block;
    font-size: 13px;
    color: var(--text-primary);
  }

  .action-desc p {
    margin: 2px 0 0;
    font-size: 12px;
    color: var(--text-tertiary);
  }

  .danger-btn {
    color: var(--error);
    border: 1px solid var(--error);
  }

  @media (max-width: 640px) {
    .modal-body {
      flex-direction: column;
    }
    .settings-nav {
      width: 100%;
      flex-direction: row;
      overflow-x: auto;
      border-right: none;
      border-bottom: 1px solid var(--border);
    }
    .field-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
