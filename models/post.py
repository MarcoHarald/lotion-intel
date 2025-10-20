"""
Pydantic models for data validation and serialization.
Ensures data integrity before database operations.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, validator
from config.settings import SOURCE_TYPES, COLLECTION_PRIORITIES, COLLECTION_STRATEGIES, STATUS_VALUES


class PostBase(BaseModel):
    """Base model for posts with common fields."""
    search_query: str = Field(..., min_length=1, max_length=1000)
    query_timestamp: datetime
    source_url: str = Field(..., min_length=1, max_length=2048)
    source_title: Optional[str] = Field(None, max_length=500)
    source_domain: Optional[str] = Field(None, max_length=255)
    source_type: str = Field(default="unknown")
    content: str = Field(..., min_length=1, max_length=10000)
    full_answer: Optional[str] = Field(None, max_length=50000)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_valid: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    
    @validator('source_type')
    def validate_source_type(cls, v):
        if v not in SOURCE_TYPES:
            raise ValueError(f'Source type must be one of: {SOURCE_TYPES}')
        return v
    
    @validator('source_url')
    def validate_url_format(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Source URL must start with http:// or https://')
        return v
    
    @validator('tags')
    def validate_tags(cls, v):
        if len(v) > 20:  # Reasonable limit for tags
            raise ValueError('Too many tags (max 20)')
        return v


class PostCreate(PostBase):
    """Model for creating new posts."""
    pass


class PostUpdate(BaseModel):
    """Model for updating existing posts."""
    source_title: Optional[str] = Field(None, max_length=500)
    source_domain: Optional[str] = Field(None, max_length=255)
    source_type: Optional[str] = None
    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    full_answer: Optional[str] = Field(None, max_length=50000)
    metadata: Optional[Dict[str, Any]] = None
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_valid: Optional[bool] = None
    tags: Optional[List[str]] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    @validator('source_type')
    def validate_source_type(cls, v):
        if v is not None and v not in SOURCE_TYPES:
            raise ValueError(f'Source type must be one of: {SOURCE_TYPES}')
        return v


class Post(PostBase):
    """Complete post model with database fields."""
    id: UUID
    collected_at: datetime
    soft_deleted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TopicBase(BaseModel):
    """Base model for monitored topics."""
    topic_name: str = Field(..., min_length=1, max_length=255)
    search_query: str = Field(..., min_length=1, max_length=1000)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = Field(None, max_length=100)
    active: bool = Field(default=True)
    check_frequency_hours: int = Field(default=24, gt=0)
    collection_priority: str = Field(default="normal")
    
    @validator('collection_priority')
    def validate_collection_priority(cls, v):
        if v not in COLLECTION_PRIORITIES:
            raise ValueError(f'Collection priority must be one of: {COLLECTION_PRIORITIES}')
        return v
    
    @validator('check_frequency_hours')
    def validate_check_frequency(cls, v):
        if v < 1:
            raise ValueError('Check frequency must be at least 1 hour')
        if v > 168:  # Max 1 week
            raise ValueError('Check frequency cannot exceed 168 hours (1 week)')
        return v


class TopicCreate(TopicBase):
    """Model for creating new topics."""
    pass


class TopicUpdate(BaseModel):
    """Model for updating existing topics."""
    topic_name: Optional[str] = Field(None, min_length=1, max_length=255)
    search_query: Optional[str] = Field(None, min_length=1, max_length=1000)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = Field(None, max_length=100)
    active: Optional[bool] = None
    check_frequency_hours: Optional[int] = Field(None, gt=0)
    collection_priority: Optional[str] = None
    
    @validator('collection_priority')
    def validate_collection_priority(cls, v):
        if v is not None and v not in COLLECTION_PRIORITIES:
            raise ValueError(f'Collection priority must be one of: {COLLECTION_PRIORITIES}')
        return v
    
    @validator('check_frequency_hours')
    def validate_check_frequency(cls, v):
        if v is not None:
            if v < 1:
                raise ValueError('Check frequency must be at least 1 hour')
            if v > 168:  # Max 1 week
                raise ValueError('Check frequency cannot exceed 168 hours (1 week)')
        return v


class Topic(TopicBase):
    """Complete topic model with database fields."""
    id: UUID
    last_checked: Optional[datetime] = None
    query_version: int = Field(default=1)
    query_history: List[Dict[str, Any]] = Field(default_factory=list)
    version: int = Field(default=1)
    created_by: Optional[UUID] = None
    total_posts_collected: int = Field(default=0, ge=0)
    avg_posts_per_query: float = Field(default=0.0, ge=0.0)
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CollectionLogBase(BaseModel):
    """Base model for collection logs."""
    topic_id: Optional[UUID] = None
    status: str
    query_used: str = Field(..., min_length=1, max_length=1000)
    total_results: int = Field(default=0, ge=0)
    new_posts: int = Field(default=0, ge=0)
    duplicate_posts: int = Field(default=0, ge=0)
    invalid_posts: int = Field(default=0, ge=0)
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None
    collection_strategy: str = Field(default="initial")
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    api_calls_used: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('status')
    def validate_status(cls, v):
        if v not in STATUS_VALUES:
            raise ValueError(f'Status must be one of: {STATUS_VALUES}')
        return v
    
    @validator('collection_strategy')
    def validate_collection_strategy(cls, v):
        if v not in COLLECTION_STRATEGIES:
            raise ValueError(f'Collection strategy must be one of: {COLLECTION_STRATEGIES}')
        return v
    
    @validator('time_range_end')
    def validate_time_range(cls, v, values):
        if v is not None and 'time_range_start' in values and values['time_range_start'] is not None:
            if v < values['time_range_start']:
                raise ValueError('Time range end must be after time range start')
        return v


class CollectionLogCreate(CollectionLogBase):
    """Model for creating new collection logs."""
    pass


class CollectionLogUpdate(BaseModel):
    """Model for updating collection logs."""
    completed_at: Optional[datetime] = None
    status: Optional[str] = None
    total_results: Optional[int] = Field(None, ge=0)
    new_posts: Optional[int] = Field(None, ge=0)
    duplicate_posts: Optional[int] = Field(None, ge=0)
    invalid_posts: Optional[int] = Field(None, ge=0)
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    api_calls_used: Optional[int] = Field(None, ge=0)
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None and v not in STATUS_VALUES:
            raise ValueError(f'Status must be one of: {STATUS_VALUES}')
        return v


class CollectionLog(CollectionLogBase):
    """Complete collection log model with database fields."""
    id: UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class QueryMetricsBase(BaseModel):
    """Base model for query metrics."""
    topic_id: UUID
    execution_date: datetime
    results_count: int = Field(default=0, ge=0)
    unique_sources_count: int = Field(default=0, ge=0)
    avg_relevance: Optional[float] = Field(None, ge=0.0, le=1.0)
    duplicate_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class QueryMetricsCreate(QueryMetricsBase):
    """Model for creating new query metrics."""
    pass


class QueryMetrics(QueryMetricsBase):
    """Complete query metrics model."""
    
    class Config:
        from_attributes = True


# Response models for API endpoints

class PostResponse(BaseModel):
    """Response model for posts with topic information."""
    id: UUID
    search_query: str
    query_timestamp: datetime
    source_url: str
    source_title: Optional[str]
    source_domain: Optional[str]
    source_type: str
    content: str
    collected_at: datetime
    relevance_score: Optional[float]
    confidence_score: float
    tags: List[str]
    topic_names: List[str] = Field(default_factory=list)


class TopicResponse(BaseModel):
    """Response model for topics with statistics."""
    id: UUID
    topic_name: str
    search_query: str
    description: Optional[str]
    category: Optional[str]
    active: bool
    check_frequency_hours: int
    collection_priority: str
    last_checked: Optional[datetime]
    total_posts_collected: int
    avg_posts_per_query: float
    created_at: datetime
    updated_at: datetime


class CollectionStatsResponse(BaseModel):
    """Response model for collection statistics."""
    topic_id: UUID
    topic_name: str
    collection_priority: str
    total_posts: int
    posts_last_24h: int
    posts_last_7d: int
    avg_confidence: Optional[float]
    unique_sources: int
    last_post_collected: Optional[datetime]


class HealthCheckResponse(BaseModel):
    """Response model for health checks."""
    status: str
    timestamp: datetime
    database_connected: bool
    api_keys_configured: bool
    active_topics_count: int
    recent_collections_count: int
    last_collection_time: Optional[datetime]
    errors: List[str] = Field(default_factory=list)
