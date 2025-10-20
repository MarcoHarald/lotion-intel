"""
Basic tests for the monitoring app.
Tests critical functionality and data validation.
"""
import pytest
import os
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.post import PostCreate, PostUpdate
from models.topic import TopicCreate, TopicUpdate
from collectors.utils import RateLimiter, DeduplicationManager, ContentValidator, ContentClassifier


class TestRateLimiter:
    """Test rate limiter functionality."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes correctly."""
        limiter = RateLimiter()
        assert limiter.calls_per_minute == []
        assert limiter.calls_per_day == []
        assert limiter.last_call_time is None
    
    def test_can_make_call_within_limits(self):
        """Test can make call when within limits."""
        limiter = RateLimiter()
        assert limiter.can_make_call() is True
    
    def test_record_call(self):
        """Test recording a call."""
        limiter = RateLimiter()
        limiter.record_call()
        assert len(limiter.calls_per_minute) == 1
        assert len(limiter.calls_per_day) == 1
        assert limiter.last_call_time is not None


class TestDeduplicationManager:
    """Test deduplication functionality."""
    
    def test_content_hash_generation(self):
        """Test content hash generation."""
        manager = DeduplicationManager()
        
        content1 = "This is a test content"
        content2 = "This is a test content"
        content3 = "This is different content"
        
        hash1 = manager.generate_content_hash(content1)
        hash2 = manager.generate_content_hash(content2)
        hash3 = manager.generate_content_hash(content3)
        
        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA256 hex length
    
    def test_url_deduplication(self):
        """Test URL deduplication."""
        manager = DeduplicationManager()
        
        url = "https://example.com/article"
        
        assert not manager.is_duplicate_url(url)
        manager.add_url(url)
        assert manager.is_duplicate_url(url)
    
    def test_content_deduplication(self):
        """Test content deduplication."""
        manager = DeduplicationManager()
        
        content = "This is test content"
        
        assert not manager.is_duplicate_content(content)
        manager.add_content(content)
        assert manager.is_duplicate_content(content)


class TestContentValidator:
    """Test content validation functionality."""
    
    def test_validate_url(self):
        """Test URL validation."""
        assert ContentValidator.validate_url("https://example.com") is True
        assert ContentValidator.validate_url("http://example.com") is True
        assert ContentValidator.validate_url("invalid-url") is False
        assert ContentValidator.validate_url("") is False
    
    def test_validate_content_length(self):
        """Test content length validation."""
        short_content = "Short"
        long_content = "This is a much longer content that should pass validation"
        
        assert ContentValidator.validate_content_length(short_content) is False
        assert ContentValidator.validate_content_length(long_content) is True
    
    def test_extract_domain(self):
        """Test domain extraction."""
        assert ContentValidator.extract_domain("https://example.com/path") == "example.com"
        assert ContentValidator.extract_domain("http://subdomain.example.com") == "subdomain.example.com"
        assert ContentValidator.extract_domain("invalid-url") is None
    
    def test_calculate_confidence_score(self):
        """Test confidence score calculation."""
        content = "This is a long and detailed article about important topics"
        url = "https://reuters.com/article"
        domain = "reuters.com"
        source_type = "news"
        
        score = ContentValidator.calculate_confidence_score(content, url, domain, source_type)
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be high for good content


class TestContentClassifier:
    """Test content classification functionality."""
    
    def test_classify_source_type(self):
        """Test source type classification."""
        assert ContentClassifier.classify_source_type("reuters.com") == "news"
        assert ContentClassifier.classify_source_type("gov.uk") == "government"
        assert ContentClassifier.classify_source_type("twitter.com") == "social_media"
        assert ContentClassifier.classify_source_type("reddit.com") == "social_media"
        assert ContentClassifier.classify_source_type("unknown.com") == "unknown"
    
    def test_extract_tags(self):
        """Test tag extraction."""
        content = "This article discusses climate change and global warming effects"
        title = "Climate Change Impact"
        
        tags = ContentClassifier.extract_tags(content, title)
        
        assert "climate" in tags
        assert len(tags) <= 10  # Should not exceed limit
    
    def test_calculate_relevance_score(self):
        """Test relevance score calculation."""
        content = "This article is about artificial intelligence and machine learning"
        search_query = "artificial intelligence"
        
        score = ContentClassifier.calculate_relevance_score(content, search_query)
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be relevant


class TestPydanticModels:
    """Test Pydantic model validation."""
    
    def test_post_create_validation(self):
        """Test PostCreate model validation."""
        valid_data = {
            "search_query": "test query",
            "query_timestamp": datetime.utcnow(),
            "source_url": "https://example.com",
            "content": "This is test content that is long enough",
            "source_type": "news"
        }
        
        post = PostCreate(**valid_data)
        assert post.search_query == "test query"
        assert post.source_url == "https://example.com"
    
    def test_post_create_invalid_url(self):
        """Test PostCreate with invalid URL."""
        invalid_data = {
            "search_query": "test query",
            "query_timestamp": datetime.utcnow(),
            "source_url": "invalid-url",
            "content": "This is test content that is long enough",
            "source_type": "news"
        }
        
        with pytest.raises(ValueError):
            PostCreate(**invalid_data)
    
    def test_topic_create_validation(self):
        """Test TopicCreate model validation."""
        valid_data = {
            "topic_name": "Test Topic",
            "search_query": "test query",
            "collection_priority": "normal",
            "check_frequency_hours": 24
        }
        
        topic = TopicCreate(**valid_data)
        assert topic.topic_name == "Test Topic"
        assert topic.collection_priority == "normal"
    
    def test_topic_create_invalid_priority(self):
        """Test TopicCreate with invalid priority."""
        invalid_data = {
            "topic_name": "Test Topic",
            "search_query": "test query",
            "collection_priority": "invalid",
            "check_frequency_hours": 24
        }
        
        with pytest.raises(ValueError):
            TopicCreate(**invalid_data)


class TestIntegration:
    """Test integration scenarios."""
    
    @patch('database.client.get_db_client')
    def test_database_connection_mock(self, mock_get_db_client):
        """Test database connection with mock."""
        mock_client = Mock()
        mock_client.test_connection.return_value = True
        mock_get_db_client.return_value = mock_client
        
        from database.client import test_database_connection
        assert test_database_connection() is True
    
    @patch('requests.post')
    def test_perplexity_api_mock(self, mock_post):
        """Test Perplexity API with mock."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Test response with [1] https://example.com citation"
                }
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        from collectors.perplexity_collector import PerplexityCollector
        collector = PerplexityCollector()
        
        # Mock the API key
        collector.api_key = "test-key"
        
        response = collector.make_api_request("test query")
        assert response is not None
        assert "choices" in response


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])