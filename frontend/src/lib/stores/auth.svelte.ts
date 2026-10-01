import { api, configureApi } from "../api/client";

const TOKEN_KEY = "aiEnsembleToken";
const USER_KEY = "aiEnsembleUser";
const REFRESH_KEY = "aiEnsembleRefresh";

interface AuthState {
  token: string | null;
  user: string | null;
  loading: boolean;
  error: string | null;
}

function decodeSub(token: string): string | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.sub ?? null;
  } catch {
    return null;
  }
}

interface SecureStore {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  removeItem(key: string): Promise<void>;
  isMobile: boolean;
}

// Default store: web localStorage. Behavior is identical to before.
const webStore: SecureStore = {
  isMobile: false,
  async getItem(key: string) {
    return localStorage.getItem(key);
  },
  async setItem(key: string, value: string) {
    localStorage.setItem(key, value);
  },
  async removeItem(key: string) {
    localStorage.removeItem(key);
  },
};

// Lazily resolved at init: on a Capacitor Android build we swap in the
// OS secure storage (Android Keystore-backed) so tokens are never in
// web localStorage. Falls back to the web store elsewhere.
let store: SecureStore = webStore;

async function resolveStore(): Promise<void> {
  try {
    const win = window as unknown as { Capacitor?: { isNativePlatform(): boolean; getPlatform(): string } };
    if (win.Capacitor?.isNativePlatform()) {
      const mod = await import("@aparajita/capacitor-secure-storage");
      const SecureStorage = mod.SecureStorage ?? (mod as unknown as { default: unknown }).default;
      store = {
        isMobile: true,
        async getItem(key: string) {
          try {
            return (await (SecureStorage as { getItem(k: string): Promise<string | null> }).getItem(key)) ?? null;
          } catch {
            return null;
          }
        },
        async setItem(key: string, value: string) {
          await (SecureStorage as { setItem(k: string, v: string): Promise<void> }).setItem(key, value);
        },
        async removeItem(key: string) {
          try {
            await (SecureStorage as { removeItem(k: string): Promise<void> }).removeItem(key);
          } catch {
            /* ignore */
          }
        },
      };
    }
  } catch {
    store = webStore;
  }
}

class AuthStore {
  #state = $state<AuthState>({
    token: null,
    user: null,
    loading: false,
    error: null,
  });

  get token() {
    return this.#state.token;
  }
  get user() {
    return this.#state.user;
  }
  get loading() {
    return this.#state.loading;
  }
  get error() {
    return this.#state.error;
  }
  get isAuthenticated() {
    return !!this.#state.token;
  }
  get isMobile() {
    return store.isMobile;
  }

  async init(): Promise<void> {
    await resolveStore();
    configureApi({
      getToken: () => this.#state.token,
      onUnauthorized: () => this.#handleUnauthorized(),
      refreshToken: () => this.tryRefresh(),
    });
    const token = await store.getItem(TOKEN_KEY);
    const user = await store.getItem(USER_KEY);
    if (token) {
      // Check if token is expired and refresh before loading any data.
      // This prevents the "Preparing models..." stuck state when returning
      // to the tab after the access token has expired.
      if (this.#isTokenExpired(token)) {
        const refreshed = await this.tryRefresh();
        if (!refreshed) {
          // Refresh failed — clear and show login
          await this.#clearStorage();
          return;
        }
      } else {
        this.#state.token = token;
        this.#state.user = user;
        this.#scheduleProactiveRefresh();
      }
    }
  }

  #isTokenExpired(token: string): boolean {
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      const exp = payload.exp;
      if (!exp) return true;
      // Consider token expired 30 seconds before actual expiry
      return exp * 1000 < Date.now() + 30000;
    } catch {
      return true;
    }
  }

  #refreshTimer: ReturnType<typeof setTimeout> | null = null;

  #scheduleProactiveRefresh(): void {
    if (this.#refreshTimer) {
      clearTimeout(this.#refreshTimer);
      this.#refreshTimer = null;
    }
    // Refresh 5 minutes before the 60-minute access token expires.
    // This prevents any 401 from ever reaching the user.
    const refreshMs = 55 * 60 * 1000;
    this.#refreshTimer = setTimeout(async () => {
      const ok = await this.tryRefresh();
      if (ok) {
        this.#scheduleProactiveRefresh();
      }
    }, refreshMs);
  }

  async login(email: string, password: string): Promise<boolean> {
    this.#state.loading = true;
    this.#state.error = null;
    try {
      const res = await api.login(email, password, store.isMobile ? "mobile" : undefined);
      this.#state.token = res.access_token;
      this.#state.user = email || decodeSub(res.access_token) || "user";
      await store.setItem(TOKEN_KEY, res.access_token);
      await store.setItem(USER_KEY, this.#state.user);
      if (res.refresh_token) {
        await store.setItem(REFRESH_KEY, res.refresh_token);
      }
      this.#scheduleProactiveRefresh();
      return true;
    } catch (e) {
      this.#state.error = e instanceof Error ? e.message : "Login failed";
      return false;
    } finally {
      this.#state.loading = false;
    }
  }

  async register(email: string, password: string): Promise<boolean> {
    this.#state.loading = true;
    this.#state.error = null;
    try {
      const res = await api.register(email, password);
      this.#state.token = res.access_token;
      this.#state.user = email || decodeSub(res.access_token) || "user";
      await store.setItem(TOKEN_KEY, res.access_token);
      await store.setItem(USER_KEY, this.#state.user);
      if (res.refresh_token) {
        await store.setItem(REFRESH_KEY, res.refresh_token);
      }
      this.#scheduleProactiveRefresh();
      return true;
    } catch (e) {
      this.#state.error = e instanceof Error ? e.message : "Registration failed";
      return false;
    } finally {
      this.#state.loading = false;
    }
  }

  // Attempt a silent refresh using a stored refresh token.
  async tryRefresh(): Promise<boolean> {
    const refreshToken = await store.getItem(REFRESH_KEY);
    if (!refreshToken) return false;
    try {
      const res = await api.refresh(refreshToken);
      this.#state.token = res.access_token;
      await store.setItem(TOKEN_KEY, res.access_token);
      if (res.refresh_token) {
        await store.setItem(REFRESH_KEY, res.refresh_token);
      }
      return true;
    } catch {
      await this.#clearStorage();
      this.#state.token = null;
      this.#state.user = null;
      return false;
    }
  }

  async #handleUnauthorized(): Promise<void> {
    // Attempt silent refresh before logging out (works for both web and mobile).
    if (await this.tryRefresh()) {
      return;
    }
    await this.logout();
  }

  async logout(): Promise<void> {
    if (this.#refreshTimer) {
      clearTimeout(this.#refreshTimer);
      this.#refreshTimer = null;
    }
    if (store.isMobile) {
      const refreshToken = await store.getItem(REFRESH_KEY);
      if (refreshToken) {
        try {
          await api.logout(refreshToken);
        } catch {
          /* ignore network errors on logout */
        }
      }
    }
    await this.#clearStorage();
    this.#state.token = null;
    this.#state.user = null;
  }

  async #clearStorage(): Promise<void> {
    await store.removeItem(TOKEN_KEY);
    await store.removeItem(USER_KEY);
    await store.removeItem(REFRESH_KEY);
  }
}

export const auth = new AuthStore();
