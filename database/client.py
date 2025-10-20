"""
Supabase database client singleton.
Handles connection management and provides database operations.
"""
import os
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("database")


class DatabaseClient:
    """Singleton Supabase client for database operations."""
    
    _instance: Optional['DatabaseClient'] = None
    _client: Optional[Client] = None
    
    def __new__(cls) -> 'DatabaseClient':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._connect()
    
    def _connect(self) -> None:
        """Initialize Supabase connection."""
        try:
            self._client = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    @property
    def client(self) -> Client:
        """Get the Supabase client instance."""
        if self._client is None:
            self._connect()
        return self._client
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            # Simple query to test connection
            result = self._client.table('monitored_topics').select('id').limit(1).execute()
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a raw SQL query."""
        try:
            result = self._client.rpc('execute_sql', {'query': query, 'params': params or {}}).execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            raise
    
    def get_table(self, table_name: str):
        """Get a table reference."""
        return self._client.table(table_name)
    
    def close(self) -> None:
        """Close the database connection."""
        if self._client:
            # Supabase client doesn't have explicit close method
            # Connection will be closed when object is garbage collected
            self._client = None
            logger.info("Database connection closed")


# Global database client instance
db_client = DatabaseClient()


def get_db_client() -> DatabaseClient:
    """Get the global database client instance."""
    return db_client


def test_database_connection() -> bool:
    """Test if database connection is working."""
    return db_client.test_connection()


# Health check function
def health_check() -> Dict[str, Any]:
    """Perform database health check."""
    try:
        # Test basic connection
        connection_ok = test_database_connection()
        
        # Test table access
        tables_ok = True
        try:
            db_client.get_table('monitored_topics').select('id').limit(1).execute()
            db_client.get_table('posts').select('id').limit(1).execute()
            db_client.get_table('collection_logs').select('id').limit(1).execute()
        except Exception as e:
            tables_ok = False
            logger.error(f"Table access test failed: {e}")
        
        return {
            'database_connected': connection_ok,
            'tables_accessible': tables_ok,
            'status': 'healthy' if connection_ok and tables_ok else 'unhealthy'
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            'database_connected': False,
            'tables_accessible': False,
            'status': 'unhealthy',
            'error': str(e)
        }
