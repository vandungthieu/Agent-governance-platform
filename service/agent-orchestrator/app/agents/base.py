from abc import ABC, abstractmethod

from app.states.workflow import TaskType


class BaseAgent(ABC):
    @abstractmethod
    def run(self, input_text: str, task_type: TaskType | None = None) -> str:
        raise NotImplementedError
