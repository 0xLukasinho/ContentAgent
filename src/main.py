"""
Main application module for ContentAgent.
Integrates all components and provides the main entry point.
"""
import os
import datetime
import re
from typing import Dict, Any, Tuple

from src.document_loader import DocumentProcessor
from src.twitter_generator import TwitterThreadGenerator
from src.cli_interface import CLIInterface
from src.config import INPUT_DIR, OUTPUT_DIR

# Import Stage 2 modules
from src.article_summary import ArticleSummaryGenerator
from src.key_findings import KeyFindingsExtractor
from src.detailed_post import DetailedPostGenerator
from src.image_prompts import ImagePromptGenerator
from src.content_formatter import ContentFormatter
from src.context_processor import ContextProcessor
from colorama import Fore, Style

class ContentAgent:
    """
    Main ContentAgent application class.
    Integrates all components and manages the workflow.
    """
    
    def __init__(self):
        """
        Initialize the ContentAgent application.
        """
        print("Initializing ContentAgent...")
        # Stage 1 components
        self.document_processor = DocumentProcessor()
        self.twitter_generator = TwitterThreadGenerator()
        self.cli = CLIInterface()
        
        # Stage 2 components
        self.article_summary_generator = ArticleSummaryGenerator()
        self.key_findings_extractor = KeyFindingsExtractor()
        self.detailed_post_generator = DetailedPostGenerator()
        self.image_prompt_generator = ImagePromptGenerator()
        self.content_formatter = ContentFormatter()
        self.context_processor = ContextProcessor()
        
        print("ContentAgent initialized.")
    
    def _create_topic_based_folder_name(self, article_title: str) -> str:
        """
        Create a safe, topic-based folder name from the article title.
        
        Args:
            article_title: The title of the article
            
        Returns:
            Safe folder name based on the topic
        """
        # Clean the title: remove special characters, convert to lowercase
        safe_title = re.sub(r'[^\w\s-]', '', article_title.lower())
        # Replace spaces with underscores and remove extra whitespace
        safe_title = re.sub(r'\s+', '_', safe_title.strip())
        # Remove any double underscores
        safe_title = re.sub(r'_+', '_', safe_title)
        # Limit length to avoid filesystem issues
        safe_title = safe_title[:50]
        # Remove trailing underscores
        safe_title = safe_title.rstrip('_')
        
        # If the title is empty after cleaning, use a default
        if not safe_title:
            safe_title = "content_generation"
        
        # Check if folder already exists, if so add a counter
        base_folder_name = safe_title
        counter = 1
        final_folder_name = base_folder_name
        
        while os.path.exists(os.path.join(OUTPUT_DIR, final_folder_name)):
            counter += 1
            final_folder_name = f"{base_folder_name}_{counter}"
        
        return final_folder_name
    
    def run(self):
        """
        Run the ContentAgent workflow.
        """
        # Get input file path from user
        input_file = self.cli.get_article_path()
        if not input_file:
            print(f"{Fore.RED}No valid input file specified. Exiting.{Style.RESET_ALL}")
            return
        
        # Get output options from user
        generate_options = self.cli.get_generation_options()
        
        # Load document
        print(f"Processing document: {os.path.basename(input_file)}")
        doc_result = self.document_processor.process_document(input_file)
        article_content = doc_result["content"]
        article_title = doc_result["title"]
        
        # Create output directory with topic-based name
        topic_folder_name = self._create_topic_based_folder_name(article_title)
        output_dir = os.path.join(OUTPUT_DIR, topic_folder_name)
        os.makedirs(output_dir, exist_ok=True)
        print(f"Output will be saved to: {output_dir}")
        print(f"{Fore.CYAN}Topic-based folder: {topic_folder_name}{Style.RESET_ALL}")
        
        # Store all generated content for image prompts
        generated_content = {}
        
        # Generate requested outputs
        if generate_options.get("twitter_thread"):
            # Generate initial thread (Stage 1)
            print("Generating social media thread...")
            thread_content = self.twitter_generator.generate_thread_from_document(
                article_content
            )
            thread_path = self.cli.save_thread(thread_content, output_dir=output_dir)
            print(f"Social media thread saved to {thread_path}")
            
            # Get user feedback loop
            while True:
                feedback_type, feedback_content = self.cli.get_user_feedback(thread_path)
                
                if feedback_type == "accept":
                    # User accepted the thread, save it to output
                    break
                    
                elif feedback_type == "edited":
                    # User edited thread manually
                    print("Thread has been manually edited.")
                    # Read the edited content from the file
                    with open(thread_path, "r", encoding="utf-8") as f:
                        thread_content = f.read()
                    break
                    
                elif feedback_type == "revise":
                    # User requested revision
                    print("Revising thread based on feedback...")
                    
                    # Update the thread with revised content
                    revised_thread = self.twitter_generator.generate_thread(
                        article_content,
                        feedback_content
                    )
                    
                    # Save the revised thread
                    thread_path = self.cli.save_thread(revised_thread, output_dir=output_dir)
                    thread_content = revised_thread
            
            # Store generated thread content for image prompts
            generated_content["twitter_thread"] = {
                "content": thread_content,
                "title": f"{article_title} - Social Media Thread",
                "file_path": thread_path
            }
        
        # Generate Stage 2 outputs
        if generate_options.get("article_summary", False):
            print("Generating article summary...")
            summary = self.article_summary_generator.generate_summary(article_content)
            summary_result = self.article_summary_generator.save_summary(summary, article_title, output_dir)
            summary_path = summary_result["file_path"]
            print(f"Article summary saved to: {summary_path}")
            
            # Get user feedback loop for article summary
            while True:
                feedback_type, feedback_content = self.cli.get_user_feedback(summary_path)
                
                if feedback_type == "accept":
                    # User accepted the summary
                    break
                    
                elif feedback_type == "edited":
                    # User edited the summary manually
                    print("Summary has been manually edited.")
                    # Read the edited content from the file
                    with open(summary_path, "r", encoding="utf-8") as f:
                        summary = f.read()
                    break
                    
                elif feedback_type == "revise":
                    # User requested revision
                    print("Revising summary based on feedback...")
                    
                    # Generate revised summary
                    summary = self.article_summary_generator.revise_summary(
                        summary, article_content, feedback_content
                    )
                    
                    # Save revised summary
                    summary_result = self.article_summary_generator.save_summary(summary, article_title, output_dir)
                    summary_path = summary_result["file_path"]
            
            # Store generated summary content for image prompts
            generated_content["article_summary"] = {
                "content": summary,
                "title": f"{article_title} - Article Summary",
                "file_path": summary_path
            }
            
        # Process detailed posts - extract arguments and generate posts
        if generate_options.get("detailed_posts", False):
            # Extract key arguments from article for detailed posts
            print("Extracting key arguments from article...")
            findings = self.key_findings_extractor.extract_findings(article_content)
            arguments = findings.get("Main Arguments", [])
            
            if arguments:
                # Store key arguments for image prompts only - don't save as file
                generated_content["key_findings"] = {
                    "content": arguments,
                    "title": f"{article_title} - Key Arguments"
                }
                
                # Load additional context files
                print("\nChecking for additional context files...")
                additional_context = self.context_processor.process_context_files()
                
                # Process each argument individually
                all_posts = {}
                for argument in arguments:
                    print(f"\nGenerating detailed post for argument: {argument[:50]}...")
                    
                    # Generate post for this argument
                    post_content = self.detailed_post_generator.generate_post_for_argument(
                        argument, 
                        article_content,
                        "",  # No custom instructions
                        additional_context
                    )
                    
                    # Save post to individual file
                    post_path = self.detailed_post_generator.save_individual_post(
                        argument,
                        post_content,
                        article_title,
                        output_dir
                    )
                    
                    # Get user feedback for this post
                    print(f"\n{Fore.CYAN}Review the post for argument:{Style.RESET_ALL} {argument[:50]}...")
                    feedback_type, feedback_content = self.cli.get_user_feedback(post_path)
                    
                    if feedback_type == "accept":
                        # User accepted the post
                        all_posts[argument] = post_content
                        print(f"{Fore.GREEN}Post accepted.{Style.RESET_ALL}")
                        
                    elif feedback_type == "edited":
                        # User edited the post manually
                        print(f"{Fore.GREEN}Post has been manually edited.{Style.RESET_ALL}")
                        # Read the edited content from the file
                        with open(post_path, "r", encoding="utf-8") as f:
                            edited_content = f.read()
                        # Extract just the post content (remove title and argument)
                        match = re.search(r'\*\*.*?\*\*\s*\n\n(.*)', edited_content, re.DOTALL)
                        if match:
                            edited_post = match.group(1).strip()
                            all_posts[argument] = edited_post
                        else:
                            all_posts[argument] = post_content
                            
                    elif feedback_type == "revise":
                        # User requested revision
                        print(f"{Fore.GREEN}Revising post based on feedback...{Style.RESET_ALL}")
                        
                        # Generate revised post
                        revised_post = self.detailed_post_generator.revise_post(
                            post_content,
                            argument, 
                            article_content,
                            feedback_content,
                            "",  # No custom instructions
                            additional_context
                        )
                        
                        # Save revised post
                        revised_path = self.detailed_post_generator.save_individual_post(
                            argument,
                            revised_post,
                            article_title,
                            output_dir
                        )
                        
                        all_posts[argument] = revised_post
                        print(f"{Fore.GREEN}Revised post saved.{Style.RESET_ALL}")
                
                # Store all generated posts for image prompts
                generated_content["detailed_posts"] = {
                    "content": all_posts,
                    "title": f"{article_title} - Detailed Posts"
                }
            else:
                print(f"{Fore.YELLOW}No key arguments found to generate detailed posts.{Style.RESET_ALL}")

        # Generate image prompts for each type of content
        if generate_options.get("image_prompts", False) and generated_content:
            print("Generating image prompts for each content piece...")
            image_prompts = self.image_prompt_generator.generate_content_specific_prompts(generated_content)
            prompts_path = self.image_prompt_generator.save_image_prompts(image_prompts, article_title, output_dir)
            print(f"Image prompts saved to: {prompts_path}")
            
        # Print completion message
        self.cli.print_completion()

def main():
    """
    Main entry point for the application.
    """
    try:
        print("Starting ContentAgent...")
        agent = ContentAgent()
        agent.run()
    except KeyboardInterrupt:
        print("\nApplication terminated by user.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 