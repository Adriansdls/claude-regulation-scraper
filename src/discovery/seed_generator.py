"""Generate seed papers from a research question."""

from typing import List, Dict, Any
from ..models.paper import Paper
from ..infrastructure.llm_client import get_llm_client
from .api_clients import MultiSourceFetcher


class SeedGenerator:
    """Generate initial seed papers for a research question."""

    def __init__(self):
        self.llm = get_llm_client()
        self.fetcher = MultiSourceFetcher()

    async def generate_seeds(
        self, research_question: str, num_seeds: int = 10
    ) -> List[Paper]:
        """Generate seed papers for a research question.

        Args:
            research_question: The research question to explore
            num_seeds: Target number of seed papers

        Returns:
            List of seed papers
        """
        # Step 1: Generate search queries using LLM
        queries = await self._generate_search_queries(research_question)

        # Step 2: Search for papers using generated queries
        all_papers = []
        for query in queries:
            papers = await self.fetcher.search_papers(query, max_results=20)
            all_papers.extend(papers)

        # Deduplicate by paper_id
        unique_papers = {}
        for paper in all_papers:
            if paper.paper_id not in unique_papers:
                unique_papers[paper.paper_id] = paper

        papers = list(unique_papers.values())

        # Step 3: Score and rank papers
        scored_papers = await self._score_and_rank_papers(papers, research_question)

        # Return top N
        return scored_papers[:num_seeds]

    async def _generate_search_queries(self, research_question: str) -> List[str]:
        """Generate search queries for a research question using LLM.

        Args:
            research_question: The research question

        Returns:
            List of search queries
        """
        prompt = f"""Given this research question, generate 5-7 diverse search queries to find relevant academic papers.

Research Question: {research_question}

Requirements:
1. Include queries with different keyword combinations
2. Include queries for seminal/foundational papers
3. Include queries for recent advances
4. Include queries for specific methodologies
5. Use academic terminology
6. Make queries specific but not too narrow

Return your response as JSON:
{{
  "queries": [
    "query 1",
    "query 2",
    ...
  ],
  "reasoning": "Brief explanation of query strategy"
}}"""

        try:
            response = await self.llm.complete_json(prompt)
            return response.get("queries", [])
        except Exception as e:
            print(f"Error generating queries: {e}")
            # Fallback: use the research question directly
            return [research_question]

    async def _score_and_rank_papers(
        self, papers: List[Paper], research_question: str
    ) -> List[Paper]:
        """Score papers for relevance and rank them.

        Args:
            papers: List of papers to score
            research_question: The research question

        Returns:
            Papers sorted by relevance (highest first)
        """
        # For each paper, score its relevance
        for paper in papers:
            score, reasoning = await self._score_paper_relevance(paper, research_question)
            paper.relevance_score = score
            paper.relevance_reasoning = reasoning

        # Sort by relevance score
        papers.sort(key=lambda p: p.relevance_score or 0, reverse=True)

        return papers

    async def _score_paper_relevance(
        self, paper: Paper, research_question: str
    ) -> tuple[float, str]:
        """Score a single paper's relevance to the research question.

        Args:
            paper: Paper to score
            research_question: The research question

        Returns:
            (score, reasoning) where score is 0-1
        """
        # Use title and abstract for quick scoring
        paper_text = f"Title: {paper.title}\n\n"
        if paper.abstract:
            paper_text += f"Abstract: {paper.abstract}"
        else:
            paper_text += "Abstract: Not available"

        prompt = f"""Score the relevance of this paper to the research question.

Research Question: {research_question}

Paper:
{paper_text}

Score the paper's relevance on a scale of 0-1:
- 1.0: Directly addresses the research question
- 0.7-0.9: Highly relevant (methodology, related problem, key background)
- 0.5-0.6: Moderately relevant (related domain, useful context)
- 0.3-0.4: Tangentially relevant (some overlap)
- 0.0-0.2: Not relevant

Return as JSON:
{{
  "score": 0.0,
  "reasoning": "Brief explanation of relevance"
}}"""

        try:
            response = await self.llm.complete_json(prompt, max_tokens=300)
            score = float(response.get("score", 0.0))
            reasoning = response.get("reasoning", "")
            return score, reasoning
        except Exception as e:
            print(f"Error scoring paper {paper.paper_id}: {e}")
            # Default to moderate relevance if LLM fails
            return 0.5, "Scoring failed, using default"
