"""
Detailed Post Generator for ContentAgent.

This module generates substantive, long-form social media posts from key arguments.
"""

import os
import re
import glob
import random
import logging
from typing import Dict, List, Tuple, Optional, Any, Union

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from colorama import Fore, Style

from src.config import OPENAI_MODEL, get_api_key

logger = logging.getLogger(__name__)

class DetailedPostGenerator:
    """Generates substantive, long-form social media posts from key arguments."""
    
    def __init__(self, samples_dir: str = "data/samples"):
        """
        Initialize the detailed post generator.
        
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
        
        self.detailed_post_prompt = ChatPromptTemplate.from_template("""
You are to write a detailed, substantive post based on the article below.

Before writing, you must carefully analyze and internalize the provided writing instructions and sample posts. Your output must strictly follow ALL instructions and match the style, formatting, and voice demonstrated in the samples. Do not ignore, reinterpret, or generalize any instruction—treat deviation as an error.

Do NOT include any analysis, blueprint, or explanation in your output—ONLY output the post itself.

Be as exhaustive and detailed as the article requires. Do not leave out important points, context, or supporting information. Do not artificially shorten the post; cover all relevant nuances and details.

SAMPLES:
{sample_posts}

INSTRUCTIONS:
{style_instructions}

ARGUMENT:
{argument}

MAIN ARTICLE CONTENT:
{context}

{additional_context_instructions}

POST:
(Write the post, following the instructions and samples exactly)
""")
        
        self.post_batch_prompt = ChatPromptTemplate.from_template("""
You are to write a detailed, substantive post for each key argument based on the article below.

Before writing, you must carefully analyze and internalize the provided writing instructions and sample posts. Your output must strictly follow ALL instructions and match the style, formatting, and voice demonstrated in the samples. Do not ignore, reinterpret, or generalize any instruction—treat deviation as an error.

Do NOT include any analysis, blueprint, or explanation in your output—ONLY output the posts themselves.

Be as exhaustive and detailed as the article requires. Do not leave out important points, context, or supporting information for any argument. Do not artificially shorten any post; cover all relevant nuances and details for each argument.

SAMPLES:
{sample_posts}

INSTRUCTIONS:
{style_instructions}

KEY ARGUMENTS TO EXPLORE (create one post for each):
{arguments}

MAIN ARTICLE CONTENT:
{context}

{additional_context_instructions}

Format your response with each post separated by triple hyphens (---), with the argument listed as a heading before each post. DO NOT include prefatory text like "Here's a post about..." - start directly with the content of each post.
""")
        
        self.detailed_post_chain = self.detailed_post_prompt | self.model
        self.post_batch_chain = self.post_batch_prompt | self.model
        
    def load_writing_instructions(self) -> str:
        """
        Load writing instructions for detailed posts.
        
        Returns:
            Writing instructions as a string
        """
        # Try to load specific instructions for posts
        instructions_path = os.path.join(self.samples_dir, "writing_instructions_post.txt")
        
        if os.path.exists(instructions_path):
            with open(instructions_path, "r", encoding="utf-8") as f:
                return f.read()
        
        # Default instructions if file not found
        return """
        Write in a substantive, informative, and conversational style. Cover each argument with depth, detail, and context, drawing on all relevant information from the article.
        Begin each post with a unique, creative, and contextually relevant hook/opening line tailored to the argument and post content. Take inspiration from user-provided sample posts if available, but always generate original hooks—do not use static or repeated templates.
        Use data points and examples to support key arguments. Balance expertise with accessibility. End with thought-provoking questions or calls to action.
        Do not use hashtags or emojis in any part of the content. Do not use markdown formatting (no headings, bullet points, etc.).
        Structure content for readability on social media.
        """
    
    def load_post_samples(self, max_samples: int = 2) -> str:
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
        formatted_samples = "Reference these example posts that match the user's writing style:\n\n"
        
        for i, sample in enumerate(samples):
            formatted_samples += f"EXAMPLE POST {i+1}:\n{sample}\n\n"
            
        return formatted_samples
    
    def _prepare_additional_context_instructions(self, additional_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Prepare instructions for incorporating additional context.
        
        Args:
            additional_context: Optional additional context documents
            
        Returns:
            Instructions for using additional context
        """
        if not additional_context or not additional_context.get("has_context", False):
            return "No additional context is available for this post."
        
        content = additional_context.get("content", "")
        if not content:
            return "No additional context is available for this post."
        
        return f"""
        Additional context is provided below. Naturally incorporate relevant information from this context into your post
        when appropriate, without explicitly mentioning or citing this additional context. Treat it as background knowledge.
        
        Additional context:
        {content}
        """
    
    def _clean_output(self, text: str) -> str:
        """
        Clean up the generated output.
        
        Args:
            text: Raw generated text
            
        Returns:
            Cleaned text
        """
        # Remove any markdown headers that might have been added
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        
        # Remove hashtags
        text = re.sub(r'#\w+', '', text)
        
        # Remove any prefatory statements like "Here's a post about..."
        text = re.sub(r'^Here\'s\s+a\s+(detailed\s+)?(post|article|thread)\s+about\s+.*?:\s*', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Trim and clean
        return text.strip()
    
    def generate_post_for_argument(
        self, 
        argument: str, 
        context: str, 
        custom_instructions: str = "", 
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a detailed social media post for a specific key argument.
        
        Args:
            argument: The key argument to create a post for
            context: The full article content for reference
            custom_instructions: Custom style instructions
            additional_context: Optional additional context documents
            
        Returns:
            The generated detailed post
        """
        logger.info(f"Generating detailed post for argument: {argument[:30]}...")
        style_instructions = self.load_writing_instructions()
        sample_posts = self.load_post_samples()
        if custom_instructions:
            style_instructions = f"{style_instructions}\n\nAdditional instructions: {custom_instructions}"
        additional_context_instructions = self._prepare_additional_context_instructions(additional_context)
        try:
            result = self.detailed_post_chain.invoke({
                "argument": argument,
                "context": context,
                "style_instructions": style_instructions,
                "sample_posts": sample_posts,
                "additional_context_instructions": additional_context_instructions
            })
            clean_result = self._clean_output(result.content)
            return clean_result
        except Exception as e:
            logger.error(f"Error generating detailed post: {e}")
            raise

    def generate_detailed_posts(
        self, 
        arguments: List[str], 
        context: str, 
        custom_instructions: str = "", 
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Generate detailed social media posts for multiple key arguments.
        
        Args:
            arguments: List of key arguments to create posts for
            context: The full article content for reference
            custom_instructions: Custom style instructions
            additional_context: Optional additional context documents
            
        Returns:
            Dictionary mapping arguments to their generated posts
        """
        logger.info(f"Generating detailed posts for {len(arguments)} arguments")
        style_instructions = self.load_writing_instructions()
        sample_posts = self.load_post_samples()
        if custom_instructions:
            style_instructions = f"{style_instructions}\n\nAdditional instructions: {custom_instructions}"
        additional_context_instructions = self._prepare_additional_context_instructions(additional_context)
        # For a small number of arguments, generate posts one by one for better quality
        if len(arguments) <= 3:
            posts = {}
            for argument in arguments:
                post = self.generate_post_for_argument(
                    argument, 
                    context, 
                    custom_instructions,
                    additional_context
                )
                posts[argument] = post
            return posts
        # For larger batches, use a batch processing approach
        try:
            arguments_text = "\n\n".join([f"- {arg}" for arg in arguments])
            result = self.post_batch_chain.invoke({
                "arguments": arguments_text,
                "context": context,
                "style_instructions": style_instructions,
                "sample_posts": sample_posts,
                "additional_context_instructions": additional_context_instructions
            })
            # Parse the batch result into individual posts
            return self._parse_batch_posts(result.content, arguments)
        except Exception as e:
            logger.error(f"Error generating detailed posts batch: {e}")
            raise

    def _parse_batch_posts(self, batch_content: str, arguments: List[str]) -> Dict[str, str]:
        """
        Parse batch post content into individual posts.
        
        Args:
            batch_content: The batch post content
            arguments: List of key arguments
            
        Returns:
            Dictionary mapping arguments to their generated posts
        """
        # Split by triple hyphens
        post_segments = re.split(r'---+', batch_content)
        posts = {}
        
        # Clean segments and assign to arguments
        cleaned_segments = [self._clean_output(segment) for segment in post_segments if segment.strip()]
        
        # Match segments to arguments - this can be complex
        # First, try to match based on the heading/first line
        for segment in cleaned_segments:
            matched = False
            
            # Check if any argument appears in the beginning of the segment
            for arg in arguments:
                # Check only the first ~150 chars to see if argument is mentioned prominently
                shortened_arg = arg[:50].strip()
                if shortened_arg and shortened_arg.lower() in segment[:150].lower():
                    posts[arg] = segment
                    matched = True
                    break
            
            # If no match found, we'll add it to an unmatched list
            if not matched and arguments:
                # Assign to any argument that doesn't have a post yet
                for arg in arguments:
                    if arg not in posts:
                        posts[arg] = segment
                        break
        
        # Ensure all arguments are covered
        for i, arg in enumerate(arguments):
            if arg not in posts and cleaned_segments:
                # If we have remaining cleaned segments, use those
                if i < len(cleaned_segments):
                    posts[arg] = cleaned_segments[i]
                # Otherwise just generate a simple placeholder
                # (this shouldn't normally happen)
                else:
                    posts[arg] = f"Post about {arg[:50]}... [Error: No content generated]"
        
        return posts
    
    def revise_post(
        self, 
        original_post: str, 
        argument: str, 
        context: str, 
        feedback: str,
        custom_instructions: str = "",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Revise a detailed post based on user feedback.
        
        Args:
            original_post: The original generated post
            argument: The key argument the post is about
            context: The full article content
            feedback: User feedback for revision
            custom_instructions: Custom style instructions
            additional_context: Optional additional context documents
            
        Returns:
            The revised post
        """
        logger.info(f"Revising post for argument: {argument[:30]}...")
        style_instructions = self.load_writing_instructions()
        sample_posts = self.load_post_samples(max_samples=1)
        if custom_instructions:
            style_instructions = f"{style_instructions}\n\nAdditional instructions: {custom_instructions}"
        additional_context_instructions = self._prepare_additional_context_instructions(additional_context)
        try:
            result = self.revision_chain.invoke({
                "original_post": original_post,
                "argument": argument,
                "context": context,
                "feedback": feedback,
                "style_instructions": style_instructions,
                "sample_posts": sample_posts,
                "additional_context_instructions": additional_context_instructions
            })
            clean_result = self._clean_output(result.content)
            return clean_result
        except Exception as e:
            logger.error(f"Error revising post: {e}")
            raise

    def save_posts(self, posts: Dict[str, str], article_title: str, output_dir: str) -> str:
        """
        Save the generated detailed posts to a file.
        
        Args:
            posts: Dictionary mapping arguments to their posts
            article_title: The title of the original article
            output_dir: Directory to save the posts
            
        Returns:
            Path to the saved file
        """
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, "detailed_posts.md")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# Detailed Social Media Posts: {article_title}\n\n")
            
            for i, (argument, post) in enumerate(posts.items()):
                f.write(f"## Key Argument {i+1}\n\n")
                f.write(f"**{argument}**\n\n")
                f.write(f"{post}\n\n")
                if i < len(posts) - 1:
                    f.write("---\n\n")
            
        logger.info(f"Detailed posts saved to {output_path}")
        print(f"{Fore.GREEN}Detailed posts saved to: {output_path}{Style.RESET_ALL}")
        
        return output_path

    def save_individual_post(self, argument: str, post_content: str, article_title: str, output_dir: str) -> str:
        """
        Save a single detailed post to a file.
        
        Args:
            argument: The key argument for the post
            post_content: The content of the post
            article_title: The title of the original article
            output_dir: Directory to save the post
            
        Returns:
            Path to the saved file
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a safe filename from the argument
        import re
        safe_arg = re.sub(r'[^\w\s-]', '', argument[:40]).strip().replace(' ', '_').lower()
        if not safe_arg:
            safe_arg = "detailed_post"
        
        # Add timestamp for uniqueness
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        output_path = os.path.join(output_dir, f"post_{safe_arg}_{timestamp}.md")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# Detailed Post: {article_title}\n\n")
            f.write(f"## Key Argument\n\n")
            f.write(f"**{argument}**\n\n")
            f.write(f"{post_content}\n")
        
        logger.info(f"Detailed post saved to {output_path}")
        print(f"{Fore.GREEN}Detailed post saved to: {output_path}{Style.RESET_ALL}")
        
        return output_path 