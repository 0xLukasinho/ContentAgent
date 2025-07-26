import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
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
                
                conn.commit()
                
                self._update_generation_stats(content_type, user_action, generation_time)
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