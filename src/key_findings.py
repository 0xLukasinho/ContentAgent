"""
Key Arguments Extractor for ContentAgent.

This module analyzes articles to identify and extract key arguments
that would be valuable for content creation.
"""

import logging
import os
import re
from typing import Dict, List, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.config import OPENAI_MODEL, OUTPUT_DIR, get_api_key
from colorama import Fore, Style

logger = logging.getLogger(__name__)

class KeyFindingsExtractor:
    """Extracts key arguments directly from input content."""
    
    def __init__(self):
        """Initialize the key arguments extractor."""
        self.model = ChatOpenAI(
            model=OPENAI_MODEL,
            openai_api_key=get_api_key("OPENAI_API_KEY"),
            temperature=0.2  # Slightly higher temperature for more interpretive ability
        )
        
        self.arguments_prompt = ChatPromptTemplate.from_template("""
        You are an expert analyst who identifies the key arguments and core claims in content.
        
        Read the following article carefully and identify the main arguments the author is making.
        
        I need you to INTERPRET and SYNTHESIZE the article's key arguments - not just extract exact quotes.
        
        IMPORTANT GUIDELINES:
        - Identify 5-8 specific, substantive arguments the author is making to support their main thesis
        - Each argument should be a complete, self-contained claim that could stand on its own
        - Arguments should represent the author's position, not just facts mentioned in the article
        - Focus on unique insights, not general information or background context
        - Express each argument as a clear assertion or position (e.g., "The technology represents a breakthrough because...")
        - Include section references where appropriate (e.g., "[Section 3]")
        - Make sure each argument is fully developed - not just a heading or fragment
        
        BAD EXAMPLES (too vague/incomplete):
        - "The system architecture consists of several components"
        - "The challenges facing implementation include:"
        - "Section 3 discusses the market implications"
        
        GOOD EXAMPLES (complete arguments):
        - "[Section 2] The proprietary algorithm delivers superior results because it incorporates both historical data and real-time feedback, enabling 35% better accuracy than competitors"
        - "Despite initial technical limitations, the technology's ability to scale through distributed networks will likely overcome current market hesitations within 12-18 months"
        
        Format your response as a numbered list:
        1. [Complete argument 1]
        2. [Complete argument 2]
        ...
        
        Article:
        {content}
        """)
        
        self.arguments_chain = self.arguments_prompt | self.model
    
    def extract_findings(self, content: str) -> Dict[str, List[str]]:
        """
        Extract key arguments from the provided content and let user confirm which to keep.
        
        Args:
            content: The article content to analyze
            
        Returns:
            Dictionary with confirmed arguments
        """
        logger.info("Extracting key arguments from article")
        
        try:
            print(f"{Fore.CYAN}Extracting key arguments from article...{Style.RESET_ALL}")
            result = self.arguments_chain.invoke({"content": content})
            arguments = self._parse_arguments(result.content)
            
            if arguments:
                print(f"\n{Fore.CYAN}=== Main Arguments ==={Style.RESET_ALL}")
                confirmed_arguments = []
                
                for i, argument in enumerate(arguments):
                    print(f"\n{Fore.GREEN}{i+1}. {argument}{Style.RESET_ALL}")
                    keep = input(f"Keep this argument for creating a post? (y/n) [y]: ")
                    if keep.lower() != 'n':
                        confirmed_arguments.append(argument)
                
                # Ask for any missing arguments
                while True:
                    print(f"\n{Fore.YELLOW}Add a missing argument or press Enter to continue:{Style.RESET_ALL}")
                    new_argument = input("> ")
                    if not new_argument:
                        break
                    confirmed_arguments.append(new_argument)
                
                return {"Main Arguments": confirmed_arguments}
            else:
                print(f"{Fore.RED}No arguments could be extracted from the article.{Style.RESET_ALL}")
                return {"Main Arguments": []}
            
        except Exception as e:
            logger.error(f"Error extracting key arguments: {e}")
            raise
    
    def _parse_arguments(self, arguments_text: str) -> List[str]:
        """
        Parse the raw arguments text into a list of arguments.
        
        Args:
            arguments_text: Raw arguments text from the LLM
            
        Returns:
            List of arguments
        """
        arguments = []
        
        # Split by lines
        lines = arguments_text.strip().split('\n')
        
        # Extract numbered arguments, potentially spanning multiple lines
        current_argument = ""
        current_number = None
        
        for line in lines:
            line = line.strip()
            if not line:
                # Empty line - if we have a current argument, save it
                if current_argument:
                    arguments.append(current_argument.strip())
                    current_argument = ""
                    current_number = None
                continue
                
            # Check if this is a new numbered item
            number_match = re.match(r'^(\d+)\.', line)
            
            if number_match:
                # Found a new numbered item
                
                # Save the previous argument if we have one
                if current_argument:
                    arguments.append(current_argument.strip())
                    current_argument = ""
                
                # Start a new argument
                current_number = int(number_match.group(1))
                current_argument = line.split('.', 1)[1].strip()
            elif current_number is not None:
                # Continuation of the current argument
                current_argument += " " + line
        
        # Add the last argument if we have one
        if current_argument:
            arguments.append(current_argument.strip())
        
        # If we couldn't extract any arguments, try other formats
        if not arguments:
            for line in lines:
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('*')):
                    argument = line.lstrip('-*').strip()
                    if argument:
                        arguments.append(argument)
        
        # If still no arguments, just use any non-empty lines
        if not arguments:
            arguments = [line.strip() for line in lines if line.strip()]
            
        return arguments
    
    def save_findings(self, findings: Dict[str, List[str]], article_title: str, output_dir: str) -> str:
        """
        Save the extracted findings to a file.
        
        Args:
            findings: The extracted and confirmed arguments
            article_title: The title of the original article
            output_dir: Directory to save the findings
            
        Returns:
            Path to the saved file
        """
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, "key_arguments.md")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# Key Arguments from: {article_title}\n\n")
            
            if "Main Arguments" in findings and findings["Main Arguments"]:
                for i, argument in enumerate(findings["Main Arguments"]):
                    f.write(f"## Argument {i+1}\n\n")
                    f.write(f"{argument}\n\n")
            else:
                f.write("No key arguments were identified.\n")
            
        logger.info(f"Key arguments saved to {output_path}")
        print(f"{Fore.GREEN}Key arguments saved to: {output_path}{Style.RESET_ALL}")
        
        return output_path 