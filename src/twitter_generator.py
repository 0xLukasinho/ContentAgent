"""
Thread Generator for ContentAgent.
Uses Anthropic's Claude model to generate social media threads from articles.
"""
import os
import glob
import re
from typing import Dict, List, Optional, Union

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document
import logging

# Import from centralized config
from src.config import OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger(__name__)

# Default templates
DEFAULT_THREAD_SYSTEM_PROMPT = """You are a social media content creator."""

DEFAULT_THREAD_PROMPT = """
You are to write a social media thread about the article below.

Your #1 goal is to emulate the style, formatting, and persona of the provided sample threads as closely as possible. Your #2 goal is to follow the writing instructions.

Analyze the sample threads and instructions internally, but ONLY output the thread itself—do NOT include any analysis or blueprint in your output.

You may use up to 25 tweets if needed to fully cover the article. There is no need to hit 25, but do not artificially stop early. Be as exhaustive and detailed as the article and samples require.

Explicitly cover all major points, arguments, and nuanced details from the article—do not leave out important information.

The thread must:
- Closely match the sample's formatting (segment length, separators, line breaks, etc.)
- Match the sample's voice and persona
- Use the writing instructions as secondary rules
- Avoid generic, formulaic, or AI-style output
- Only use hook styles (like 'Unpopular take:') if they are genuinely contextually appropriate for the content

SAMPLES:
{sample_threads}

INSTRUCTIONS:
{style_instructions}

ARTICLE:
{article_text}

THREAD:
(Write the thread, following the blueprint)
"""

class TwitterThreadGenerator:
    """
    Generates social media threads from articles using Anthropic's Claude model.
    """
    
    def __init__(
        self,
        system_prompt: Optional[str] = None,
        thread_prompt: Optional[str] = None,
        model_name: str = OPENAI_MODEL,
        samples_dir: str = "data/samples",
        memory_manager=None
    ): 
        """
        Initialize the thread generator.
        
        Args:
            system_prompt: Custom system prompt for the LLM
            thread_prompt: Custom prompt template for thread generation
            model_name: Anthropic model to use
            samples_dir: Directory containing writing samples and instructions
        """
        # Set samples directories
        self.samples_dir = samples_dir
        self.thread_samples_dir = os.path.join(samples_dir, "sample_threads")
        self.memory_manager = memory_manager
        
        # Create sample directories if they don't exist
        os.makedirs(self.thread_samples_dir, exist_ok=True)
        
        # Initialize the LLM (OpenAI)
        self.llm = ChatOpenAI(
            model=OPENAI_MODEL,
            openai_api_key=OPENAI_API_KEY,
            temperature=0.7  # Increased for more creative, less generic output
        )
        
        # Set prompt templates
        self.system_prompt = system_prompt or DEFAULT_THREAD_SYSTEM_PROMPT
        self.thread_prompt_template = PromptTemplate(
            input_variables=["article_text", "style_instructions", "sample_threads"],
            template=thread_prompt or DEFAULT_THREAD_PROMPT
        )
        
        # Create the chain
        self.chain = (
            {
                "article_text": RunnablePassthrough(), 
                "style_instructions": RunnablePassthrough(),
                "sample_threads": RunnablePassthrough()
            }
            | self.thread_prompt_template
            | self.llm
            | StrOutputParser()
        )
    
    def load_writing_instructions(self) -> str:
        """
        Load writing instructions for thread content.
        
        Returns:
            Writing instructions as a string
        """
        # Try to load specific instructions for thread
        instructions_path = os.path.join(self.samples_dir, "writing_instructions_thread.txt")
        
        if os.path.exists(instructions_path):
            with open(instructions_path, "r", encoding="utf-8") as f:
                return f.read()
        
        # Default instructions if file not found
        return """
        Write in a clear, engaging, and informative style. Cover all major points, arguments, and details from the article, ensuring depth, nuance, and completeness.
        Start the thread with a unique, creative, and contextually relevant hook that grabs attention. For each segment, craft an original, compelling opening line inspired by the article's content and, if available, the user's sample threads. Avoid repeating hook templates—each segment's hook should be distinct and tailored.
        Allow as many segments as needed to fully represent the article's richness—do not restrict yourself to a set number. Each segment should be clear, engaging, and under 280 characters, but prioritize substance and informativeness over brevity.
        Do not use hashtags or emojis. Do not number the segments. Separate each segment with a line of dashes (------).
        """
    
    def load_thread_samples(self, max_samples: int = 3) -> str:
        """
        Load thread samples from the samples directory.
        
        Args:
            max_samples: Maximum number of samples to include
            
        Returns:
            String with sample threads formatted for the prompt
        """
        samples = []
        sample_files = glob.glob(os.path.join(self.thread_samples_dir, "*.txt"))
        sample_files.extend(glob.glob(os.path.join(self.thread_samples_dir, "*.md")))
        
        # Shuffle files to get variety if we have more than max_samples
        import random
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
                            logger.info(f"Loaded thread sample from {file_path} ({len(content)} chars)")
                            if count >= max_samples:
                                break
                except Exception as e:
                    logger.error(f"Error loading sample {file_path}: {e}")
        
        if not samples:
            return ""
        
        # Format the samples for inclusion in the prompt
        formatted_samples = "Reference these example threads that match the user's writing style:\n\n"
        
        for i, sample in enumerate(samples):
            formatted_samples += f"EXAMPLE THREAD {i+1}:\n{sample}\n\n"
            
        return formatted_samples
    
    def generate_thread(
        self,
        article_text: str,
        custom_instructions: str = ""
    ) -> str:
        """
        Generate a thread from the provided article text.
        
        Args:
            article_text: Text of the article to convert into a thread
            custom_instructions: Any additional custom instructions
            
        Returns:
            Generated thread as a string
        """
        # Load writing instructions and samples
        style_instructions = self.load_writing_instructions()
        sample_threads = self.load_thread_samples()
        
        # Add any custom instructions
        if custom_instructions:
            style_instructions = f"{style_instructions}\n\nAdditional instructions: {custom_instructions}"
        
        # Add memory-based enhancements if available
        if self.memory_manager:
            memory_enhancements = self.memory_manager.get_prompt_enhancements("twitter_thread")
            if memory_enhancements:
                style_instructions = f"{style_instructions}{memory_enhancements}"
        
        return self.chain.invoke(
            {
                "article_text": article_text, 
                "style_instructions": style_instructions,
                "sample_threads": sample_threads
            }
        )
    
    def generate_thread_from_document(
        self,
        document_content: str,
        custom_instructions: str = ""
    ) -> str:
        """
        Generate a thread from a document's content.
        
        Args:
            document_content: Content of the document as a string
            custom_instructions: Any additional custom instructions
            
        Returns:
            Generated thread as a string
        """
        return self.generate_thread(document_content, custom_instructions)
    
    def generate_thread_from_documents(
        self,
        documents: List[Document],
        custom_instructions: str = ""
    ) -> str:
        """
        Generate a thread from a list of document chunks.
        
        Args:
            documents: List of Document objects
            custom_instructions: Any additional custom instructions
            
        Returns:
            Generated thread as a string
        """
        # Combine document content
        article_text = "\n\n".join([doc.page_content for doc in documents])
        return self.generate_thread(article_text, custom_instructions)
    
    def revise_thread(
        self,
        original_thread: str,
        article_text: str,
        feedback: str,
        custom_instructions: str = ""
    ) -> str:
        """
        Revise a thread based on user feedback while preserving style guidelines.
        
        Args:
            original_thread: The original generated thread
            article_text: The original article content
            feedback: User feedback for revision
            custom_instructions: Any additional custom instructions
            
        Returns:
            Revised thread as a string
        """
        logger.info("Revising thread based on feedback while preserving style")
        
        # Load writing instructions and samples (same as original generation)
        style_instructions = self.load_writing_instructions()
        sample_threads = self.load_thread_samples()
        
        # Combine feedback with custom instructions
        revision_instructions = custom_instructions
        if feedback:
            revision_instructions = f"{custom_instructions}\n\nUser feedback for revision: {feedback}" if custom_instructions else f"User feedback for revision: {feedback}"
        
        # Add memory-based enhancements if available
        if self.memory_manager:
            memory_enhancements = self.memory_manager.get_prompt_enhancements("twitter_thread")
            if memory_enhancements:
                style_instructions = f"{style_instructions}{memory_enhancements}"
        
        # Create a revision-specific prompt that includes the original thread for context
        revision_prompt_template = PromptTemplate(
            input_variables=["article_text", "style_instructions", "sample_threads", "original_thread", "revision_instructions"],
            template="""
You are to revise a social media thread about the article below, based on user feedback.

Your #1 goal is to emulate the style, formatting, and persona of the provided sample threads as closely as possible. Your #2 goal is to follow the writing instructions. Your #3 goal is to address the user's feedback.

Analyze the sample threads and instructions internally, but ONLY output the revised thread itself—do NOT include any analysis or blueprint in your output.

You may use up to 25 tweets if needed to fully cover the article. There is no need to hit 25, but do not artificially stop early. Be as exhaustive and detailed as the article and samples require.

The revised thread must:
- Closely match the sample's formatting (segment length, separators, line breaks, etc.)
- Match the sample's voice and persona
- Use the writing instructions as secondary rules
- Address the user's feedback and concerns
- Avoid generic, formulaic, or AI-style output
- Only use hook styles (like 'Unpopular take:') if they are genuinely contextually appropriate for the content

SAMPLES:
{sample_threads}

INSTRUCTIONS:
{style_instructions}

ORIGINAL THREAD:
{original_thread}

REVISION INSTRUCTIONS:
{revision_instructions}

ARTICLE:
{article_text}

REVISED THREAD:
(Write the revised thread, following the style guidelines while addressing the feedback)
"""
        )
        
        # Create a revision-specific chain
        revision_chain = (
            {
                "article_text": RunnablePassthrough(),
                "style_instructions": RunnablePassthrough(),
                "sample_threads": RunnablePassthrough(),
                "original_thread": RunnablePassthrough(),
                "revision_instructions": RunnablePassthrough()
            }
            | revision_prompt_template
            | self.llm
            | StrOutputParser()
        )
        
        return revision_chain.invoke({
            "article_text": article_text,
            "style_instructions": style_instructions,
            "sample_threads": sample_threads,
            "original_thread": original_thread,
            "revision_instructions": revision_instructions
        }) 