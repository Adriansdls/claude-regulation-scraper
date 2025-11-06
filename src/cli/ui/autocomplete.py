"""Smart autocomplete for commands and queries.

Provides intelligent suggestions based on context, history, and graph content.
"""

from typing import List, Dict, Optional, Iterable
from prompt_toolkit.completion import Completer, Completion, WordCompleter
from prompt_toolkit.document import Document


# Common query templates
QUERY_TEMPLATES = [
    "find gaps in the literature",
    "find gaps about {topic}",
    "detect communities using {algorithm}",
    "calculate {centrality} centrality",
    "who are the most influential authors",
    "show me the top papers by {metric}",
    "find papers about {topic}",
    "how is {paper} connected to {paper}",
    "find citation rings",
    "detect echo chambers",
    "show research trends over time",
    "analyze {author} collaboration patterns",
    "find papers published in {year}",
    "count papers by year",
    "show papers that cite {paper}",
    "find papers citing both {topic} and {topic}",
    "what topics are emerging",
    "show me disconnected communities",
    "find bridge papers between fields",
    "analyze path between {concept} and {concept}",
]

# Common commands
COMMANDS = [
    "help",
    "stats",
    "memory",
    "clear",
    "export markdown",
    "export json",
    "load session",
    "bookmarks",
    "themes",
    "exit",
    "quit",
]

# Centrality metrics
CENTRALITY_METRICS = [
    "pagerank",
    "betweenness",
    "closeness",
    "degree",
    "eigenvector",
]

# Community detection algorithms
COMMUNITY_ALGORITHMS = [
    "louvain",
    "leiden",
    "label_propagation",
]

# Common research topics (can be extended from graph)
COMMON_TOPICS = [
    "transformers",
    "graph neural networks",
    "attention mechanism",
    "BERT",
    "GPT",
    "deep learning",
    "neural networks",
    "machine learning",
    "natural language processing",
    "computer vision",
    "reinforcement learning",
]


class QueryCompleter(Completer):
    """Smart query completer with context awareness."""

    def __init__(
        self,
        knowledge_graph=None,
        enable_templates: bool = True,
        enable_fuzzy: bool = True
    ):
        """
        Initialize completer.

        Args:
            knowledge_graph: KnowledgeGraph instance for entity completion
            enable_templates: Enable query templates
            enable_fuzzy: Enable fuzzy matching
        """
        self.kg = knowledge_graph
        self.enable_templates = enable_templates
        self.enable_fuzzy = enable_fuzzy

        # Build completion list
        self.completions = []

        # Add commands
        self.completions.extend(COMMANDS)

        # Add query templates
        if enable_templates:
            self.completions.extend(QUERY_TEMPLATES)

        # Add entity names from graph
        if knowledge_graph:
            self._load_graph_entities()

    def _load_graph_entities(self):
        """Load entity names from knowledge graph."""
        try:
            # Add paper titles (limited to avoid overwhelming)
            if hasattr(self.kg, 'papers'):
                paper_titles = [p.get('title', '') for p in self.kg.papers[:100]]
                self.completions.extend([t for t in paper_titles if t])

            # Add author names
            if hasattr(self.kg, 'entities'):
                authors = [
                    e.get('text', '')
                    for e in self.kg.entities
                    if e.get('type') == 'PERSON'
                ][:50]
                self.completions.extend(authors)

            # Add key concepts
            concepts = [
                e.get('text', '')
                for e in self.kg.entities
                if e.get('type') in ['TECHNOLOGY', 'METHOD', 'CONCEPT']
            ][:100]
            self.completions.extend(concepts)

        except Exception:
            pass  # Gracefully handle if graph doesn't have expected structure

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        """
        Get completions for current input.

        Args:
            document: Current document
            complete_event: Completion event

        Yields:
            Completion objects
        """
        text = document.text_before_cursor.lower()

        # Handle empty input - show popular templates
        if not text.strip():
            for template in QUERY_TEMPLATES[:10]:
                yield Completion(
                    template,
                    start_position=0,
                    display=template,
                    display_meta="template"
                )
            return

        # Get word being typed
        word_before_cursor = document.get_word_before_cursor(WORD=True)

        # Match completions
        matches = []

        for completion_text in self.completions:
            comp_lower = completion_text.lower()

            # Exact start match
            if comp_lower.startswith(text):
                matches.append((completion_text, 0, "match"))

            # Word start match
            elif comp_lower.startswith(word_before_cursor.lower()):
                matches.append((completion_text, -len(word_before_cursor), "partial"))

            # Fuzzy match (contains)
            elif self.enable_fuzzy and text in comp_lower:
                matches.append((completion_text, 0, "fuzzy"))

        # Sort by relevance
        matches.sort(key=lambda x: (
            x[2] != "match",  # Exact matches first
            len(x[0]),  # Then by length
        ))

        # Yield top matches
        for completion_text, start_pos, match_type in matches[:50]:
            # Determine display meta
            if completion_text in COMMANDS:
                meta = "command"
            elif completion_text in QUERY_TEMPLATES:
                meta = "template"
            elif completion_text in CENTRALITY_METRICS:
                meta = "metric"
            elif completion_text in COMMUNITY_ALGORITHMS:
                meta = "algorithm"
            else:
                meta = "entity"

            yield Completion(
                completion_text,
                start_position=start_pos,
                display=completion_text,
                display_meta=meta
            )


def get_command_completer() -> WordCompleter:
    """
    Get simple command completer.

    Returns:
        WordCompleter for basic commands
    """
    return WordCompleter(
        COMMANDS,
        ignore_case=True,
        sentence=True,
        match_middle=True
    )


class ContextualCompleter(Completer):
    """Completer that adapts based on conversation context."""

    def __init__(self, base_completer: Completer):
        """
        Initialize contextual completer.

        Args:
            base_completer: Base completer to wrap
        """
        self.base_completer = base_completer
        self.recent_topics = []
        self.recent_entities = []

    def update_context(self, query: str, response: str):
        """
        Update context from query/response.

        Args:
            query: User query
            response: Agent response
        """
        # Extract topics mentioned
        for topic in COMMON_TOPICS:
            if topic.lower() in query.lower() or topic.lower() in response.lower():
                if topic not in self.recent_topics:
                    self.recent_topics.insert(0, topic)

        # Keep recent topics limited
        self.recent_topics = self.recent_topics[:20]

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        """Get completions with context awareness."""
        # Get base completions
        base_completions = list(self.base_completer.get_completions(document, complete_event))

        # Add recent topics as suggestions
        if not document.text.strip() and self.recent_topics:
            for topic in self.recent_topics[:5]:
                yield Completion(
                    f"tell me more about {topic}",
                    start_position=0,
                    display=f"tell me more about {topic}",
                    display_meta="suggestion"
                )

        # Return base completions
        for comp in base_completions:
            yield comp


def get_suggestions_for_query_type(query_type: str) -> List[str]:
    """
    Get suggested follow-up queries.

    Args:
        query_type: Type of query (gaps, communities, centrality, etc.)

    Returns:
        List of suggested follow-up queries
    """
    suggestions = {
        "gaps": [
            "show me the most important gaps",
            "find papers that could fill these gaps",
            "are there any authors working on these gaps?",
        ],
        "communities": [
            "show me the largest community",
            "find papers that bridge communities",
            "which communities are most isolated?",
        ],
        "centrality": [
            "show me papers with high betweenness",
            "find the most cited papers in this community",
            "who are the influential authors?",
        ],
        "echo_chambers": [
            "show me the strongest citation rings",
            "find communities with low external citations",
            "are there any papers that break the echo chamber?",
        ],
        "trends": [
            "which topics are growing fastest?",
            "show me emerging research areas",
            "what topics are declining?",
        ],
    }

    return suggestions.get(query_type, [])
