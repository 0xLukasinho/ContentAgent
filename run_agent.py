#!/usr/bin/env python
"""
New entry point script for ContentAgent.
Properly uses centralized configuration management.
"""
import os
import sys

# Import config first to ensure environment is set up
from src.config import INPUT_DIR

# Create a sample article if none exist
md_files = os.listdir(INPUT_DIR)
if not any(f.endswith('.md') or f.endswith('.docx') for f in md_files):
    print("Creating sample article in input directory...")
    with open(os.path.join(INPUT_DIR, "sample_article.md"), "w", encoding="utf-8") as f:
        f.write("# Sample Article\n\nThis is a sample article created by ContentAgent.")

# Import and run the main function
from src.main import main

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc() 