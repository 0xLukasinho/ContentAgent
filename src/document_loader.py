"""
Document loader for the ContentAgent system.
Handles loading and parsing of Markdown and DOCX files.
"""
import os
import datetime
from typing import Dict, List, Optional, Union

class DocumentProcessor:
    """
    Handles loading and processing documents for the ContentAgent system.
    Currently supports Markdown and DOCX files.
    """
    
    def __init__(self):
        """Initialize the document processor."""
        pass
    
    def process_document(self, file_path: str) -> Dict[str, str]:
        """
        Load and process a document as a single entity without chunking.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary with document content and metadata
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Extract basic metadata
        file_name = os.path.basename(file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        file_title = os.path.splitext(file_name)[0].replace('_', ' ').title()
        
        # Process based on file type
        if file_extension == '.md':
            content = self._load_markdown(file_path)
        elif file_extension == '.docx':
            content = self._load_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}. Supported formats: .md, .docx")
        
        # Extract title from content if available
        article_title = self._extract_title(content) or file_title
        
        # Create a timestamp for this processing run
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return {
            "content": content,
            "title": article_title,
            "file_path": file_path,
            "file_name": file_name,
            "processed_at": timestamp
        }
    
    def _load_markdown(self, file_path: str) -> str:
        """Load content from a Markdown file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def _load_docx(self, file_path: str) -> str:
        """Load content from a DOCX file."""
        import docx2txt
        return docx2txt.process(file_path)
    
    def _extract_title(self, content: str) -> Optional[str]:
        """
        Extract title from document content.
        
        Returns:
            Extracted title or None if no title found
        """
        # Look for # Title or similar at the beginning
        lines = content.strip().split('\n')
        if lines and lines[0].startswith('#'):
            return lines[0].lstrip('#').strip()
        return None 