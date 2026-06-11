"""
Base strategy interface for the COT project.

Harness Engineering integration:
Each strategy MUST declare which of the five subsystems it utilizes.
This enables systematic ablation studies (controlled variable exclusion tests)
to quantify the marginal contribution of each subsystem.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List

from models.base import BaseModel
from tasks.base import BaseTask


class BaseStrategy(ABC):
    """Abstract base class for COT reasoning strategies."""

    def __init__(self, name: str, model: BaseModel, task: BaseTask, **kwargs):
        self.name = name
        self.model = model
        self.task = task
        self.config = kwargs

    @abstractmethod
    def run(self, example: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Run the strategy on a single example.

        Returns:
            A dict with at least:
            - "prediction": str, the extracted answer
            - "output": str, the raw model output
            - "metadata": dict, strategy-specific info
        """
        pass

    def get_strategy_info(self) -> Dict[str, Any]:
        """Return strategy metadata for experiment tracking."""
        return {
            "name": self.name,
            "config": self.config,
            "harness_subsystems": self.harness_subsystems(),
        }

    def harness_subsystems(self) -> Dict[str, bool]:
        """
        Declare which Harness Engineering subsystems this strategy uses.

        Five subsystems (walkinglabs model):
        - instructions:  structured prompt templates (system/human instructions)
        - tools:         external tools (retriever, calculator, search, etc.)
        - environment:   task environment (dataset, answer extraction, evaluation)
        - state:         runtime state tracking (intermediate results, reasoning steps)
        - feedback:      feedback loops (verification, critique, self-reflection)

        Subclasses MUST override this to accurately reflect their design.
        """
        return {
            "instructions": True,
            "tools": False,
            "environment": True,
            "state": False,
            "feedback": False,
        }
