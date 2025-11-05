"""PDF acquisition from multiple sources."""

import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import hashlib

from ..models.paper import Paper, PaperSource
from ..infrastructure.config import get_config
from ..infrastructure.cache import get_cache


class PDFDownloadResult:
    """Result of PDF download attempt."""

    def __init__(
        self,
        success: bool,
        pdf_path: Optional[str] = None,
        source: Optional[str] = None,
        error: Optional[str] = None,
        file_size: Optional[int] = None,
    ):
        self.success = success
        self.pdf_path = pdf_path
        self.source = source
        self.error = error
        self.file_size = file_size


class PDFDownloader:
    """Download PDFs from multiple sources with fallback strategy."""

    def __init__(self):
        self.config = get_config()
        self.cache = get_cache()
        self.papers_dir = Path(self.config.papers_dir)
        self.papers_dir.mkdir(parents=True, exist_ok=True)

    async def download_pdf(self, paper: Paper) -> PDFDownloadResult:
        """Download PDF for a paper using multi-source strategy.

        Strategy:
        1. Check if already downloaded
        2. Try arXiv (if arXiv ID exists)
        3. Try OpenAccess PDF URL from metadata
        4. Try Unpaywall API
        5. Try direct DOI resolution
        6. Give up gracefully

        Args:
            paper: Paper to download PDF for

        Returns:
            PDFDownloadResult with success status and path
        """
        # Check if already downloaded
        expected_path = self._get_pdf_path(paper)
        if expected_path.exists():
            return PDFDownloadResult(
                success=True,
                pdf_path=str(expected_path),
                source="cached",
                file_size=expected_path.stat().st_size,
            )

        # Try each source in order
        sources = [
            ("arxiv", self._download_from_arxiv),
            ("openaccess_url", self._download_from_url),
            ("unpaywall", self._download_from_unpaywall),
            ("doi", self._download_from_doi),
        ]

        for source_name, download_func in sources:
            try:
                result = await download_func(paper)
                if result.success:
                    # Update paper metadata
                    paper.has_pdf = True
                    paper.pdf_path = result.pdf_path
                    return result
            except Exception as e:
                print(f"Failed to download from {source_name}: {e}")
                continue

        # All sources failed
        return PDFDownloadResult(success=False, error="All download sources exhausted")

    async def _download_from_arxiv(self, paper: Paper) -> PDFDownloadResult:
        """Download from arXiv."""
        arxiv_id = paper.primary_arxiv_id
        if not arxiv_id:
            return PDFDownloadResult(success=False, error="No arXiv ID")

        # arXiv PDF URL format
        url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        return await self._download_pdf_from_url(url, paper, source="arxiv")

    async def _download_from_url(self, paper: Paper) -> PDFDownloadResult:
        """Download from open access PDF URL in metadata."""
        if not paper.metadata.pdf_url:
            return PDFDownloadResult(success=False, error="No PDF URL in metadata")

        url = str(paper.metadata.pdf_url)
        return await self._download_pdf_from_url(url, paper, source="openaccess")

    async def _download_from_unpaywall(self, paper: Paper) -> PDFDownloadResult:
        """Download using Unpaywall API."""
        doi = paper.primary_doi
        if not doi:
            return PDFDownloadResult(success=False, error="No DOI")

        # Unpaywall API
        unpaywall_url = f"https://api.unpaywall.org/v2/{doi}"
        params = {"email": "research-graph-explorer@example.com"}  # Unpaywall requires email

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(unpaywall_url, params=params, timeout=10) as resp:
                    if resp.status != 200:
                        return PDFDownloadResult(success=False, error=f"Unpaywall returned {resp.status}")

                    data = await resp.json()

                    # Check for OA location
                    best_oa = data.get("best_oa_location")
                    if best_oa and best_oa.get("url_for_pdf"):
                        pdf_url = best_oa["url_for_pdf"]
                        return await self._download_pdf_from_url(pdf_url, paper, source="unpaywall")

            return PDFDownloadResult(success=False, error="No OA PDF found in Unpaywall")

        except Exception as e:
            return PDFDownloadResult(success=False, error=f"Unpaywall error: {e}")

    async def _download_from_doi(self, paper: Paper) -> PDFDownloadResult:
        """Try to resolve DOI to PDF."""
        doi = paper.primary_doi
        if not doi:
            return PDFDownloadResult(success=False, error="No DOI")

        # Try DOI.org resolution
        doi_url = f"https://doi.org/{doi}"

        try:
            async with aiohttp.ClientSession() as session:
                # Follow redirects, see if we get a PDF
                async with session.get(
                    doi_url,
                    allow_redirects=True,
                    timeout=15,
                    headers={"Accept": "application/pdf"},
                ) as resp:
                    content_type = resp.headers.get("Content-Type", "")

                    if "application/pdf" in content_type:
                        # We got a PDF!
                        return await self._download_pdf_from_url(str(resp.url), paper, source="doi")

            return PDFDownloadResult(success=False, error="DOI did not resolve to PDF")

        except Exception as e:
            return PDFDownloadResult(success=False, error=f"DOI resolution error: {e}")

    async def _download_pdf_from_url(
        self, url: str, paper: Paper, source: str
    ) -> PDFDownloadResult:
        """Actually download PDF from URL.

        Args:
            url: PDF URL
            paper: Paper object
            source: Source name for logging

        Returns:
            PDFDownloadResult
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as resp:
                    if resp.status != 200:
                        return PDFDownloadResult(
                            success=False, error=f"HTTP {resp.status} from {source}"
                        )

                    # Check content type
                    content_type = resp.headers.get("Content-Type", "")
                    if "pdf" not in content_type.lower() and "octet-stream" not in content_type.lower():
                        return PDFDownloadResult(
                            success=False,
                            error=f"Not a PDF (Content-Type: {content_type})",
                        )

                    # Read content
                    content = await resp.read()

                    # Verify it's actually a PDF (starts with %PDF)
                    if not content.startswith(b"%PDF"):
                        return PDFDownloadResult(success=False, error="Not a valid PDF file")

                    # Save to disk
                    pdf_path = self._get_pdf_path(paper)
                    pdf_path.parent.mkdir(parents=True, exist_ok=True)

                    async with aiofiles.open(pdf_path, "wb") as f:
                        await f.write(content)

                    return PDFDownloadResult(
                        success=True,
                        pdf_path=str(pdf_path),
                        source=source,
                        file_size=len(content),
                    )

        except asyncio.TimeoutError:
            return PDFDownloadResult(success=False, error=f"Timeout downloading from {source}")
        except Exception as e:
            return PDFDownloadResult(success=False, error=f"Download error from {source}: {e}")

    def _get_pdf_path(self, paper: Paper) -> Path:
        """Get local path for paper's PDF.

        Args:
            paper: Paper object

        Returns:
            Path to PDF file
        """
        # Create safe filename from paper ID
        safe_id = paper.paper_id.replace("/", "_").replace(":", "_")

        # Use hash if ID is too long
        if len(safe_id) > 100:
            safe_id = hashlib.md5(paper.paper_id.encode()).hexdigest()

        return self.papers_dir / f"{safe_id}.pdf"

    async def batch_download(
        self, papers: list[Paper], max_concurrent: int = 5
    ) -> Dict[str, PDFDownloadResult]:
        """Download PDFs for multiple papers concurrently.

        Args:
            papers: List of papers
            max_concurrent: Maximum concurrent downloads

        Returns:
            Dict mapping paper_id to PDFDownloadResult
        """
        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)

        async def download_with_semaphore(paper: Paper):
            async with semaphore:
                result = await self.download_pdf(paper)
                results[paper.paper_id] = result
                return result

        # Download all papers
        tasks = [download_with_semaphore(paper) for paper in papers]
        await asyncio.gather(*tasks, return_exceptions=True)

        return results

    def get_download_stats(self, results: Dict[str, PDFDownloadResult]) -> Dict[str, Any]:
        """Get statistics about download results.

        Args:
            results: Dict of download results

        Returns:
            Statistics dictionary
        """
        total = len(results)
        successful = sum(1 for r in results.values() if r.success)
        failed = total - successful

        # Count by source
        by_source = {}
        for result in results.values():
            if result.success and result.source:
                by_source[result.source] = by_source.get(result.source, 0) + 1

        # Total size
        total_size = sum(r.file_size or 0 for r in results.values() if r.success)

        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "by_source": by_source,
            "total_size_mb": total_size / (1024 * 1024),
        }
