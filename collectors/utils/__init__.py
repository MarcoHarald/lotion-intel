"""
Utility functions for collectors.
Handles deduplication, validation, classification, and rate limiting.
"""
import hashlib
import time
import re
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse
from datetime import datetime, timedelta
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("collector_utils")


class RateLimiter:
    """Rate limiter for API calls with exponential backoff."""
    
    def __init__(self):
        self.calls_per_minute: List[datetime] = []
        self.calls_per_day: List[datetime] = []
        self.last_call_time: Optional[datetime] = None
    
    def can_make_call(self) -> bool:
        """Check if we can make an API call without exceeding limits."""
        now = datetime.utcnow()
        
        # Clean old calls
        minute_ago = now - timedelta(minutes=1)
        day_ago = now - timedelta(days=1)
        
        self.calls_per_minute = [call for call in self.calls_per_minute if call > minute_ago]
        self.calls_per_day = [call for call in self.calls_per_day if call > day_ago]
        
        # Check limits
        if len(self.calls_per_minute) >= settings.max_queries_per_minute:
            return False
        if len(self.calls_per_day) >= settings.max_queries_per_day:
            return False
        
        return True
    
    def record_call(self) -> None:
        """Record an API call."""
        now = datetime.utcnow()
        self.calls_per_minute.append(now)
        self.calls_per_day.append(now)
        self.last_call_time = now
    
    def get_wait_time(self) -> float:
        """Get the time to wait before next call."""
        if not self.last_call_time:
            return 0.0
        
        elapsed = (datetime.utcnow() - self.last_call_time).total_seconds()
        wait_time = settings.query_delay_seconds - elapsed
        return max(0.0, wait_time)
    
    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limits."""
        wait_time = self.get_wait_time()
        if wait_time > 0:
            logger.info(f"Rate limiting: waiting {wait_time:.1f} seconds")
            time.sleep(wait_time)


class DeduplicationManager:
    """Manages content deduplication."""
    
    def __init__(self):
        self.url_cache: Set[str] = set()
        self.content_hash_cache: Set[str] = set()
    
    def generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication."""
        # Normalize content: lowercase, strip whitespace, remove extra spaces
        normalized = re.sub(r'\s+', ' ', content.lower().strip())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    def is_duplicate_url(self, url: str) -> bool:
        """Check if URL already exists."""
        return url in self.url_cache
    
    def is_duplicate_content(self, content: str) -> bool:
        """Check if content already exists."""
        content_hash = self.generate_content_hash(content)
        return content_hash in self.content_hash_cache
    
    def add_url(self, url: str) -> None:
        """Add URL to cache."""
        self.url_cache.add(url)
    
    def add_content(self, content: str) -> None:
        """Add content hash to cache."""
        content_hash = self.generate_content_hash(content)
        self.content_hash_cache.add(content_hash)
    
    def clear_cache(self) -> None:
        """Clear deduplication cache."""
        self.url_cache.clear()
        self.content_hash_cache.clear()


class ContentValidator:
    """Validates content quality and format."""
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format."""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False
    
    @staticmethod
    def validate_content_length(content: str) -> bool:
        """Validate content length."""
        return len(content.strip()) >= settings.min_content_length
    
    @staticmethod
    def validate_source_quality(url: str, domain: str) -> bool:
        """Validate source quality based on domain."""
        if not domain:
            return False
        
        # Check against trusted domains
        trusted_domains = [d.lower() for d in settings.trusted_domains]
        domain_lower = domain.lower()
        
        # Check if domain is in trusted list
        for trusted in trusted_domains:
            if domain_lower.endswith(trusted):
                return True
        
        # Additional quality checks
        quality_indicators = [
            'news', 'gov', 'edu', 'org', 'reuters', 'bbc', 'cnn', 'nytimes'
        ]
        
        return any(indicator in domain_lower for indicator in quality_indicators)
    
    @staticmethod
    def extract_domain(url: str) -> Optional[str]:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return None
    
    @staticmethod
    def calculate_confidence_score(
        content: str, 
        url: str, 
        domain: str, 
        source_type: str
    ) -> float:
        """Calculate confidence score for content quality."""
        score = 0.5  # Base score
        
        # Content length bonus
        if len(content) > 200:
            score += 0.1
        if len(content) > 500:
            score += 0.1
        
        # Domain quality bonus
        if ContentValidator.validate_source_quality(url, domain):
            score += 0.2
        
        # Source type bonus
        source_type_scores = {
            'news': 0.2,
            'government': 0.3,
            'blog': 0.1,
            'forum': 0.05,
            'social_media': 0.05,
            'unknown': 0.0
        }
        score += source_type_scores.get(source_type, 0.0)
        
        # URL format bonus
        if ContentValidator.validate_url(url):
            score += 0.05
        
        return min(1.0, max(0.0, score))


class ContentClassifier:
    """Classifies content and assigns tags."""
    
    @staticmethod
    def classify_source_type(domain: str) -> str:
        """Classify source type based on domain."""
        if not domain:
            return 'unknown'
        
        domain_lower = domain.lower()
        
        # News sources
        news_indicators = ['news', 'reuters', 'bbc', 'cnn', 'nytimes', 'guardian', 'wsj']
        if any(indicator in domain_lower for indicator in news_indicators):
            return 'news'
        
        # Government sources
        gov_indicators = ['gov', 'europa.eu', 'who.int', 'un.org']
        if any(indicator in domain_lower for indicator in gov_indicators):
            return 'government'
        
        # Social media
        social_indicators = ['twitter', 'facebook', 'linkedin', 'reddit', 'youtube']
        if any(indicator in domain_lower for indicator in social_indicators):
            return 'social_media'
        
        # Forums
        forum_indicators = ['forum', 'discussion', 'community']
        if any(indicator in domain_lower for indicator in forum_indicators):
            return 'forum'
        
        # Blogs
        blog_indicators = ['blog', 'medium', 'substack']
        if any(indicator in domain_lower for indicator in blog_indicators):
            return 'blog'
        
        return 'unknown'
    
    @staticmethod
    def extract_tags(content: str, title: str = "") -> List[str]:
        """Extract relevant tags from content."""
        tags = []
        text = f"{title} {content}".lower()
        
        # Topic-based tags
        topic_keywords = {
            'climate': ['climate', 'global warming', 'carbon', 'emissions', 'greenhouse'],
            'technology': ['ai', 'artificial intelligence', 'tech', 'software', 'digital'],
            'health': ['health', 'medical', 'healthcare', 'pandemic', 'vaccine'],
            'economy': ['economy', 'economic', 'financial', 'market', 'recession'],
            'politics': ['political', 'government', 'policy', 'election', 'democracy'],
            'environment': ['environment', 'environmental', 'pollution', 'sustainability'],
            'security': ['security', 'cybersecurity', 'privacy', 'data protection'],
            'education': ['education', 'school', 'university', 'learning', 'student']
        }
        
        for tag, keywords in topic_keywords.items():
            if any(keyword in text for keyword in keywords):
                tags.append(tag)
        
        # Limit tags
        return tags[:10]
    
    @staticmethod
    def calculate_relevance_score(content: str, search_query: str) -> float:
        """Calculate relevance score based on search query."""
        query_words = set(search_query.lower().split())
        content_words = set(content.lower().split())
        
        # Calculate word overlap
        overlap = len(query_words.intersection(content_words))
        total_query_words = len(query_words)
        
        if total_query_words == 0:
            return 0.5
        
        relevance = overlap / total_query_words
        return min(1.0, relevance + 0.3)  # Boost score slightly


# Global instances
rate_limiter = RateLimiter()
deduplication_manager = DeduplicationManager()
content_validator = ContentValidator()
content_classifier = ContentClassifier()
