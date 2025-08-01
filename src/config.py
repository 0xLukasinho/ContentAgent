"""
Configuration management for ContentAgent.
Centralizes loading of environment variables and application settings.
"""
import os
import sys
from dotenv import load_dotenv

# Get absolute path to the .env file
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Try to load environment variables from .env file
if os.path.exists(env_path):
    try:
        # Use dotenv to load environment variables
        load_dotenv(dotenv_path=env_path, override=True, encoding="utf-8-sig")
    except Exception as e:
        print(f"Warning: Error loading .env with dotenv: {e}")
        
        # Manual parsing as backup
        try:
            with open(env_path, 'r', encoding="utf-8-sig") as f:
                content = f.read()
                # Parse the .env file manually to handle any format issues
                for line in content.splitlines():
                    if line and not line.startswith('#'):
                        try:
                            key, value = line.strip().split('=', 1)
                            os.environ[key.strip()] = value.strip()
                        except Exception:
                            pass
        except Exception:
            print("Warning: Could not parse .env file")

# No fallback - API keys must be provided via environment variables

# Get the API key from environment
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Validate required keys
if not OPENAI_API_KEY:
    print("\nERROR: OpenAI API key not found in environment variables.")
    print("Make sure your .env file contains a line like:")
    print("OPENAI_API_KEY=your_openai_key_here")
    print(f"Current .env file path: {env_path}")
    sys.exit(1)

# Model settings
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini-2025-04-14"  # User requested 'mini' variant
OPENAI_MODEL = DEFAULT_OPENAI_MODEL  # Export as the standard model name

# File paths
INPUT_DIR = os.path.join("data", "input")
OUTPUT_DIR = os.path.join("data", "output")
SAMPLES_DIR = os.path.join("data", "samples")
MEMORY_DIR = os.path.join("data", "memory")

# Valid file extensions for articles
VALID_EXTENSIONS = [".txt", ".md", ".docx", ".pdf"]

# Memory system settings
MEMORY_DATABASE_PATH = os.path.join(MEMORY_DIR, "content_agent_memory.db")
MEMORY_MAX_RECORDS = 2000
MEMORY_ENABLED = True

# Create required directories
for directory in [INPUT_DIR, OUTPUT_DIR, SAMPLES_DIR, MEMORY_DIR]:
    os.makedirs(directory, exist_ok=True)

class Config:
    """Configuration class for ContentAgent."""
    
    def __init__(self):
        self.openai_api_key = OPENAI_API_KEY
        self.openai_model = OPENAI_MODEL
        self.data_dir = "data"
        self.input_dir = INPUT_DIR
        self.output_dir = OUTPUT_DIR
        self.samples_dir = SAMPLES_DIR
        self.memory_dir = MEMORY_DIR
        self.memory_database_path = MEMORY_DATABASE_PATH
        self.memory_max_records = MEMORY_MAX_RECORDS
        self.memory_enabled = MEMORY_ENABLED
        self.valid_extensions = VALID_EXTENSIONS

def get_api_key(key_name: str) -> str:
    """
    Get the specified API key from environment variables.
    
    Args:
        key_name: Name of the API key to retrieve
        
    Returns:
        API key value
        
    Raises:
        ValueError: If the API key is not found
    """
    api_key = os.environ.get(key_name)
    
    if not api_key:
        raise ValueError(f"{key_name} not found in environment variables.")
    
    return api_key 