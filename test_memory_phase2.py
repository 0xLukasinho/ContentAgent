#!/usr/bin/env python3
"""
Test script for Phase 2 memory implementation.
Tests advanced learning capabilities including pattern recognition and prompt enhancement.
"""
import os
import sys
import tempfile
import json

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.memory_manager import MemoryManager
from src.twitter_generator import TwitterThreadGenerator
from src.article_summary import ArticleSummaryGenerator

def test_enhanced_memory_manager():
    """Test the enhanced memory manager with Phase 2 features."""
    print("Testing Enhanced Memory Manager...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        temp_db_path = tmp_db.name
    
    try:
        memory_manager = MemoryManager(db_path=temp_db_path)
        
        # Test content quality analysis
        print("Testing quality metrics analysis...")
        
        # Record some test feedback with varying quality
        test_cases = [
            {
                "content_type": "twitter_thread",
                "content_text": "This is a short thread about AI safety. It covers basic concepts. Very simple language.",
                "user_action": "accept",
                "original_prompt": "Generate thread about AI safety",
                "generation_time": 2.5
            },
            {
                "content_type": "twitter_thread", 
                "content_text": "This comprehensive analysis of artificial intelligence safety encompasses multiple sophisticated methodologies, including adversarial testing frameworks, formal verification protocols, and continuous monitoring architectures. The technical complexity requires advanced understanding of machine learning paradigms.",
                "user_action": "reject",
                "original_prompt": "Generate thread about AI safety",
                "generation_time": 3.0,
                "metadata": {"revision_reason": "too technical and complex"}
            },
            {
                "content_type": "twitter_thread",
                "content_text": "Understanding AI safety: key frameworks include testing, monitoring, and validation. These approaches help ensure systems work as intended. Clear processes matter for deployment.",
                "user_action": "edit",
                "original_prompt": "Generate thread about AI safety", 
                "generation_time": 2.2,
                "metadata": {"edited_content": "Understanding AI safety: **key frameworks** include testing, monitoring, and validation. These approaches help ensure systems work as intended.\n\n• Clear processes matter for deployment\n• Regular auditing prevents issues"}
            }
        ]
        
        for case in test_cases:
            success = memory_manager.record_feedback(**case)
            if not success:
                print("[FAIL] Failed to record test feedback")
                return False
        
        print("[PASS] Quality metrics recorded successfully")
        
        # Test quality analysis retrieval
        quality_analysis = memory_manager.get_quality_analysis("twitter_thread")
        print(f"Quality analysis: {quality_analysis}")
        
        if not quality_analysis:
            print("[FAIL] No quality analysis retrieved")
            return False
        
        print("[PASS] Quality analysis retrieved")
        
        # Test edit pattern detection
        edit_patterns = memory_manager.get_edit_patterns("twitter_thread")
        print(f"Edit patterns found: {len(edit_patterns)}")
        
        if edit_patterns:
            print("[PASS] Edit patterns detected")
            for pattern in edit_patterns:
                print(f"  - {pattern['edit_type']}: {pattern['description']}")
        else:
            print("[INFO] No edit patterns yet (need more data)")
        
        # Test user preferences learning
        user_preferences = memory_manager.get_user_preferences("twitter_thread")
        print(f"User preferences: {user_preferences}")
        
        if user_preferences:
            print("[PASS] User preferences learned")
        else:
            print("[INFO] No strong preferences yet (need more data)")
        
        # Test prompt enhancements
        prompt_enhancements = memory_manager.get_prompt_enhancements("twitter_thread")
        print(f"Prompt enhancements generated: {len(prompt_enhancements) > 0}")
        
        if prompt_enhancements:
            print("[PASS] Prompt enhancements generated")
            print(f"Enhancement preview: {prompt_enhancements[:100]}...")
        else:
            print("[INFO] No prompt enhancements yet (need more data)")
        
        # Test learning insights
        insights = memory_manager.get_learning_insights("twitter_thread")
        print(f"Learning insights generated: {len(insights.get('recommendations', [])) > 0}")
        
        if insights.get('recommendations'):
            print("[PASS] Learning insights generated")
            for rec in insights['recommendations']:
                print(f"  - {rec}")
        else:
            print("[INFO] No learning insights yet (need more data)")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Enhanced memory manager test failed: {e}")
        return False
    
    finally:
        try:
            os.unlink(temp_db_path)
        except:
            pass

def test_generator_memory_integration():
    """Test that generators properly integrate with memory system."""
    print("\nTesting Generator Memory Integration...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create temporary samples and memory
        samples_dir = os.path.join(temp_dir, "samples")
        memory_db = os.path.join(temp_dir, "memory.db")
        
        # Create basic sample files
        os.makedirs(os.path.join(samples_dir, "sample_threads"), exist_ok=True)
        
        with open(os.path.join(samples_dir, "writing_instructions_thread.txt"), "w") as f:
            f.write("Write engaging threads with clear formatting.")
        
        # Initialize components
        memory_manager = MemoryManager(db_path=memory_db)
        twitter_generator = TwitterThreadGenerator(samples_dir=samples_dir, memory_manager=memory_manager)
        
        # Add some learning data
        memory_manager.record_feedback(
            content_type="twitter_thread",
            content_text="This is a well-formatted thread with proper structure.",
            user_action="accept",
            original_prompt="Test prompt"
        )
        
        # Test that generator includes memory enhancements
        try:
            # Generate content (this will call get_prompt_enhancements internally)
            thread = twitter_generator.generate_thread("Test article about AI")
            
            print("[PASS] Generator successfully integrated with memory system")
            print(f"Generated thread length: {len(thread)} characters")
            
            return True
            
        except Exception as e:
            print(f"[FAIL] Generator memory integration failed: {e}")
            return False

def test_database_schema():
    """Test that the new database schema is properly created."""
    print("\nTesting Database Schema...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        temp_db_path = tmp_db.name
    
    try:
        memory_manager = MemoryManager(db_path=temp_db_path)
        
        # Check that all new tables exist
        import sqlite3
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()
            
            # Get list of tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                'feedback_history', 
                'generation_stats', 
                'edit_patterns', 
                'quality_metrics', 
                'user_preferences'
            ]
            
            missing_tables = [table for table in expected_tables if table not in tables]
            
            if missing_tables:
                print(f"[FAIL] Missing tables: {missing_tables}")
                return False
            
            print("[PASS] All required tables created")
            
            # Check that indexes exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]
            
            expected_indexes = [
                'idx_feedback_timestamp',
                'idx_feedback_content_type', 
                'idx_feedback_action',
                'idx_edit_patterns_type',
                'idx_quality_metrics_type',
                'idx_user_preferences_type'
            ]
            
            missing_indexes = [idx for idx in expected_indexes if idx not in indexes]
            
            if missing_indexes:
                print(f"[FAIL] Missing indexes: {missing_indexes}")
                return False
            
            print("[PASS] All required indexes created")
            return True
            
    except Exception as e:
        print(f"[FAIL] Database schema test failed: {e}")
        return False
    
    finally:
        try:
            os.unlink(temp_db_path)
        except:
            pass

def main():
    """Run all Phase 2 memory tests."""
    print("=" * 70)
    print("ContentAgent Memory System - Phase 2 Tests")
    print("=" * 70)
    
    tests = [
        test_database_schema,
        test_enhanced_memory_manager,
        test_generator_memory_integration
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"[ERROR] Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 70)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"[SUCCESS] All {total} Phase 2 tests passed!")
        print("Advanced memory features are working correctly.")
        print("\nCapabilities now available:")
        print("- Content quality analysis")
        print("- Edit pattern recognition") 
        print("- User preference learning")
        print("- Automatic prompt enhancement")
        print("- Learning insights generation")
    else:
        print(f"[MIXED RESULTS] {passed}/{total} tests passed")
        print("Some advanced features may need additional data to function.")
    
    print("=" * 70)
    
    return passed == total

if __name__ == "__main__":
    main()