"""
Context Processor for ContentAgent.

This module handles the loading and processing of additional context files
that provide supplementary information for generating better content.
"""

import os
import glob
import logging
from typing import List, Dict, Any

from docx import Document
from colorama import Fore, Style

from src.config import VALID_EXTENSIONS

logger = logging.getLogger(__name__)

class ContextProcessor:
    """
    Loads and processes additional context files to enhance content generation.
    """
    
    def __init__(self, context_dir: str = os.path.join("data", "input", "additional_content")):
        """
        Initialize the context processor.
        
        Args:
            context_dir: Directory containing additional context files
        """
        self.context_dir = context_dir
        
        # Create the directory if it doesn't exist
        os.makedirs(context_dir, exist_ok=True)
    
    def get_available_context_files(self) -> List[str]:
        """
        Get list of available context files in the context directory.
        
        Returns:
            List of file paths
        """
        context_files = []
        
        # Find files with supported extensions
        for ext in [".txt", ".md", ".docx"]:
            context_files.extend(glob.glob(os.path.join(self.context_dir, f"*{ext}")))
        
        return sorted(context_files)
    
    def process_context_files(self) -> Dict[str, Any]:
        """
        Load and process all available context files.
        
        Returns:
            Dictionary with combined context content and metadata
        """
        context_files = self.get_available_context_files()
        
        if not context_files:
            logger.info("No additional context files found")
            print(f"{Fore.YELLOW}No additional context files found in {self.context_dir}{Style.RESET_ALL}")
            return {"content": "", "files": [], "has_context": False}
        
        # Process each file
        context_contents = []
        processed_files = []
        
        for file_path in context_files:
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            
            try:
                # Process different file types
                if file_ext == ".docx":
                    content = self._extract_docx_content(file_path)
                else:  # .txt or .md
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                
                # Add file metadata
                processed_files.append({
                    "path": file_path,
                    "name": file_name,
                    "size": os.path.getsize(file_path)
                })
                
                # Format content with file name as header
                formatted_content = f"--- CONTEXT DOCUMENT: {file_name} ---\n\n{content}\n\n"
                context_contents.append(formatted_content)
                
                logger.info(f"Processed context file: {file_name}")
            
            except Exception as e:
                logger.error(f"Error processing context file {file_name}: {e}")
                print(f"{Fore.RED}Error processing context file {file_name}: {e}{Style.RESET_ALL}")
        
        # Combine all context content
        combined_content = "\n".join(context_contents)
        
        if combined_content:
            print(f"{Fore.GREEN}Loaded {len(processed_files)} additional context files{Style.RESET_ALL}")
            
            # Print file names
            for idx, file_info in enumerate(processed_files, 1):
                print(f"  {idx}. {file_info['name']}")
        
        return {
            "content": combined_content,
            "files": processed_files,
            "has_context": bool(combined_content)
        }
    
    def _extract_docx_content(self, file_path: str) -> str:
        """
        Extract text content from a DOCX file.
        
        Args:
            file_path: Path to the DOCX file
            
        Returns:
            Extracted text content
        """
        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs) 