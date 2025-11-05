"""Frontier-based paper explorer with intelligent BFS."""

import asyncio
from collections import defaultdict
from typing import List, Set, Dict, Optional
from queue import PriorityQueue
from dataclasses import dataclass
from datetime import datetime

from ..models.paper import Paper
from ..infrastructure.config import get_config
from .api_clients import MultiSourceFetcher, SemanticScholarClient
from .relevance_scorer import RelevanceScorer


@dataclass
class FrontierItem:
    """Item in the exploration frontier."""

    paper_id: str
    priority: float  # Higher = more important
    discovered_via: str  # How we found this paper
    parent_id: Optional[str] = None

    def __lt__(self, other):
        # Higher priority first (negate for max heap)
        return self.priority > other.priority


class ExplorationStats:
    """Statistics about the exploration process."""

    def __init__(self):
        self.papers_explored = 0
        self.papers_relevant = 0
        self.papers_skipped = 0
        self.frontier_size = 0
        self.start_time = datetime.now()
        self.relevance_distribution = defaultdict(int)  # score bucket -> count

    def add_paper(self, paper: Paper):
        """Record a paper being explored."""
        self.papers_explored += 1

        if paper.relevance_score and paper.relevance_score >= 0.6:
            self.papers_relevant += 1

        # Track distribution
        if paper.relevance_score:
            bucket = int(paper.relevance_score * 10) / 10  # 0.1 buckets
            self.relevance_distribution[bucket] += 1

    def should_stop(self, config) -> tuple[bool, str]:
        """Determine if exploration should stop.

        Returns:
            (should_stop, reason)
        """
        # Stop if we've hit max papers
        if self.papers_explored >= config.max_papers:
            return True, f"Reached max papers limit ({config.max_papers})"

        # Stop if last N papers were all low relevance
        recent_low = 0
        recent_window = 50
        if self.papers_explored > recent_window:
            # Check if we're finding relevant papers
            if self.papers_relevant / self.papers_explored < 0.1:
                return True, "Diminishing returns: <10% relevant papers found"

        return False, ""

    def __str__(self):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return f"""Exploration Stats:
- Papers explored: {self.papers_explored}
- Relevant papers: {self.papers_relevant} ({self.papers_relevant / max(self.papers_explored, 1) * 100:.1f}%)
- Frontier size: {self.frontier_size}
- Time elapsed: {elapsed:.1f}s
- Papers/minute: {self.papers_explored / (elapsed / 60):.1f}"""


class FrontierExplorer:
    """Explore papers using frontier-based search with relevance scoring."""

    def __init__(self, research_question: str):
        """Initialize explorer.

        Args:
            research_question: Research question to explore
        """
        self.research_question = research_question
        self.config = get_config()
        self.fetcher = MultiSourceFetcher()
        self.s2_client = SemanticScholarClient()
        self.scorer = RelevanceScorer(research_question)

        # State
        self.frontier: PriorityQueue[FrontierItem] = PriorityQueue()
        self.visited: Set[str] = set()
        self.relevant_papers: List[Paper] = []
        self.stats = ExplorationStats()

    async def explore(
        self,
        seed_papers: List[Paper],
        max_papers: Optional[int] = None,
        relevance_threshold: Optional[float] = None,
    ) -> List[Paper]:
        """Explore papers starting from seeds.

        Args:
            seed_papers: Initial seed papers
            max_papers: Maximum papers to explore (overrides config)
            relevance_threshold: Minimum relevance score (overrides config)

        Returns:
            List of relevant papers found
        """
        # Override config if specified
        if max_papers:
            self.config.max_papers = max_papers
        if relevance_threshold:
            self.config.relevance_threshold = relevance_threshold

        # Initialize frontier with seeds
        for paper in seed_papers:
            self.frontier.put(
                FrontierItem(
                    paper_id=paper.paper_id,
                    priority=paper.relevance_score or 0.9,
                    discovered_via="seed",
                )
            )
            # Add seeds to relevant papers if above threshold
            if paper.relevance_score and paper.relevance_score >= self.config.relevance_threshold:
                self.relevant_papers.append(paper)

        print(f"Starting exploration with {len(seed_papers)} seed papers...")
        print(f"Target: {self.config.max_papers} papers, threshold: {self.config.relevance_threshold}")

        # Main exploration loop
        while not self.frontier.empty():
            # Check stopping criteria
            should_stop, reason = self.stats.should_stop(self.config)
            if should_stop:
                print(f"\nStopping: {reason}")
                break

            # Get next paper from frontier
            item = self.frontier.get()

            # Skip if already visited
            if item.paper_id in self.visited:
                self.stats.papers_skipped += 1
                continue

            # Mark as visited
            self.visited.add(item.paper_id)

            # Fetch paper details
            paper = await self.fetcher.fetch_paper(item.paper_id)
            if not paper:
                continue

            # Track discovery provenance
            paper.discovered_via = item.discovered_via

            # Score relevance if not already scored
            if paper.relevance_score is None:
                score, reasoning = await self.scorer.score_paper(paper)
                paper.relevance_score = score
                paper.relevance_reasoning = reasoning

            # Update stats
            self.stats.add_paper(paper)

            # Add to relevant papers if above threshold
            if paper.relevance_score >= self.config.relevance_threshold:
                self.relevant_papers.append(paper)

            # Print progress
            if self.stats.papers_explored % 10 == 0:
                print(f"\rExplored: {self.stats.papers_explored}, Relevant: {self.stats.papers_relevant}, Frontier: {self.frontier.qsize()}", end="")

            # Expand frontier if paper is relevant
            if paper.relevance_score >= self.config.relevance_threshold * 0.8:
                await self._expand_frontier(paper)

            # Update frontier size
            self.stats.frontier_size = self.frontier.qsize()

        print("\n")
        print(self.stats)

        # Sort by relevance
        self.relevant_papers.sort(key=lambda p: p.relevance_score or 0, reverse=True)

        return self.relevant_papers

    async def _expand_frontier(self, paper: Paper):
        """Expand frontier by adding references and citations.

        Args:
            paper: Paper to expand from
        """
        relevance_score = paper.relevance_score or 0.5

        # Priority decay factors
        reference_decay = 0.9  # References slightly less important
        citation_decay = 0.85  # Citations even less important

        # Add backward citations (references)
        for ref_id in paper.references[:50]:  # Limit to first 50
            if ref_id not in self.visited:
                self.frontier.put(
                    FrontierItem(
                        paper_id=ref_id,
                        priority=relevance_score * reference_decay,
                        discovered_via=f"reference_from:{paper.paper_id}",
                        parent_id=paper.paper_id,
                    )
                )

        # Add forward citations (papers citing this)
        # Only fetch if paper is highly relevant (expensive operation)
        if relevance_score >= 0.8:
            citations = await self.s2_client.get_paper_citations(paper.paper_id, limit=50)

            for cit in citations[:30]:  # Limit to first 30
                cit_paper_id = cit.get("citedPaper", {}).get("paperId")
                if cit_paper_id and cit_paper_id not in self.visited:
                    # Boost priority if citation is influential
                    boost = 1.1 if cit.get("isInfluential", False) else 1.0

                    self.frontier.put(
                        FrontierItem(
                            paper_id=cit_paper_id,
                            priority=relevance_score * citation_decay * boost,
                            discovered_via=f"cited_by:{paper.paper_id}",
                            parent_id=paper.paper_id,
                        )
                    )

    async def get_exploration_graph(self) -> Dict[str, List[str]]:
        """Get the exploration graph (for visualization).

        Returns:
            Dict mapping paper_id to list of paper_ids it led to
        """
        graph = defaultdict(list)

        # Build graph from relevant papers
        for paper in self.relevant_papers:
            if paper.discovered_via and ":" in paper.discovered_via:
                parent_id = paper.discovered_via.split(":")[1]
                graph[parent_id].append(paper.paper_id)

        return dict(graph)

    def get_discovery_statistics(self) -> Dict[str, any]:
        """Get detailed discovery statistics.

        Returns:
            Dictionary with various statistics
        """
        return {
            "total_explored": self.stats.papers_explored,
            "total_relevant": self.stats.papers_relevant,
            "relevance_rate": self.stats.papers_relevant / max(self.stats.papers_explored, 1),
            "avg_relevance": (
                sum(p.relevance_score or 0 for p in self.relevant_papers) / len(self.relevant_papers)
                if self.relevant_papers
                else 0
            ),
            "papers_by_year": self._papers_by_year(),
            "papers_by_venue": self._papers_by_venue(),
            "top_authors": self._top_authors(),
            "discovery_methods": self._discovery_methods(),
        }

    def _papers_by_year(self) -> Dict[int, int]:
        """Count papers by year."""
        by_year = defaultdict(int)
        for paper in self.relevant_papers:
            if paper.year:
                by_year[paper.year] += 1
        return dict(sorted(by_year.items()))

    def _papers_by_venue(self) -> Dict[str, int]:
        """Count papers by venue."""
        by_venue = defaultdict(int)
        for paper in self.relevant_papers:
            if paper.metadata.venue:
                by_venue[paper.metadata.venue] += 1
        # Return top 10
        return dict(sorted(by_venue.items(), key=lambda x: x[1], reverse=True)[:10])

    def _top_authors(self) -> List[tuple[str, int]]:
        """Get most frequent authors."""
        author_counts = defaultdict(int)
        for paper in self.relevant_papers:
            for author in paper.authors:
                author_counts[author.name] += 1
        # Return top 10
        return sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    def _discovery_methods(self) -> Dict[str, int]:
        """Count papers by discovery method."""
        methods = defaultdict(int)
        for paper in self.relevant_papers:
            if paper.discovered_via:
                method = paper.discovered_via.split(":")[0]
                methods[method] += 1
        return dict(methods)
