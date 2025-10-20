"""
Seed topics script.
Adds sample topics to the database for testing.
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from storage.topic_repository import TopicRepository
from models.topic import TopicCreate
from config.logging_config import get_logger

logger = get_logger("seed_topics")


def create_sample_topics():
    """Create sample topics for testing."""
    sample_topics = [
        {
            "topic_name": "Climate Change News",
            "search_query": "climate change news latest developments",
            "description": "Monitor latest climate change news and developments",
            "category": "Environment",
            "collection_priority": "critical",
            "check_frequency_hours": 6
        },
        {
            "topic_name": "AI Regulation",
            "search_query": "artificial intelligence regulation policy",
            "description": "Track AI regulation and policy developments",
            "category": "Technology",
            "collection_priority": "normal",
            "check_frequency_hours": 24
        },
        {
            "topic_name": "Cybersecurity Threats",
            "search_query": "cybersecurity threats vulnerabilities",
            "description": "Monitor cybersecurity threats and vulnerabilities",
            "category": "Security",
            "collection_priority": "critical",
            "check_frequency_hours": 6
        },
        {
            "topic_name": "Economic Indicators",
            "search_query": "economic indicators inflation unemployment",
            "description": "Track key economic indicators and trends",
            "category": "Economy",
            "collection_priority": "normal",
            "check_frequency_hours": 24
        },
        {
            "topic_name": "Health Research",
            "search_query": "medical research health studies",
            "description": "Monitor latest health and medical research",
            "category": "Health",
            "collection_priority": "low",
            "check_frequency_hours": 72
        },
        {
            "topic_name": "Renewable Energy",
            "search_query": "renewable energy solar wind power",
            "description": "Track renewable energy developments and innovations",
            "category": "Energy",
            "collection_priority": "normal",
            "check_frequency_hours": 24
        },
        {
            "topic_name": "Space Exploration",
            "search_query": "space exploration NASA SpaceX missions",
            "description": "Monitor space exploration news and missions",
            "category": "Science",
            "collection_priority": "low",
            "check_frequency_hours": 72
        },
        {
            "topic_name": "Digital Privacy",
            "search_query": "digital privacy data protection regulations",
            "description": "Track digital privacy and data protection developments",
            "category": "Privacy",
            "collection_priority": "normal",
            "check_frequency_hours": 24
        }
    ]
    
    topic_repo = TopicRepository()
    created_count = 0
    
    for topic_data in sample_topics:
        try:
            # Check if topic already exists
            existing_topics = topic_repo.get_active()
            if any(topic.topic_name == topic_data["topic_name"] for topic in existing_topics):
                logger.info(f"Topic '{topic_data['topic_name']}' already exists, skipping")
                continue
            
            # Create topic
            topic_create = TopicCreate(**topic_data)
            topic = topic_repo.create(topic_create)
            
            logger.info(f"Created topic: {topic.topic_name}")
            created_count += 1
            
        except Exception as e:
            logger.error(f"Error creating topic '{topic_data['topic_name']}': {e}")
    
    return created_count


def main():
    """Main seed function."""
    print("🌱 Seeding Sample Topics")
    print("=" * 30)
    
    try:
        created_count = create_sample_topics()
        
        if created_count > 0:
            print(f"✅ Created {created_count} sample topics")
        else:
            print("ℹ️  No new topics created (all already exist)")
        
        print("\nSample topics created:")
        print("- Climate Change News (Critical)")
        print("- AI Regulation (Normal)")
        print("- Cybersecurity Threats (Critical)")
        print("- Economic Indicators (Normal)")
        print("- Health Research (Low)")
        print("- Renewable Energy (Normal)")
        print("- Space Exploration (Low)")
        print("- Digital Privacy (Normal)")
        
        print("\n🎉 Topic seeding completed!")
        print("\nNext steps:")
        print("1. Run: streamlit run dashboard/app.py")
        print("2. Go to Topics page to manage topics")
        print("3. Run: python scheduler/collection_scheduler.py --once")
        
        return True
        
    except Exception as e:
        logger.error(f"Error seeding topics: {e}")
        print(f"❌ Error seeding topics: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
