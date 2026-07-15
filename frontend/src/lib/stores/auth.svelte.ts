import { api, configureApi } from "../api/client";

const TOKEN_KEY = "aiEnsembleToken";
const USER_KEY = "aiEnsembleUser";

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

  init(): void {
    configureApi({
      getToken: () => this.#state.token,
      onUnauthorized: () => this.logout(),
    });
    const token = sessionStorage.getItem(TOKEN_KEY);
    const user = sessionStorage.getItem(USER_KEY);
    if (token) {
      this.#state.token = token;
      this.#state.user = user;
    }
  }

  async login(email: string, password: string): Promise<boolean> {
    this.#state.loading = true;
    this.#state.error = null;
    try {
      const res = await api.login(email, password);
      this.#setAuth(res.access_token, email);
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
      this.#setAuth(res.access_token, email);
      return true;
    } catch (e) {
      this.#state.error = e instanceof Error ? e.message : "Registration failed";
      return false;
    } finally {
      this.#state.loading = false;
    }
  }

  #setAuth(token: string, email: string): void {
    this.#state.token = token;
    this.#state.user = email || decodeSub(token) || "user";
    sessionStorage.setItem(TOKEN_KEY, token);
    sessionStorage.setItem(USER_KEY, this.#state.user);
  }

  logout(): void {
    this.#state.token = null;
    this.#state.user = null;
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
  }
}

export const auth = new AuthStore();
