"""
Repository classes for CRUD operations.
Encapsulates database operations with proper error handling.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from supabase import Client
from database.client import get_db_client
from models.post import Post, PostCreate, PostUpdate
from models.topic import Topic, TopicCreate, TopicUpdate, CollectionLog, CollectionLogCreate, CollectionLogUpdate
from config.logging_config import get_logger

logger = get_logger("repositories")


class BaseRepository:
    """Base repository class with common database operations."""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.db_client = get_db_client()
        self.table = self.db_client.get_table(table_name)
    
    def _handle_error(self, operation: str, error: Exception) -> None:
        """Handle database errors with logging."""
        logger.error(f"Database error in {operation}: {error}")
        raise


class PostRepository(BaseRepository):
    """Repository for posts table operations."""
    
    def __init__(self):
        super().__init__('posts')
    
    def create(self, post_data: PostCreate) -> Post:
        """Create a new post."""
        try:
            # Convert Pydantic model to dict
            data = post_data.dict()
            data['collected_at'] = datetime.utcnow()
            
            result = self.table.insert(data).execute()
            if result.data:
                return Post(**result.data[0])
            raise Exception("No data returned from insert")
        except Exception as e:
            self._handle_error("create_post", e)
    
    def get_by_id(self, post_id: UUID) -> Optional[Post]:
        """Get post by ID."""
        try:
            result = self.table.select('*').eq('id', str(post_id)).execute()
            if result.data:
                return Post(**result.data[0])
            return None
        except Exception as e:
            self._handle_error("get_post_by_id", e)
    
    def exists_by_url(self, source_url: str) -> bool:
        """Check if post exists by source URL."""
        try:
            result = self.table.select('id').eq('source_url', source_url).execute()
            return len(result.data) > 0
        except Exception as e:
            self._handle_error("check_post_exists_by_url", e)
    
    def exists_by_content_hash(self, content_hash: str) -> bool:
        """Check if post exists by content hash."""
        try:
            result = self.table.select('id').eq('metadata->content_hash', content_hash).execute()
            return len(result.data) > 0
        except Exception as e:
            self._handle_error("check_post_exists_by_content_hash", e)
    
    def get_by_topic(self, topic_id: UUID, limit: int = 100, offset: int = 0) -> List[Post]:
        """Get posts by topic ID."""
        try:
            # Join with topic_posts table
            result = self.table.select('posts.*').eq('topic_posts.topic_id', str(topic_id)).execute()
            posts = [Post(**post) for post in result.data[offset:offset + limit]]
            return posts
        except Exception as e:
            self._handle_error("get_posts_by_topic", e)
    
    def get_recent(self, limit: int = 50, days: int = 7) -> List[Post]:
        """Get recent posts."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            result = self.table.select('*').gte('collected_at', cutoff_date.isoformat()).order('collected_at', desc=True).limit(limit).execute()
            return [Post(**post) for post in result.data]
        except Exception as e:
            self._handle_error("get_recent_posts", e)
    
    def get_by_confidence_score(self, min_score: float, max_score: float = 1.0, limit: int = 100) -> List[Post]:
        """Get posts by confidence score range."""
        try:
            result = self.table.select('*').gte('confidence_score', min_score).lte('confidence_score', max_score).order('confidence_score', desc=True).limit(limit).execute()
            return [Post(**post) for post in result.data]
        except Exception as e:
            self._handle_error("get_posts_by_confidence_score", e)
    
    def soft_delete(self, post_id: UUID) -> bool:
        """Soft delete a post."""
        try:
            result = self.table.update({'soft_deleted_at': datetime.utcnow().isoformat()}).eq('id', str(post_id)).execute()
            return len(result.data) > 0
        except Exception as e:
            self._handle_error("soft_delete_post", e)
    
    def update(self, post_id: UUID, post_data: PostUpdate) -> Optional[Post]:
        """Update a post."""
        try:
            data = post_data.dict(exclude_unset=True)
            if not data:
                return self.get_by_id(post_id)
            
            result = self.table.update(data).eq('id', str(post_id)).execute()
            if result.data:
                return Post(**result.data[0])
            return None
        except Exception as e:
            self._handle_error("update_post", e)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get post statistics."""
        try:
            # Total posts
            total_result = self.table.select('id', count='exact').execute()
            total_posts = total_result.count
            
            # Posts today
            today = datetime.utcnow().date()
            today_result = self.table.select('id', count='exact').gte('collected_at', today.isoformat()).execute()
            posts_today = today_result.count
            
            # Posts this week
            week_ago = datetime.utcnow() - timedelta(days=7)
            week_result = self.table.select('id', count='exact').gte('collected_at', week_ago.isoformat()).execute()
            posts_this_week = week_result.count
            
            # Average confidence score
            avg_result = self.table.select('confidence_score').not_.is_('confidence_score', 'null').execute()
            avg_confidence = sum(post['confidence_score'] for post in avg_result.data) / len(avg_result.data) if avg_result.data else 0.0
            
            return {
                'total_posts': total_posts,
                'posts_today': posts_today,
                'posts_this_week': posts_this_week,
                'avg_confidence_score': avg_confidence
            }
        except Exception as e:
            self._handle_error("get_post_stats", e)


class TopicRepository(BaseRepository):
    """Repository for monitored_topics table operations."""
    
    def __init__(self):
        super().__init__('monitored_topics')
    
    def create(self, topic_data: TopicCreate) -> Topic:
        """Create a new topic."""
        try:
            data = topic_data.dict()
            data['created_at'] = datetime.utcnow().isoformat()
            data['updated_at'] = datetime.utcnow().isoformat()
            
            result = self.table.insert(data).execute()
            if result.data:
                return Topic(**result.data[0])
            raise Exception("No data returned from insert")
        except Exception as e:
            self._handle_error("create_topic", e)
    
    def get_by_id(self, topic_id: UUID) -> Optional[Topic]:
        """Get topic by ID."""
        try:
            result = self.table.select('*').eq('id', str(topic_id)).execute()
            if result.data:
                return Topic(**result.data[0])
            return None
        except Exception as e:
            self._handle_error("get_topic_by_id", e)
    
    def get_active(self) -> List[Topic]:
        """Get all active topics."""
        try:
            result = self.table.select('*').eq('active', True).execute()
            return [Topic(**topic) for topic in result.data]
        except Exception as e:
            self._handle_error("get_active_topics", e)
    
    def get_due_for_collection(self) -> List[Topic]:
        """Get topics due for collection."""
        try:
            now = datetime.utcnow()
            result = self.table.select('*').eq('active', True).or_(
                f'last_checked.is.null,last_checked.lt.{now.isoformat()}'
            ).execute()
            
            # Filter by check frequency
            due_topics = []
            for topic_data in result.data:
                topic = Topic(**topic_data)
                if topic.last_checked is None:
                    due_topics.append(topic)
                else:
                    hours_since_check = (now - topic.last_checked).total_seconds() / 3600
                    if hours_since_check >= topic.check_frequency_hours:
                        due_topics.append(topic)
            
            return due_topics
        except Exception as e:
            self._handle_error("get_topics_due_for_collection", e)
    
    def get_by_priority(self, priority: str) -> List[Topic]:
        """Get topics by collection priority."""
        try:
            result = self.table.select('*').eq('collection_priority', priority).eq('active', True).execute()
            return [Topic(**topic) for topic in result.data]
        except Exception as e:
            self._handle_error("get_topics_by_priority", e)
    
    def update_last_checked(self, topic_id: UUID) -> bool:
        """Update last checked timestamp."""
        try:
            result = self.table.update({'last_checked': datetime.utcnow().isoformat()}).eq('id', str(topic_id)).execute()
            return len(result.data) > 0
        except Exception as e:
            self._handle_error("update_last_checked", e)
    
    def update_metrics(self, topic_id: UUID, posts_collected: int) -> bool:
        """Update topic metrics."""
        try:
            # Get current metrics
            topic = self.get_by_id(topic_id)
            if not topic:
                return False
            
            new_total = topic.total_posts_collected + posts_collected
            new_avg = new_total / max(topic.query_version, 1)
            
            result = self.table.update({
                'total_posts_collected': new_total,
                'avg_posts_per_query': new_avg
            }).eq('id', str(topic_id)).execute()
            
            return len(result.data) > 0
        except Exception as e:
            self._handle_error("update_topic_metrics", e)
    
    def update(self, topic_id: UUID, topic_data: TopicUpdate) -> Optional[Topic]:
        """Update a topic."""
        try:
            data = topic_data.dict(exclude_unset=True)
            if not data:
                return self.get_by_id(topic_id)
            
            data['updated_at'] = datetime.utcnow().isoformat()
            result = self.table.update(data).eq('id', str(topic_id)).execute()
            if result.data:
                return Topic(**result.data[0])
            return None
        except Exception as e:
            self._handle_error("update_topic", e)
    
    def delete(self, topic_id: UUID) -> bool:
        """Delete a topic."""
        try:
            result = self.table.delete().eq('id', str(topic_id)).execute()
            return len(result.data) > 0
        except Exception as e:
            self._handle_error("delete_topic", e)


class CollectionLogRepository(BaseRepository):
    """Repository for collection_logs table operations."""
    
    def __init__(self):
        super().__init__('collection_logs')
    
    def create_log(self, log_data: CollectionLogCreate) -> CollectionLog:
        """Create a new collection log."""
        try:
            data = log_data.dict()
            data['started_at'] = datetime.utcnow().isoformat()
            
            result = self.table.insert(data).execute()
            if result.data:
                return CollectionLog(**result.data[0])
            raise Exception("No data returned from insert")
        except Exception as e:
            self._handle_error("create_collection_log", e)
    
    def update_log(self, log_id: UUID, log_data: CollectionLogUpdate) -> Optional[CollectionLog]:
        """Update a collection log."""
        try:
            data = log_data.dict(exclude_unset=True)
            if not data:
                return self.get_by_id(log_id)
            
            if 'completed_at' not in data:
                data['completed_at'] = datetime.utcnow().isoformat()
            
            result = self.table.update(data).eq('id', str(log_id)).execute()
            if result.data:
                return CollectionLog(**result.data[0])
            return None
        except Exception as e:
            self._handle_error("update_collection_log", e)
    
    def get_by_id(self, log_id: UUID) -> Optional[CollectionLog]:
        """Get collection log by ID."""
        try:
            result = self.table.select('*').eq('id', str(log_id)).execute()
            if result.data:
                return CollectionLog(**result.data[0])
            return None
        except Exception as e:
            self._handle_error("get_collection_log_by_id", e)
    
    def get_by_topic(self, topic_id: UUID, limit: int = 50) -> List[CollectionLog]:
        """Get collection logs by topic."""
        try:
            result = self.table.select('*').eq('topic_id', str(topic_id)).order('started_at', desc=True).limit(limit).execute()
            return [CollectionLog(**log) for log in result.data]
        except Exception as e:
            self._handle_error("get_collection_logs_by_topic", e)
    
    def get_recent(self, limit: int = 100) -> List[CollectionLog]:
        """Get recent collection logs."""
        try:
            result = self.table.select('*').order('started_at', desc=True).limit(limit).execute()
            return [CollectionLog(**log) for log in result.data]
        except Exception as e:
            self._handle_error("get_recent_collection_logs", e)
    
    def get_errors(self, limit: int = 50) -> List[CollectionLog]:
        """Get collection logs with errors."""
        try:
            result = self.table.select('*').eq('status', 'error').order('started_at', desc=True).limit(limit).execute()
            return [CollectionLog(**log) for log in result.data]
        except Exception as e:
            self._handle_error("get_error_collection_logs", e)
