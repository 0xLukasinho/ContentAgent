"""
Content Formatter for ContentAgent.

This module improves the formatting and styling of generated content
to make it more engaging, readable, and consistent.
"""

import logging
import re
from typing import Dict, List, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.config import OPENAI_MODEL, get_api_key

logger = logging.getLogger(__name__)

class ContentFormatter:
    """Formats and styles generated content for improved readability and engagement."""
    
    def __init__(self):
        """Initialize the content formatter."""
        self.model = ChatOpenAI(
            model=OPENAI_MODEL,
            openai_api_key=get_api_key("OPENAI_API_KEY"),
            temperature=0.3
        )
        
        self.format_prompt = ChatPromptTemplate.from_template("""
        You are an expert content editor who improves the formatting, styling, and readability of text.
        
        Enhance the following content by:
        1. Improving paragraph structure and flow
        2. Adding clear section headings where appropriate
        3. Incorporating bullet points or numbered lists for clarity
        4. Ensuring consistent formatting throughout
        5. Maintaining the original meaning and information
        6. Optimizing for the intended platform: {platform}
        
        Content:
        {content}
        
        Style preferences (if any):
        {style_preferences}
        """)
        
        self.format_chain = self.format_prompt | self.model
    
    def format_content(self, content: str, platform: str = "Twitter", style_preferences: str = "") -> str:
        """
        Format and style the provided content.
        
        Args:
            content: The content to format
            platform: The target platform for the content
            style_preferences: Optional style preferences
            
        Returns:
            The formatted content
        """
        logger.info(f"Formatting content for {platform}")
        
        try:
            result = self.format_chain.invoke({
                "content": content,
                "platform": platform,
                "style_preferences": style_preferences
            })
            return result.content
        except Exception as e:
            logger.error(f"Error formatting content: {e}")
            raise
    
    def add_emoji(self, content: str, frequency: str = "moderate") -> str:
        """
        Add appropriate emojis to the content.
        
        Args:
            content: The content to add emojis to
            frequency: Emoji frequency (low, moderate, high)
            
        Returns:
            Content with added emojis
        """
        emoji_prompt = ChatPromptTemplate.from_template("""
        You are an expert at enhancing content with appropriate emojis.
        
        Add emojis to the following content. The emoji usage should be:
        - Frequency: {frequency} (low: only 1-2 key points, moderate: main sections, high: throughout)
        - Relevant to the content they accompany
        - Not overused or distracting
        - Placed at the beginning of key points or sections, not randomly in sentences
        
        Content:
        {content}
        """)
        
        emoji_chain = emoji_prompt | self.model
        
        try:
            result = emoji_chain.invoke({
                "content": content,
                "frequency": frequency
            })
            return result.content
        except Exception as e:
            logger.error(f"Error adding emojis: {e}")
            return content  # Return original content if emoji addition fails
    
    def improve_readability(self, content: str) -> str:
        """
        Improve the readability of the content.
        
        Args:
            content: The content to improve
            
        Returns:
            Content with improved readability
        """
        # Basic readability improvements
        improved = content
        
        # Break up very long paragraphs (more than 6 sentences)
        paragraphs = improved.split("\n\n")
        result_paragraphs = []
        
        for para in paragraphs:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            if len(sentences) > 6:
                # Split into smaller paragraphs of 3-4 sentences
                new_paras = []
                for i in range(0, len(sentences), 4):
                    new_paras.append(" ".join(sentences[i:i+4]))
                result_paragraphs.extend(new_paras)
            else:
                result_paragraphs.append(para)
        
        improved = "\n\n".join(result_paragraphs)
        
        # Replace very long words with simpler alternatives using LLM
        if len(re.findall(r'\b\w{15,}\b', improved)) > 3:
            simplify_prompt = ChatPromptTemplate.from_template("""
            Improve this text by replacing overly complex words with simpler alternatives.
            Focus on clarity and readability without changing the meaning.
            
            Text:
            {text}
            """)
            
            simplify_chain = simplify_prompt | self.model
            
            try:
                result = simplify_chain.invoke({"text": improved})
                improved = result.content
            except Exception as e:
                logger.error(f"Error simplifying text: {e}")
        
        return improved 