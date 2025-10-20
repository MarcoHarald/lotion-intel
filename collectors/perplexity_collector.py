"""
Perplexity API collector implementation.
Handles API communication and response processing.
"""
import requests
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from models.topic import Topic
from collectors.base_collector import BaseCollector
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("perplexity_collector")


class PerplexityCollector(BaseCollector):
    """Collector implementation for Perplexity API."""
    
    def __init__(self):
        super().__init__()
        self.api_key = settings.perplexity_api_key
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def build_query(self, topic: Topic, strategy: str) -> str:
        """Build query string based on topic and strategy."""
        base_query = topic.search_query
        
        if strategy == 'initial':
            # For initial collection, get recent content
            days_ago = settings.initial_collection_days
            time_constraint = f" from the last {days_ago} days"
            return f"{base_query}{time_constraint}"
        
        elif strategy == 'incremental':
            # For incremental collection, get content since last check
            if topic.last_checked:
                last_check = topic.last_checked.strftime("%Y-%m-%d")
                return f"{base_query} since {last_check}"
            else:
                return f"{base_query} recent news"
        
        else:  # gap_fill
            return f"{base_query} latest updates"
    
    def make_api_request(self, query: str) -> Optional[Dict[str, Any]]:
        """Make API request to Perplexity."""
        try:
            payload = {
                "model": "llama-3.1-sonar-small-128k-online",
                "messages": [
                    {
                        "role": "user",
                        "content": f"Find recent news and articles about: {query}. Provide citations with URLs, titles, and brief summaries. Focus on credible sources."
                    }
                ],
                "max_tokens": 4000,
                "temperature": 0.1,
                "top_p": 0.9
            }
            
            logger.info(f"Making API request for query: {query}")
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=settings.health_check_timeout_seconds
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in API request: {e}")
            return None
    
    def extract_citations(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract citations from Perplexity response."""
        citations = []
        
        try:
            # Get the main content
            content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            if not content:
                logger.warning("No content in API response")
                return citations
            
            # Store full response for reference
            full_answer = content
            
            # Parse citations from the response
            # Perplexity typically includes citations in the format [1], [2], etc.
            import re
            
            # Find citation patterns
            citation_pattern = r'\[(\d+)\]\s*([^\[]+)'
            matches = re.findall(citation_pattern, content)
            
            for i, (num, citation_text) in enumerate(matches):
                # Extract URL from citation text
                url_pattern = r'(https?://[^\s]+)'
                url_match = re.search(url_pattern, citation_text)
                
                if url_match:
                    url = url_match.group(1)
                    
                    # Extract title (text before URL)
                    title = citation_text.replace(url, '').strip()
                    if not title:
                        title = f"Citation {num}"
                    
                    # Extract content snippet
                    content_snippet = citation_text[:500]  # Limit content length
                    
                    citation = {
                        'url': url,
                        'title': title,
                        'content': content_snippet,
                        'full_answer': full_answer,
                        'metadata': {
                            'citation_number': int(num),
                            'source': 'perplexity',
                            'collected_at': datetime.utcnow().isoformat()
                        }
                    }
                    
                    citations.append(citation)
            
            # If no structured citations found, try to extract URLs from content
            if not citations:
                url_pattern = r'(https?://[^\s]+)'
                urls = re.findall(url_pattern, content)
                
                for i, url in enumerate(urls[:10]):  # Limit to 10 URLs
                    # Extract surrounding text as title/content
                    url_start = content.find(url)
                    start = max(0, url_start - 100)
                    end = min(len(content), url_start + len(url) + 100)
                    surrounding_text = content[start:end]
                    
                    citation = {
                        'url': url,
                        'title': f"Source {i+1}",
                        'content': surrounding_text,
                        'full_answer': full_answer,
                        'metadata': {
                            'citation_number': i + 1,
                            'source': 'perplexity',
                            'collected_at': datetime.utcnow().isoformat()
                        }
                    }
                    
                    citations.append(citation)
            
            logger.info(f"Extracted {len(citations)} citations from response")
            return citations
            
        except Exception as e:
            logger.error(f"Error extracting citations: {e}")
            return []
    
    def collect_posts(self, topic: Topic, strategy: str) -> List[Dict[str, Any]]:
        """Collect posts using Perplexity API."""
        try:
            # Build query
            query = self.build_query(topic, strategy)
            
            # Make API request
            response = self.make_api_request(query)
            if not response:
                logger.error(f"Failed to get response for topic {topic.topic_name}")
                return []
            
            # Extract citations
            citations = self.extract_citations(response)
            
            logger.info(f"Collected {len(citations)} citations for topic {topic.topic_name}")
            return citations
            
        except Exception as e:
            logger.error(f"Error collecting posts for topic {topic.topic_name}: {e}")
            return []
    
    def test_api_connection(self) -> bool:
        """Test API connection."""
        try:
            test_query = "test query"
            response = self.make_api_request(test_query)
            return response is not None
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False
