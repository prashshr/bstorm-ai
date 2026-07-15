export type LogLevel = "info" | "warn" | "error";

export interface LogEntry {
  ts: number;
  level: LogLevel;
  message: string;
}

const MAX_LOGS = 200;

class DebugStore {
  #logs = $state<LogEntry[]>([]);
  #open = $state(false);
  #filter = $state<LogLevel | "all">("all");

  get logs() {
    return this.#logs;
  }
  get open() {
    return this.#open;
  }
  get filter() {
    return this.#filter;
  }
  get filtered() {
    if (this.#filter === "all") return this.#logs;
    return this.#logs.filter((l) => l.level === this.#filter);
  }

  log(message: string, level: LogLevel = "info"): void {
    this.#logs.push({ ts: Date.now(), level, message });
    if (this.#logs.length > MAX_LOGS) this.#logs.shift();
    // Mirror to console for developers
    const fn = level === "error" ? console.error : level === "warn" ? console.warn : console.log;
    fn(`[ai-ensemble] ${message}`);
  }

  setFilter(f: LogLevel | "all"): void {
    this.#filter = f;
  }
  toggle(): void {
    this.#open = !this.#open;
  }
  clear(): void {
    this.#logs = [];
  }
}

export const debug = new DebugStore();
