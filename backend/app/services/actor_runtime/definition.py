from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentDefinition:
    """Static agent persona configuration (identity & capabilities).
    Stateless and shared across any number of discussion sessions.
    """

    id: str
    name: str
    avatar: str = "🤖"
    role_description: str = ""
    system_prompt: str = ""
    provider: str = ""
    model: str = ""
    temperature: float = 0.7
    capabilities: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)


DEFAULT_SPECIALIST_DEFINITIONS: dict[str, AgentDefinition] = {
    "architect": AgentDefinition(
        id="architect",
        name="System Architect",
        avatar="🏗️",
        role_description="Scalability, clean architecture & system topologies",
        system_prompt="You are a Senior System Architect. Analyze problems focusing on scalability, clean boundaries, modularity, and trade-offs.",
        model="default",
    ),
    "security": AgentDefinition(
        id="security",
        name="Security Auditor",
        avatar="🛡️",
        role_description="OWASP, zero-trust, threat modeling & vulnerability analysis",
        system_prompt="You are a Lead Security Auditor. Analyze proposals focusing on OWASP top 10, zero-trust, data privacy, and vulnerability risks.",
        model="default",
    ),
    "coder": AgentDefinition(
        id="coder",
        name="Pragmatic Coder",
        avatar="💻",
        role_description="Implementation simplicity, performance & robust code patterns",
        system_prompt="You are a Pragmatic Senior Engineer. Focus on clean code, testability, execution speed, and practical maintainability.",
        model="default",
    ),
    "advocate": AgentDefinition(
        id="advocate",
        name="Devil's Advocate",
        avatar="😈",
        role_description="Unstated assumptions, edge-case challenges & risk scenarios",
        system_prompt="You are the Devil's Advocate. Challenge assumptions, highlight edge cases, find failure modes, and question consensus.",
        model="default",
    ),
}
