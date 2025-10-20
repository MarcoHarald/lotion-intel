# Monitoring App - Development Brief

## Project Overview
Build a modular monitoring system that tracks emerging local/national issues by collecting curated content via Perplexity API searches. Store structured data in Supabase (PostgreSQL + pgvector) with a phased architecture: simple data collection now, AI-powered analysis later.

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

### Tables

**posts** - All collected content
- ID (primary key), search_query, query_timestamp
- source_url (unique), source_title, source_domain, source_type
- content (required), full_answer (optional)
- metadata (JSONB), collected_at, relevance_score, is_valid
- Future: embedding vector(1536)

**monitored_topics** - Tracking configuration
- ID, topic_name (unique), search_query, description, category
- active, check_frequency_hours, last_checked
- query_version, query_history (JSONB)
- Metrics: total_posts_collected, avg_posts_per_query
- created_at, updated_at (auto-trigger)

**topic_posts** - Many-to-many linking
- Composite PK: topic_id, post_id (cascade delete)
- assigned_at timestamp

**collection_logs** - Audit trail
- ID, topic_id (nullable)
- started_at, completed_at, status
- query_used, total_results, new_posts, duplicate_posts, invalid_posts
- error_message, error_traceback
- api_calls_used, metadata (JSONB)

**query_metrics** - Performance tracking
- Composite PK: topic_id, execution_date
- results_count, unique_sources_count, avg_relevance
- duplicate_rate, error_rate

### Indexes
Posts: source_url, collected_at DESC, source_domain, query_timestamp DESC, metadata GIN
Topics: active (partial), last_checked
Logs: status, started_at DESC

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

### Database
**client.py**: Supabase connection singleton
**Repositories**: Encapsulate CRUD operations
- PostRepository: create, exists_by_url, exists_by_content_hash, get_by_topic, get_recent
- TopicRepository: create, get_active, get_due_for_collection, update_last_checked, update_metrics
- LogRepository: create_log, get_by_topic, get_recent, get_errors

### Collectors
**base_collector.py**: Abstract class with should_collect, validate_post, log_collection_attempt, handle_rate_limit
**perplexity_collector.py**: Query API, process citations, transform to post format, handle errors
**Utils**:
- deduplication: URL existence check, content hash generation, session cache
- validation: URL format, content length, source quality, domain extraction
- classification: Determine source_type from domain patterns
- rate_limiter: Track calls per minute/day, enforce waits, exponential backoff

### Scheduler
**collection_scheduler.py**: Get due topics, run collectors, log results, continue on errors

### Dashboard (Streamlit)
- Overview: totals, charts, recent activity
- Posts: table with filters (date, source, topic)
- Topics: manage (add/edit/activate/deactivate)
- Logs: audit trail, errors, metrics

---

## Data Flow

1. Scheduler triggers hourly
2. Get active topics due for collection
3. For each topic:
   - Check rate limits, wait if needed
   - Query Perplexity API
   - For each citation: validate → check duplicate → classify → insert (if valid)
   - Update topic metrics and last_checked
   - Log results
4. Errors logged but don't stop processing

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

## Configuration (.env)
```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your_key
PERPLEXITY_API_KEY=your_key
MAX_QUERIES_PER_MINUTE=10
MAX_QUERIES_PER_DAY=1000
QUERY_DELAY_SECONDS=6.0
DEFAULT_CHECK_FREQUENCY_HOURS=24
MIN_CONTENT_LENGTH=50
LOG_LEVEL=INFO
```

**Constants**: Trusted domains list, source types (news/government/forum/blog/social_media/unknown), statuses (success/rate_limited/error)

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

## Development Sequence

1. **Foundation**: Project structure, requirements.txt, .env setup, git init
2. **Database**: Write schema.sql, setup script, test connection
3. **Configuration**: settings.py, logging_config.py, test loading
4. **Models**: Pydantic models with validation, test with valid/invalid data
5. **Database Client**: Singleton, error handling, test queries
6. **Repositories**: All CRUD methods, unit tests, test against Supabase
7. **Utilities**: Deduplication, validation, classification, rate limiter with tests
8. **Collectors**: BaseCollector, PerplexityCollector (stub API), error handling, test workflow
9. **Scheduler**: Orchestration logic, test without running, add logging
10. **Dashboard**: All Streamlit views, test interactions
11. **Scripts**: seed_topics.py, manual trigger script, documentation
12. **Integration**: End-to-end test, verify logs, test errors, fix bugs
13. **Documentation**: Setup instructions, troubleshooting guide

---

## Known Challenges & Mitigations

**Duplicate Content**: UNIQUE constraint on source_url, check before insert
**API Rate Limits**: Rate limiter from start, track usage, stagger queries
**Query Quality**: Track metrics, easy query updates, A/B testing
**Cost vs Freshness**: Per-topic frequency, start conservative
**Source Quality**: Validation before storage, trusted domains filter
**Missing Dates**: Store query_timestamp fallback, extract from URLs
**API Changes**: Store full response in metadata, graceful handling
**Storage Growth**: Monitor size, archive old data, upgrade plan when needed

---

## Phase 1 Deliverables

**Must Have**:
✅ Schema deployed, all repositories, deduplication, validation, rate limiter, collectors, scheduler, dashboard, logging, topic management, seed script

**Success Criteria**:
Manual trigger works, scheduler runs hourly, no duplicate URLs, rate limits respected, errors logged not crashed, dashboard shows real-time data, can add topics, audit trail visible

**Out of Scope**: Embeddings, semantic search, RAG, AI agents, advanced analytics, auth, multi-user

---

## Cost Estimates (Monthly)

**Phase 1**: Perplexity ~$0.30-$1.50 (300 queries), Supabase free tier = **~$0.30-$1.50/month**
**Phase 2**: Add OpenAI embeddings ~$1-3/month + Supabase Pro $25/month = **~$26-28/month**
**Phase 3+**: Add LLM costs $10-50/month

---

## Quick Start

1. Create Supabase project, get URL/key
2. Setup: `python -m venv venv`, activate, `pip install -r requirements.txt`
3. Create `.env` from `.env.example`, fill values
4. Run `python scripts/setup_database.py`
5. Run `python scripts/seed_topics.py`
6. Test: `streamlit run dashboard/app.py`
7. Collect: `python scheduler/collection_scheduler.py --once`

---

## Troubleshooting

**Connection failed**: Check .env credentials, Supabase not paused, internet
**Rate limit**: Normal, system waits/retries, increase QUERY_DELAY_SECONDS
**Duplicate error**: Working correctly, URL exists
**No posts**: Check topics active, last_checked timing, API results, logs
**Dashboard issues**: Check Streamlit installed, connection, terminal errors

**Debug**: Set `LOG_LEVEL=DEBUG` in .env for verbose output

---

## Completion Checklist

- [ ] Schema deployed and tested
- [ ] Topics manageable via dashboard  
- [ ] Manual collection works
- [ ] Scheduler runs automatically
- [ ] Deduplication prevents duplicates
- [ ] Rate limiting enforced
- [ ] Dashboard functional
- [ ] Logs provide audit trail
- [ ] Errors handled gracefully
- [ ] 3+ topics monitored for 1 week successfully
- [ ] Tests passing

**Begin implementation step-by-step. Test each component standalone before integration. Prioritize simplicity and reliability.**