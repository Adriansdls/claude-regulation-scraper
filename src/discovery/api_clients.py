"""API clients for paper discovery services."""

import asyncio
import time
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
import aiohttp

# Optional: arxiv library (may not be available in all environments)
try:
    import arxiv as arxiv_api
    ARXIV_AVAILABLE = True
except ImportError:
    ARXIV_AVAILABLE = False
    arxiv_api = None

if TYPE_CHECKING:
    from typing import Any as ArxivResult
elif ARXIV_AVAILABLE:
    ArxivResult = arxiv_api.Result
else:
    ArxivResult = Any

from ..models.paper import Paper, Author, PaperSource, PaperMetadata
from ..infrastructure.cache import get_cache
from ..infrastructure.config import get_config


class SemanticScholarClient:
    """Client for Semantic Scholar API."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self):
        self.config = get_config()
        self.cache = get_cache()
        self.api_key = self.config.semantic_scholar_api_key
        self.rate_limit_delay = 0.1  # 100ms between requests (conservative)
        self.last_request_time = 0

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key if available."""
        headers = {"User-Agent": "ResearchGraphExplorer/0.1"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    async def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    async def get_paper(self, paper_id: str, fields: Optional[List[str]] = None) -> Optional[Paper]:
        """Get paper by Semantic Scholar ID.

        Args:
            paper_id: Semantic Scholar paper ID or DOI/ArXiv ID
            fields: Fields to retrieve (default: comprehensive set)

        Returns:
            Paper object or None if not found
        """
        # Check cache
        cache_key = f"s2_paper:{paper_id}"
        cached = await self.cache.get(cache_key)
        if cached:
            return Paper(**cached)

        # Default fields
        if fields is None:
            fields = [
                "paperId",
                "title",
                "abstract",
                "year",
                "authors",
                "externalIds",
                "url",
                "venue",
                "publicationDate",
                "citationCount",
                "referenceCount",
                "influentialCitationCount",
                "isOpenAccess",
                "openAccessPdf",
                "fieldsOfStudy",
                "s2FieldsOfStudy",
                "citations",
                "references",
            ]

        url = f"{self.BASE_URL}/paper/{paper_id}"
        params = {"fields": ",".join(fields)}

        await self._rate_limit()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers(), params=params) as resp:
                    if resp.status == 404:
                        return None
                    elif resp.status != 200:
                        raise Exception(f"Semantic Scholar API error: {resp.status}")

                    data = await resp.json()

            # Convert to Paper model
            paper = self._convert_to_paper(data)

            # Cache
            await self.cache.set(cache_key, paper.dict(), ttl=86400)  # 24 hours

            return paper

        except Exception as e:
            print(f"Error fetching paper {paper_id}: {e}")
            return None

    async def search_papers(
        self, query: str, limit: int = 100, fields: Optional[List[str]] = None
    ) -> List[Paper]:
        """Search for papers by query.

        Args:
            query: Search query
            limit: Maximum number of results
            fields: Fields to retrieve

        Returns:
            List of Paper objects
        """
        # Check cache
        cache_key = f"s2_search:{query}:{limit}"
        cached = await self.cache.get(cache_key)
        if cached:
            return [Paper(**p) for p in cached]

        if fields is None:
            fields = [
                "paperId",
                "title",
                "abstract",
                "year",
                "authors",
                "externalIds",
                "citationCount",
                "isOpenAccess",
                "fieldsOfStudy",
            ]

        url = f"{self.BASE_URL}/paper/search"
        params = {"query": query, "limit": min(limit, 100), "fields": ",".join(fields)}

        await self._rate_limit()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers(), params=params) as resp:
                    if resp.status != 200:
                        raise Exception(f"Semantic Scholar API error: {resp.status}")

                    data = await resp.json()

            papers = [self._convert_to_paper(p) for p in data.get("data", [])]

            # Cache
            await self.cache.set(cache_key, [p.dict() for p in papers], ttl=3600)  # 1 hour

            return papers

        except Exception as e:
            print(f"Error searching papers: {e}")
            return []

    async def get_paper_citations(
        self, paper_id: str, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get papers that cite this paper.

        Args:
            paper_id: Semantic Scholar paper ID
            limit: Maximum number of citations

        Returns:
            List of citation data
        """
        url = f"{self.BASE_URL}/paper/{paper_id}/citations"
        params = {"limit": min(limit, 1000), "fields": "paperId,title,year,citationCount"}

        await self._rate_limit()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers(), params=params) as resp:
                    if resp.status != 200:
                        return []

                    data = await resp.json()
                    return data.get("data", [])

        except Exception:
            return []

    async def get_paper_references(
        self, paper_id: str, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get papers that this paper cites.

        Args:
            paper_id: Semantic Scholar paper ID
            limit: Maximum number of references

        Returns:
            List of reference data
        """
        url = f"{self.BASE_URL}/paper/{paper_id}/references"
        params = {"limit": min(limit, 1000), "fields": "paperId,title,year,citationCount"}

        await self._rate_limit()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers(), params=params) as resp:
                    if resp.status != 200:
                        return []

                    data = await resp.json()
                    return data.get("data", [])

        except Exception:
            return []

    def _convert_to_paper(self, data: Dict[str, Any]) -> Paper:
        """Convert Semantic Scholar API response to Paper model."""
        paper_id = data.get("paperId", "")

        # Authors
        authors = []
        for author_data in data.get("authors", []):
            authors.append(
                Author(
                    name=author_data.get("name", "Unknown"),
                    author_id=author_data.get("authorId"),
                )
            )

        # Metadata
        metadata = PaperMetadata(
            doi=data.get("externalIds", {}).get("DOI"),
            arxiv_id=data.get("externalIds", {}).get("ArXiv"),
            pubmed_id=data.get("externalIds", {}).get("PubMed"),
            venue=data.get("venue"),
            citation_count=data.get("citationCount", 0),
            reference_count=data.get("referenceCount", 0),
            influential_citation_count=data.get("influentialCitationCount", 0),
            is_open_access=data.get("isOpenAccess", False),
            pdf_url=data.get("openAccessPdf", {}).get("url") if data.get("openAccessPdf") else None,
            fields_of_study=data.get("fieldsOfStudy", []),
            s2_fields={
                f.get("category", ""): f.get("source", "")
                for f in data.get("s2FieldsOfStudy", [])
            },
        )

        # Parse date
        pub_date = None
        if data.get("publicationDate"):
            try:
                pub_date = datetime.fromisoformat(data["publicationDate"])
            except Exception:
                pass

        # References and citations
        references = []
        if "references" in data:
            references = [ref.get("paperId", "") for ref in data["references"] if ref.get("paperId")]

        cited_by = []
        if "citations" in data:
            cited_by = [cit.get("paperId", "") for cit in data["citations"] if cit.get("paperId")]

        return Paper(
            paper_id=paper_id,
            external_ids=data.get("externalIds", {}),
            title=data.get("title", "Unknown Title"),
            abstract=data.get("abstract"),
            authors=authors,
            year=data.get("year"),
            publication_date=pub_date,
            references=references,
            cited_by=cited_by,
            metadata=metadata,
            source=PaperSource.SEMANTIC_SCHOLAR,
        )


class ArXivClient:
    """Client for arXiv API."""

    def __init__(self):
        self.cache = get_cache()

    async def search_papers(self, query: str, max_results: int = 100) -> List[Paper]:
        """Search arXiv for papers.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of Paper objects
        """
        # Check if arxiv library is available
        if not ARXIV_AVAILABLE:
            print("Warning: arxiv library not available. Skipping arXiv search.")
            return []

        # Check cache
        cache_key = f"arxiv_search:{query}:{max_results}"
        cached = await self.cache.get(cache_key)
        if cached:
            return [Paper(**p) for p in cached]

        try:
            search = arxiv_api.Search(
                query=query, max_results=max_results, sort_by=arxiv_api.SortCriterion.Relevance
            )

            papers = []
            for result in search.results():
                paper = self._convert_to_paper(result)
                papers.append(paper)

            # Cache
            await self.cache.set(cache_key, [p.dict() for p in papers], ttl=3600)

            return papers

        except Exception as e:
            print(f"Error searching arXiv: {e}")
            return []

    def _convert_to_paper(self, result: ArxivResult) -> Paper:
        """Convert arXiv result to Paper model."""
        arxiv_id = result.entry_id.split("/")[-1]

        authors = [Author(name=author.name) for author in result.authors]

        metadata = PaperMetadata(
            arxiv_id=arxiv_id,
            pdf_url=result.pdf_url,
            is_open_access=True,
            fields_of_study=[cat for cat in result.categories],
        )

        return Paper(
            paper_id=f"arXiv:{arxiv_id}",
            external_ids={"ArXiv": arxiv_id},
            title=result.title,
            abstract=result.summary,
            authors=authors,
            year=result.published.year if result.published else None,
            publication_date=result.published,
            metadata=metadata,
            source=PaperSource.ARXIV,
        )


class MultiSourceFetcher:
    """Fetcher that tries multiple sources with fallback."""

    def __init__(self):
        self.semantic_scholar = SemanticScholarClient()
        self.arxiv = ArXivClient()

    async def fetch_paper(self, paper_id: str) -> Optional[Paper]:
        """Fetch paper from multiple sources.

        Args:
            paper_id: Paper identifier (can be Semantic Scholar ID, DOI, arXiv ID)

        Returns:
            Paper object or None
        """
        # Try Semantic Scholar first (has most comprehensive data)
        paper = await self.semantic_scholar.get_paper(paper_id)
        if paper:
            return paper

        # If it's an arXiv ID, try arXiv directly
        if "arxiv" in paper_id.lower():
            arxiv_id = paper_id.replace("arXiv:", "")
            papers = await self.arxiv.search_papers(f"id:{arxiv_id}", max_results=1)
            if papers:
                return papers[0]

        return None

    async def search_papers(self, query: str, max_results: int = 100) -> List[Paper]:
        """Search for papers across multiple sources.

        Args:
            query: Search query
            max_results: Maximum number of results per source

        Returns:
            Combined list of papers (deduplicated)
        """
        # Search both sources in parallel
        results = await asyncio.gather(
            self.semantic_scholar.search_papers(query, limit=max_results),
            self.arxiv.search_papers(query, max_results=max_results),
            return_exceptions=True,
        )

        # Combine and deduplicate
        papers = []
        seen_titles = set()

        for result in results:
            if isinstance(result, Exception):
                continue
            for paper in result:
                # Simple deduplication by title
                title_key = paper.title.lower().strip()
                if title_key not in seen_titles:
                    papers.append(paper)
                    seen_titles.add(title_key)

        return papers
