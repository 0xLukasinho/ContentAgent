import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import logging
import difflib
import re
from collections import Counter, defaultdict
import textstat
from src.config import Config

logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self, db_path: Optional[str] = None):
        self.config = Config()
        self.db_path = db_path or os.path.join(self.config.data_dir, "memory", "content_agent_memory.db")
        self.max_records = 2000
        
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the SQLite database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS feedback_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        content_type TEXT NOT NULL,
                        content_text TEXT NOT NULL,
                        user_action TEXT NOT NULL,
                        original_prompt TEXT,
                        generation_time REAL,
                        content_hash TEXT,
                        metadata TEXT
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS generation_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content_type TEXT NOT NULL,
                        total_generated INTEGER DEFAULT 0,
                        total_accepted INTEGER DEFAULT 0,
                        total_rejected INTEGER DEFAULT 0,
                        total_edited INTEGER DEFAULT 0,
                        avg_generation_time REAL DEFAULT 0.0,
                        last_updated TEXT NOT NULL
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS edit_patterns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content_type TEXT NOT NULL,
                        edit_type TEXT NOT NULL,
                        pattern_description TEXT,
                        frequency INTEGER DEFAULT 1,
                        examples TEXT,
                        last_seen TEXT NOT NULL
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS quality_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        feedback_id INTEGER,
                        content_type TEXT NOT NULL,
                        user_action TEXT NOT NULL,
                        readability_score REAL,
                        complexity_score REAL,
                        length_chars INTEGER,
                        length_words INTEGER,
                        timestamp TEXT NOT NULL,
                        FOREIGN KEY (feedback_id) REFERENCES feedback_history (id)
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content_type TEXT NOT NULL,
                        preference_type TEXT NOT NULL,
                        preference_value TEXT,
                        confidence_score REAL DEFAULT 0.0,
                        last_updated TEXT NOT NULL
                    )
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_feedback_timestamp 
                    ON feedback_history(timestamp)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_feedback_content_type 
                    ON feedback_history(content_type)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_feedback_action 
                    ON feedback_history(user_action)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_edit_patterns_type 
                    ON edit_patterns(content_type, edit_type)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_quality_metrics_type 
                    ON quality_metrics(content_type, user_action)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_user_preferences_type 
                    ON user_preferences(content_type, preference_type)
                ''')
                
                conn.commit()
                logger.info(f"Memory database initialized at {self.db_path}")
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def record_feedback(self, 
                       content_type: str,
                       content_text: str,
                       user_action: str,
                       original_prompt: Optional[str] = None,
                       generation_time: Optional[float] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Record user feedback for generated content."""
        try:
            timestamp = datetime.now().isoformat()
            content_hash = str(hash(content_text))
            metadata_json = json.dumps(metadata) if metadata else None
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO feedback_history 
                    (timestamp, content_type, content_text, user_action, 
                     original_prompt, generation_time, content_hash, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (timestamp, content_type, content_text, user_action,
                      original_prompt, generation_time, content_hash, metadata_json))
                
                feedback_id = cursor.lastrowid
                conn.commit()
                
                # Analyze content quality
                self._analyze_content_quality(feedback_id, content_type, user_action, content_text)
                
                # For edit actions, analyze edit patterns if we have previous content
                if user_action == 'edit' and metadata and 'edited_content' in metadata:
                    self._analyze_edit_patterns(content_type, content_text, metadata['edited_content'])
                
                self._update_generation_stats(content_type, user_action, generation_time)
                self._update_user_preferences(content_type, user_action, content_text, metadata)
                self._enforce_record_limit()
                
                logger.info(f"Recorded {user_action} feedback for {content_type}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error recording feedback: {e}")
            return False
    
    def _update_generation_stats(self, content_type: str, user_action: str, generation_time: Optional[float]):
        """Update generation statistics for a content type."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM generation_stats WHERE content_type = ?
                ''', (content_type,))
                
                stats = cursor.fetchone()
                timestamp = datetime.now().isoformat()
                
                if stats:
                    total_generated = stats[2] + 1
                    total_accepted = stats[3] + (1 if user_action == 'accept' else 0)
                    total_rejected = stats[4] + (1 if user_action == 'reject' else 0)
                    total_edited = stats[5] + (1 if user_action == 'edit' else 0)
                    
                    if generation_time and stats[6]:
                        avg_generation_time = (stats[6] * stats[2] + generation_time) / total_generated
                    else:
                        avg_generation_time = generation_time or stats[6] or 0.0
                    
                    cursor.execute('''
                        UPDATE generation_stats 
                        SET total_generated = ?, total_accepted = ?, total_rejected = ?, 
                            total_edited = ?, avg_generation_time = ?, last_updated = ?
                        WHERE content_type = ?
                    ''', (total_generated, total_accepted, total_rejected, 
                          total_edited, avg_generation_time, timestamp, content_type))
                else:
                    total_accepted = 1 if user_action == 'accept' else 0
                    total_rejected = 1 if user_action == 'reject' else 0
                    total_edited = 1 if user_action == 'edit' else 0
                    
                    cursor.execute('''
                        INSERT INTO generation_stats 
                        (content_type, total_generated, total_accepted, total_rejected, 
                         total_edited, avg_generation_time, last_updated)
                        VALUES (?, 1, ?, ?, ?, ?, ?)
                    ''', (content_type, total_accepted, total_rejected, 
                          total_edited, generation_time or 0.0, timestamp))
                
                conn.commit()
                
        except sqlite3.Error as e:
            logger.error(f"Error updating generation stats: {e}")
    
    def _enforce_record_limit(self):
        """Maintain maximum record limit by removing oldest entries."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM feedback_history')
                count = cursor.fetchone()[0]
                
                if count > self.max_records:
                    excess = count - self.max_records
                    cursor.execute('''
                        DELETE FROM feedback_history 
                        WHERE id IN (
                            SELECT id FROM feedback_history 
                            ORDER BY timestamp ASC 
                            LIMIT ?
                        )
                    ''', (excess,))
                    
                    conn.commit()
                    logger.info(f"Removed {excess} old records to maintain limit")
                    
        except sqlite3.Error as e:
            logger.error(f"Error enforcing record limit: {e}")
    
    def _analyze_content_quality(self, feedback_id: int, content_type: str, user_action: str, content_text: str):
        """Analyze content quality metrics and store them."""
        try:
            # Calculate readability and complexity metrics
            readability_score = textstat.flesch_reading_ease(content_text)
            complexity_score = textstat.flesch_kincaid_grade(content_text)
            length_chars = len(content_text)
            length_words = textstat.lexicon_count(content_text)
            
            timestamp = datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO quality_metrics 
                    (feedback_id, content_type, user_action, readability_score, 
                     complexity_score, length_chars, length_words, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (feedback_id, content_type, user_action, readability_score,
                      complexity_score, length_chars, length_words, timestamp))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error analyzing content quality: {e}")
    
    def _analyze_edit_patterns(self, content_type: str, original_content: str, edited_content: str):
        """Analyze patterns in user edits to learn preferences."""
        try:
            # Calculate diff between original and edited content
            diff = list(difflib.unified_diff(
                original_content.splitlines(keepends=True),
                edited_content.splitlines(keepends=True),
                fromfile='original',
                tofile='edited',
                n=3
            ))
            
            if not diff:
                return  # No changes detected
            
            # Analyze different types of edits
            patterns = self._extract_edit_patterns(original_content, edited_content, diff)
            
            timestamp = datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for pattern_type, pattern_info in patterns.items():
                    # Check if this pattern already exists
                    cursor.execute('''
                        SELECT id, frequency FROM edit_patterns 
                        WHERE content_type = ? AND edit_type = ? AND pattern_description = ?
                    ''', (content_type, pattern_type, pattern_info['description']))
                    
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Update frequency
                        cursor.execute('''
                            UPDATE edit_patterns 
                            SET frequency = frequency + 1, last_seen = ?
                            WHERE id = ?
                        ''', (timestamp, existing[0]))
                    else:
                        # Insert new pattern
                        cursor.execute('''
                            INSERT INTO edit_patterns 
                            (content_type, edit_type, pattern_description, frequency, examples, last_seen)
                            VALUES (?, ?, ?, 1, ?, ?)
                        ''', (content_type, pattern_type, pattern_info['description'], 
                              json.dumps(pattern_info['examples']), timestamp))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error analyzing edit patterns: {e}")
    
    def _extract_edit_patterns(self, original: str, edited: str, diff: List[str]) -> Dict[str, Dict]:
        """Extract patterns from edit differences."""
        patterns = {}
        
        # Analyze length changes
        orig_words = len(original.split())
        edited_words = len(edited.split())
        word_diff = edited_words - orig_words
        
        if abs(word_diff) > 5:  # Significant length change
            if word_diff > 0:
                patterns['length_increase'] = {
                    'description': f'Tends to expand content by ~{word_diff} words',
                    'examples': [f'Added {word_diff} words']
                }
            else:
                patterns['length_decrease'] = {
                    'description': f'Tends to shorten content by ~{abs(word_diff)} words',
                    'examples': [f'Removed {abs(word_diff)} words']
                }
        
        # Analyze formatting changes
        formatting_changes = []
        if '**' in edited and '**' not in original:
            formatting_changes.append('Added bold formatting')
        if original.count('\n') != edited.count('\n'):
            formatting_changes.append('Changed paragraph structure')
        if '•' in edited and '•' not in original:
            formatting_changes.append('Added bullet points')
        
        if formatting_changes:
            patterns['formatting'] = {
                'description': 'Prefers specific formatting changes',
                'examples': formatting_changes
            }
        
        # Analyze vocabulary changes
        orig_words_set = set(re.findall(r'\b\w+\b', original.lower()))
        edited_words_set = set(re.findall(r'\b\w+\b', edited.lower()))
        
        added_words = edited_words_set - orig_words_set
        removed_words = orig_words_set - edited_words_set
        
        if len(added_words) > 3:
            patterns['vocabulary_addition'] = {
                'description': 'Tends to add technical/specific vocabulary',
                'examples': list(added_words)[:10]  # Limit examples
            }
        
        if len(removed_words) > 3:
            patterns['vocabulary_removal'] = {
                'description': 'Tends to remove certain types of words',
                'examples': list(removed_words)[:10]  # Limit examples
            }
        
        return patterns
    
    def _update_user_preferences(self, content_type: str, user_action: str, content_text: str, metadata: Optional[Dict]):
        """Update user preferences based on feedback patterns."""
        try:
            timestamp = datetime.now().isoformat()
            
            # Calculate content characteristics
            preferences = {}
            
            if user_action == 'accept':
                # Extract preferences from accepted content
                word_count = len(content_text.split())
                readability = textstat.flesch_reading_ease(content_text)
                
                preferences['preferred_length'] = str(word_count)
                preferences['preferred_readability'] = str(readability)
                
                # Check for formatting preferences
                if '**' in content_text:
                    preferences['uses_bold'] = 'true'
                if '•' in content_text or '-' in content_text:
                    preferences['uses_bullets'] = 'true'
                if content_text.count('\n\n') > 2:
                    preferences['prefers_paragraphs'] = 'true'
            
            elif user_action == 'reject':
                # Learn what to avoid from rejected content
                if metadata and 'revision_reason' in metadata:
                    reason = metadata['revision_reason'].lower()
                    if any(word in reason for word in ['too long', 'verbose', 'lengthy']):
                        preferences['avoid_long_content'] = 'true'
                    if any(word in reason for word in ['too short', 'brief', 'more detail']):
                        preferences['avoid_short_content'] = 'true'
                    if any(word in reason for word in ['technical', 'complex', 'difficult']):
                        preferences['avoid_technical'] = 'true'
                    if any(word in reason for word in ['simple', 'basic', 'more depth']):
                        preferences['avoid_simple'] = 'true'
            
            # Store preferences
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for pref_type, pref_value in preferences.items():
                    # Check if preference already exists
                    cursor.execute('''
                        SELECT id, confidence_score FROM user_preferences 
                        WHERE content_type = ? AND preference_type = ?
                    ''', (content_type, pref_type))
                    
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Update confidence score
                        new_confidence = min(1.0, existing[1] + 0.1)
                        cursor.execute('''
                            UPDATE user_preferences 
                            SET preference_value = ?, confidence_score = ?, last_updated = ?
                            WHERE id = ?
                        ''', (pref_value, new_confidence, timestamp, existing[0]))
                    else:
                        # Insert new preference
                        cursor.execute('''
                            INSERT INTO user_preferences 
                            (content_type, preference_type, preference_value, confidence_score, last_updated)
                            VALUES (?, ?, ?, 0.3, ?)
                        ''', (content_type, pref_type, pref_value, timestamp))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
    
    def get_generation_stats(self, content_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get generation statistics for content types."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if content_type:
                    cursor.execute('''
                        SELECT * FROM generation_stats WHERE content_type = ?
                    ''', (content_type,))
                else:
                    cursor.execute('SELECT * FROM generation_stats')
                
                rows = cursor.fetchall()
                
                stats = []
                for row in rows:
                    stats.append({
                        'content_type': row[1],
                        'total_generated': row[2],
                        'total_accepted': row[3],
                        'total_rejected': row[4],
                        'total_edited': row[5],
                        'acceptance_rate': row[3] / row[2] if row[2] > 0 else 0,
                        'avg_generation_time': row[6],
                        'last_updated': row[7]
                    })
                
                return stats
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving generation stats: {e}")
            return []
    
    def get_recent_feedback(self, content_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent feedback entries."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if content_type:
                    cursor.execute('''
                        SELECT * FROM feedback_history 
                        WHERE content_type = ?
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (content_type, limit))
                else:
                    cursor.execute('''
                        SELECT * FROM feedback_history 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (limit,))
                
                rows = cursor.fetchall()
                
                feedback = []
                for row in rows:
                    metadata = json.loads(row[8]) if row[8] else {}
                    feedback.append({
                        'id': row[0],
                        'timestamp': row[1],
                        'content_type': row[2],
                        'content_text': row[3],
                        'user_action': row[4],
                        'original_prompt': row[5],
                        'generation_time': row[6],
                        'content_hash': row[7],
                        'metadata': metadata
                    })
                
                return feedback
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving recent feedback: {e}")
            return []
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get general database information."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM feedback_history')
                total_feedback = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM generation_stats')
                content_types = cursor.fetchone()[0]
                
                cursor.execute('''
                    SELECT MIN(timestamp), MAX(timestamp) FROM feedback_history
                ''')
                date_range = cursor.fetchone()
                
                return {
                    'database_path': self.db_path,
                    'total_feedback_records': total_feedback,
                    'content_types_tracked': content_types,
                    'earliest_record': date_range[0],
                    'latest_record': date_range[1],
                    'max_records_limit': self.max_records
                }
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving database info: {e}")
            return {}
    
    def get_edit_patterns(self, content_type: Optional[str] = None, min_frequency: int = 2) -> List[Dict[str, Any]]:
        """Get discovered edit patterns."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if content_type:
                    cursor.execute('''
                        SELECT edit_type, pattern_description, frequency, examples, last_seen
                        FROM edit_patterns 
                        WHERE content_type = ? AND frequency >= ?
                        ORDER BY frequency DESC
                    ''', (content_type, min_frequency))
                else:
                    cursor.execute('''
                        SELECT content_type, edit_type, pattern_description, frequency, examples, last_seen
                        FROM edit_patterns 
                        WHERE frequency >= ?
                        ORDER BY content_type, frequency DESC
                    ''', (min_frequency,))
                
                rows = cursor.fetchall()
                
                patterns = []
                for row in rows:
                    if content_type:
                        pattern = {
                            'edit_type': row[0],
                            'description': row[1],
                            'frequency': row[2],
                            'examples': json.loads(row[3]) if row[3] else [],
                            'last_seen': row[4]
                        }
                    else:
                        pattern = {
                            'content_type': row[0],
                            'edit_type': row[1],
                            'description': row[2],
                            'frequency': row[3],
                            'examples': json.loads(row[4]) if row[4] else [],
                            'last_seen': row[5]
                        }
                    patterns.append(pattern)
                
                return patterns
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving edit patterns: {e}")
            return []
    
    def get_quality_analysis(self, content_type: Optional[str] = None) -> Dict[str, Any]:
        """Get quality metrics analysis."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if content_type:
                    cursor.execute('''
                        SELECT user_action, AVG(readability_score), AVG(complexity_score), 
                               AVG(length_words), COUNT(*) as count
                        FROM quality_metrics 
                        WHERE content_type = ?
                        GROUP BY user_action
                    ''', (content_type,))
                else:
                    cursor.execute('''
                        SELECT content_type, user_action, AVG(readability_score), AVG(complexity_score), 
                               AVG(length_words), COUNT(*) as count
                        FROM quality_metrics 
                        GROUP BY content_type, user_action
                    ''')
                
                rows = cursor.fetchall()
                
                analysis = {}
                for row in rows:
                    if content_type:
                        key = row[0]  # user_action
                        analysis[key] = {
                            'avg_readability': round(row[1], 2) if row[1] else 0,
                            'avg_complexity': round(row[2], 2) if row[2] else 0,
                            'avg_length': round(row[3], 2) if row[3] else 0,
                            'sample_count': row[4]
                        }
                    else:
                        content_key = row[0]
                        action_key = row[1]
                        if content_key not in analysis:
                            analysis[content_key] = {}
                        analysis[content_key][action_key] = {
                            'avg_readability': round(row[2], 2) if row[2] else 0,
                            'avg_complexity': round(row[3], 2) if row[3] else 0,
                            'avg_length': round(row[4], 2) if row[4] else 0,
                            'sample_count': row[5]
                        }
                
                return analysis
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving quality analysis: {e}")
            return {}
    
    def get_user_preferences(self, content_type: Optional[str] = None, min_confidence: float = 0.5) -> Dict[str, Any]:
        """Get learned user preferences."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if content_type:
                    cursor.execute('''
                        SELECT preference_type, preference_value, confidence_score, last_updated
                        FROM user_preferences 
                        WHERE content_type = ? AND confidence_score >= ?
                        ORDER BY confidence_score DESC
                    ''', (content_type, min_confidence))
                else:
                    cursor.execute('''
                        SELECT content_type, preference_type, preference_value, confidence_score, last_updated
                        FROM user_preferences 
                        WHERE confidence_score >= ?
                        ORDER BY content_type, confidence_score DESC
                    ''', (min_confidence,))
                
                rows = cursor.fetchall()
                
                preferences = {}
                for row in rows:
                    if content_type:
                        preferences[row[0]] = {
                            'value': row[1],
                            'confidence': round(row[2], 2),
                            'last_updated': row[3]
                        }
                    else:
                        content_key = row[0]
                        if content_key not in preferences:
                            preferences[content_key] = {}
                        preferences[content_key][row[1]] = {
                            'value': row[2],
                            'confidence': round(row[3], 2),
                            'last_updated': row[4]
                        }
                
                return preferences
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving user preferences: {e}")
            return {}
    
    def get_learning_insights(self, content_type: str) -> Dict[str, Any]:
        """Get comprehensive learning insights for a content type."""
        try:
            insights = {
                'generation_stats': self.get_generation_stats(content_type),
                'edit_patterns': self.get_edit_patterns(content_type),
                'quality_analysis': self.get_quality_analysis(content_type),
                'user_preferences': self.get_user_preferences(content_type),
                'recommendations': []
            }
            
            # Generate recommendations based on patterns
            recommendations = []
            
            # Quality-based recommendations
            quality = insights['quality_analysis']
            if 'accept' in quality and 'reject' in quality:
                accepted = quality['accept']
                rejected = quality['reject']
                
                if accepted['avg_readability'] > rejected['avg_readability']:
                    recommendations.append(f"User prefers readability score around {accepted['avg_readability']}")
                
                if accepted['avg_length'] != rejected['avg_length']:
                    if accepted['avg_length'] > rejected['avg_length']:
                        recommendations.append(f"User prefers longer content (~{int(accepted['avg_length'])} words)")
                    else:
                        recommendations.append(f"User prefers shorter content (~{int(accepted['avg_length'])} words)")
            
            # Pattern-based recommendations
            patterns = insights['edit_patterns']
            if patterns:
                for pattern in patterns[:3]:  # Top 3 patterns
                    if pattern['frequency'] >= 3:
                        recommendations.append(f"Common edit: {pattern['description']}")
            
            # Preference-based recommendations
            preferences = insights['user_preferences']
            for pref_type, pref_data in preferences.items():
                if pref_data['confidence'] >= 0.7:
                    recommendations.append(f"Strong preference: {pref_type} = {pref_data['value']}")
            
            insights['recommendations'] = recommendations
            return insights
            
        except Exception as e:
            logger.error(f"Error generating learning insights: {e}")
            return {}
    
    def get_prompt_enhancements(self, content_type: str) -> str:
        """Generate prompt enhancements based on learned user preferences."""
        try:
            preferences = self.get_user_preferences(content_type, min_confidence=0.4)
            patterns = self.get_edit_patterns(content_type, min_frequency=2)
            quality = self.get_quality_analysis(content_type)
            
            enhancements = []
            
            # Add length preferences
            if 'preferred_length' in preferences and preferences['preferred_length']['confidence'] >= 0.5:
                target_length = int(preferences['preferred_length']['value'])
                enhancements.append(f"Target approximately {target_length} words based on user preferences.")
            
            # Add readability preferences
            if 'preferred_readability' in preferences and preferences['preferred_readability']['confidence'] >= 0.5:
                target_readability = float(preferences['preferred_readability']['value'])
                if target_readability > 60:
                    enhancements.append("Use clear, accessible language (user prefers higher readability).")
                elif target_readability < 40:
                    enhancements.append("Use more sophisticated, complex language (user prefers lower readability).")
            
            # Add formatting preferences
            formatting_prefs = []
            if 'uses_bold' in preferences and preferences['uses_bold']['confidence'] >= 0.5:
                formatting_prefs.append("Use **bold** formatting for key terms")
            if 'uses_bullets' in preferences and preferences['uses_bullets']['confidence'] >= 0.5:
                formatting_prefs.append("Use bullet points or lists when appropriate")
            if 'prefers_paragraphs' in preferences and preferences['prefers_paragraphs']['confidence'] >= 0.5:
                formatting_prefs.append("Structure content in clear paragraphs")
            
            if formatting_prefs:
                enhancements.append(f"Formatting preferences: {', '.join(formatting_prefs)}.")
            
            # Add content preferences based on rejection patterns
            avoid_prefs = []
            if 'avoid_long_content' in preferences:
                avoid_prefs.append("avoid overly lengthy explanations")
            if 'avoid_short_content' in preferences:
                avoid_prefs.append("provide comprehensive detail")
            if 'avoid_technical' in preferences:
                avoid_prefs.append("use accessible, non-technical language")
            if 'avoid_simple' in preferences:
                avoid_prefs.append("include technical depth and complexity")
            
            if avoid_prefs:
                enhancements.append(f"Content preferences: {', '.join(avoid_prefs)}.")
            
            # Add insights from edit patterns
            edit_insights = []
            for pattern in patterns[:2]:  # Top 2 most frequent patterns
                if pattern['edit_type'] == 'vocabulary_addition' and pattern['frequency'] >= 3:
                    edit_insights.append("User often adds technical vocabulary")
                elif pattern['edit_type'] == 'formatting' and pattern['frequency'] >= 3:
                    edit_insights.append("User frequently adjusts formatting")
                elif pattern['edit_type'] == 'length_increase' and pattern['frequency'] >= 3:
                    edit_insights.append("User often expands content length")
                elif pattern['edit_type'] == 'length_decrease' and pattern['frequency'] >= 3:
                    edit_insights.append("User often shortens content")
            
            if edit_insights:
                enhancements.append(f"Based on edit history: {', '.join(edit_insights)}.")
            
            # Combine all enhancements
            if enhancements:
                enhancement_text = "\n\nUSER PREFERENCE ADJUSTMENTS:\n" + "\n".join(f"- {enhancement}" for enhancement in enhancements)
                return enhancement_text
            else:
                return ""
                
        except Exception as e:
            logger.error(f"Error generating prompt enhancements: {e}")
            return ""