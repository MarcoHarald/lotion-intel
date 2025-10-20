"""
Topic repository for CRUD operations on monitored_topics table.
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from database.client import get_db_client
from models.topic import Topic, TopicCreate, TopicUpdate
from config.logging_config import get_logger

logger = get_logger("topic_repository")


class TopicRepository:
    """Repository for monitored_topics table operations."""
    
    def __init__(self):
        self.db_client = get_db_client()
        self.table = self.db_client.get_table('monitored_topics')
    
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
            logger.error(f"Database error in create_topic: {e}")
            raise
    
    def get_by_id(self, topic_id: UUID) -> Optional[Topic]:
        """Get topic by ID."""
        try:
            result = self.table.select('*').eq('id', str(topic_id)).execute()
            if result.data:
                return Topic(**result.data[0])
            return None
        except Exception as e:
            logger.error(f"Database error in get_topic_by_id: {e}")
            raise
    
    def get_active(self) -> List[Topic]:
        """Get all active topics."""
        try:
            result = self.table.select('*').eq('active', True).execute()
            return [Topic(**topic) for topic in result.data]
        except Exception as e:
            logger.error(f"Database error in get_active_topics: {e}")
            raise
    
    def get_due_for_collection(self) -> List[Topic]:
        """Get topics due for collection."""
        try:
            now = datetime.utcnow()
            result = self.table.select('*').eq('active', True).execute()
            
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
            logger.error(f"Database error in get_topics_due_for_collection: {e}")
            raise
    
    def get_by_priority(self, priority: str) -> List[Topic]:
        """Get topics by collection priority."""
        try:
            result = self.table.select('*').eq('collection_priority', priority).eq('active', True).execute()
            return [Topic(**topic) for topic in result.data]
        except Exception as e:
            logger.error(f"Database error in get_topics_by_priority: {e}")
            raise
    
    def update_last_checked(self, topic_id: UUID) -> bool:
        """Update last checked timestamp."""
        try:
            result = self.table.update({'last_checked': datetime.utcnow().isoformat()}).eq('id', str(topic_id)).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Database error in update_last_checked: {e}")
            raise
    
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
            logger.error(f"Database error in update_topic_metrics: {e}")
            raise
    
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
            logger.error(f"Database error in update_topic: {e}")
            raise
    
    def delete(self, topic_id: UUID) -> bool:
        """Delete a topic."""
        try:
            result = self.table.delete().eq('id', str(topic_id)).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Database error in delete_topic: {e}")
            raise
