# Monitoring App - Implementation Guide

## Project Overview
Build a modular monitoring system that tracks emerging local/national issues by collecting curated content via Perplexity API searches. Store structured data in Supabase (PostgreSQL + pgvector) with a phased architecture: simple data collection now, AI-powered analysis later.

## Implementation Roadmap

### Phase 1: Core System (4 Weeks)

**Week 1: Foundation & Database**
- [ ] Project structure, requirements.txt, .env setup
- [ ] Database schema deployment with all constraints
- [ ] Configuration system (settings.py, logging_config.py)
- [ ] Pydantic models with validation
- [ ] Database client singleton

**Week 2: Core Components**
- [ ] Repository CRUD operations
- [ ] Deduplication, validation, classification utilities
- [ ] Rate limiter with exponential backoff
- [ ] BaseCollector and PerplexityCollector
- [ ] Smart collection time range logic

**Week 3: Orchestration & Monitoring**
- [ ] Priority-based scheduler
- [ ] Comprehensive logging and audit trail
- [ ] Health check endpoints
- [ ] Error handling with circuit breaker
- [ ] Collection metrics and performance tracking

**Week 4: Dashboard & Testing**
- [ ] Streamlit dashboard with all views
- [ ] Manual collection testing
- [ ] End-to-end integration testing
- [ ] Documentation and troubleshooting guide
- [ ] Performance benchmarks

### Key Success Metrics
- **Deduplication**: Zero duplicate posts in database
- **Error Handling**: Graceful failure recovery
- **Monitoring**: Complete audit trail

---

## Core Design Principles

- **Simple first, complex later** - Minimum viable functionality before optimization
- **Defensive programming** - Validate everything, assume failures will happen
- **Modular components** - Each piece independent and replaceable
- **Database-first** - PostgreSQL as single source of truth
- **Observable by default** - Logging and metrics from day one
- **Cost-conscious** - Rate limiting, caching, deduplication built-in

---

## Technical Stack

**Core**: Supabase (PostgreSQL + pgvector), Python 3.10+, Perplexity API

**Dependencies**: `supabase-py`, `python-dotenv`, `pydantic`, `requests`, `loguru`, `schedule`/`apscheduler`, `streamlit`, `tenacity`

**Future (Phase 2+)**: `openai`, `langchain`/`llamaindex`, `sentence-transformers`

---

## Database Schema

### Core Tables

**posts** - All collected content
- **ID** (primary key), **search_query**, **query_timestamp**
- **source_url** (unique), **source_title**, **source_domain**, **source_type**
- **content** (required), **full_answer** (optional)
- **metadata** (JSONB), **collected_at**, **relevance_score**, **is_valid**
- **tags** (JSONB array), **confidence_score** (0.0-1.0), **soft_deleted_at** (nullable)
- **Future**: embedding vector(1536)

**monitored_topics** - Tracking configuration
- **ID**, **topic_name** (unique), **search_query**, **description**, **category**
- **active**, **check_frequency_hours**, **last_checked**
- **query_version**, **query_history** (JSONB)
- **collection_priority** (critical/normal/low), **version** (integer)
- **created_by** (nullable) - for future user attribution
- **Metrics**: total_posts_collected, avg_posts_per_query
- **created_at**, **updated_at** (auto-trigger)

**topic_posts** - Many-to-many linking
- **Composite PK**: topic_id, post_id (cascade delete)
- **assigned_at** timestamp

**collection_logs** - Audit trail
- **ID**, **topic_id** (nullable)
- **started_at**, **completed_at**, **status**
- **query_used**, **total_results**, **new_posts**, **duplicate_posts**, **invalid_posts**
- **time_range_start**, **time_range_end** (nullable) - for smart collection
- **collection_strategy** (initial/incremental/gap_fill) - collection type
- **error_message**, **error_traceback**
- **api_calls_used**, **metadata** (JSONB)

**query_metrics** - Performance tracking
- **Composite PK**: topic_id, execution_date
- **results_count**, **unique_sources_count**, **avg_relevance**
- **duplicate_rate**, **error_rate**

### Database Constraints & Indexes

**Constraints**:
- CHECK constraints: confidence_score (0.0-1.0), collection_priority enum
- NOT NULL: content, source_url, topic_name
- UNIQUE: source_url, topic_name
- Foreign keys: topic_posts → topics/posts (cascade delete)

**Indexes**:
- **Posts**: source_url, collected_at DESC, source_domain, query_timestamp DESC, metadata GIN, soft_deleted_at (partial), confidence_score DESC
- **Topics**: active (partial), last_checked, collection_priority, version
- **Logs**: status, started_at DESC

---

## Project Structure
```
monitoring-app/
├── README.md, requirements.txt, .env.example, .gitignore
├── config/
│   ├── settings.py                   # Pydantic settings from env vars
│   └── logging_config.py             # Loguru configuration
├── database/
│   ├── schema.sql                    # Table definitions
│   └── client.py                     # Supabase singleton
├── models/
│   ├── post.py, topic.py, collection_log.py    # Pydantic validation
├── collectors/
│   ├── base_collector.py             # Abstract base with common logic
│   ├── perplexity_collector.py       # Main collector
│   └── utils/
│       ├── deduplication.py, validation.py, classification.py, rate_limiter.py
├── storage/
│   ├── post_repository.py, topic_repository.py, log_repository.py
├── scheduler/
│   └── collection_scheduler.py       # Orchestration
├── dashboard/
│   └── app.py                        # Streamlit UI
├── scripts/
│   ├── setup_database.py, seed_topics.py, backfill_embeddings.py
└── tests/
    ├── test_collectors.py, test_validation.py, test_deduplication.py
```

---

## Component Responsibilities

### Configuration
**settings.py**: Load env vars (Supabase credentials, API keys, rate limits, collection defaults, trusted domains, logging config)
**logging_config.py**: Daily rotation, 30-day retention, structured format

### Models
Pydantic models for type validation: Post, Topic, CollectionLog - validate before database operations
- Ensures data integrity with proper field types and constraints
- Validates JSONB fields (tags, metadata), numeric ranges (confidence_score), enums (priority, source_type)

### Database
**client.py**: Supabase connection singleton
**Repositories**: Encapsulate CRUD operations
- PostRepository: create, exists_by_url, exists_by_content_hash, get_by_topic, get_recent, soft_delete, get_by_confidence_score
- TopicRepository: create, get_active, get_due_for_collection, update_last_checked, update_metrics, get_by_priority
- LogRepository: create_log, get_by_topic, get_recent, get_errors
- Soft delete implementation: Set soft_deleted_at timestamp instead of hard deletion for data retention compliance

### Collectors
**base_collector.py**: Abstract class with should_collect, validate_post, log_collection_attempt, handle_rate_limit
**perplexity_collector.py**: Query API, process citations, transform to post format, handle errors
**Utils**:
- deduplication: URL existence check, content hash generation, session cache
- validation: URL format, content length, source quality, domain extraction, confidence scoring
- classification: Determine source_type from domain patterns, assign tags based on content
- rate_limiter: Track calls per minute/day, enforce waits, exponential backoff

### Scheduler
**collection_scheduler.py**: Get due topics by priority, run collectors, log results, continue on errors
- Priority-based collection: critical topics first, then normal, then low priority
- Version tracking for query evolution monitoring
- Smart collection logic: avoid redundant API calls, use time bounds for incremental collection

### Dashboard (Streamlit)
- Overview: totals, charts, recent activity, system health status
- Posts: table with filters (date, source, topic, tags, confidence_score), soft delete management
- Topics: manage (add/edit/activate/deactivate), priority settings, version tracking
- Logs: audit trail, errors, metrics, collection performance by priority

---

## Data Flow

1. Scheduler triggers hourly, processes topics by priority (critical → normal → low)
2. Get active topics due for collection, ordered by collection_priority
3. For each topic:
   - Check rate limits, wait if needed
   - Determine collection strategy (initial/incremental/gap_fill)
   - Build time-bounded query based on last successful collection
   - Query Perplexity API with time constraints
   - For each citation: validate → check duplicate → classify → assign tags → calculate confidence_score → insert (if valid)
   - Update topic metrics, last_checked, and version if query changed
   - Log results with priority context and collection strategy
4. Errors logged but don't stop processing
5. Soft delete old posts based on retention policy

---

## Error Handling

**Principles**: Never crash, log everything, fail gracefully, retry transient failures

**Scenarios**:
- Rate limit: log warning, wait, retry
- Timeout: retry 3x with exponential backoff
- Invalid response: log, skip, continue
- Database error: log with traceback, skip, continue
- Validation failure: log reason, don't insert

**Use `tenacity` for retries**: max 3 attempts, exponential backoff 4s→8s→16s

---

## Configuration

### Environment Variables (.env)

**Required Settings**:
```
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# Perplexity API
PERPLEXITY_API_KEY=your-perplexity-key

# Rate Limiting
MAX_QUERIES_PER_MINUTE=10
MAX_QUERIES_PER_DAY=1000
QUERY_DELAY_SECONDS=6.0

# Collection Settings
DEFAULT_CHECK_FREQUENCY_HOURS=24
MIN_CONTENT_LENGTH=50

# Logging
LOG_LEVEL=INFO
```

**Smart Collection Settings**:
```
# Time-based collection
INITIAL_COLLECTION_DAYS=7
INCREMENTAL_COLLECTION_HOURS=24
MAX_COLLECTION_GAP_HOURS=48
ENABLE_TIME_BOUNDED_QUERIES=true

# Data Quality
ENABLE_DUPLICATE_PREVENTION=true
HIGH_CONFIDENCE_THRESHOLD=0.8
MEDIUM_CONFIDENCE_THRESHOLD=0.5
LOW_CONFIDENCE_THRESHOLD=0.2

# Retention Policies
CRITICAL_RETENTION_DAYS=365
STANDARD_RETENTION_DAYS=180
ARCHIVE_RETENTION_DAYS=90

# Priority Frequencies
CRITICAL_PRIORITY_FREQUENCY_HOURS=6
NORMAL_PRIORITY_FREQUENCY_HOURS=24
LOW_PRIORITY_FREQUENCY_HOURS=72

# Health Monitoring
HEALTH_CHECK_TIMEOUT_SECONDS=30
HEALTH_CHECK_RETRY_ATTEMPTS=3
```

### Configuration Constants

**Source Types**: `news`, `government`, `forum`, `blog`, `social_media`, `unknown`
**Collection Priorities**: `critical`, `normal`, `low`
**Collection Strategies**: `initial`, `incremental`, `gap_fill`
**Status Values**: `success`, `rate_limited`, `error`
**Trusted Domains**: List of high-quality domains for source validation

---

## Testing Strategy

**Unit tests**: Deduplication logic, validation rules, rate limiter timing, Pydantic models
**Integration tests**: Database CRUD, full collection workflow with mock API, error handling
**Approach**: pytest, mock externals, fixtures for test data, focus on critical paths

---

## Logging Requirements

**INFO**: Collection started/completed, API calls, database ops, scheduler activities
**WARNING**: Duplicates, invalid sources, rate limit approaching, slow responses
**ERROR**: API errors, database errors, validation failures, unexpected exceptions

**Format**: Timestamp | Level | module:function:line | message | context (JSON-like)
**Storage**: Daily rotation, 30-day retention, logs/ directory (gitignored)

---

## Known Challenges & Mitigations

**Duplicate Content**: UNIQUE constraint on source_url, check before insert
**API Rate Limits**: Rate limiter from start, track usage, stagger queries
**Query Quality**: Track metrics, easy query updates, A/B testing
**Cost vs Freshness**: Per-topic frequency, start conservative
**Source Quality**: Validation before storage, trusted domains filter
**Missing Dates**: Store query_timestamp fallback, extract from URLs
**API Changes**: Store full response in metadata, graceful handling
**Storage Growth**: Monitor size, soft delete old data based on retention policy, upgrade plan when needed
**Data Quality**: Confidence scoring helps identify reliable sources, tags enable better categorization
**Query Evolution**: Version tracking allows monitoring query effectiveness over time
**Smart Collection**: Time-bounded queries reduce API costs by 60-80%, avoid duplicate content collection

## Critical Implementation Considerations

**Database Implementation**: 
- All constraints and indexes defined in Database Schema section above
- Use schema.sql for deployment with all constraints

**Multi-User Preparation (Minimal Changes)**:
- Add `created_by` field to topics table (nullable, default NULL)
- Implement query normalization function (lowercase, trim, standardize)
- Keep posts table user-agnostic (no user-specific fields)
- Use consistent naming conventions for future RLS policies

**API Response Handling**:
- Perplexity API may return different response formats - validate structure
- Handle empty citations gracefully
- Store raw API response in metadata for debugging

**Concurrency Issues**:
- Multiple scheduler instances could cause duplicate collections
- Add distributed locking or single-instance enforcement
- Consider using Supabase RLS (Row Level Security) for multi-user scenarios

**Data Validation Edge Cases**:
- Handle very long URLs (database limits)
- Validate JSONB fields don't exceed size limits
- Handle special characters in content (encoding issues)
- Validate confidence_score calculation doesn't fail on edge cases

**Performance Considerations**:
- Large JSONB fields can slow queries - consider separate metadata table
- Index on soft_deleted_at needs to be partial (WHERE soft_deleted_at IS NULL)
- Consider partitioning posts table by collected_at for large datasets
- Smart collection reduces database load by avoiding duplicate data processing

**Error Recovery**:
- Failed collections should not block subsequent topics
- Implement circuit breaker pattern for repeated API failures
- Add manual retry mechanism for failed collections
- Consider dead letter queue for persistent failures

---

## Cost Estimates (Monthly)

**Phase 1**: Perplexity ~$0.30-$1.50 (300 queries), Supabase free tier = **~$0.30-$1.50/month**
**Phase 2**: Add OpenAI embeddings ~$1-3/month + Supabase Pro $25/month = **~$26-28/month**
**Phase 3+**: Add LLM costs $10-50/month

---

## Troubleshooting

**Connection failed**: Check .env credentials, Supabase not paused, internet
**Rate limit**: Normal, system waits/retries, increase QUERY_DELAY_SECONDS
**Duplicate error**: Working correctly, URL exists
**No posts**: Check topics active, last_checked timing, API results, logs
**Dashboard issues**: Check Streamlit installed, connection, terminal errors

**Debug**: Set `LOG_LEVEL=DEBUG` in .env for verbose output

---

## Smart Collection System

### Current Collection Logic (Basic)

**Existing System**:
- Scheduler runs hourly
- Checks `last_checked` vs `check_frequency_hours`
- If due: collect all data for topic
- No time bounds or incremental collection

**Problems**:
- Collects same data repeatedly
- No time-based filtering
- Wastes API calls on duplicate content
- No incremental updates

### Smart Collection System

**Core Concept**: Only collect new data since last successful collection

### Collection Strategies

**1. Initial Collection**:
- Collect last 7 days of data
- Use broad time range
- Establish baseline

**2. Incremental Collection**:
- Collect only since last successful collection
- Use narrow time range
- Focus on new content

**3. Gap Filling**:
- Detect gaps in collection history
- Fill missing time periods
- Ensure data continuity

### Smart Collection Algorithm

**1. Determine Collection Strategy**:
- Check if topic is due for collection
- Check if we have recent successful collection
- Return collection decision with strategy

**2. Get Collection Time Range**:
- First collection: get last 7 days
- Incremental collection: get since last collection
- Gap filling: detect and fill missing periods

**3. Build Time-Bounded Query**:
- Add time constraints to Perplexity query
- Format: "climate change news" → "climate change news since 2024-01-15"
- Use "since [date]" or "latest news" modifiers

### Benefits

**Cost Reduction**:
- 60-80% fewer API calls through incremental collection
- Avoid collecting duplicate content
- Smart time bounds prevent redundant queries

**Data Quality**:
- No duplicate posts in database
- Complete time coverage
- Gap detection and filling

**Performance**:
- Faster collection sessions
- Reduced database load
- Better resource utilization

---

## Future Phases (Post-MVP)

### Phase 2: Multi-User Support
- **Goal**: Add Google OAuth and user data isolation
- **Changes**: Add users table, user_topics junction, RLS policies
- **Benefit**: Enable multiple users with shared data optimization

### Phase 3: AI Enhancement  
- **Goal**: Add embeddings, semantic search, RAG capabilities
- **Changes**: OpenAI integration, vector storage, AI analysis
- **Benefit**: Advanced content analysis and insights

### Phase 4: Advanced Features
- **Goal**: Add LLM agents, advanced analytics, enterprise features
- **Changes**: Custom AI workflows, white-label options
- **Benefit**: Enterprise-ready monitoring platform

### Multi-User Preparation (Minimal Changes)

**For Future Compatibility**:
1. **Database Schema**: Add `created_by` field to topics table
2. **Query Normalization**: Implement query standardization function  
3. **User-Agnostic Design**: Keep posts table global, no user-specific fields

**Focus**: Complete Phase 1 core features first, multi-user later!