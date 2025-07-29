"""
CLI Interface for ContentAgent.
Handles user interaction through the command line.
"""
import os
import sys
import glob
from typing import Dict, List, Optional, Union, Tuple
import tempfile
import subprocess
import colorama
from colorama import Fore, Style
import time

# Import from centralized config
from src.config import INPUT_DIR, OUTPUT_DIR, VALID_EXTENSIONS

# Initialize colorama
colorama.init()

class CLIInterface:
    """
    Command Line Interface for ContentAgent.
    Handles user interaction and feedback.
    """
    
    def __init__(self, output_dir: str = OUTPUT_DIR, input_dir: str = INPUT_DIR, memory_manager=None):
        """
        Initialize the CLI interface.
        
        Args:
            output_dir: Directory for output files
            input_dir: Directory for input files
            memory_manager: MemoryManager instance for feedback recording
        """
        self.output_dir = output_dir
        self.input_dir = input_dir
        self.memory_manager = memory_manager
        
        # Create directories if they don't exist
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(input_dir, exist_ok=True)
    
    def print_welcome(self):
        """
        Print welcome message and instructions.
        """
        print(f"{Fore.CYAN}===================================={Style.RESET_ALL}")
        print(f"{Fore.CYAN}          ContentAgent             {Style.RESET_ALL}")
        print(f"{Fore.CYAN}===================================={Style.RESET_ALL}")
        print("Generate social media content from articles.")
        print()
    
    def get_article_path(self) -> str:
        """
        Get article path from the input directory.
        If multiple articles exist, let the user choose.
        
        Returns:
            Path to the article file
        """
        # Check if input directory exists and create if not
        os.makedirs(self.input_dir, exist_ok=True)
        
        # Get list of article files in the input directory
        article_files = []
        for ext in VALID_EXTENSIONS:
            article_files.extend(glob.glob(os.path.join(self.input_dir, f"*{ext}")))
        
        # If there are article files, let the user choose one
        if article_files:
            # Sort files for consistent display
            article_files.sort()
            
            # Display article options
            for i, file_path in enumerate(article_files, 1):
                file_name = os.path.basename(file_path)
                print(f"{i}. {file_name}")
            
            # Get user selection
            while True:
                try:
                    choice = int(input("Enter your choice (1-{}): ".format(len(article_files))))
                    if 1 <= choice <= len(article_files):
                        return article_files[choice - 1]
                    else:
                        print("Invalid choice. Please try again.")
                except ValueError:
                    print("Please enter a number.")
        
        # If no article files found, ask for file path
        print(f"No article files found in {self.input_dir}.")
        print(f"Please place article files in {self.input_dir} and try again.")
        exit(1)
    
    def save_thread(self, thread_content: str, prefix: str = "twitter_thread", output_dir: str = None) -> str:
        """
        Save thread content to a file.
        
        Args:
            thread_content: Thread content to save
            prefix: Prefix for the output filename
            output_dir: Directory to save the file (defaults to self.output_dir)
            
        Returns:
            Path to the saved file
        """
        # Use provided output directory or default
        if output_dir is None:
            output_dir = self.output_dir
            
        # Create a filename with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.md"
        
        # Make sure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Full path
        output_path = os.path.join(output_dir, filename)
        
        # Save the content
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(thread_content)
        
        print(f"{Fore.GREEN}Thread saved to: {output_path}{Style.RESET_ALL}")
        return output_path
    
    def get_generation_options(self) -> Dict[str, bool]:
        """
        Ask the user which content types they want to generate.
        
        Returns:
            Dictionary of content types and whether to generate them
        """
        print(f"\n{Fore.CYAN}What content would you like to generate?{Style.RESET_ALL}")
        
        options = {
            "twitter_thread": self._get_yes_no("Generate Twitter Thread?", default=True),
            "article_summary": self._get_yes_no("Generate Article Summary?", default=False),
            "detailed_posts": self._get_yes_no("Generate Detailed Posts?", default=False),
            "image_prompts": self._get_yes_no("Generate Image Prompts?", default=False),
        }
        
        # Print selected options
        print(f"\n{Fore.CYAN}Selected content types:{Style.RESET_ALL}")
        for option, selected in options.items():
            if selected:
                # Convert option name to display format
                display_name = " ".join([word.capitalize() for word in option.split("_")])
                print(f"- {display_name}")
        
        return options
    
    def _get_yes_no(self, prompt: str, default: bool = True) -> bool:
        """
        Ask a yes/no question and return a boolean.
        
        Args:
            prompt: Question to ask
            default: Default value (True for yes, False for no)
            
        Returns:
            Boolean response (True for yes, False for no)
        """
        default_str = "y" if default else "n"
        response = input(f"{prompt} (y/n) [{default_str}]: ")
        
        if not response:
            return default
        
        return response.lower() == "y"
    
    def get_user_feedback(self, thread_path: str, content_type: str = "content", 
                         content_text: str = "", original_prompt: str = "", 
                         generation_time: float = None) -> tuple:
        """
        Get user feedback on generated content.
        
        Args:
            thread_path: Path to the file containing the generated content
            content_type: Type of content generated (e.g., "twitter_thread", "article_summary")
            content_text: The actual generated content text
            original_prompt: The prompt used to generate the content
            generation_time: Time taken to generate the content in seconds
            
        Returns:
            Tuple of (feedback_type, feedback_content)
        """
        print(f"\n{Fore.CYAN}Generated content saved to: {thread_path}{Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}What would you like to do with this content?{Style.RESET_ALL}")
        print("1. Accept as is")
        print("2. Edit manually")
        print("3. Request revision (provide feedback)")
        
        while True:
            try:
                choice = input(f"{Fore.GREEN}Enter your choice (1-3) [1]: {Style.RESET_ALL}")
                
                if not choice:
                    # Default to accept
                    print(f"{Fore.GREEN}Content accepted.{Style.RESET_ALL}")
                    self._record_feedback("accept", content_type, content_text, original_prompt, generation_time)
                    return ("accept", "")
                    
                option = int(choice)
                if option == 1:
                    # Accept as is
                    print(f"{Fore.GREEN}Content accepted.{Style.RESET_ALL}")
                    self._record_feedback("accept", content_type, content_text, original_prompt, generation_time)
                    return ("accept", "")
                elif option == 2:
                    # Edit manually
                    print(f"{Fore.GREEN}Opening content for editing...{Style.RESET_ALL}")
                    self._open_file_in_editor(thread_path)
                    print(f"{Fore.GREEN}Manual edits applied.{Style.RESET_ALL}")
                    
                    # Read the edited content to track changes
                    try:
                        with open(thread_path, "r", encoding="utf-8") as f:
                            edited_content = f.read()
                        edit_metadata = {"edited_content": edited_content}
                    except Exception:
                        edit_metadata = {}
                    
                    self._record_feedback("edit", content_type, content_text, original_prompt, generation_time, edit_metadata)
                    return ("edited", "")
                elif option == 3:
                    # Request revision
                    print(f"{Fore.GREEN}Please provide feedback for revision:{Style.RESET_ALL}")
                    feedback = input("> ")
                    if feedback:
                        print(f"{Fore.GREEN}Feedback received. Generating revision...{Style.RESET_ALL}")
                        self._record_feedback("reject", content_type, content_text, original_prompt, generation_time, {"revision_reason": feedback})
                        return ("revise", feedback)
                    else:
                        print(f"{Fore.RED}No feedback provided. Please try again.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}Invalid choice. Please enter a number between 1 and 3.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Please enter a valid number.{Style.RESET_ALL}")
    
    def _open_file_in_editor(self, file_path: str):
        """
        Open a file in the user's default editor.
        
        Args:
            file_path: Path to the file to open
        """
        if sys.platform == "win32":
            os.startfile(file_path)
        else:
            import subprocess
            try:
                subprocess.call(['open', file_path])
            except:
                subprocess.call(['xdg-open', file_path])
                
        input(f"{Fore.YELLOW}Press Enter when you're done editing the file...{Style.RESET_ALL}")
    
    def _record_feedback(self, user_action: str, content_type: str, content_text: str, 
                        original_prompt: str, generation_time: float, metadata: dict = None):
        """
        Record user feedback using the memory manager.
        
        Args:
            user_action: The action taken by the user (accept, edit, reject)
            content_type: Type of content generated
            content_text: The actual generated content
            original_prompt: The prompt used to generate content
            generation_time: Time taken to generate in seconds
            metadata: Additional metadata dictionary
        """
        if self.memory_manager:
            try:
                success = self.memory_manager.record_feedback(
                    content_type=content_type,
                    content_text=content_text,
                    user_action=user_action,
                    original_prompt=original_prompt,
                    generation_time=generation_time,
                    metadata=metadata
                )
                if not success:
                    print(f"{Fore.YELLOW}Warning: Failed to record feedback in memory system.{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}Warning: Error recording feedback: {e}{Style.RESET_ALL}")
    
    def print_completion(self):
        """
        Print completion message.
        """
        print(f"\n{Fore.GREEN}Content generation complete!{Style.RESET_ALL}")
        print(f"Check your output directory: {self.output_dir}")
        print(f"\n{Fore.CYAN}Thank you for using ContentAgent.{Style.RESET_ALL}") 