import { debug } from "./debug.svelte";

export interface AgentRuntimeEvent {
  id: string;
  type: "UserAsked" | "AgentResponded" | "AgentQuestioned" | "AgentCritiqued" | "AgentRevised" | "ConfidenceShifted" | "ConsensusUpdated";
  discussionId: number;
  agentId: string;
  agentName: string;
  avatar: string;
  content: string;
  targetAgent?: string;
  confidenceScore: number; // 0-100
  roundNum: number;
  timestamp: number;
}

class AgentRuntimeStore {
  #events = $state<AgentRuntimeEvent[]>([]);
  #confidenceScores = $state<Record<string, number>>({});
  #consensusVersion = $state(1);

  get events() {
    return this.#events;
  }
  get confidenceScores() {
    return this.#confidenceScores;
  }
  get consensusVersion() {
    return this.#consensusVersion;
  }

  getConfidence(agentName: string): number {
    return this.#confidenceScores[agentName] ?? 90;
  }

  addEvent(event: Omit<AgentRuntimeEvent, "id" | "timestamp">): void {
    const entry: AgentRuntimeEvent = {
      ...event,
      id: `ev-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      timestamp: Date.now(),
    };
    this.#events = [...this.#events, entry];
    if (event.confidenceScore !== undefined) {
      this.#confidenceScores = {
        ...this.#confidenceScores,
        [event.agentName]: event.confidenceScore,
      };
    }
    if (event.type === "ConsensusUpdated") {
      this.#consensusVersion += 1;
    }
    debug.log(`[agentRuntime] Event: ${event.type} from ${event.agentName}`);
  }

  clear(): void {
    this.#events = [];
    this.#confidenceScores = {};
    this.#consensusVersion = 1;
  }
}

export const agentRuntime = new AgentRuntimeStore();
