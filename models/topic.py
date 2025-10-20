"""
Pydantic models for topics and collection logs.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, validator
from config.settings import COLLECTION_PRIORITIES, COLLECTION_STRATEGIES, STATUS_VALUES


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
