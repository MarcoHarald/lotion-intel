"""
Main application entry point.
Provides CLI interface for running the monitoring app.
"""
import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scheduler.collection_scheduler import CollectionScheduler
from config.logging_config import get_logger

logger = get_logger("main")


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description="Monitoring App - AI-powered content monitoring system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py dashboard          # Start the web dashboard
  python main.py collect --once     # Run collection once
  python main.py collect --continuous  # Run continuous collection
  python main.py setup              # Setup database and seed topics
  python main.py health             # Check system health
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Start the web dashboard')
    dashboard_parser.add_argument('--port', type=int, default=8501, help='Port for dashboard (default: 8501)')
    dashboard_parser.add_argument('--host', default='localhost', help='Host for dashboard (default: localhost)')
    
    # Collection command
    collect_parser = subparsers.add_parser('collect', help='Run data collection')
    collect_parser.add_argument('--once', action='store_true', help='Run collection once and exit')
    collect_parser.add_argument('--continuous', action='store_true', help='Run continuous collection')
    collect_parser.add_argument('--interval', type=int, default=60, help='Collection interval in minutes (default: 60)')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Setup the application')
    setup_parser.add_argument('--database-only', action='store_true', help='Setup database only')
    setup_parser.add_argument('--topics-only', action='store_true', help='Seed topics only')
    
    # Health command
    health_parser = subparsers.add_parser('health', help='Check system health')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Run tests')
    test_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == 'dashboard':
            return run_dashboard(args)
        elif args.command == 'collect':
            return run_collection(args)
        elif args.command == 'setup':
            return run_setup(args)
        elif args.command == 'health':
            return run_health_check()
        elif args.command == 'test':
            return run_tests(args)
        else:
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Application error: {e}")
        return 1


def run_dashboard(args):
    """Run the Streamlit dashboard."""
    import subprocess
    
    logger.info(f"Starting dashboard on {args.host}:{args.port}")
    
    cmd = [
        'streamlit', 'run', 'dashboard/app.py',
        '--server.port', str(args.port),
        '--server.address', args.host
    ]
    
    try:
        subprocess.run(cmd, check=True)
        return 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Dashboard failed to start: {e}")
        return 1
    except FileNotFoundError:
        logger.error("Streamlit not found. Please install it with: pip install streamlit")
        return 1


def run_collection(args):
    """Run data collection."""
    scheduler = CollectionScheduler()
    
    if args.once:
        logger.info("Running single collection cycle")
        results = scheduler.run_collection_cycle()
        
        print(f"Collection completed:")
        print(f"  Topics processed: {results['topics_processed']}")
        print(f"  Successful: {results['successful_collections']}")
        print(f"  Failed: {results['failed_collections']}")
        print(f"  Posts collected: {results['total_posts_collected']}")
        
        if results['errors']:
            print("Errors encountered:")
            for error in results['errors']:
                print(f"  - {error}")
        
        return 0 if results['failed_collections'] == 0 else 1
        
    elif args.continuous:
        logger.info(f"Starting continuous collection with {args.interval} minute intervals")
        scheduler.run_continuous(args.interval)
        return 0
    else:
        logger.error("Please specify --once or --continuous")
        return 1


def run_setup(args):
    """Run application setup."""
    import subprocess
    
    if args.database_only:
        logger.info("Setting up database only")
        result = subprocess.run([sys.executable, 'scripts/setup_database.py'], check=False)
        return result.returncode
    elif args.topics_only:
        logger.info("Seeding topics only")
        result = subprocess.run([sys.executable, 'scripts/seed_topics.py'], check=False)
        return result.returncode
    else:
        logger.info("Running full setup")
        
        # Setup database
        logger.info("Setting up database...")
        db_result = subprocess.run([sys.executable, 'scripts/setup_database.py'], check=False)
        if db_result.returncode != 0:
            logger.error("Database setup failed")
            return db_result.returncode
        
        # Seed topics
        logger.info("Seeding topics...")
        topics_result = subprocess.run([sys.executable, 'scripts/seed_topics.py'], check=False)
        if topics_result.returncode != 0:
            logger.error("Topic seeding failed")
            return topics_result.returncode
        
        logger.info("Setup completed successfully!")
        return 0


def run_health_check():
    """Run system health check."""
    scheduler = CollectionScheduler()
    health = scheduler.get_system_health()
    
    print("System Health Check")
    print("=" * 30)
    print(f"Database Connected: {'✅' if health['database_connected'] else '❌'}")
    print(f"API Connected: {'✅' if health['api_connected'] else '❌'}")
    print(f"Scheduler Running: {'✅' if health['scheduler_running'] else '❌'}")
    print(f"Active Topics: {health['active_topics_count']}")
    print(f"Due Topics: {health['due_topics_count']}")
    print(f"Recent Collections: {health['recent_collections']}")
    print(f"Recent Errors: {health['recent_errors']}")
    
    if 'error' in health:
        print(f"Error: {health['error']}")
        return 1
    
    return 0 if health['database_connected'] and health['api_connected'] else 1


def run_tests(args):
    """Run tests."""
    import subprocess
    
    cmd = [sys.executable, '-m', 'pytest', 'tests/']
    
    if args.verbose:
        cmd.append('-v')
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except FileNotFoundError:
        logger.error("pytest not found. Please install it with: pip install pytest")
        return 1


if __name__ == "__main__":
    sys.exit(main())
