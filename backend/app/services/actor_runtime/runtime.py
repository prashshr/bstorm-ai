from dataclasses import dataclass, field
from typing import Any

from app.services.actor_runtime.definition import AgentDefinition


@dataclass
class DiscussionEvent:
    """Typed event in the discussion stream."""

    type: str  # UserAsked, AgentResponded, AgentQuestioned, AgentCritiqued, AgentRevised, ConfidenceShifted, ConsensusUpdated
    discussion_id: int
    agent_id: str
    agent_name: str
    avatar: str
    content: str
    target_agent: str | None = None
    confidence_score: float = 0.90  # 0.0 to 1.0
    round_num: int = 1
    timestamp: float = 0.0


@dataclass
class AgentRuntime:
    """Dynamic, discussion-scoped runtime instance for an agent.
    Isolated per discussion ID so the underlying static AgentDefinition
    can participate in multiple concurrent discussions independently.
    """

    discussion_id: int
    definition: AgentDefinition
    confidence: float = 0.90  # 0.0 to 1.0
    inbox: list[DiscussionEvent] = field(default_factory=list)
    claims: list[str] = field(default_factory=list)
    retracted_claims: list[str] = field(default_factory=list)
    current_opinion: str = ""
    event_history: list[DiscussionEvent] = field(default_factory=list)

    def receive_event(self, event: DiscussionEvent) -> None:
        """Process incoming event and queue to inbox if directed to this agent."""
        self.event_history.append(event)
        if event.target_agent == self.definition.name or f"@{self.definition.name}" in event.content:
            self.inbox.append(event)

    def update_confidence(self, new_score: float) -> float:
        old = self.confidence
        self.confidence = max(0.0, min(1.0, new_score))
        return self.confidence
