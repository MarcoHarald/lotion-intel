"""
Configuration settings loaded from environment variables.
Uses Pydantic for validation and type safety.
"""
from typing import List, Optional
from pydantic import BaseSettings, Field, validator
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Supabase Configuration
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")
    
    # Perplexity API
    perplexity_api_key: str = Field(..., env="PERPLEXITY_API_KEY")
    
    # Rate Limiting
    max_queries_per_minute: int = Field(default=10, env="MAX_QUERIES_PER_MINUTE")
    max_queries_per_day: int = Field(default=1000, env="MAX_QUERIES_PER_DAY")
    query_delay_seconds: float = Field(default=6.0, env="QUERY_DELAY_SECONDS")
    
    # Collection Settings
    default_check_frequency_hours: int = Field(default=24, env="DEFAULT_CHECK_FREQUENCY_HOURS")
    min_content_length: int = Field(default=50, env="MIN_CONTENT_LENGTH")
    
    # Smart Collection Settings
    initial_collection_days: int = Field(default=7, env="INITIAL_COLLECTION_DAYS")
    incremental_collection_hours: int = Field(default=24, env="INCREMENTAL_COLLECTION_HOURS")
    max_collection_gap_hours: int = Field(default=48, env="MAX_COLLECTION_GAP_HOURS")
    enable_time_bounded_queries: bool = Field(default=True, env="ENABLE_TIME_BOUNDED_QUERIES")
    
    # Data Quality
    enable_duplicate_prevention: bool = Field(default=True, env="ENABLE_DUPLICATE_PREVENTION")
    high_confidence_threshold: float = Field(default=0.8, env="HIGH_CONFIDENCE_THRESHOLD")
    medium_confidence_threshold: float = Field(default=0.5, env="MEDIUM_CONFIDENCE_THRESHOLD")
    low_confidence_threshold: float = Field(default=0.2, env="LOW_CONFIDENCE_THRESHOLD")
    
    # Retention Policies
    critical_retention_days: int = Field(default=365, env="CRITICAL_RETENTION_DAYS")
    standard_retention_days: int = Field(default=180, env="STANDARD_RETENTION_DAYS")
    archive_retention_days: int = Field(default=90, env="ARCHIVE_RETENTION_DAYS")
    
    # Priority Frequencies
    critical_priority_frequency_hours: int = Field(default=6, env="CRITICAL_PRIORITY_FREQUENCY_HOURS")
    normal_priority_frequency_hours: int = Field(default=24, env="NORMAL_PRIORITY_FREQUENCY_HOURS")
    low_priority_frequency_hours: int = Field(default=72, env="LOW_PRIORITY_FREQUENCY_HOURS")
    
    # Health Monitoring
    health_check_timeout_seconds: int = Field(default=30, env="HEALTH_CHECK_TIMEOUT_SECONDS")
    health_check_retry_attempts: int = Field(default=3, env="HEALTH_CHECK_RETRY_ATTEMPTS")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Trusted domains for source validation
    trusted_domains: List[str] = Field(
        default=[
            "reuters.com", "bbc.com", "cnn.com", "nytimes.com", "washingtonpost.com",
            "guardian.com", "wsj.com", "bloomberg.com", "ap.org", "npr.org",
            "gov.uk", "gov.au", "gov.ca", "europa.eu", "who.int", "un.org"
        ],
        env="TRUSTED_DOMAINS"
    )
    
    @validator('high_confidence_threshold', 'medium_confidence_threshold', 'low_confidence_threshold')
    def validate_confidence_thresholds(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence thresholds must be between 0.0 and 1.0')
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()
    
    @validator('trusted_domains', pre=True)
    def parse_trusted_domains(cls, v):
        if isinstance(v, str):
            return [domain.strip() for domain in v.split(',')]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


# Constants
class Constants:
    """Application constants."""
    
    # Source Types
    SOURCE_TYPES = [
        "news", "government", "forum", "blog", 
        "social_media", "unknown"
    ]
    
    # Collection Priorities
    COLLECTION_PRIORITIES = ["critical", "normal", "low"]
    
    # Collection Strategies
    COLLECTION_STRATEGIES = ["initial", "incremental", "gap_fill"]
    
    # Status Values
    STATUS_VALUES = ["success", "rate_limited", "error"]
    
    # Database Constraints
    MAX_URL_LENGTH = 2048
    MAX_TITLE_LENGTH = 500
    MAX_CONTENT_LENGTH = 10000
    MAX_METADATA_SIZE = 10000  # JSONB field size limit
    
    # API Limits
    PERPLEXITY_MAX_TOKENS = 4000
    PERPLEXITY_TIMEOUT_SECONDS = 30
    
    # Collection Limits
    MAX_POSTS_PER_COLLECTION = 50
    MAX_TOPICS_PER_SCHEDULER_RUN = 10


# Export commonly used constants
SOURCE_TYPES = Constants.SOURCE_TYPES
COLLECTION_PRIORITIES = Constants.COLLECTION_PRIORITIES
COLLECTION_STRATEGIES = Constants.COLLECTION_STRATEGIES
STATUS_VALUES = Constants.STATUS_VALUES
