"""
Article Summary Generator for ContentAgent.

This module generates objective, factual summaries of articles
that present the key points without adding recommendations or analysis.
"""

import logging
import os
import glob
import random
from typing import Dict, Any, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.config import OPENAI_MODEL, OUTPUT_DIR, get_api_key
from colorama import Fore, Style

logger = logging.getLogger(__name__)

class ArticleSummaryGenerator:
    """Generates factual, objective summaries of articles."""
    
    def __init__(self, samples_dir: str = "data/samples"):
        """
        Initialize the article summary generator.
        
        Args:
            samples_dir: Directory containing writing samples and instructions
        """
        # Set samples directories
        self.samples_dir = samples_dir
        self.post_samples_dir = os.path.join(samples_dir, "sample_posts")
        
        # Create sample directories if they don't exist
        os.makedirs(self.post_samples_dir, exist_ok=True)
        
        # Initialize the LLM (OpenAI)
        self.model = ChatOpenAI(
            model=OPENAI_MODEL,
            openai_api_key=get_api_key("OPENAI_API_KEY"),
            temperature=0.7  # Increased for more creative, less generic output
        )
        
        self.summary_prompt = ChatPromptTemplate.from_template("""
You are to write a detailed, substantive post based on the article below.

Before writing, you must carefully analyze and internalize the provided writing instructions and sample posts. Your output must strictly follow ALL instructions and match the style, formatting, and voice demonstrated in the samples. Do not ignore, reinterpret, or generalize any instruction—treat deviation as an error.

Do NOT include any analysis, blueprint, or explanation in your output—ONLY output the post itself.

Be as exhaustive and detailed as the article requires. Do not leave out important points, context, or supporting information. Do not artificially shorten the post; cover all relevant nuances and details.

SAMPLES:
{sample_posts}

INSTRUCTIONS:
{style_instructions}

ARTICLE:
{content}

POST:
(Write the post, following the instructions and samples exactly)
""")
        
        self.revision_prompt = ChatPromptTemplate.from_template("""
        You previously created a factual, objective summary of an article.
        
        {style_instructions}
        
        {sample_posts}
        
        Original summary:
        {original_summary}
        
        Please revise the summary based on the following feedback:
        {feedback}
        
        Remember, the summary should:
        1. Begin with a concise overview of the article
        2. Cover the main points and key details in a logical flow
        3. Use clear, straightforward language
        4. Be factual and objective - only include information from the article
        5. Be well-structured with clear paragraphs for readability
        6. Do NOT use any markdown formatting (no headings, bullet points, etc.)
        7. Do NOT use hashtags or emojis
        8. Keep the summary to approximately 400-600 words
        
        Article:
        {content}
        """)
        
        self.summary_chain = self.summary_prompt | self.model
        self.revision_chain = self.revision_prompt | self.model
    
    def load_writing_instructions(self) -> str:
        """
        Load writing instructions for post content.
        
        Returns:
            Writing instructions as a string
        """
        # Try to load specific instructions for post
        instructions_path = os.path.join(self.samples_dir, "writing_instructions_post.txt")
        
        if os.path.exists(instructions_path):
            with open(instructions_path, "r", encoding="utf-8") as f:
                return f.read()
        
        # Default instructions if file not found
        return """
        Write in a substantive, informative, and engaging style. Cover all major points, arguments, and details from the article, ensuring depth, nuance, and completeness. Err on the side of including more detail for rich articles.
        Start with a strong, contextually relevant opening that sets up the summary. If user sample posts are available, take inspiration from their style, but always generate an original summary tailored to the current article.
        Use clear, straightforward language. Be factual and objective—only include information that's actually in the article. Do not add any new insights, recommendations, or analysis.
        Do not use hashtags or emojis in any part of the content. Do not use markdown formatting (no headings, bullet points, etc.).
        There is no strict word limit; be as comprehensive as needed to do justice to the article's richness.
        Structure content for readability.
        """
    
    def load_post_samples(self, max_samples: int = 1) -> str:
        """
        Load post samples from the samples directory.
        
        Args:
            max_samples: Maximum number of samples to include
            
        Returns:
            String with sample posts formatted for the prompt
        """
        samples = []
        sample_files = glob.glob(os.path.join(self.post_samples_dir, "*.txt"))
        sample_files.extend(glob.glob(os.path.join(self.post_samples_dir, "*.md")))
        
        # Shuffle files to get variety if we have more than max_samples
        random.shuffle(sample_files)
        
        count = 0
        for file_path in sample_files:
            if not os.path.basename(file_path).startswith("writing_instructions_"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            samples.append(content)
                            count += 1
                            logger.info(f"Loaded post sample from {file_path} ({len(content)} chars)")
                            if count >= max_samples:
                                break
                except Exception as e:
                    logger.error(f"Error loading sample {file_path}: {e}")
        
        if not samples:
            return ""
        
        # Format the samples for inclusion in the prompt
        formatted_samples = "Reference these example posts that match the user's writing style for tone and structure (though your summary should be purely factual):\n\n"
        
        for i, sample in enumerate(samples):
            formatted_samples += f"EXAMPLE POST {i+1}:\n{sample}\n\n"
            
        return formatted_samples
    
    def generate_summary(self, content: str, custom_instructions: str = "") -> str:
        """
        Generate a factual, objective summary of the article.
        
        Args:
            content: The article content to summarize
            custom_instructions: Any additional custom instructions
            
        Returns:
            The generated summary
        """
        logger.info("Generating article summary")
        
        # Load writing instructions and samples
        style_instructions = self.load_writing_instructions()
        sample_posts = self.load_post_samples(max_samples=2)
        
        # Add any custom instructions
        if custom_instructions:
            style_instructions = f"{style_instructions}\n\nAdditional instructions: {custom_instructions}"
        
        try:
            result = self.summary_chain.invoke({
                "content": content,
                "style_instructions": style_instructions,
                "sample_posts": sample_posts
            })
            return result.content
        except Exception as e:
            logger.error(f"Error generating article summary: {e}")
            raise
    
    def revise_summary(self, original_summary: str, content: str, feedback: str, custom_instructions: str = "") -> str:
        """
        Revise an article summary based on user feedback.
        
        Args:
            original_summary: The original generated summary
            content: The article content
            feedback: User feedback for revision
            custom_instructions: Any additional custom instructions
            
        Returns:
            The revised summary
        """
        logger.info("Revising article summary based on feedback")
        
        # Load writing instructions and samples
        style_instructions = self.load_writing_instructions()
        sample_posts = self.load_post_samples()
        
        # Add any custom instructions
        if custom_instructions:
            style_instructions = f"{style_instructions}\n\nAdditional instructions: {custom_instructions}"
        
        try:
            result = self.revision_chain.invoke({
                "original_summary": original_summary,
                "content": content,
                "feedback": feedback,
                "style_instructions": style_instructions,
                "sample_posts": sample_posts
            })
            return result.content
        except Exception as e:
            logger.error(f"Error revising article summary: {e}")
            raise
    
    def save_summary(self, summary: str, article_title: str, output_dir: str) -> Dict[str, Any]:
        """
        Save the generated summary to a file.
        
        Args:
            summary: The generated summary
            article_title: The title of the original article
            output_dir: Directory to save the summary
            
        Returns:
            Dictionary with file path and content
        """
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, "article_summary.md")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# Summary: {article_title}\n\n")
            f.write(summary)
        
        logger.info(f"Article summary saved to {output_path}")
        print(f"{Fore.GREEN}Article summary saved to: {output_path}{Style.RESET_ALL}")
        
        return {
            "file_path": output_path,
            "content": summary
        } 