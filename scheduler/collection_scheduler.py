"""
Priority-based collection scheduler.
Orchestrates data collection across all topics.
"""
import time
import argparse
from typing import List, Dict, Any
from datetime import datetime
from collectors.perplexity_collector import PerplexityCollector
from storage.topic_repository import TopicRepository
from storage.log_repository import CollectionLogRepository
from config.settings import settings, COLLECTION_PRIORITIES
from config.logging_config import get_logger

logger = get_logger("scheduler")


class CollectionScheduler:
    """Priority-based collection scheduler."""
    
    def __init__(self):
        self.topic_repo = TopicRepository()
        self.log_repo = CollectionLogRepository()
        self.collector = PerplexityCollector()
        self.running = False
    
    def get_topics_by_priority(self) -> Dict[str, List]:
        """Get topics grouped by priority."""
        topics_by_priority = {}
        
        for priority in COLLECTION_PRIORITIES:
            topics = self.topic_repo.get_by_priority(priority)
            topics_by_priority[priority] = topics
        
        return topics_by_priority
    
    def get_due_topics(self) -> List:
        """Get all topics due for collection."""
        return self.topic_repo.get_due_for_collection()
    
    def run_collection_cycle(self) -> Dict[str, Any]:
        """Run a single collection cycle."""
        logger.info("Starting collection cycle")
        
        start_time = datetime.utcnow()
        results = {
            'start_time': start_time,
            'topics_processed': 0,
            'successful_collections': 0,
            'failed_collections': 0,
            'total_posts_collected': 0,
            'errors': []
        }
        
        try:
            # Get topics due for collection
            due_topics = self.get_due_topics()
            
            if not due_topics:
                logger.info("No topics due for collection")
                return results
            
            # Sort by priority (critical first, then normal, then low)
            priority_order = {'critical': 0, 'normal': 1, 'low': 2}
            due_topics.sort(key=lambda t: priority_order.get(t.collection_priority, 1))
            
            logger.info(f"Found {len(due_topics)} topics due for collection")
            
            # Process each topic
            for topic in due_topics:
                try:
                    logger.info(f"Processing topic: {topic.topic_name} (priority: {topic.collection_priority})")
                    
                    # Collect data for topic
                    collection_result = self.collector.collect_for_topic(topic)
                    
                    results['topics_processed'] += 1
                    
                    if collection_result['success']:
                        results['successful_collections'] += 1
                        results['total_posts_collected'] += collection_result.get('posts_collected', 0)
                        logger.info(f"Successfully collected {collection_result.get('posts_collected', 0)} posts for {topic.topic_name}")
                    else:
                        results['failed_collections'] += 1
                        error_msg = collection_result.get('error', 'Unknown error')
                        results['errors'].append(f"{topic.topic_name}: {error_msg}")
                        logger.error(f"Failed to collect data for {topic.topic_name}: {error_msg}")
                    
                    # Small delay between topics to be respectful
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Unexpected error processing topic {topic.topic_name}: {e}")
                    results['failed_collections'] += 1
                    results['errors'].append(f"{topic.topic_name}: {str(e)}")
                    continue
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            results['end_time'] = end_time
            results['duration_seconds'] = duration
            
            logger.info(f"Collection cycle completed in {duration:.1f} seconds")
            logger.info(f"Results: {results['successful_collections']} successful, {results['failed_collections']} failed")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in collection cycle: {e}")
            results['errors'].append(f"Collection cycle error: {str(e)}")
            return results
    
    def run_continuous(self, interval_minutes: int = 60) -> None:
        """Run continuous collection with specified interval."""
        logger.info(f"Starting continuous collection with {interval_minutes} minute intervals")
        
        self.running = True
        
        try:
            while self.running:
                # Run collection cycle
                results = self.run_collection_cycle()
                
                # Log summary
                logger.info(f"Cycle completed: {results['successful_collections']} successful, {results['failed_collections']} failed")
                
                # Wait for next cycle
                logger.info(f"Waiting {interval_minutes} minutes until next collection cycle")
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            logger.info("Collection scheduler stopped by user")
        except Exception as e:
            logger.error(f"Error in continuous collection: {e}")
        finally:
            self.running = False
    
    def stop(self) -> None:
        """Stop the scheduler."""
        self.running = False
        logger.info("Collection scheduler stop requested")
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health status."""
        try:
            # Check database connection
            db_health = self.topic_repo.db_client.test_connection()
            
            # Check API connection
            api_health = self.collector.test_api_connection()
            
            # Get topic counts
            active_topics = self.topic_repo.get_active()
            due_topics = self.get_due_topics()
            
            # Get recent collection logs
            recent_logs = self.log_repo.get_recent(limit=10)
            error_logs = self.log_repo.get_errors(limit=5)
            
            return {
                'database_connected': db_health,
                'api_connected': api_health,
                'active_topics_count': len(active_topics),
                'due_topics_count': len(due_topics),
                'recent_collections': len(recent_logs),
                'recent_errors': len(error_logs),
                'scheduler_running': self.running,
                'last_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {
                'database_connected': False,
                'api_connected': False,
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }


def main():
    """Main entry point for scheduler."""
    parser = argparse.ArgumentParser(description='Collection Scheduler')
    parser.add_argument('--once', action='store_true', help='Run collection once and exit')
    parser.add_argument('--interval', type=int, default=60, help='Collection interval in minutes (default: 60)')
    parser.add_argument('--health', action='store_true', help='Check system health and exit')
    
    args = parser.parse_args()
    
    scheduler = CollectionScheduler()
    
    if args.health:
        health = scheduler.get_system_health()
        print("System Health:")
        for key, value in health.items():
            print(f"  {key}: {value}")
        return
    
    if args.once:
        logger.info("Running single collection cycle")
        results = scheduler.run_collection_cycle()
        print(f"Collection completed: {results['successful_collections']} successful, {results['failed_collections']} failed")
    else:
        scheduler.run_continuous(args.interval)


if __name__ == "__main__":
    main()
