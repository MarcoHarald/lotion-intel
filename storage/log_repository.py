"""
Collection log repository for CRUD operations on collection_logs table.
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from database.client import get_db_client
from models.topic import CollectionLog, CollectionLogCreate, CollectionLogUpdate
from config.logging_config import get_logger

logger = get_logger("collection_log_repository")


class CollectionLogRepository:
    """Repository for collection_logs table operations."""
    
    def __init__(self):
        self.db_client = get_db_client()
        self.table = self.db_client.get_table('collection_logs')
    
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
            logger.error(f"Database error in create_collection_log: {e}")
            raise
    
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
            logger.error(f"Database error in update_collection_log: {e}")
            raise
    
    def get_by_id(self, log_id: UUID) -> Optional[CollectionLog]:
        """Get collection log by ID."""
        try:
            result = self.table.select('*').eq('id', str(log_id)).execute()
            if result.data:
                return CollectionLog(**result.data[0])
            return None
        except Exception as e:
            logger.error(f"Database error in get_collection_log_by_id: {e}")
            raise
    
    def get_by_topic(self, topic_id: UUID, limit: int = 50) -> List[CollectionLog]:
        """Get collection logs by topic."""
        try:
            result = self.table.select('*').eq('topic_id', str(topic_id)).order('started_at', desc=True).limit(limit).execute()
            return [CollectionLog(**log) for log in result.data]
        except Exception as e:
            logger.error(f"Database error in get_collection_logs_by_topic: {e}")
            raise
    
    def get_recent(self, limit: int = 100) -> List[CollectionLog]:
        """Get recent collection logs."""
        try:
            result = self.table.select('*').order('started_at', desc=True).limit(limit).execute()
            return [CollectionLog(**log) for log in result.data]
        except Exception as e:
            logger.error(f"Database error in get_recent_collection_logs: {e}")
            raise
    
    def get_errors(self, limit: int = 50) -> List[CollectionLog]:
        """Get collection logs with errors."""
        try:
            result = self.table.select('*').eq('status', 'error').order('started_at', desc=True).limit(limit).execute()
            return [CollectionLog(**log) for log in result.data]
        except Exception as e:
            logger.error(f"Database error in get_error_collection_logs: {e}")
            raise
