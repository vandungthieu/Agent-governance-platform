from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolResult:
    name: str
    output: Any
    metadata: dict[str, Any]


class Tool(Protocol):
    name: str
    description: str

    def run(self, **kwargs: Any) -> ToolResult:
        ...

