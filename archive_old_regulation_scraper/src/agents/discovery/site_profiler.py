"""
Site Profiler
Advanced website structure analysis for the Discovery Agent
"""
import re
import logging
from typing import Dict, List, Optional, Set, Any, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Comment
import aiohttp
from datetime import datetime
import asyncio

from ...models.extraction_models import ContentType
from ...models.regulation_models import DocumentType


class TechnicalProfiler:
    """Analyzes technical aspects of websites"""
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.logger = logging.getLogger(__name__)
    
    async def analyze_technical_stack(self, content: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Analyze the technical stack of the website"""
        soup = BeautifulSoup(content, 'html.parser')
        
        analysis = {
            "cms": self._detect_cms(content, soup),
            "frameworks": self._detect_frameworks(content, soup),
            "libraries": self._detect_libraries(content, soup),
            "server_technology": self._detect_server_tech(headers),
            "meta_framework": self._detect_meta_framework(soup),
            "accessibility_features": self._analyze_accessibility(soup),
            "seo_features": self._analyze_seo(soup),
            "performance_indicators": self._analyze_performance_indicators(soup)
        }
        
        return analysis
    
    def _detect_cms(self, content: str, soup: BeautifulSoup) -> Optional[str]:
        """Detect Content Management System"""
        cms_indicators = {
            "wordpress": [
                "wp-content", "wp-includes", "wordpress", 
                r'generator.*wordpress', r'wp-json'
            ],
            "drupal": [
                "drupal", r'sites/all', r'sites/default',
                r'generator.*drupal'
            ],
            "joomla": [
                "joomla", r'option=com_', r'generator.*joomla'
            ],
            "sharepoint": [
                "sharepoint", "_layouts", "SP.UI", "SPClientTemplates"
            ],
            "squiz_matrix": [
                "squiz matrix", "_designs", "__data", "matrix"
            ]
        }
        
        content_lower = content.lower()
        
        for cms, indicators in cms_indicators.items():
            for indicator in indicators:
                if re.search(indicator, content_lower):
                    return cms
        
        return None
    
    def _detect_frameworks(self, content: str, soup: BeautifulSoup) -> List[str]:
        """Detect web frameworks"""
        frameworks = []
        content_lower = content.lower()
        
        framework_indicators = {
            "react": ["react", "data-reactroot", "_react"],
            "angular": ["angular", "ng-app", "ng-version", "@angular"],
            "vue": ["vue.js", "v-app", "__vue__", "vue-router"],
            "ember": ["ember", "ember.js", "ember-application"],
            "backbone": ["backbone", "backbone.js"],
            "jquery": ["jquery", "$.fn.jquery"],
            "bootstrap": ["bootstrap", "btn btn-", "container-fluid"],
            "foundation": ["foundation", "zurb-foundation"]
        }
        
        for framework, indicators in framework_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                frameworks.append(framework)
        
        return frameworks
    
    def _detect_libraries(self, content: str, soup: BeautifulSoup) -> List[str]:
        """Detect JavaScript libraries"""
        libraries = []
        
        # Check script tags for common libraries
        scripts = soup.find_all('script', src=True)
        for script in scripts:
            src = script.get('src', '').lower()
            
            if 'jquery' in src:
                libraries.append('jquery')
            elif 'lodash' in src or 'underscore' in src:
                libraries.append('lodash/underscore')
            elif 'moment' in src:
                libraries.append('moment.js')
            elif 'd3' in src:
                libraries.append('d3.js')
            elif 'chart' in src:
                libraries.append('charting')
        
        return list(set(libraries))
    
    def _detect_server_tech(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Detect server technology from headers"""
        server_info = {}
        
        # Server header
        server = headers.get('server', '')
        if server:
            server_info['server'] = server
            
            if 'apache' in server.lower():
                server_info['web_server'] = 'Apache'
            elif 'nginx' in server.lower():
                server_info['web_server'] = 'Nginx'
            elif 'iis' in server.lower():
                server_info['web_server'] = 'IIS'
        
        # Technology headers
        if 'x-powered-by' in headers:
            server_info['powered_by'] = headers['x-powered-by']
        
        if 'x-aspnet-version' in headers:
            server_info['aspnet_version'] = headers['x-aspnet-version']
        
        # CDN detection
        cdn_headers = ['cf-ray', 'x-cache', 'x-served-by', 'x-amz-cf-id']
        for header in cdn_headers:
            if header in headers:
                server_info['cdn'] = True
                break
        
        return server_info
    
    def _detect_meta_framework(self, soup: BeautifulSoup) -> Optional[str]:
        """Detect meta frameworks like Next.js, Nuxt.js"""
        # Check for Next.js
        if soup.find('script', {'id': '__NEXT_DATA__'}):
            return 'next.js'
        
        # Check for Nuxt.js
        if soup.find(attrs={'data-n-head': True}):
            return 'nuxt.js'
        
        # Check for Gatsby
        if soup.find(attrs={'id': '___gatsby'}):
            return 'gatsby'
        
        return None
    
    def _analyze_accessibility(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze accessibility features"""
        features = {
            "alt_text_usage": 0,
            "aria_labels": 0,
            "skip_links": 0,
            "semantic_headings": 0,
            "focus_indicators": 0
        }
        
        # Alt text on images
        images = soup.find_all('img')
        images_with_alt = [img for img in images if img.get('alt')]
        if images:
            features["alt_text_usage"] = len(images_with_alt) / len(images)
        
        # ARIA labels
        aria_elements = soup.find_all(attrs={"aria-label": True}) + \
                      soup.find_all(attrs={"aria-labelledby": True})
        features["aria_labels"] = len(aria_elements)
        
        # Skip links
        skip_links = soup.find_all('a', href=re.compile(r'#.*'))
        skip_link_text = [link.get_text().lower() for link in skip_links]
        skip_indicators = ['skip', 'jump', 'main content']
        features["skip_links"] = sum(1 for text in skip_link_text 
                                   if any(indicator in text for indicator in skip_indicators))
        
        # Semantic heading structure
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        features["semantic_headings"] = len(headings)
        
        return features
    
    def _analyze_seo(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze SEO features"""
        seo = {
            "has_title": bool(soup.find('title')),
            "has_meta_description": bool(soup.find('meta', attrs={'name': 'description'})),
            "has_meta_keywords": bool(soup.find('meta', attrs={'name': 'keywords'})),
            "has_canonical": bool(soup.find('link', attrs={'rel': 'canonical'})),
            "has_robots_meta": bool(soup.find('meta', attrs={'name': 'robots'})),
            "structured_data": self._detect_structured_data(soup)
        }
        
        return seo
    
    def _detect_structured_data(self, soup: BeautifulSoup) -> List[str]:
        """Detect structured data formats"""
        structured_data = []
        
        # JSON-LD
        json_ld_scripts = soup.find_all('script', {'type': 'application/ld+json'})
        if json_ld_scripts:
            structured_data.append('json-ld')
        
        # Microdata
        if soup.find(attrs={'itemscope': True}):
            structured_data.append('microdata')
        
        # RDFa
        if soup.find(attrs={'property': True}) or soup.find(attrs={'typeof': True}):
            structured_data.append('rdfa')
        
        return structured_data
    
    def _analyze_performance_indicators(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze performance-related indicators"""
        performance = {
            "lazy_loading": bool(soup.find(attrs={'loading': 'lazy'})),
            "preload_links": len(soup.find_all('link', attrs={'rel': 'preload'})),
            "prefetch_links": len(soup.find_all('link', attrs={'rel': 'prefetch'})),
            "async_scripts": len(soup.find_all('script', attrs={'async': True})),
            "defer_scripts": len(soup.find_all('script', attrs={'defer': True}))
        }
        
        return performance


class ContentAnalyzer:
    """Analyzes content structure and patterns"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_content_patterns(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze content patterns for regulation extraction"""
        patterns = {
            "document_structure": self._analyze_document_structure(soup),
            "navigation_patterns": self._analyze_navigation_patterns(soup),
            "content_organization": self._analyze_content_organization(soup),
            "metadata_patterns": self._analyze_metadata_patterns(soup),
            "search_functionality": self._analyze_search_functionality(soup),
            "pagination_patterns": self._analyze_pagination_patterns(soup)
        }
        
        return patterns
    
    def _analyze_document_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze how documents are structured"""
        structure = {
            "hierarchical_headings": self._check_hierarchical_headings(soup),
            "numbered_sections": self._find_numbered_sections(soup),
            "definition_lists": len(soup.find_all('dl')),
            "article_tags": len(soup.find_all('article')),
            "section_tags": len(soup.find_all('section')),
            "legal_citations": self._find_legal_citations(soup)
        }
        
        return structure
    
    def _check_hierarchical_headings(self, soup: BeautifulSoup) -> bool:
        """Check if headings follow hierarchical structure"""
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if len(headings) < 2:
            return False
        
        # Check if headings follow logical order
        levels = [int(h.name[1]) for h in headings]
        
        # Should start with h1 or h2 and not skip levels drastically
        if levels[0] > 2:
            return False
        
        for i in range(1, len(levels)):
            if levels[i] - levels[i-1] > 2:  # Skipping more than 2 levels
                return False
        
        return True
    
    def _find_numbered_sections(self, soup: BeautifulSoup) -> int:
        """Find numbered sections (common in legal documents)"""
        # Look for patterns like "1.", "1.1", "Section 1", etc.
        text = soup.get_text()
        
        patterns = [
            r'\b\d+\.\s',           # "1. "
            r'\b\d+\.\d+\s',        # "1.1 "
            r'\bSection\s+\d+',     # "Section 1"
            r'\bArticle\s+\d+',     # "Article 1"
            r'\bPart\s+[IVX]+',     # "Part I", "Part II"
            r'\b[IVX]+\.\s',        # "I. ", "II. "
        ]
        
        total_matches = 0
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            total_matches += len(matches)
        
        return total_matches
    
    def _find_legal_citations(self, soup: BeautifulSoup) -> int:
        """Find legal citations in the content"""
        text = soup.get_text()
        
        # Common legal citation patterns
        citation_patterns = [
            r'\b\d{4}\s+[A-Z]+\s+\d+',          # "2021 USC 123"
            r'\b\d+\s+U\.S\.C\.\s+§?\s*\d+',    # "42 U.S.C. § 1983"
            r'\bPub\.\s*L\.\s*No\.\s*\d+-\d+',  # "Pub. L. No. 117-58"
            r'\b\d+\s+F\.\s*\d+\s+\d+',         # "123 F.3d 456"
            r'\bS\.\s*\d+|\bH\.R\.\s*\d+',      # "S. 1234" or "H.R. 5678"
        ]
        
        total_citations = 0
        for pattern in citation_patterns:
            matches = re.findall(pattern, text)
            total_citations += len(matches)
        
        return total_citations
    
    def _analyze_navigation_patterns(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze navigation patterns"""
        navigation = {
            "breadcrumb_nav": bool(soup.find(attrs={'class': re.compile('breadcrumb', re.I)})),
            "main_navigation": len(soup.find_all('nav')),
            "sidebar_navigation": bool(soup.find(attrs={'class': re.compile('sidebar|side-nav', re.I)})),
            "footer_links": len(soup.find_all('footer')),
            "dropdown_menus": len(soup.find_all(attrs={'class': re.compile('dropdown', re.I)}))
        }
        
        return navigation
    
    def _analyze_content_organization(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze how content is organized"""
        organization = {
            "tabbed_content": len(soup.find_all(attrs={'class': re.compile('tab', re.I)})),
            "accordion_content": len(soup.find_all(attrs={'class': re.compile('accordion|collaps', re.I)})),
            "card_layout": len(soup.find_all(attrs={'class': re.compile('card', re.I)})),
            "grid_layout": len(soup.find_all(attrs={'class': re.compile('grid|col-', re.I)})),
            "list_items": len(soup.find_all('li'))
        }
        
        return organization
    
    def _analyze_metadata_patterns(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze metadata patterns"""
        metadata = {
            "publication_dates": self._find_publication_dates(soup),
            "document_ids": self._find_document_identifiers(soup),
            "status_indicators": self._find_status_indicators(soup),
            "author_information": self._find_author_info(soup),
            "version_information": self._find_version_info(soup)
        }
        
        return metadata
    
    def _find_publication_dates(self, soup: BeautifulSoup) -> int:
        """Find publication dates in various formats"""
        text = soup.get_text()
        
        date_patterns = [
            r'\b\d{1,2}/\d{1,2}/\d{4}',      # MM/DD/YYYY
            r'\b\d{4}-\d{2}-\d{2}',          # YYYY-MM-DD
            r'\b[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}',  # January 1, 2021
            r'\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}',    # 1 January 2021
        ]
        
        total_dates = 0
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            total_dates += len(matches)
        
        return total_dates
    
    def _find_document_identifiers(self, soup: BeautifulSoup) -> int:
        """Find document identifiers"""
        text = soup.get_text()
        
        # Look for various ID patterns
        id_patterns = [
            r'\b[A-Z]{2,4}-\d{4}-\d+',      # UK style: SI-2021-1234
            r'\b\d{4}/\d+/[A-Z]+',          # EU style: 2021/123/EC
            r'\bNo\.\s*\d+\s*of\s*\d{4}',   # "No. 123 of 2021"
            r'\bS\.I\.\s*\d{4}/\d+',        # UK Statutory Instrument
        ]
        
        total_ids = 0
        for pattern in id_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            total_ids += len(matches)
        
        return total_ids
    
    def _find_status_indicators(self, soup: BeautifulSoup) -> int:
        """Find status indicators for documents"""
        text = soup.get_text().lower()
        
        status_keywords = [
            'in force', 'enacted', 'repealed', 'amended', 'superseded',
            'draft', 'proposed', 'under review', 'consultation'
        ]
        
        return sum(1 for keyword in status_keywords if keyword in text)
    
    def _find_author_info(self, soup: BeautifulSoup) -> int:
        """Find author/authority information"""
        # Look for common author/authority patterns
        author_selectors = [
            'author', 'by-author', 'byline', 'authority',
            'department', 'ministry', 'secretary'
        ]
        
        author_count = 0
        for selector in author_selectors:
            elements = soup.find_all(attrs={'class': re.compile(selector, re.I)})
            author_count += len(elements)
        
        return author_count
    
    def _find_version_info(self, soup: BeautifulSoup) -> int:
        """Find version information"""
        text = soup.get_text().lower()
        
        version_patterns = [
            r'version\s+\d+', r'v\d+\.\d+', r'revision\s+\d+',
            r'updated\s+\d', r'amended\s+\d'
        ]
        
        total_versions = 0
        for pattern in version_patterns:
            matches = re.findall(pattern, text)
            total_versions += len(matches)
        
        return total_versions
    
    def _analyze_search_functionality(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze search functionality"""
        search = {
            "search_forms": len(soup.find_all('form', attrs={'class': re.compile('search', re.I)})),
            "search_inputs": len(soup.find_all('input', attrs={'type': 'search'})) + 
                           len(soup.find_all('input', attrs={'name': re.compile('search|query', re.I)})),
            "filter_options": len(soup.find_all('select')) + 
                            len(soup.find_all('input', attrs={'type': 'checkbox'})),
            "advanced_search": bool(soup.find(text=re.compile('advanced search', re.I)))
        }
        
        return search
    
    def _analyze_pagination_patterns(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze pagination patterns"""
        pagination = {
            "pagination_controls": len(soup.find_all(attrs={'class': re.compile('pag', re.I)})),
            "next_prev_links": len(soup.find_all('a', text=re.compile('next|previous|prev', re.I))),
            "numbered_pages": len(soup.find_all('a', text=re.compile(r'^\d+$'))),
            "results_per_page": bool(soup.find(text=re.compile('results per page|items per page', re.I)))
        }
        
        return pagination


class SiteProfiler:
    """Main site profiler that combines technical and content analysis"""
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.technical_profiler = TechnicalProfiler(session)
        self.content_analyzer = ContentAnalyzer()
        self.logger = logging.getLogger(__name__)
    
    async def create_comprehensive_profile(self, url: str, content: str, 
                                         headers: Dict[str, str]) -> Dict[str, Any]:
        """Create comprehensive site profile"""
        soup = BeautifulSoup(content, 'html.parser')
        
        profile = {
            "technical_analysis": await self.technical_profiler.analyze_technical_stack(content, headers),
            "content_patterns": self.content_analyzer.analyze_content_patterns(soup),
            "extraction_readiness": self._assess_extraction_readiness(soup, content),
            "complexity_score": self._calculate_complexity_score(soup, content),
            "regulation_indicators": self._assess_regulation_indicators(soup, content)
        }
        
        return profile
    
    def _assess_extraction_readiness(self, soup: BeautifulSoup, content: str) -> Dict[str, float]:
        """Assess how ready the site is for different extraction methods"""
        readiness = {
            "html_parsing": self._assess_html_readiness(soup),
            "api_extraction": self._assess_api_readiness(content),
            "pdf_extraction": self._assess_pdf_readiness(soup),
            "ocr_needed": self._assess_ocr_need(soup),
            "js_execution": self._assess_js_need(content)
        }
        
        return readiness
    
    def _assess_html_readiness(self, soup: BeautifulSoup) -> float:
        """Assess readiness for HTML parsing extraction"""
        score = 0.0
        
        # Semantic markup
        if soup.find('article') or soup.find('section'):
            score += 0.3
        
        # Proper heading structure
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if len(headings) > 2:
            score += 0.2
        
        # Content organization
        if soup.find('nav') and soup.find('main'):
            score += 0.2
        
        # Structured lists
        if soup.find('ol') or soup.find('ul'):
            score += 0.1
        
        # Tables for data
        if soup.find('table'):
            score += 0.1
        
        # Metadata
        if soup.find('time') or soup.find(attrs={'datetime': True}):
            score += 0.1
        
        return min(1.0, score)
    
    def _assess_api_readiness(self, content: str) -> float:
        """Assess potential for API extraction"""
        score = 0.0
        
        # Look for API endpoints
        api_indicators = [
            'api/', '/api', 'rest/', 'graphql', 'json',
            'endpoints', 'swagger', 'openapi'
        ]
        
        content_lower = content.lower()
        for indicator in api_indicators:
            if indicator in content_lower:
                score += 0.2
        
        return min(1.0, score)
    
    def _assess_pdf_readiness(self, soup: BeautifulSoup) -> float:
        """Assess need for PDF extraction"""
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
        total_links = len(soup.find_all('a', href=True))
        
        if total_links == 0:
            return 0.0
        
        return min(1.0, len(pdf_links) / total_links * 2)
    
    def _assess_ocr_need(self, soup: BeautifulSoup) -> float:
        """Assess need for OCR extraction"""
        score = 0.0
        
        # Many images might indicate scanned documents
        images = soup.find_all('img')
        if len(images) > 5:
            score += 0.3
        
        # Canvas elements might contain rendered text
        if soup.find('canvas'):
            score += 0.4
        
        # PDF embeds might need OCR
        embeds = soup.find_all('embed', src=re.compile(r'\.pdf$', re.I))
        if embeds:
            score += 0.3
        
        return min(1.0, score)
    
    def _assess_js_need(self, content: str) -> float:
        """Assess need for JavaScript execution"""
        score = 0.0
        
        # Heavy JavaScript usage
        script_tags = content.lower().count('<script')
        if script_tags > 5:
            score += 0.3
        
        # SPA indicators
        spa_indicators = ['angular', 'react', 'vue', 'ember']
        for indicator in spa_indicators:
            if indicator in content.lower():
                score += 0.4
                break
        
        # Dynamic loading indicators
        if 'loading...' in content.lower() or 'spinner' in content.lower():
            score += 0.3
        
        return min(1.0, score)
    
    def _calculate_complexity_score(self, soup: BeautifulSoup, content: str) -> float:
        """Calculate overall site complexity score"""
        factors = []
        
        # DOM complexity
        dom_depth = self._calculate_dom_depth(soup)
        factors.append(min(1.0, dom_depth / 20))  # Normalize to 0-1
        
        # Content size
        text_size = len(soup.get_text())
        factors.append(min(1.0, text_size / 50000))  # Normalize to 0-1
        
        # Script complexity
        script_count = content.lower().count('<script')
        factors.append(min(1.0, script_count / 20))
        
        # Table complexity
        tables = soup.find_all('table')
        complex_tables = sum(1 for table in tables if len(table.find_all('tr')) > 10)
        factors.append(min(1.0, complex_tables / 5))
        
        return sum(factors) / len(factors)
    
    def _calculate_dom_depth(self, element, depth=0):
        """Calculate maximum DOM depth"""
        if not hasattr(element, 'children'):
            return depth
        
        max_depth = depth
        for child in element.children:
            if hasattr(child, 'name') and child.name:
                child_depth = self._calculate_dom_depth(child, depth + 1)
                max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def _assess_regulation_indicators(self, soup: BeautifulSoup, content: str) -> Dict[str, Any]:
        """Assess indicators that this is a regulation/legal site"""
        indicators = {
            "legal_keywords": self._count_legal_keywords(content),
            "citation_patterns": self._count_citation_patterns(content),
            "official_language": self._assess_official_language(soup),
            "government_indicators": self._count_government_indicators(content),
            "document_structure": self._assess_legal_document_structure(soup)
        }
        
        return indicators
    
    def _count_legal_keywords(self, content: str) -> int:
        """Count legal keywords in content"""
        legal_keywords = [
            'regulation', 'act', 'bill', 'law', 'statute', 'code',
            'section', 'subsection', 'article', 'paragraph',
            'whereas', 'pursuant', 'hereby', 'thereof', 'heretofore',
            'jurisdiction', 'authority', 'enforcement', 'compliance',
            'legislative', 'regulatory', 'statutory', 'legal'
        ]
        
        content_lower = content.lower()
        return sum(content_lower.count(keyword) for keyword in legal_keywords)
    
    def _count_citation_patterns(self, content: str) -> int:
        """Count legal citation patterns"""
        citation_patterns = [
            r'\b\d+\s+U\.S\.C\.\s+',
            r'\bPub\.\s*L\.\s*No\.',
            r'\bS\.\s*\d+|\bH\.R\.\s*\d+',
            r'\b\d{4}/\d+/[A-Z]+',
            r'\bSI\s+\d{4}/\d+',
            r'\bNo\.\s*\d+\s*of\s*\d{4}'
        ]
        
        total_citations = 0
        for pattern in citation_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            total_citations += len(matches)
        
        return total_citations
    
    def _assess_official_language(self, soup: BeautifulSoup) -> bool:
        """Assess if site uses official/formal language"""
        text = soup.get_text().lower()
        
        formal_indicators = [
            'official', 'government', 'department', 'ministry',
            'federal', 'national', 'state', 'public',
            'authority', 'commission', 'agency', 'bureau'
        ]
        
        return sum(1 for indicator in formal_indicators if indicator in text) >= 3
    
    def _count_government_indicators(self, content: str) -> int:
        """Count government/official indicators"""
        gov_indicators = [
            '.gov', '.gov.uk', '.europa.eu', '.gc.ca', '.gov.au',
            'parliament', 'congress', 'senate', 'house',
            'minister', 'secretary', 'president', 'governor',
            'official', 'federal', 'national', 'state'
        ]
        
        content_lower = content.lower()
        return sum(1 for indicator in gov_indicators if indicator in content_lower)
    
    def _assess_legal_document_structure(self, soup: BeautifulSoup) -> bool:
        """Assess if site has typical legal document structure"""
        structure_indicators = 0
        
        # Numbered sections
        if re.search(r'\b\d+\.\s', soup.get_text()):
            structure_indicators += 1
        
        # Hierarchical headings
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4'])
        if len(headings) >= 3:
            structure_indicators += 1
        
        # Definition lists
        if soup.find('dl'):
            structure_indicators += 1
        
        # Tables with regulatory data
        tables = soup.find_all('table')
        if tables:
            structure_indicators += 1
        
        # Formal language patterns
        formal_text = ['whereas', 'therefore', 'pursuant to', 'in accordance with']
        text = soup.get_text().lower()
        if any(pattern in text for pattern in formal_text):
            structure_indicators += 1
        
        return structure_indicators >= 3