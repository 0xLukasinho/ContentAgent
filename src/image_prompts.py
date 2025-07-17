"""
Image Prompt Generator for ContentAgent.

This module generates text prompts for AI image generation tools like DALL-E or Midjourney.
These prompts describe visuals that would complement the article content.
"""

import logging
import os
from typing import Dict, List, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.config import OPENAI_MODEL, OUTPUT_DIR, SAMPLES_DIR, get_api_key

logger = logging.getLogger(__name__)

class ImagePromptGenerator:
    """Generates text prompts for AI image generation tools."""
    
    def __init__(self):
        """Initialize the image prompt generator."""
        self.model = ChatOpenAI(
            model=OPENAI_MODEL,
            openai_api_key=get_api_key("OPENAI_API_KEY"),
            temperature=0.7
        )
        
        # Load image style instructions
        self.style_instructions = self._load_style_instructions()
        
        self.image_prompt_template = ChatPromptTemplate.from_template("""
        You are an expert at creating detailed, effective prompts for AI image generation tools like DALL-E and Midjourney.
        
        Create ONE detailed image prompt based on the following content. The prompt should:
        
        1. Describe a single compelling visual that captures the essence of the content
        2. Be highly detailed and specific about style, composition, lighting, mood, etc.
        3. Include specific visual elements that represent the key themes
        4. Be optimized for AI image generators (clear descriptions, not relying on text within images)
        5. Avoid prohibited content (violence, adult content, etc.)
        6. Be 50-100 words in length
        7. IMPORTANT: Incorporate the provided style guidelines throughout the entire prompt
        
        STYLE GUIDELINES TO FOLLOW:
        {style_instructions}
        
        Make sure every aspect of the image prompt (colors, composition, mood, artistic style, etc.) 
        follows these style guidelines while still being relevant to the content.
        
        Provide your response in this format:
        
        ## Image Title
        
        [The detailed prompt text incorporating the style guidelines]
        
        ## Connection to Content
        [1-2 sentences explaining how this visual connects to the content]
        
        Content:
        {content}
        
        Content type:
        {content_type}
        
        Content title/topic:
        {content_title}
        """)
        
        self.image_prompt_chain = self.image_prompt_template | self.model
    
    def _load_style_instructions(self) -> str:
        """
        Load image style instructions from the samples directory.
        
        Returns:
            String containing the style instructions, or default instructions if file not found
        """
        style_file_path = os.path.join(SAMPLES_DIR, "image_style_instructions.txt")
        
        try:
            with open(style_file_path, "r", encoding="utf-8") as f:
                instructions = f.read().strip()
            logger.info(f"Loaded image style instructions from {style_file_path}")
            return instructions
        except FileNotFoundError:
            logger.warning(f"Image style instructions file not found at {style_file_path}. Using default style.")
            return "Use a modern, professional style with clean composition and appropriate colors for business/tech content."
        except Exception as e:
            logger.error(f"Error loading image style instructions: {e}")
            return "Use a modern, professional style with clean composition and appropriate colors for business/tech content."
    
    def generate_image_prompt(self, content: str, content_type: str, content_title: str) -> str:
        """
        Generate an image prompt specific to the provided content.
        
        Args:
            content: The content to base the prompt on
            content_type: Type of content (management_summary, detailed_post, etc.)
            content_title: Title or topic of the content
            
        Returns:
            The generated image prompt
        """
        logger.info(f"Generating image prompt for {content_type}: {content_title}")
        
        # For longer content, use just the first portion to focus the prompt
        content_excerpt = content[:2000] if len(content) > 2000 else content
        
        try:
            result = self.image_prompt_chain.invoke({
                "content": content_excerpt,
                "content_type": content_type,
                "content_title": content_title,
                "style_instructions": self.style_instructions
            })
            return result.content
        except Exception as e:
            logger.error(f"Error generating image prompt: {e}")
            raise
    
    def generate_content_specific_prompts(self, content_items: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        """
        Generate one image prompt for each piece of content.
        
        Args:
            content_items: Dictionary of content items with their metadata
                Format: {
                    "content_type": {
                        "content": str,
                        "title": str,
                        "file_path": str
                    }
                }
            
        Returns:
            Dictionary of content types and their corresponding image prompts
        """
        prompts = {}
        
        for content_type, item in content_items.items():
            if not item.get("content"):
                continue
                
            prompt = self.generate_image_prompt(
                item["content"], 
                content_type, 
                item.get("title", "Untitled")
            )
            
            prompts[content_type] = prompt
        
        return prompts
    
    def save_image_prompts(self, prompts: Dict[str, str], article_title: str, output_dir: str = None) -> str:
        """
        Save the generated image prompts to a file.
        
        Args:
            prompts: Dictionary of content types and their corresponding image prompts
            article_title: The title of the original article
            output_dir: Directory to save the prompts (defaults to config OUTPUT_DIR)
            
        Returns:
            The path to the saved file
        """
        if not output_dir:
            output_dir = os.path.join(OUTPUT_DIR, f"{article_title.replace(' ', '_')}_output")
            
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, "image_prompts.md")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# Image Prompts: {article_title}\n\n")
            
            for content_type, prompt in prompts.items():
                formatted_type = content_type.replace("_", " ").title()
                f.write(f"## For {formatted_type}\n\n")
                f.write(prompt)
                f.write("\n\n---\n\n")
            
        logger.info(f"Image prompts saved to {output_path}")
        return output_path 