from typing import Any

from app.services.actor_runtime.runtime import AgentRuntime, DiscussionEvent


class ModeratorFSM:
    """Finite State Machine governing discussion orchestration.
    Evaluates consensus stability, decides next speakers, triggers early stopping,
    and manages evolving consensus versions (v1 -> v2 -> v3).
    """

    def __init__(self, discussion_id: int, agents: list[AgentRuntime], max_rounds: int = 3):
        self.discussion_id = discussion_id
        self.agents = agents
        self.max_rounds = max_rounds
        self.current_round = 1
        self.consensus_version = 1
        self.state = "initial"  # initial -> stances -> cross_talk -> consensus -> complete

    def is_consensus_stable(self) -> bool:
        """Returns True if all agents share high confidence (>82%) and no unaddressed challenges remain."""
        if not self.agents:
            return True
        high_confidence = all(agent.confidence >= 0.82 for agent in self.agents)
        no_pending_inbox = not any(agent.inbox for agent in self.agents)
        return high_confidence and no_pending_inbox

    def advance_round(self) -> int:
        self.current_round += 1
        self.consensus_version += 1
        return self.current_round

    def should_terminate_early((self)) -> bool:
        """Determines if debate can terminate early due to stable consensus or max rounds reached."""
        if self.current_round >= self.max_rounds:
            return True
        return self.is_consensus_stable()
