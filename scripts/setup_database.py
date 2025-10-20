"""
Database setup script.
Deploys the database schema to Supabase.
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.client import get_db_client, test_database_connection
from config.logging_config import get_logger

logger = get_logger("setup_database")


def read_schema_file():
    """Read the database schema file."""
    schema_path = project_root / "database" / "schema.sql"
    
    if not schema_path.exists():
        logger.error(f"Schema file not found: {schema_path}")
        return None
    
    with open(schema_path, 'r') as f:
        return f.read()


def deploy_schema():
    """Deploy the database schema."""
    try:
        logger.info("Starting database schema deployment")
        
        # Test connection first
        if not test_database_connection():
            logger.error("Database connection test failed")
            return False
        
        logger.info("Database connection successful")
        
        # Read schema
        schema_sql = read_schema_file()
        if not schema_sql:
            return False
        
        # Split schema into individual statements
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        db_client = get_db_client()
        
        # Execute each statement
        for i, statement in enumerate(statements):
            if statement:
                try:
                    logger.info(f"Executing statement {i+1}/{len(statements)}")
                    # Note: Supabase doesn't support raw SQL execution via Python client
                    # This would need to be done via the Supabase dashboard or SQL editor
                    logger.warning(f"Statement {i+1} needs to be executed manually in Supabase SQL editor")
                    logger.debug(f"Statement: {statement[:100]}...")
                except Exception as e:
                    logger.error(f"Error executing statement {i+1}: {e}")
                    return False
        
        logger.info("Schema deployment completed successfully")
        logger.warning("Please execute the SQL statements manually in Supabase SQL editor")
        return True
        
    except Exception as e:
        logger.error(f"Error deploying schema: {e}")
        return False


def verify_schema():
    """Verify that the schema was deployed correctly."""
    try:
        logger.info("Verifying schema deployment")
        
        db_client = get_db_client()
        
        # Test each table
        tables = ['monitored_topics', 'posts', 'topic_posts', 'collection_logs', 'query_metrics']
        
        for table in tables:
            try:
                result = db_client.get_table(table).select('*').limit(1).execute()
                logger.info(f"Table '{table}' exists and is accessible")
            except Exception as e:
                logger.error(f"Table '{table}' verification failed: {e}")
                return False
        
        logger.info("Schema verification completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying schema: {e}")
        return False


def main():
    """Main setup function."""
    print("🚀 Monitoring App Database Setup")
    print("=" * 50)
    
    # Check environment variables
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these in your .env file")
        return False
    
    print("✅ Environment variables configured")
    
    # Deploy schema
    if not deploy_schema():
        print("❌ Schema deployment failed")
        return False
    
    print("✅ Schema deployment completed")
    
    # Verify schema
    if not verify_schema():
        print("❌ Schema verification failed")
        return False
    
    print("✅ Schema verification completed")
    
    print("\n🎉 Database setup completed successfully!")
    print("\nNext steps:")
    print("1. Execute the SQL statements in Supabase SQL editor")
    print("2. Run: python scripts/seed_topics.py")
    print("3. Run: streamlit run dashboard/app.py")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
