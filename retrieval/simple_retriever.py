"""
Simple keyword-based retriever for quick RAG experiments.
Uses TF-IDF-like scoring with Jaccard similarity over tokenized words.
"""
import json
import math
import os
import re
from typing import List, Dict, Any

from .base import BaseRetriever


class SimpleKeywordRetriever(BaseRetriever):
    """Keyword-based retriever with a local knowledge base."""

    def __init__(self, knowledge_path: str = "data/knowledge_base.json", top_k: int = 3, **kwargs):
        super().__init__(name="simple_keyword", **kwargs)
        self.knowledge_path = knowledge_path
        self.default_top_k = top_k
        self.entries: List[Dict[str, Any]] = []
        self._load_knowledge()

    def _load_knowledge(self):
        if not os.path.exists(self.knowledge_path):
            # Initialize with an empty list if file doesn't exist
            self.entries = []
            return
        with open(self.knowledge_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.entries = data if isinstance(data, list) else data.get("entries", [])

    def _tokenize(self, text: str) -> set:
        """Simple tokenization: lowercase, extract alphabetic tokens."""
        text = text.lower()
        tokens = re.findall(r"[a-z]+", text)
        # Filter out very common stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                      "being", "have", "has", "had", "do", "does", "did", "will",
                      "would", "could", "should", "may", "might", "must", "shall",
                      "can", "need", "dare", "ought", "used", "to", "of", "in",
                      "for", "on", "with", "at", "by", "from", "as", "into",
                      "through", "during", "before", "after", "above", "below",
                      "between", "under", "and", "but", "or", "yet", "so", "if",
                      "because", "although", "though", "while", "where", "when",
                      "that", "which", "who", "whom", "whose", "what", "this",
                      "these", "those", "i", "you", "he", "she", "it", "we", "they",
                      "me", "him", "her", "us", "them", "my", "your", "his",
                      "its", "our", "their", "what", "how", "all", "any", "both",
                      "each", "few", "more", "most", "other", "some", "such",
                      "no", "nor", "not", "only", "own", "same", "than", "too",
                      "very", "just", "then", "now", "here", "there", "why",
                      "again", "once", "upon", "out", "up", "down", "off", "over",
                      "also", "get", "got", "gets", "one", "two", "three", "four",
                      "five", "six", "seven", "eight", "nine", "ten"}
        return set(t for t in tokens if t not in stop_words and len(t) > 2)

    def _score(self, query_tokens: set, entry_tokens: set) -> float:
        """Compute Jaccard-like relevance score."""
        if not entry_tokens:
            return 0.0
        intersection = query_tokens & entry_tokens
        union = query_tokens | entry_tokens
        if not union:
            return 0.0
        # Weighted Jaccard: boost exact matches
        return len(intersection) / len(union)

    def retrieve(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        k = top_k if top_k is not None else self.default_top_k
        query_tokens = self._tokenize(query)
        if not query_tokens or not self.entries:
            return []

        scored = []
        for entry in self.entries:
            content = entry.get("content", "")
            entry_tokens = self._tokenize(content)
            score = self._score(query_tokens, entry_tokens)
            if score > 0:
                scored.append({
                    "content": content,
                    "score": score,
                    "source": entry.get("source", "unknown"),
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]
