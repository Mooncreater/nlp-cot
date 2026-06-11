"""
Base retriever interface for RAG-enhanced COT.
Harness Engineering mapping:
- Tools: the retriever acts as an external knowledge tool
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseRetriever(ABC):
    """Abstract base class for knowledge retrieval."""

    def __init__(self, name: str, **kwargs):
        self.name = name
        self.config = kwargs

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve relevant knowledge entries for the given query.

        Returns:
            List of dicts, each with at least:
            - "content": str, the knowledge text
            - "score": float, relevance score
            - "source": str, optional source identifier
        """
        pass

    def get_retriever_info(self) -> Dict[str, Any]:
        return {"name": self.name, "config": self.config}
