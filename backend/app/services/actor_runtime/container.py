from app.services.actor_runtime.definition import AgentDefinition
from app.services.actor_runtime.moderator import ModeratorFSM
from app.services.actor_runtime.runtime import AgentRuntime, DiscussionEvent


class DiscussionContainer:
    """Discussion container instance owning runtime states for all assigned agents
    and the orchestrating ModeratorFSM.
    Inverts ownership so Discussion -> contains -> AgentRuntime A, B, Moderator.
    """

    def __init__(self, discussion_id: int, agent_definitions: list[AgentDefinition], max_rounds: int = 3):
        self.discussion_id = discussion_id
        self.runtimes: dict[str, AgentRuntime] = {
            defn.name: AgentRuntime(discussion_id=discussion_id, definition=defn)
            for defn in agent_definitions
        }
        self.moderator = ModeratorFSM(
            discussion_id=discussion_id,
            agents=list(self.runtimes.values()),
            max_rounds=max_rounds,
        )
        self.events: list[DiscussionEvent] = []

    def dispatch_event(self, event: DiscussionEvent) -> None:
        self.events.append(event)
        for runtime in self.runtimes.values():
            runtime.receive_event(event)

    def get_agent_runtime(self, name: str) -> AgentRuntime | None:
        return self.runtimes.get(name)
