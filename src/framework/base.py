from abc import ABC, abstractmethod
from typing import Any, Dict, List

class ETLTask(ABC):
    """Abstract base class for an individual atomic task."""
    name: str = "base_task"
    max_retries: int = 2
    backoff_seconds: float = 1.0

    @abstractmethod
    def execute(self, context: Any) -> Dict[str, Any]:
        """
        Executes task logic.
        Receives ETLContext and returns a dictionary of output state updates.
        """
        pass

class ETLJob(ABC):
    """Abstract base class for a multi-task ETL job."""
    name: str
    description: str = ""
    tasks: List[ETLTask] = []

    def get_task(self, task_name: str) -> ETLTask:
        for task in self.tasks:
            if task.name == task_name:
                return task
        valid_tasks = [t.name for t in self.tasks]
        raise KeyError(f"Task '{task_name}' not found in job '{self.name}'. Available: {valid_tasks}")
