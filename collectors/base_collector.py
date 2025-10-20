"""
Base collector class with common functionality.
Abstract base class for all collectors.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
from models.topic import Topic, CollectionLogCreate, CollectionLogUpdate
from models.post import PostCreate
from storage.topic_repository import TopicRepository
from storage.log_repository import CollectionLogRepository
from storage.post_repository import PostRepository
from collectors.utils import rate_limiter, deduplication_manager, content_validator, content_classifier
from config.logging_config import get_logger

logger = get_logger("base_collector")


class BaseCollector(ABC):
    """Abstract base class for all collectors."""
    
    def __init__(self):
        self.topic_repo = TopicRepository()
        self.log_repo = CollectionLogRepository()
        self.post_repo = PostRepository()
        self.collection_log: Optional[CollectionLogCreate] = None
    
    def should_collect(self, topic: Topic) -> bool:
        """Check if topic should be collected."""
        if not topic.active:
            logger.info(f"Topic {topic.topic_name} is inactive, skipping")
            return False
        
        # Check rate limits
        if not rate_limiter.can_make_call():
            logger.warning("Rate limit reached, skipping collection")
            return False
        
        return True
    
    def validate_post(self, post_data: Dict[str, Any]) -> bool:
        """Validate post data before insertion."""
        try:
            # Check URL format
            if not content_validator.validate_url(post_data.get('source_url', '')):
                logger.warning(f"Invalid URL format: {post_data.get('source_url')}")
                return False
            
            # Check content length
            if not content_validator.validate_content_length(post_data.get('content', '')):
                logger.warning(f"Content too short: {len(post_data.get('content', ''))} chars")
                return False
            
            # Check for duplicates
            if deduplication_manager.is_duplicate_url(post_data.get('source_url', '')):
                logger.info(f"Duplicate URL found: {post_data.get('source_url')}")
                return False
            
            if deduplication_manager.is_duplicate_content(post_data.get('content', '')):
                logger.info("Duplicate content found")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating post: {e}")
            return False
    
    def process_post(self, raw_post: Dict[str, Any], topic: Topic) -> Optional[PostCreate]:
        """Process raw post data into PostCreate model."""
        try:
            # Extract basic fields
            source_url = raw_post.get('url', '')
            content = raw_post.get('content', '')
            title = raw_post.get('title', '')
            
            # Extract domain
            domain = content_validator.extract_domain(source_url)
            
            # Classify source type
            source_type = content_classifier.classify_source_type(domain)
            
            # Calculate scores
            confidence_score = content_validator.calculate_confidence_score(
                content, source_url, domain, source_type
            )
            
            relevance_score = content_classifier.calculate_relevance_score(
                content, topic.search_query
            )
            
            # Extract tags
            tags = content_classifier.extract_tags(content, title)
            
            # Create post data
            post_data = PostCreate(
                search_query=topic.search_query,
                query_timestamp=datetime.utcnow(),
                source_url=source_url,
                source_title=title,
                source_domain=domain,
                source_type=source_type,
                content=content,
                full_answer=raw_post.get('full_answer'),
                metadata=raw_post.get('metadata', {}),
                relevance_score=relevance_score,
                confidence_score=confidence_score,
                tags=tags
            )
            
            return post_data
        except Exception as e:
            logger.error(f"Error processing post: {e}")
            return None
    
    def log_collection_attempt(self, topic: Topic, strategy: str) -> UUID:
        """Log collection attempt start."""
        try:
            log_data = CollectionLogCreate(
                topic_id=topic.id,
                status='success',  # Will be updated if error occurs
                query_used=topic.search_query,
                collection_strategy=strategy,
                metadata={'topic_name': topic.topic_name}
            )
            
            self.collection_log = log_data
            log = self.log_repo.create_log(log_data)
            logger.info(f"Started collection for topic {topic.topic_name} with strategy {strategy}")
            return log.id
        except Exception as e:
            logger.error(f"Error logging collection attempt: {e}")
            raise
    
    def update_collection_log(self, log_id: UUID, **updates) -> None:
        """Update collection log with results."""
        try:
            log_update = CollectionLogUpdate(**updates)
            self.log_repo.update_log(log_id, log_update)
        except Exception as e:
            logger.error(f"Error updating collection log: {e}")
    
    def handle_rate_limit(self) -> None:
        """Handle rate limiting."""
        rate_limiter.wait_if_needed()
        rate_limiter.record_call()
    
    def collect_for_topic(self, topic: Topic) -> Dict[str, Any]:
        """Main collection method for a topic."""
        if not self.should_collect(topic):
            return {'success': False, 'reason': 'Should not collect'}
        
        # Determine collection strategy
        strategy = self.determine_collection_strategy(topic)
        
        # Log collection start
        log_id = self.log_collection_attempt(topic, strategy)
        
        try:
            # Handle rate limiting
            self.handle_rate_limit()
            
            # Perform collection
            raw_posts = self.collect_posts(topic, strategy)
            
            # Process and validate posts
            processed_posts = []
            duplicates = 0
            invalid = 0
            
            for raw_post in raw_posts:
                if self.validate_post(raw_post):
                    post_data = self.process_post(raw_post, topic)
                    if post_data:
                        try:
                            # Create post in database
                            post = self.post_repo.create(post_data)
                            processed_posts.append(post)
                            
                            # Add to deduplication cache
                            deduplication_manager.add_url(post.source_url)
                            deduplication_manager.add_content(post.content)
                            
                        except Exception as e:
                            logger.error(f"Error creating post: {e}")
                            invalid += 1
                    else:
                        invalid += 1
                else:
                    duplicates += 1
            
            # Update topic metrics
            self.topic_repo.update_last_checked(topic.id)
            self.topic_repo.update_metrics(topic.id, len(processed_posts))
            
            # Update collection log
            self.update_collection_log(
                log_id,
                status='success',
                total_results=len(raw_posts),
                new_posts=len(processed_posts),
                duplicate_posts=duplicates,
                invalid_posts=invalid,
                api_calls_used=1
            )
            
            logger.info(f"Collection completed for {topic.topic_name}: {len(processed_posts)} new posts")
            
            return {
                'success': True,
                'posts_collected': len(processed_posts),
                'duplicates': duplicates,
                'invalid': invalid,
                'strategy': strategy
            }
            
        except Exception as e:
            logger.error(f"Collection failed for {topic.topic_name}: {e}")
            
            # Update collection log with error
            self.update_collection_log(
                log_id,
                status='error',
                error_message=str(e),
                error_traceback=str(e)
            )
            
            return {
                'success': False,
                'error': str(e),
                'strategy': strategy
            }
    
    def determine_collection_strategy(self, topic: Topic) -> str:
        """Determine collection strategy based on topic history."""
        if topic.last_checked is None:
            return 'initial'
        else:
            return 'incremental'
    
    @abstractmethod
    def collect_posts(self, topic: Topic, strategy: str) -> List[Dict[str, Any]]:
        """Abstract method to collect posts. Must be implemented by subclasses."""
        pass
