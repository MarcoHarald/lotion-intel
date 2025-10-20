"""
Streamlit dashboard for monitoring app.
Provides web interface for viewing and managing the system.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid

# Import our modules
from storage.topic_repository import TopicRepository
from storage.post_repository import PostRepository
from storage.log_repository import CollectionLogRepository
from models.topic import TopicCreate, TopicUpdate
from models.post import PostUpdate
from scheduler.collection_scheduler import CollectionScheduler
from config.logging_config import get_logger

logger = get_logger("dashboard")

# Page configuration
st.set_page_config(
    page_title="Monitoring App Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize repositories
@st.cache_resource
def get_repositories():
    return {
        'topic_repo': TopicRepository(),
        'post_repo': PostRepository(),
        'log_repo': CollectionLogRepository()
    }

@st.cache_resource
def get_scheduler():
    return CollectionScheduler()

repos = get_repositories()
scheduler = get_scheduler()

# Sidebar navigation
st.sidebar.title("📊 Monitoring App")
page = st.sidebar.selectbox(
    "Navigate",
    ["Overview", "Posts", "Topics", "Collection Logs", "System Health"]
)

# Helper functions
def format_datetime(dt):
    """Format datetime for display."""
    if dt is None:
        return "Never"
    return dt.strftime("%Y-%m-%d %H:%M")

def get_time_ago(dt):
    """Get human-readable time ago."""
    if dt is None:
        return "Never"
    
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600} hours ago"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60} minutes ago"
    else:
        return "Just now"

# Overview Page
if page == "Overview":
    st.title("📊 System Overview")
    
    # Get statistics
    try:
        # Topic statistics
        active_topics = repos['topic_repo'].get_active()
        due_topics = repos['topic_repo'].get_due_for_collection()
        
        # Post statistics
        post_stats = repos['post_repo'].get_stats()
        
        # Collection logs
        recent_logs = repos['log_repo'].get_recent(limit=10)
        error_logs = repos['log_repo'].get_errors(limit=5)
        
        # Create metrics columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Active Topics", len(active_topics))
        
        with col2:
            st.metric("Due for Collection", len(due_topics))
        
        with col3:
            st.metric("Total Posts", post_stats['total_posts'])
        
        with col4:
            st.metric("Posts Today", post_stats['posts_today'])
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Posts by Priority")
            priority_counts = {}
            for topic in active_topics:
                priority = topic.collection_priority
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            if priority_counts:
                fig = px.pie(
                    values=list(priority_counts.values()),
                    names=list(priority_counts.keys()),
                    title="Topics by Priority"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Recent Activity")
            if recent_logs:
                # Create activity chart
                activity_data = []
                for log in recent_logs:
                    activity_data.append({
                        'Date': log.started_at.date(),
                        'Status': log.status,
                        'Posts': log.new_posts
                    })
                
                df = pd.DataFrame(activity_data)
                fig = px.bar(
                    df.groupby(['Date', 'Status']).size().reset_index(name='Count'),
                    x='Date',
                    y='Count',
                    color='Status',
                    title="Collection Activity"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No recent collection activity")
        
        # Recent posts
        st.subheader("Recent Posts")
        recent_posts = repos['post_repo'].get_recent(limit=10)
        
        if recent_posts:
            posts_data = []
            for post in recent_posts:
                posts_data.append({
                    'Title': post.source_title or 'No title',
                    'Domain': post.source_domain or 'Unknown',
                    'Confidence': f"{post.confidence_score:.2f}",
                    'Collected': get_time_ago(post.collected_at),
                    'Tags': ', '.join(post.tags[:3])  # Show first 3 tags
                })
            
            df = pd.DataFrame(posts_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No recent posts found")
        
        # System health
        st.subheader("System Health")
        health = scheduler.get_system_health()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Database",
                "✅ Connected" if health['database_connected'] else "❌ Disconnected"
            )
        
        with col2:
            st.metric(
                "API",
                "✅ Connected" if health['api_connected'] else "❌ Disconnected"
            )
        
        with col3:
            st.metric(
                "Scheduler",
                "✅ Running" if health['scheduler_running'] else "❌ Stopped"
            )
        
    except Exception as e:
        st.error(f"Error loading overview data: {e}")
        logger.error(f"Error in overview page: {e}")

# Posts Page
elif page == "Posts":
    st.title("📰 Posts Management")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        days_filter = st.selectbox("Time Range", [7, 30, 90, 365], index=0)
    
    with col2:
        confidence_filter = st.selectbox("Confidence Score", ["All", "High (0.8+)", "Medium (0.5-0.8)", "Low (<0.5)"])
    
    with col3:
        source_type_filter = st.selectbox("Source Type", ["All", "news", "government", "blog", "forum", "social_media", "unknown"])
    
    # Get posts based on filters
    try:
        recent_posts = repos['post_repo'].get_recent(limit=1000, days=days_filter)
        
        # Apply filters
        filtered_posts = recent_posts
        
        if confidence_filter != "All":
            if confidence_filter == "High (0.8+)":
                filtered_posts = [p for p in filtered_posts if p.confidence_score >= 0.8]
            elif confidence_filter == "Medium (0.5-0.8)":
                filtered_posts = [p for p in filtered_posts if 0.5 <= p.confidence_score < 0.8]
            elif confidence_filter == "Low (<0.5)":
                filtered_posts = [p for p in filtered_posts if p.confidence_score < 0.5]
        
        if source_type_filter != "All":
            filtered_posts = [p for p in filtered_posts if p.source_type == source_type_filter]
        
        st.write(f"Showing {len(filtered_posts)} posts")
        
        # Display posts
        for post in filtered_posts:
            with st.expander(f"{post.source_title or 'No title'} - {post.source_domain or 'Unknown domain'}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**URL:** {post.source_url}")
                    st.write(f"**Content:** {post.content[:500]}{'...' if len(post.content) > 500 else ''}")
                    st.write(f"**Tags:** {', '.join(post.tags)}")
                
                with col2:
                    st.metric("Confidence", f"{post.confidence_score:.2f}")
                    st.metric("Relevance", f"{post.relevance_score:.2f}" if post.relevance_score else "N/A")
                    st.write(f"**Collected:** {get_time_ago(post.collected_at)}")
                    
                    if st.button("Soft Delete", key=f"delete_{post.id}"):
                        repos['post_repo'].soft_delete(post.id)
                        st.success("Post soft deleted")
                        st.rerun()
    
    except Exception as e:
        st.error(f"Error loading posts: {e}")
        logger.error(f"Error in posts page: {e}")

# Topics Page
elif page == "Topics":
    st.title("🎯 Topics Management")
    
    # Add new topic
    with st.expander("Add New Topic"):
        with st.form("add_topic"):
            topic_name = st.text_input("Topic Name")
            search_query = st.text_input("Search Query")
            description = st.text_area("Description")
            category = st.text_input("Category")
            collection_priority = st.selectbox("Priority", ["critical", "normal", "low"])
            check_frequency_hours = st.number_input("Check Frequency (hours)", min_value=1, max_value=168, value=24)
            
            if st.form_submit_button("Add Topic"):
                if topic_name and search_query:
                    try:
                        topic_data = TopicCreate(
                            topic_name=topic_name,
                            search_query=search_query,
                            description=description,
                            category=category,
                            collection_priority=collection_priority,
                            check_frequency_hours=check_frequency_hours
                        )
                        
                        topic = repos['topic_repo'].create(topic_data)
                        st.success(f"Topic '{topic_name}' created successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating topic: {e}")
                else:
                    st.error("Topic name and search query are required")
    
    # Display existing topics
    try:
        active_topics = repos['topic_repo'].get_active()
        
        if active_topics:
            st.subheader("Active Topics")
            
            for topic in active_topics:
                with st.expander(f"{topic.topic_name} ({topic.collection_priority})"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Search Query:** {topic.search_query}")
                        st.write(f"**Description:** {topic.description or 'No description'}")
                        st.write(f"**Category:** {topic.category or 'No category'}")
                        st.write(f"**Last Checked:** {get_time_ago(topic.last_checked)}")
                        st.write(f"**Posts Collected:** {topic.total_posts_collected}")
                    
                    with col2:
                        st.metric("Frequency", f"{topic.check_frequency_hours}h")
                        st.metric("Avg Posts/Query", f"{topic.avg_posts_per_query:.1f}")
                        
                        # Action buttons
                        if st.button("Edit", key=f"edit_{topic.id}"):
                            st.session_state[f"editing_{topic.id}"] = True
                        
                        if st.button("Deactivate", key=f"deactivate_{topic.id}"):
                            repos['topic_repo'].update(topic.id, TopicUpdate(active=False))
                            st.success("Topic deactivated")
                            st.rerun()
                        
                        if st.button("Delete", key=f"delete_{topic.id}"):
                            repos['topic_repo'].delete(topic.id)
                            st.success("Topic deleted")
                            st.rerun()
                    
                    # Edit form
                    if st.session_state.get(f"editing_{topic.id}", False):
                        with st.form(f"edit_form_{topic.id}"):
                            new_name = st.text_input("Topic Name", value=topic.topic_name)
                            new_query = st.text_input("Search Query", value=topic.search_query)
                            new_description = st.text_area("Description", value=topic.description or "")
                            new_category = st.text_input("Category", value=topic.category or "")
                            new_priority = st.selectbox("Priority", ["critical", "normal", "low"], index=["critical", "normal", "low"].index(topic.collection_priority))
                            new_frequency = st.number_input("Check Frequency (hours)", min_value=1, max_value=168, value=topic.check_frequency_hours)
                            
                            if st.form_submit_button("Update Topic"):
                                try:
                                    update_data = TopicUpdate(
                                        topic_name=new_name,
                                        search_query=new_query,
                                        description=new_description,
                                        category=new_category,
                                        collection_priority=new_priority,
                                        check_frequency_hours=new_frequency
                                    )
                                    
                                    repos['topic_repo'].update(topic.id, update_data)
                                    st.success("Topic updated successfully!")
                                    st.session_state[f"editing_{topic.id}"] = False
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating topic: {e}")
        else:
            st.info("No active topics found")
    
    except Exception as e:
        st.error(f"Error loading topics: {e}")
        logger.error(f"Error in topics page: {e}")

# Collection Logs Page
elif page == "Collection Logs":
    st.title("📋 Collection Logs")
    
    # Filters
    col1, col2 = st.columns(2)
    
    with col1:
        log_limit = st.selectbox("Number of logs", [50, 100, 200, 500], index=1)
    
    with col2:
        status_filter = st.selectbox("Status Filter", ["All", "success", "error", "rate_limited"])
    
    try:
        # Get logs
        if status_filter == "All":
            logs = repos['log_repo'].get_recent(limit=log_limit)
        else:
            logs = repos['log_repo'].get_recent(limit=log_limit)
            logs = [log for log in logs if log.status == status_filter]
        
        if logs:
            # Create logs dataframe
            logs_data = []
            for log in logs:
                logs_data.append({
                    'Started': format_datetime(log.started_at),
                    'Completed': format_datetime(log.completed_at),
                    'Status': log.status,
                    'Strategy': log.collection_strategy,
                    'Query': log.query_used[:50] + "..." if len(log.query_used) > 50 else log.query_used,
                    'New Posts': log.new_posts,
                    'Duplicates': log.duplicate_posts,
                    'Invalid': log.invalid_posts,
                    'API Calls': log.api_calls_used,
                    'Error': log.error_message[:100] + "..." if log.error_message and len(log.error_message) > 100 else log.error_message
                })
            
            df = pd.DataFrame(logs_data)
            st.dataframe(df, use_container_width=True)
            
            # Summary statistics
            st.subheader("Summary Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Collections", len(logs))
            
            with col2:
                successful = len([log for log in logs if log.status == 'success'])
                st.metric("Successful", successful)
            
            with col3:
                failed = len([log for log in logs if log.status == 'error'])
                st.metric("Failed", failed)
            
            with col4:
                total_posts = sum(log.new_posts for log in logs)
                st.metric("Total Posts", total_posts)
        else:
            st.info("No collection logs found")
    
    except Exception as e:
        st.error(f"Error loading collection logs: {e}")
        logger.error(f"Error in collection logs page: {e}")

# System Health Page
elif page == "System Health":
    st.title("🏥 System Health")
    
    try:
        health = scheduler.get_system_health()
        
        # Overall status
        st.subheader("Overall Status")
        if health['database_connected'] and health['api_connected']:
            st.success("✅ System is healthy")
        else:
            st.error("❌ System has issues")
        
        # Detailed health information
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Connections")
            st.write(f"**Database:** {'✅ Connected' if health['database_connected'] else '❌ Disconnected'}")
            st.write(f"**API:** {'✅ Connected' if health['api_connected'] else '❌ Disconnected'}")
            st.write(f"**Scheduler:** {'✅ Running' if health['scheduler_running'] else '❌ Stopped'}")
        
        with col2:
            st.subheader("Statistics")
            st.write(f"**Active Topics:** {health['active_topics_count']}")
            st.write(f"**Due Topics:** {health['due_topics_count']}")
            st.write(f"**Recent Collections:** {health['recent_collections']}")
            st.write(f"**Recent Errors:** {health['recent_errors']}")
        
        # Manual collection trigger
        st.subheader("Manual Collection")
        if st.button("Run Collection Cycle"):
            with st.spinner("Running collection cycle..."):
                results = scheduler.run_collection_cycle()
                
                st.success(f"Collection completed!")
                st.write(f"**Topics Processed:** {results['topics_processed']}")
                st.write(f"**Successful:** {results['successful_collections']}")
                st.write(f"**Failed:** {results['failed_collections']}")
                st.write(f"**Posts Collected:** {results['total_posts_collected']}")
                
                if results['errors']:
                    st.error("Errors encountered:")
                    for error in results['errors']:
                        st.write(f"- {error}")
        
        # Error logs
        if health['recent_errors'] > 0:
            st.subheader("Recent Errors")
            error_logs = repos['log_repo'].get_errors(limit=10)
            
            for log in error_logs:
                with st.expander(f"Error at {format_datetime(log.started_at)}"):
                    st.write(f"**Query:** {log.query_used}")
                    st.write(f"**Error:** {log.error_message}")
                    if log.error_traceback:
                        st.code(log.error_traceback)
    
    except Exception as e:
        st.error(f"Error loading system health: {e}")
        logger.error(f"Error in system health page: {e}")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**Monitoring App Dashboard**")
st.sidebar.markdown("Built with Streamlit")
st.sidebar.markdown(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
