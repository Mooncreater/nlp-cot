"""
Base task interface for the COT project.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Iterator


class BaseTask(ABC):
    """Abstract base class for task environments."""

    def __init__(self, name: str, **kwargs):
        self.name = name
        self.config = kwargs

    @abstractmethod
    def load_data(self, split: str = "dev") -> List[Dict[str, Any]]:
        """Load dataset for the given split."""
        pass

    @abstractmethod
    def format_prompt(self, example: Dict[str, Any]) -> str:
        """Format an example into a prompt string."""
        pass

    @abstractmethod
    def extract_answer(self, text: str) -> str:
        """Extract the answer choice from generated text."""
        pass

    @abstractmethod
    def evaluate(self, prediction: str, example: Dict[str, Any]) -> bool:
        """Check if prediction matches the ground truth."""
        pass

    def get_task_info(self) -> Dict[str, Any]:
        """Return task metadata for experiment tracking."""
        return {
            "name": self.name,
            "config": self.config,
        }
