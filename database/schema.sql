-- Monitoring App Database Schema
-- PostgreSQL with pgvector extension for future AI features

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- Create custom types
CREATE TYPE collection_priority AS ENUM ('critical', 'normal', 'low');
CREATE TYPE source_type AS ENUM ('news', 'government', 'forum', 'blog', 'social_media', 'unknown');
CREATE TYPE collection_strategy AS ENUM ('initial', 'incremental', 'gap_fill');
CREATE TYPE collection_status AS ENUM ('success', 'rate_limited', 'error');

-- Core Tables

-- Monitored Topics Table
CREATE TABLE monitored_topics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic_name VARCHAR(255) NOT NULL UNIQUE,
    search_query TEXT NOT NULL,
    description TEXT,
    category VARCHAR(100),
    active BOOLEAN NOT NULL DEFAULT true,
    check_frequency_hours INTEGER NOT NULL DEFAULT 24,
    last_checked TIMESTAMP WITH TIME ZONE,
    query_version INTEGER NOT NULL DEFAULT 1,
    query_history JSONB DEFAULT '[]'::jsonb,
    collection_priority collection_priority NOT NULL DEFAULT 'normal',
    version INTEGER NOT NULL DEFAULT 1,
    created_by UUID, -- For future multi-user support
    total_posts_collected INTEGER DEFAULT 0,
    avg_posts_per_query DECIMAL(5,2) DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_frequency_positive CHECK (check_frequency_hours > 0),
    CONSTRAINT query_version_positive CHECK (query_version > 0),
    CONSTRAINT version_positive CHECK (version > 0),
    CONSTRAINT total_posts_non_negative CHECK (total_posts_collected >= 0),
    CONSTRAINT avg_posts_non_negative CHECK (avg_posts_per_query >= 0.0)
);

-- Posts Table
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    search_query TEXT NOT NULL,
    query_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source_url TEXT NOT NULL UNIQUE,
    source_title VARCHAR(500),
    source_domain VARCHAR(255),
    source_type source_type NOT NULL DEFAULT 'unknown',
    content TEXT NOT NULL,
    full_answer TEXT, -- Optional full Perplexity response
    metadata JSONB DEFAULT '{}'::jsonb,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    relevance_score DECIMAL(3,2), -- 0.00 to 1.00
    is_valid BOOLEAN NOT NULL DEFAULT true,
    tags JSONB DEFAULT '[]'::jsonb,
    confidence_score DECIMAL(3,2) DEFAULT 0.5, -- 0.00 to 1.00
    soft_deleted_at TIMESTAMP WITH TIME ZONE,
    -- Future: embedding vector(1536), -- For AI features
    
    -- Constraints
    CONSTRAINT relevance_score_range CHECK (relevance_score IS NULL OR (relevance_score >= 0.0 AND relevance_score <= 1.0)),
    CONSTRAINT confidence_score_range CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CONSTRAINT content_not_empty CHECK (LENGTH(TRIM(content)) > 0),
    CONSTRAINT source_url_not_empty CHECK (LENGTH(TRIM(source_url)) > 0)
);

-- Topic-Posts Junction Table (Many-to-Many)
CREATE TABLE topic_posts (
    topic_id UUID NOT NULL REFERENCES monitored_topics(id) ON DELETE CASCADE,
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (topic_id, post_id)
);

-- Collection Logs Table (Audit Trail)
CREATE TABLE collection_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic_id UUID REFERENCES monitored_topics(id) ON DELETE SET NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status collection_status NOT NULL,
    query_used TEXT NOT NULL,
    total_results INTEGER DEFAULT 0,
    new_posts INTEGER DEFAULT 0,
    duplicate_posts INTEGER DEFAULT 0,
    invalid_posts INTEGER DEFAULT 0,
    time_range_start TIMESTAMP WITH TIME ZONE,
    time_range_end TIMESTAMP WITH TIME ZONE,
    collection_strategy collection_strategy NOT NULL DEFAULT 'initial',
    error_message TEXT,
    error_traceback TEXT,
    api_calls_used INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Constraints
    CONSTRAINT total_results_non_negative CHECK (total_results >= 0),
    CONSTRAINT new_posts_non_negative CHECK (new_posts >= 0),
    CONSTRAINT duplicate_posts_non_negative CHECK (duplicate_posts >= 0),
    CONSTRAINT invalid_posts_non_negative CHECK (invalid_posts >= 0),
    CONSTRAINT api_calls_non_negative CHECK (api_calls_used >= 0),
    CONSTRAINT completion_after_start CHECK (completed_at IS NULL OR completed_at >= started_at)
);

-- Query Metrics Table (Performance Tracking)
CREATE TABLE query_metrics (
    topic_id UUID NOT NULL REFERENCES monitored_topics(id) ON DELETE CASCADE,
    execution_date DATE NOT NULL,
    results_count INTEGER DEFAULT 0,
    unique_sources_count INTEGER DEFAULT 0,
    avg_relevance DECIMAL(3,2),
    duplicate_rate DECIMAL(3,2) DEFAULT 0.0,
    error_rate DECIMAL(3,2) DEFAULT 0.0,
    
    PRIMARY KEY (topic_id, execution_date),
    
    -- Constraints
    CONSTRAINT results_count_non_negative CHECK (results_count >= 0),
    CONSTRAINT unique_sources_non_negative CHECK (unique_sources_count >= 0),
    CONSTRAINT avg_relevance_range CHECK (avg_relevance IS NULL OR (avg_relevance >= 0.0 AND avg_relevance <= 1.0)),
    CONSTRAINT duplicate_rate_range CHECK (duplicate_rate >= 0.0 AND duplicate_rate <= 1.0),
    CONSTRAINT error_rate_range CHECK (error_rate >= 0.0 AND error_rate <= 1.0)
);

-- Indexes for Performance

-- Posts Table Indexes
CREATE INDEX idx_posts_source_url ON posts(source_url);
CREATE INDEX idx_posts_collected_at_desc ON posts(collected_at DESC);
CREATE INDEX idx_posts_source_domain ON posts(source_domain);
CREATE INDEX idx_posts_query_timestamp_desc ON posts(query_timestamp DESC);
CREATE INDEX idx_posts_metadata_gin ON posts USING GIN(metadata);
CREATE INDEX idx_posts_soft_deleted_at ON posts(soft_deleted_at) WHERE soft_deleted_at IS NULL;
CREATE INDEX idx_posts_confidence_score_desc ON posts(confidence_score DESC);
CREATE INDEX idx_posts_source_type ON posts(source_type);
CREATE INDEX idx_posts_is_valid ON posts(is_valid);

-- Topics Table Indexes
CREATE INDEX idx_topics_active ON monitored_topics(active) WHERE active = true;
CREATE INDEX idx_topics_last_checked ON monitored_topics(last_checked);
CREATE INDEX idx_topics_collection_priority ON monitored_topics(collection_priority);
CREATE INDEX idx_topics_version ON monitored_topics(version);
CREATE INDEX idx_topics_category ON monitored_topics(category);

-- Collection Logs Indexes
CREATE INDEX idx_logs_status ON collection_logs(status);
CREATE INDEX idx_logs_started_at_desc ON collection_logs(started_at DESC);
CREATE INDEX idx_logs_topic_id ON collection_logs(topic_id);
CREATE INDEX idx_logs_collection_strategy ON collection_logs(collection_strategy);

-- Topic-Posts Junction Indexes
CREATE INDEX idx_topic_posts_topic_id ON topic_posts(topic_id);
CREATE INDEX idx_topic_posts_post_id ON topic_posts(post_id);
CREATE INDEX idx_topic_posts_assigned_at ON topic_posts(assigned_at);

-- Query Metrics Indexes
CREATE INDEX idx_metrics_execution_date ON query_metrics(execution_date);
CREATE INDEX idx_metrics_topic_id ON query_metrics(topic_id);

-- Triggers for Auto-Updated Timestamps

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for monitored_topics
CREATE TRIGGER update_topics_updated_at 
    BEFORE UPDATE ON monitored_topics 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to extract domain from URL
CREATE OR REPLACE FUNCTION extract_domain_from_url(url TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN regexp_replace(
        regexp_replace(url, '^https?://', '', 'gi'),
        '/.*$', '', 'g'
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to calculate content hash for deduplication
CREATE OR REPLACE FUNCTION calculate_content_hash(content TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN encode(digest(LOWER(TRIM(content)), 'sha256'), 'hex');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Views for Common Queries

-- Active Topics View
CREATE VIEW active_topics AS
SELECT 
    id, topic_name, search_query, description, category,
    check_frequency_hours, last_checked, collection_priority,
    total_posts_collected, avg_posts_per_query, created_at, updated_at
FROM monitored_topics 
WHERE active = true;

-- Recent Posts View
CREATE VIEW recent_posts AS
SELECT 
    p.id, p.search_query, p.query_timestamp, p.source_url, p.source_title,
    p.source_domain, p.source_type, p.content, p.collected_at,
    p.relevance_score, p.confidence_score, p.tags, p.metadata,
    array_agg(t.topic_name) as topic_names
FROM posts p
LEFT JOIN topic_posts tp ON p.id = tp.post_id
LEFT JOIN monitored_topics t ON tp.topic_id = t.id
WHERE p.soft_deleted_at IS NULL AND p.is_valid = true
GROUP BY p.id, p.search_query, p.query_timestamp, p.source_url, p.source_title,
         p.source_domain, p.source_type, p.content, p.collected_at,
         p.relevance_score, p.confidence_score, p.tags, p.metadata
ORDER BY p.collected_at DESC;

-- Collection Statistics View
CREATE VIEW collection_statistics AS
SELECT 
    t.id as topic_id,
    t.topic_name,
    t.collection_priority,
    COUNT(p.id) as total_posts,
    COUNT(CASE WHEN p.collected_at >= NOW() - INTERVAL '24 hours' THEN 1 END) as posts_last_24h,
    COUNT(CASE WHEN p.collected_at >= NOW() - INTERVAL '7 days' THEN 1 END) as posts_last_7d,
    AVG(p.confidence_score) as avg_confidence,
    COUNT(DISTINCT p.source_domain) as unique_sources,
    MAX(p.collected_at) as last_post_collected
FROM monitored_topics t
LEFT JOIN topic_posts tp ON t.id = tp.topic_id
LEFT JOIN posts p ON tp.post_id = p.id AND p.soft_deleted_at IS NULL
WHERE t.active = true
GROUP BY t.id, t.topic_name, t.collection_priority;

-- Comments and Documentation
COMMENT ON TABLE monitored_topics IS 'Configuration for topics to monitor and collect data for';
COMMENT ON TABLE posts IS 'All collected content from various sources';
COMMENT ON TABLE topic_posts IS 'Many-to-many relationship between topics and posts';
COMMENT ON TABLE collection_logs IS 'Audit trail of all collection attempts and results';
COMMENT ON TABLE query_metrics IS 'Performance metrics for collection queries';

COMMENT ON COLUMN monitored_topics.collection_priority IS 'Determines collection frequency: critical=6h, normal=24h, low=72h';
COMMENT ON COLUMN posts.confidence_score IS 'AI confidence in content quality (0.0-1.0)';
COMMENT ON COLUMN posts.soft_deleted_at IS 'Soft delete timestamp for data retention compliance';
COMMENT ON COLUMN collection_logs.collection_strategy IS 'Type of collection: initial, incremental, or gap_fill';
