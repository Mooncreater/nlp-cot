"""
Base LLM interface for the COT project.
All model wrappers must inherit from BaseModel.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseModel(ABC):
    """Abstract base class for language model interfaces."""

    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        self.config = kwargs

    @abstractmethod
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stop: Optional[List[str]] = None,
        n: int = 1,
        **kwargs
    ) -> List[str]:
        """
        Generate text completions for the given prompt.

        Args:
            prompt: The input prompt string.
            temperature: Sampling temperature.
            max_tokens: Maximum number of tokens to generate.
            stop: Optional list of stop sequences.
            n: Number of completions to generate.

        Returns:
            A list of generated text strings (length == n).
        """
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stop: Optional[List[str]] = None,
        n: int = 1,
        **kwargs
    ) -> List[str]:
        """
        Generate chat completions for the given messages.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            temperature: Sampling temperature.
            max_tokens: Maximum number of tokens to generate.
            stop: Optional list of stop sequences.
            n: Number of completions to generate.

        Returns:
            A list of generated text strings (length == n).
        """
        pass

    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata for experiment tracking."""
        return {
            "model_name": self.model_name,
            "config": self.config,
        }
