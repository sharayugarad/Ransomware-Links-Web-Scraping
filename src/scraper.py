"""
Scraper module for fetching URLs from various sources with date filtering.
"""
import logging
import random
import re
import time
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class URLScraper:
    """Scrapes URLs from multiple sources with retry logic and date filtering."""
    
    # User agents to rotate (helps avoid 403 errors)
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    ]
    
    def __init__(self, timeout: int = 30, max_retries: int = 3, filter_date: str = "2025-01-14"):
        self.timeout = timeout
        self.max_retries = max_retries
        self.filter_date = self._parse_filter_date(filter_date)
        self.session = self._create_session()
        
        logger.info(f"Date filter active: Only URLs from {self.filter_date.strftime('%Y-%m-%d')} onwards")
    
    def _parse_filter_date(self, date_str: str) -> datetime:
        """Parse filter date string to datetime object."""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            logger.warning(f"Invalid date format: {date_str}, using 2025-01-14")
            return datetime(2025, 1, 14)
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers to look more like a real browser
        session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
        return session
    
    def fetch_url(self, url: str, use_random_ua: bool = False) -> Optional[str]:
        """Fetch URL content with error handling and 403 retry logic."""
        try:
            headers = {}
            if use_random_ua:
                headers['User-Agent'] = random.choice(self.USER_AGENTS)
            else:
                headers['User-Agent'] = self.USER_AGENTS[0]
            
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=self.timeout, headers=headers)
            response.raise_for_status()
            logger.debug(f"Successfully fetched {url} ({len(response.content)} bytes)")
            return response.text
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.warning(f"403 Forbidden for {url} - Website blocking request")
                # Try with random user agent
                if not use_random_ua:
                    logger.info("Retrying with different user agent...")
                    time.sleep(2)
                    return self.fetch_url(url, use_random_ua=True)
                else:
                    logger.error(f"Still blocked after retry. Skipping {url}")
            else:
                logger.error(f"HTTP error {e.response.status_code} for {url}")
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching {url}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
        return None
    
    def _extract_date_from_url(self, url: str) -> Optional[datetime]:
        """Extract date from URL patterns like /2025/01/14/ or /posts/2025-01-14-title."""
        # Pattern 1: /YYYY/MM/DD/
        pattern1 = r'/(\d{4})/(\d{1,2})/(\d{1,2})/'
        match = re.search(pattern1, url)
        if match:
            try:
                year, month, day = match.groups()
                return datetime(int(year), int(month), int(day))
            except ValueError:
                pass
        
        # Pattern 2: /YYYY-MM-DD or /YYYYMMDD
        pattern2 = r'/(\d{4})-(\d{2})-(\d{2})'
        match = re.search(pattern2, url)
        if match:
            try:
                year, month, day = match.groups()
                return datetime(int(year), int(month), int(day))
            except ValueError:
                pass
        
        # Pattern 3: YYYYMMDD without separators
        pattern3 = r'/(\d{8})'
        match = re.search(pattern3, url)
        if match:
            try:
                date_str = match.group(1)
                year = int(date_str[0:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                return datetime(year, month, day)
            except (ValueError, IndexError):
                pass
        
        return None
    
    def _parse_sitemap_date(self, lastmod: str) -> Optional[datetime]:
        """Parse lastmod date from sitemap."""
        if not lastmod:
            return None
        
        # Try different date formats
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",  # 2025-01-14T10:00:00+00:00
            "%Y-%m-%dT%H:%M:%S",     # 2025-01-14T10:00:00
            "%Y-%m-%d",               # 2025-01-14
        ]
        
        for fmt in formats:
            try:
                # Remove timezone info for simpler comparison
                cleaned = lastmod.split('+')[0].split('Z')[0]
                return datetime.strptime(cleaned, fmt.replace('%z', ''))
            except ValueError:
                continue
        
        return None
    
    def _filter_url_by_date(self, url: str, lastmod: Optional[str] = None) -> bool:
        """Check if URL should be included based on date filter."""
        # First, try lastmod from sitemap
        if lastmod:
            date = self._parse_sitemap_date(lastmod)
            if date:
                is_valid = date >= self.filter_date
                if not is_valid:
                    logger.debug(f"Filtered out (lastmod): {url} (date: {date.strftime('%Y-%m-%d')})")
                return is_valid
        
        # Second, try extracting date from URL
        date = self._extract_date_from_url(url)
        if date:
            is_valid = date >= self.filter_date
            if not is_valid:
                logger.debug(f"Filtered out (URL date): {url} (date: {date.strftime('%Y-%m-%d')})")
            return is_valid
        
        # If no date found, include the URL (assume it might be recent)
        logger.debug(f"No date found for: {url}, including by default")
        return True
    
    def parse_xml_sitemap(self, xml_content: str, source_name: str) -> List[str]:
        """Parse XML sitemap and extract URLs with date filtering."""
        urls = []
        filtered_count = 0
        
        try:
            soup = BeautifulSoup(xml_content, 'lxml-xml')
            
            # Find all <url> tags in sitemap
            url_tags = soup.find_all('url')
            
            for url_tag in url_tags:
                loc = url_tag.find('loc')
                if loc:
                    url = loc.get_text(strip=True)
                    
                    # Check for lastmod
                    lastmod_tag = url_tag.find('lastmod')
                    lastmod = lastmod_tag.get_text(strip=True) if lastmod_tag else None
                    
                    # Apply date filter
                    if self._filter_url_by_date(url, lastmod):
                        urls.append(url)
                    else:
                        filtered_count += 1
            
            logger.info(f"Extracted {len(urls)} URLs from {source_name} sitemap (filtered out {filtered_count} old URLs)")
        except Exception as e:
            logger.error(f"Error parsing XML sitemap for {source_name}: {e}")
        
        return urls
    
    def parse_html_links(self, html_content: str, base_url: str, source_name: str) -> List[str]:
        """Parse HTML and extract all links with date filtering."""
        urls = []
        filtered_count = 0
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all <a> tags
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, href)
                
                # Only include URLs from the same domain
                if urlparse(absolute_url).netloc == urlparse(base_url).netloc:
                    # Apply date filter
                    if self._filter_url_by_date(absolute_url):
                        urls.append(absolute_url)
                    else:
                        filtered_count += 1
            
            # Remove duplicates
            urls = list(set(urls))
            logger.info(f"Extracted {len(urls)} URLs from {source_name} HTML (filtered out {filtered_count} old URLs)")
        except Exception as e:
            logger.error(f"Error parsing HTML for {source_name}: {e}")
        
        return urls
    
    def scrape_dexpose(self) -> List[str]:
        """Scrape URLs from dexpose.io sitemap."""
        url = "https://dexpose.io/sitemap-0.xml"
        content = self.fetch_url(url)
        if content:
            return self.parse_xml_sitemap(content, "dexpose.io")
        return []
    
    def scrape_ransomware_live(self) -> List[str]:
        """Scrape URLs from ransomware.live sitemap."""
        url = "https://www.ransomware.live/sitemap.xml"
        content = self.fetch_url(url)
        if content:
            return self.parse_xml_sitemap(content, "ransomware.live")
        return []
    
    def scrape_redpacket_security(self) -> List[str]:
        """Scrape URLs from redpacketsecurity.com."""
        url = "https://www.redpacketsecurity.com/"
        content = self.fetch_url(url, use_random_ua=True)  # Start with random UA to avoid 403
        if content:
            return self.parse_html_links(content, url, "redpacketsecurity.com")
        return []
    
    def scrape_all_sources(self) -> dict:
        """Scrape all configured sources and return results."""
        results = {}
        
        sources = [
            ("dexpose.io", self.scrape_dexpose),
            ("ransomware.live", self.scrape_ransomware_live),
            ("redpacketsecurity.com", self.scrape_redpacket_security)
        ]
        
        for source_name, scrape_func in sources:
            try:
                logger.info(f"Starting scrape for {source_name}")
                urls = scrape_func()
                results[source_name] = urls
                logger.info(f"Completed scrape for {source_name}: {len(urls)} URLs (after filtering)")
                
                # Brief delay between sources to be polite
                time.sleep(2)
            except Exception as e:
                logger.error(f"Unexpected error scraping {source_name}: {e}")
                results[source_name] = []
        
        return results
    
    def close(self):
        """Close the session."""
        self.session.close()