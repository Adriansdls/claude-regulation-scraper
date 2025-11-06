"""Extraction module - Phase 2 of Research Graph Explorer."""

# Always available
from .pdf_downloader import PDFDownloader, PDFDownloadResult
from .knowledge_graph import KnowledgeGraph

# Lazy imports for optional components
TEXT_EXTRACTOR_AVAILABLE = False
LANGEXTRACT_AVAILABLE = False
ORCHESTRATOR_AVAILABLE = False

TextExtractor = None
TextExtractionResult = None
LangExtractWrapper = None
ExtractionOrchestrator = None

def _try_import_text_extractor():
    global TextExtractor, TextExtractionResult, TEXT_EXTRACTOR_AVAILABLE
    try:
        from .text_extractor import TextExtractor as _TextExtractor, TextExtractionResult as _TextExtractionResult
        TextExtractor = _TextExtractor
        TextExtractionResult = _TextExtractionResult
        TEXT_EXTRACTOR_AVAILABLE = True
    except Exception:
        pass

def _try_import_langextract():
    global LangExtractWrapper, LANGEXTRACT_AVAILABLE
    try:
        from .langextract_wrapper import LangExtractWrapper as _LangExtractWrapper
        LangExtractWrapper = _LangExtractWrapper
        LANGEXTRACT_AVAILABLE = True
    except Exception:
        pass

def _try_import_orchestrator():
    global ExtractionOrchestrator, ORCHESTRATOR_AVAILABLE
    try:
        from .orchestrator import ExtractionOrchestrator as _ExtractionOrchestrator
        ExtractionOrchestrator = _ExtractionOrchestrator
        ORCHESTRATOR_AVAILABLE = True
    except Exception:
        pass

__all__ = [
    "PDFDownloader",
    "PDFDownloadResult",
    "TextExtractor",
    "TextExtractionResult",
    "LangExtractWrapper",
    "KnowledgeGraph",
    "ExtractionOrchestrator",
]
