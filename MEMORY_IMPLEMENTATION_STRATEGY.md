# ContentAgent Memory Function Implementation Strategy

## Overview

This document outlines the implementation strategy for adding memory and learning capabilities to the ContentAgent system. The goal is to create a system that learns from user feedback and improves content generation over time, while maintaining simplicity and using only free, local tools.

## Core Architecture Decision: SQLite + Pattern Analysis

**SQLite Database**: Single source of truth for all memory data
- User feedback history (accept/reject/edit actions)
- Content generation statistics and success metrics
- Edit pattern analysis results
- Content quality metrics

**No JSON Preferences**: Existing style instructions and samples already handle user preferences

## Technology Stack (Free & Local Only)

### Core Components
- **SQLite3** (built into Python) - All persistent memory storage
- **difflib** (built into Python) - Text edit analysis
- **collections.Counter** (built into Python) - Pattern frequency analysis

### Enhanced Analysis Tools
- **scikit-learn** (free) - Pattern recognition and clustering of user behavior
  - Cluster similar edit patterns to identify user preferences
  - Classify content quality based on acceptance patterns
  - Predict likelihood of content acceptance
- **textstat** (free) - Content readability and quality analysis
  - Measure readability scores (Flesch-Kincaid, etc.)
  - Track content complexity preferences
  - Analyze correlation between readability and acceptance rates

## Database Schema

```sql
-- User feedback on generated content
CREATE TABLE feedback_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    content_type TEXT NOT NULL,  -- 'twitter_thread', 'detailed_post', etc.
    topic TEXT,
    content_hash TEXT,           -- SHA256 of original content
    action TEXT NOT NULL,        -- 'accept', 'reject', 'edit'
    session_id TEXT,
    original_content TEXT,
    edited_content TEXT,         -- NULL if not edited
    user_rating INTEGER          -- 1-5 scale, optional
);

-- Analysis of user edit patterns
CREATE TABLE edit_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    content_type TEXT NOT NULL,
    original_length INTEGER,
    edited_length INTEGER,
    readability_change REAL,     -- Change in readability score
    tone_keywords TEXT,          -- JSON array of tone-related changes
    structural_changes TEXT,     -- JSON array of structure modifications
    edit_distance INTEGER,       -- Levenshtein distance
    pattern_cluster INTEGER      -- Cluster ID from scikit-learn
);

-- Content generation success metrics
CREATE TABLE generation_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_type TEXT NOT NULL,
    topic TEXT,
    prompt_variant_hash TEXT,    -- Hash of the prompt used
    acceptance_rate REAL,
    avg_edit_distance REAL,
    avg_readability_score REAL,
    total_generations INTEGER,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Content quality metrics
CREATE TABLE quality_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash TEXT,
    content_type TEXT,
    flesch_kincaid_grade REAL,
    flesch_reading_ease REAL,
    gunning_fog REAL,
    automated_readability_index REAL,
    word_count INTEGER,
    sentence_count INTEGER,
    accepted BOOLEAN
);
```

## Memory Manager Implementation

```python
class MemoryManager:
    def __init__(self):
        self.db_path = "data/memory/content_memory.db"
        self._init_database()
        self._load_ml_models()
    
    # === Core Memory Functions ===
    def record_feedback(self, content_type, topic, content, action, edited_content=None):
        """Record user feedback and trigger analysis"""
        
    def analyze_edit_patterns(self, original, edited, content_type):
        """Analyze edit using difflib + textstat + scikit-learn"""
        
    def get_improvement_suggestions(self, content_type, topic):
        """Provide suggestions based on learned patterns"""
    
    # === Pattern Recognition (scikit-learn) ===
    def cluster_edit_patterns(self):
        """Use KMeans to cluster similar edit behaviors"""
        
    def predict_content_acceptance(self, content, content_type):
        """Predict if content will be accepted based on features"""
        
    def classify_edit_intent(self, original, edited):
        """Classify the type of edit (tone, length, structure, etc.)"""
    
    # === Quality Analysis (textstat) ===
    def analyze_content_quality(self, content):
        """Calculate readability and quality metrics"""
        
    def find_optimal_readability(self, content_type):
        """Find readability range with highest acceptance"""
        
    def suggest_readability_improvements(self, content, target_metrics):
        """Suggest changes to improve readability"""
    
    # === Learning and Adaptation ===
    def update_generation_preferences(self, content_type, topic):
        """Learn from patterns to modify future generation"""
        
    def get_prompt_enhancements(self, content_type, topic):
        """Generate prompt modifications based on memory"""
```

## Integration Points

### 1. CLI Interface Enhancement (`cli_interface.py`)

```python
# Enhanced feedback collection
def collect_feedback_with_memory(content, content_type, topic, memory_manager):
    action = get_user_action()  # existing function
    
    if action == "edit":
        edited_content = get_user_edit()
        memory_manager.record_feedback(content_type, topic, content, "edit", edited_content)
        memory_manager.analyze_edit_patterns(content, edited_content, content_type)
    else:
        memory_manager.record_feedback(content_type, topic, content, action)
    
    # Get immediate suggestions for next generation
    suggestions = memory_manager.get_improvement_suggestions(content_type, topic)
    if suggestions:
        display_suggestions(suggestions)
```

### 2. Content Generator Enhancement

```python
# Before content generation in each generator
def generate_with_memory(self, content, memory_manager, content_type, topic):
    # Get memory-based improvements
    prompt_enhancements = memory_manager.get_prompt_enhancements(content_type, topic)
    target_readability = memory_manager.find_optimal_readability(content_type)
    
    # Modify base prompt
    enhanced_prompt = self.base_prompt + prompt_enhancements
    if target_readability:
        enhanced_prompt += f"\nAim for readability level: {target_readability}"
    
    # Generate content
    generated_content = self.llm.invoke(enhanced_prompt)
    
    # Predict acceptance likelihood
    acceptance_score = memory_manager.predict_content_acceptance(generated_content, content_type)
    
    return generated_content, acceptance_score
```

## Learning Mechanisms

### 1. Edit Pattern Analysis (difflib + scikit-learn)

```python
def analyze_edit_patterns(self, original, edited, content_type):
    # Text difference analysis
    differ = difflib.SequenceMatcher(None, original, edited)
    edit_distance = self._calculate_edit_distance(original, edited)
    
    # Quality metric changes
    original_metrics = self.analyze_content_quality(original)
    edited_metrics = self.analyze_content_quality(edited)
    readability_change = edited_metrics['flesch_reading_ease'] - original_metrics['flesch_reading_ease']
    
    # Extract edit features for clustering
    features = [
        len(original), len(edited),
        edit_distance, readability_change,
        original_metrics['word_count'], edited_metrics['word_count']
    ]
    
    # Predict cluster and store
    cluster = self.edit_classifier.predict([features])[0]
    self._store_edit_pattern(original, edited, content_type, features, cluster)
```

### 2. Quality-Acceptance Correlation (textstat)

```python
def analyze_content_quality(self, content):
    return {
        'flesch_kincaid_grade': textstat.flesch_kincaid().score(content),
        'flesch_reading_ease': textstat.flesch_reading_ease(content),
        'gunning_fog': textstat.gunning_fog(content),
        'word_count': textstat.lexicon_count(content),
        'sentence_count': textstat.sentence_count(content)
    }

def find_optimal_readability(self, content_type):
    # Query accepted content and find readability sweet spot
    accepted_content = self._get_accepted_content(content_type)
    readability_scores = [self.analyze_content_quality(content) for content in accepted_content]
    
    # Find optimal range using statistical analysis
    optimal_flesch = np.mean([score['flesch_reading_ease'] for score in readability_scores])
    return optimal_flesch
```

### 3. Predictive Content Acceptance (scikit-learn)

```python
def predict_content_acceptance(self, content, content_type):
    # Extract features
    quality_metrics = self.analyze_content_quality(content)
    features = [
        quality_metrics['flesch_reading_ease'],
        quality_metrics['word_count'],
        quality_metrics['sentence_count'],
        len(content.split('\n')),  # paragraph count
    ]
    
    # Predict using trained model
    acceptance_probability = self.acceptance_classifier.predict_proba([features])[0][1]
    return acceptance_probability
```

## Implementation Steps

### Phase 1: Foundation (Week 1)
1. Create MemoryManager class with SQLite database
2. Set up basic feedback recording in CLI interface
3. Implement simple edit analysis using difflib
4. Add textstat integration for quality metrics

### Phase 2: Pattern Recognition (Week 2)
1. Implement scikit-learn clustering for edit patterns
2. Create content acceptance prediction model
3. Build quality-acceptance correlation analysis
4. Add prompt enhancement based on learned patterns

### Phase 3: Advanced Learning (Week 3)
1. Implement predictive content generation
2. Add real-time improvement suggestions
3. Create memory-based prompt optimization
4. Build analytics dashboard for memory insights

## File Structure

```
data/
├── memory/
│   ├── content_memory.db        # SQLite database
│   ├── models/                  # Pickled scikit-learn models
│   │   ├── edit_classifier.pkl
│   │   └── acceptance_predictor.pkl
│   └── backup/                  # Memory backups
src/
├── memory_manager.py           # Main memory implementation
├── memory_analytics.py         # Analysis and reporting
└── memory_models.py           # ML model training and management
```

## Resource Management

### Database Size Control
- Limit feedback history to last 2000 records
- Archive older data to backup files
- Use SQLite indexes for performance
- Compress content storage using TEXT compression

### Model Training Schedule
- Retrain pattern clustering weekly
- Update acceptance predictor after every 50 feedback items
- Refresh quality correlation analysis monthly

### Performance Optimizations
- Cache frequently accessed statistics in memory
- Batch database operations
- Use background threads for ML model training
- Lazy load models only when needed

## Success Metrics

### Short-term (1 month)
- 20% improvement in first-attempt acceptance rate
- Reduced average edit distance by 30%
- Faster content generation due to better prompts

### Long-term (3 months)
- 50% improvement in content quality consistency
- User-specific style adaptation
- Predictive content suggestions with 70%+ accuracy

## Privacy and Data Handling

- All data stored locally on user's machine
- No external API calls for memory functionality
- User can clear memory database at any time
- Memory data excluded from version control (.gitignore)

---

This strategy provides a robust, scalable memory system that learns from user behavior while maintaining simplicity and staying within the constraints of free, local tools.