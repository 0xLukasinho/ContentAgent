#!/usr/bin/env python3
"""
Memory Analytics Dashboard for ContentAgent.
Shows learning insights, patterns, and recommendations.
"""
import os
import sys
import json
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.memory_manager import MemoryManager

def display_analytics():
    """Display comprehensive memory analytics."""
    print("=" * 80)
    print("ContentAgent Memory Analytics Dashboard")
    print("=" * 80)
    
    memory_manager = MemoryManager()
    
    # Database overview
    db_info = memory_manager.get_database_info()
    print(f"\n[DATABASE] Overview:")
    print(f"   Total feedback records: {db_info.get('total_feedback_records', 0)}")
    print(f"   Content types tracked: {db_info.get('content_types_tracked', 0)}")
    print(f"   Database location: {db_info.get('database_path', 'Unknown')}")
    
    if db_info.get('total_feedback_records', 0) == 0:
        print("\n[INFO] No feedback data yet. Use ContentAgent to generate and review content to see analytics.")
        return
    
    # Generation statistics
    print(f"\n[STATS] Generation Statistics:")
    all_stats = memory_manager.get_generation_stats()
    if all_stats:
        for stat in all_stats:
            print(f"   {stat['content_type'].replace('_', ' ').title()}:")
            print(f"     • Generated: {stat['total_generated']}")
            print(f"     • Acceptance rate: {stat['acceptance_rate']:.1%}")
            print(f"     • Edited: {stat['total_edited']}")
            print(f"     • Rejected: {stat['total_rejected']}")
            print(f"     • Avg generation time: {stat['avg_generation_time']:.1f}s")
    else:
        print("   No statistics available yet.")
    
    # Content type analysis
    content_types = ['twitter_thread', 'article_summary', 'detailed_post']
    
    for content_type in content_types:
        stats = memory_manager.get_generation_stats(content_type)
        if not stats:
            continue
            
        print(f"\n[ANALYSIS] {content_type.replace('_', ' ').title()}:")
        
        # Quality analysis
        quality = memory_manager.get_quality_analysis(content_type)
        if quality:
            print(f"   Quality Metrics:")
            for action, metrics in quality.items():
                if metrics['sample_count'] > 0:
                    print(f"     {action.title()} content:")
                    print(f"       • Readability: {metrics['avg_readability']:.1f}")
                    print(f"       • Complexity: {metrics['avg_complexity']:.1f}")
                    print(f"       • Length: {metrics['avg_length']:.0f} words")
                    print(f"       • Samples: {metrics['sample_count']}")
        
        # Edit patterns
        patterns = memory_manager.get_edit_patterns(content_type)
        if patterns:
            print(f"   Edit Patterns:")
            for pattern in patterns[:3]:  # Top 3
                print(f"     • {pattern['edit_type']}: {pattern['description']} ({pattern['frequency']}x)")
        
        # User preferences
        preferences = memory_manager.get_user_preferences(content_type)
        if preferences:
            print(f"   Learned Preferences:")
            for pref_type, pref_data in preferences.items():
                if pref_data['confidence'] >= 0.5:
                    print(f"     • {pref_type}: {pref_data['value']} (confidence: {pref_data['confidence']:.0%})")
        
        # Learning insights
        insights = memory_manager.get_learning_insights(content_type)
        if insights.get('recommendations'):
            print(f"   [RECOMMENDATIONS]:")
            for rec in insights['recommendations'][:3]:  # Top 3
                print(f"     • {rec}")
        
        # Prompt enhancements preview
        enhancements = memory_manager.get_prompt_enhancements(content_type)
        if enhancements:
            print(f"   [ENHANCEMENTS] Prompt Enhancements Active:")
            enhancement_lines = enhancements.split('\n')
            for line in enhancement_lines[1:4]:  # Skip header, show first 3
                if line.strip().startswith('- '):
                    print(f"     • {line.strip()[2:]}")
    
    print(f"\n[UPDATED] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

def display_recent_feedback():
    """Display recent feedback for review."""
    print("\n[RECENT FEEDBACK] Last 10 items:")
    
    memory_manager = MemoryManager()
    recent = memory_manager.get_recent_feedback(limit=10)
    
    if not recent:
        print("   No feedback recorded yet.")
        return
    
    for feedback in recent:
        timestamp = datetime.fromisoformat(feedback['timestamp']).strftime('%m/%d %H:%M')
        content_preview = feedback['content_text'][:50] + "..." if len(feedback['content_text']) > 50 else feedback['content_text']
        print(f"   [{timestamp}] {feedback['content_type']} - {feedback['user_action']}")
        print(f"     \"{content_preview}\"")

def main():
    """Main analytics display."""
    try:
        display_analytics()
        display_recent_feedback()
        
        print(f"\n[TIP] The more you use ContentAgent and provide feedback,")
        print(f"   the smarter it becomes at matching your preferences!")
        
    except Exception as e:
        print(f"Error displaying analytics: {e}")
        print("Make sure you've run ContentAgent at least once to initialize the memory system.")

if __name__ == "__main__":
    main()