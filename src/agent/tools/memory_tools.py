"""Memory tools for context retention across sessions.

Allows the agent to save insights and recall them later, providing long-term
memory and context awareness.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path


class MemoryStore:
    """
    Persistent memory storage for agent insights.

    Stores insights as JSON with timestamps, tags, and full-text search.
    """

    def __init__(self, memory_file: str = None):
        """Initialize memory store."""
        if memory_file is None:
            # Default to user's home directory
            home = Path.home()
            memory_dir = home / ".rge" / "memory"
            memory_dir.mkdir(parents=True, exist_ok=True)
            memory_file = str(memory_dir / "insights.json")

        self.memory_file = memory_file
        self._ensure_memory_file()

    def _ensure_memory_file(self):
        """Ensure memory file exists."""
        if not os.path.exists(self.memory_file):
            with open(self.memory_file, 'w') as f:
                json.dump([], f)

    def save(self, insight: str, tags: List[str] = None, metadata: Dict = None) -> str:
        """
        Save an insight to memory.

        Args:
            insight: The insight text
            tags: Optional tags for categorization
            metadata: Optional additional metadata

        Returns:
            ID of saved insight
        """
        # Load existing
        with open(self.memory_file, 'r') as f:
            memories = json.load(f)

        # Create new insight
        insight_id = f"insight_{len(memories) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        memory_entry = {
            "id": insight_id,
            "insight": insight,
            "tags": tags or [],
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }

        memories.append(memory_entry)

        # Save
        with open(self.memory_file, 'w') as f:
            json.dump(memories, f, indent=2)

        return insight_id

    def search(self, query: str = None, tags: List[str] = None, limit: int = 10) -> List[Dict]:
        """
        Search memories.

        Args:
            query: Text to search for (searches in insight text)
            tags: Tags to filter by
            limit: Maximum results to return

        Returns:
            List of matching memory entries
        """
        with open(self.memory_file, 'r') as f:
            memories = json.load(f)

        results = []

        for memory in memories:
            # Filter by tags if specified
            if tags:
                if not any(tag in memory["tags"] for tag in tags):
                    continue

            # Filter by query if specified
            if query:
                query_lower = query.lower()
                if query_lower not in memory["insight"].lower():
                    # Also check tags
                    if not any(query_lower in tag.lower() for tag in memory["tags"]):
                        continue

            results.append(memory)

        # Sort by timestamp (most recent first)
        results.sort(key=lambda x: x["timestamp"], reverse=True)

        return results[:limit]

    def get_all(self) -> List[Dict]:
        """Get all memories."""
        with open(self.memory_file, 'r') as f:
            return json.load(f)

    def clear(self):
        """Clear all memories."""
        with open(self.memory_file, 'w') as f:
            json.dump([], f)


class SaveInsightTool:
    """
    Save important insights to memory.

    Allows the agent to remember key findings across sessions.
    """

    name = "save_insight"
    description = """
    Save an important insight or finding to long-term memory.

    Use this when you discover:
    - Important gaps in the literature
    - Significant echo chambers or citation patterns
    - Key influential papers or concepts
    - Interesting trends or patterns
    - Answers to user's research questions

    The insight will be saved with a timestamp and can be recalled later.
    This helps maintain context across multiple analysis sessions.

    Parameters:
    - insight: The insight text (what you discovered)
    - tags: List of tags for categorization (e.g., ["gap", "GNN", "underexplored"])
    - metadata: Optional additional information (dict)

    Returns the ID of the saved insight.

    Example:
    save_insight(
        insight="Found 5 important but isolated concepts in GNN literature",
        tags=["gap", "GNN", "isolated_concepts"],
        metadata={"num_gaps": 5, "importance_threshold": 0.5}
    )
    """

    def __init__(self, memory_store: MemoryStore = None):
        self.memory = memory_store or MemoryStore()

    def __call__(
        self,
        insight: str,
        tags: List[str] = None,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """Save insight to memory."""
        try:
            insight_id = self.memory.save(insight, tags, metadata)

            return {
                "success": True,
                "insight_id": insight_id,
                "message": f"Insight saved with ID: {insight_id}",
                "tags": tags or [],
                "interpretation": (
                    f"Saved insight to memory. You can recall it later using "
                    f"recall_insights with query or tags."
                )
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }


class RecallInsightsTool:
    """
    Recall previously saved insights from memory.

    Allows the agent to remember what it discovered in previous sessions.
    """

    name = "recall_insights"
    description = """
    Recall previously saved insights from memory.

    Use this when you need to:
    - Remember what you found in previous analyses
    - Check if you've already answered a similar question
    - Build on previous findings
    - Provide context from earlier work

    Parameters:
    - query: Text to search for (searches in insight text and tags)
    - tags: Filter by specific tags (e.g., ["gap", "GNN"])
    - limit: Maximum number of insights to return (default: 10)

    Returns list of matching insights with timestamps and metadata.

    Example:
    recall_insights(query="gaps in GNN", limit=5)
    recall_insights(tags=["echo_chamber", "citation_ring"])
    """

    def __init__(self, memory_store: MemoryStore = None):
        self.memory = memory_store or MemoryStore()

    def __call__(
        self,
        query: str = None,
        tags: List[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Recall insights from memory."""
        try:
            results = self.memory.search(query=query, tags=tags, limit=limit)

            if not results:
                return {
                    "success": True,
                    "num_results": 0,
                    "insights": [],
                    "interpretation": "No matching insights found in memory."
                }

            # Format for display
            formatted = []
            for memory in results:
                formatted.append({
                    "id": memory["id"],
                    "insight": memory["insight"],
                    "tags": memory["tags"],
                    "timestamp": memory["timestamp"],
                    "metadata": memory.get("metadata", {})
                })

            return {
                "success": True,
                "num_results": len(formatted),
                "insights": formatted,
                "interpretation": self._interpret_results(formatted, query, tags)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _interpret_results(self, insights, query, tags) -> str:
        """Generate human-readable interpretation."""
        if not insights:
            return "No insights found."

        num = len(insights)
        search_desc = []
        if query:
            search_desc.append(f"query '{query}'")
        if tags:
            search_desc.append(f"tags {tags}")

        search_text = " and ".join(search_desc) if search_desc else "all insights"

        most_recent = insights[0]["timestamp"][:10]  # Just the date

        return (
            f"Found {num} insight(s) matching {search_text}. "
            f"Most recent from {most_recent}. "
            f"These insights provide context from previous analyses."
        )
