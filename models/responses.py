"""
Response models for API endpoints and dashboard.
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


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


class DashboardStatsResponse(BaseModel):
    """Response model for dashboard statistics."""
    total_posts: int
    total_topics: int
    active_topics: int
    posts_today: int
    posts_this_week: int
    avg_confidence_score: Optional[float]
    top_sources: List[dict]
    recent_activity: List[dict]
    collection_health: dict
