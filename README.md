# Monitoring App - Quick Reference

## What is this?

A smart monitoring system that automatically tracks emerging local and national issues by collecting curated content from the web using AI-powered searches. Think of it as your personal news monitoring assistant that never sleeps.

## Key Features

- **Smart Collection**: Only collects new data, reducing API costs by 60-80%
- **No Duplicates**: Automatically prevents collecting the same content twice
- **Real-time Dashboard**: Beautiful web interface to view and manage your monitoring
- **Reliable**: Built with error handling and automatic retries
- **Cost-Effective**: Optimized to minimize API usage and costs

## Quick Start

### 1. Prerequisites
- Python 3.10+
- Supabase account (free)
- Perplexity API key

### 2. Setup (5 minutes)
```bash
# Clone and setup
git clone <your-repo>
cd monitoring-app
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys

# Deploy database
python scripts/setup_database.py

# Add sample topics
python scripts/seed_topics.py
```

### 3. Run
```bash
# Start dashboard
streamlit run dashboard/app.py

# Test collection (optional)
python scheduler/collection_scheduler.py --once
```

## How it Works

1. **You define topics** to monitor (e.g., "climate change news", "AI regulation")
2. **System collects data** automatically every few hours using smart queries
3. **Dashboard shows results** with filtering, search, and analytics
4. **Smart collection** only gets new data since last check (saves money!)

## Dashboard Features

- **Overview**: See total posts, recent activity, system health
- **Posts**: Browse collected content with filters by date, source, topic
- **Topics**: Add, edit, activate/deactivate monitoring topics
- **Logs**: View collection history and any errors
- **Analytics**: Track performance and costs

## Configuration

### Environment Variables (.env)
```bash
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
PERPLEXITY_API_KEY=your-perplexity-key

# Optional (defaults work fine)
MAX_QUERIES_PER_DAY=1000
DEFAULT_CHECK_FREQUENCY_HOURS=24
LOG_LEVEL=INFO
```

### Topic Priorities
- **Critical**: Check every 6 hours
- **Normal**: Check every 24 hours  
- **Low**: Check every 72 hours

## Cost Estimates

- **Free Tier**: ~$0.30-$1.50/month (300 queries)
- **Premium**: ~$26-28/month (unlimited queries + AI features)

## Troubleshooting

**Dashboard won't load?**
- Check if Streamlit is installed: `pip install streamlit`
- Verify .env file has correct API keys
- Check terminal for error messages

**No posts appearing?**
- Check if topics are active in dashboard
- Verify API keys are working
- Check logs for collection errors

**Rate limit errors?**
- Normal behavior - system waits and retries automatically
- Increase `QUERY_DELAY_SECONDS` in .env if needed

## File Structure

```
monitoring-app/
├── README.md          # Technical documentation
├── README2.md         # This quick reference
├── requirements.txt   # Python dependencies
├── .env.example       # Configuration template
├── config/            # Settings and logging
├── database/          # Schema and connection
├── models/            # Data validation
├── collectors/        # Data collection logic
├── storage/           # Database operations
├── scheduler/         # Automated collection
├── dashboard/         # Web interface
└── scripts/           # Setup and utilities
```

## Development

For detailed technical implementation, see `README.md` which contains:
- Complete database schema
- Architecture details
- Implementation roadmap
- Technical specifications

## Support

- **Issues**: Check logs in dashboard or terminal output
- **Debug**: Set `LOG_LEVEL=DEBUG` in .env for verbose output
- **Documentation**: See README.md for technical details

---

**Ready to start monitoring?** Follow the Quick Start steps above!
