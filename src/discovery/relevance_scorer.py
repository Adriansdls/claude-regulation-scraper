"""Score papers for relevance to research question."""

from typing import Optional
from ..models.paper import Paper
from ..infrastructure.llm_client import get_llm_client


class RelevanceScorer:
    """Score papers for relevance to a research question."""

    def __init__(self, research_question: str):
        """Initialize scorer.

        Args:
            research_question: The research question to score against
        """
        self.research_question = research_question
        self.llm = get_llm_client()

    async def score_paper(self, paper: Paper, use_full_text: bool = False) -> tuple[float, str]:
        """Score a paper's relevance.

        Args:
            paper: Paper to score
            use_full_text: Whether to use full text (slower but more accurate)

        Returns:
            (score, reasoning) where score is 0-1
        """
        # Prepare paper text
        if use_full_text and paper.full_text:
            # For long papers, use abstract + introduction + conclusion
            paper_text = self._extract_key_sections(paper)
        else:
            paper_text = f"Title: {paper.title}\n\n"
            if paper.abstract:
                paper_text += f"Abstract: {paper.abstract}"

        # Add metadata signals
        metadata_text = self._format_metadata(paper)

        prompt = f"""Score this paper's relevance to the research question.

Research Question: {self.research_question}

Paper:
{paper_text}

Additional Context:
{metadata_text}

Scoring Guidelines:
1.0: Directly addresses the research question
0.8-0.9: Highly relevant (key methodology, directly related problem)
0.6-0.7: Relevant (important background, related approach)
0.4-0.5: Moderately relevant (useful context, similar domain)
0.2-0.3: Tangentially relevant (some overlap in concepts)
0.0-0.1: Not relevant

Consider:
- Does it address the core question?
- Does it provide key methodology or background?
- Is it a seminal paper in the field?
- Does it have high citation count (indicates importance)?
- Is it recent (for emerging topics)?

Return as JSON:
{{
  "score": 0.0,
  "reasoning": "Detailed explanation of relevance",
  "key_contributions": ["contribution 1", "contribution 2"],
  "relevance_type": "direct|methodology|background|context|none"
}}"""

        try:
            response = await self.llm.complete_json(prompt, max_tokens=500)
            score = float(response.get("score", 0.0))
            reasoning = response.get("reasoning", "")

            # Store additional metadata
            paper.relevance_score = score
            paper.relevance_reasoning = reasoning

            return score, reasoning

        except Exception as e:
            print(f"Error scoring paper {paper.paper_id}: {e}")
            return 0.5, f"Error during scoring: {e}"

    def _extract_key_sections(self, paper: Paper) -> str:
        """Extract key sections from full text."""
        if not paper.structured_text:
            return paper.full_text[:5000] if paper.full_text else ""

        # Prioritize: abstract, introduction, conclusion
        sections = []
        for section_name in ["abstract", "introduction", "conclusion"]:
            if section_name in paper.structured_text:
                sections.append(f"{section_name.upper()}:\n{paper.structured_text[section_name]}")

        text = "\n\n".join(sections)

        # Limit length
        if len(text) > 8000:
            text = text[:8000] + "...(truncated)"

        return text

    def _format_metadata(self, paper: Paper) -> str:
        """Format paper metadata as context."""
        lines = []

        if paper.year:
            lines.append(f"Year: {paper.year}")

        if paper.metadata.citation_count:
            lines.append(f"Citations: {paper.metadata.citation_count}")

        if paper.metadata.venue:
            lines.append(f"Venue: {paper.metadata.venue}")

        if paper.metadata.fields_of_study:
            lines.append(f"Fields: {', '.join(paper.metadata.fields_of_study[:5])}")

        if paper.authors:
            author_names = [a.name for a in paper.authors[:3]]
            if len(paper.authors) > 3:
                author_names.append("et al.")
            lines.append(f"Authors: {', '.join(author_names)}")

        return "\n".join(lines) if lines else "No additional metadata"

    async def batch_score_papers(self, papers: list[Paper]) -> list[Paper]:
        """Score multiple papers.

        Args:
            papers: List of papers to score

        Returns:
            Papers with relevance scores updated
        """
        for paper in papers:
            score, reasoning = await self.score_paper(paper)
            paper.relevance_score = score
            paper.relevance_reasoning = reasoning

        return papers
