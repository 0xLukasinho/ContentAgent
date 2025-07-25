# ContentAgent

An advanced AI-powered content generation system that processes various document types and generates social media content with learned writing styles.

## Features

### 🧠 Intelligent Style Learning
- **Adaptive Writing Styles**: Each content generator learns from sample content and writing instructions
- **Direct Sample Processing**: Writers process their own style samples without centralized processing
- **Flexible Style Customization**: Easy-to-edit instruction files for different content types

### 📄 Multi-Document Support
- **Format Flexibility**: Supports Markdown (.md) and Word documents (.docx)
- **Automatic Detection**: Intelligently detects and processes articles in the input folder
- **Additional Content Integration**: Supports supplementary content through the additional_content folder

### 🎯 Content Generation Types
- **Twitter Threads**: Engaging multi-tweet narratives that summarize key points
- **Article Summaries**: Concise overviews following X-Post style guidelines
- **Detailed Posts**: Individual long-form social media posts with custom targeting
- **Image Prompts**: AI-generated prompts for creating relevant visuals

### 🔄 Interactive Workflows
- **Individual Post Processing**: Each detailed post is generated and reviewed separately
- **Real-time Feedback**: Accept, edit, or request AI revisions for each content piece
- **Flexible Generation Options**: Choose which content types to generate per session

## Setup

1. **Install Dependencies**:
   ```
   pip install -r requirements.txt
   ```

2. **Configure API Access**:
   Create a `.env` file in the root directory:
   ```
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

## Usage

### Quick Start
1. **Add Content**: Place your article files in `data/input/`
2. **Run the Agent**: `python run_agent.py`
3. **Select Options**: Choose your preferred content generation types
4. **Review & Refine**: Use the interactive feedback system to perfect your content

### Detailed Workflow

#### Step 1: Input Preparation
- Place source documents in `data/input/`
- Add any supplementary content to `data/input/additional_content/`
- Supported formats: `.md`, `.docx`

#### Step 2: Content Generation
The system will prompt you to select from:
- **Twitter Thread**: Multi-tweet narrative (optional)
- **Article Summary**: Concise overview in X-Post style
- **Detailed Posts**: Individual long-form posts (specify count)
- **Image Prompts**: Visual content suggestions

#### Step 3: Interactive Review
For each content type:
- **Accept**: Use the generated content as-is
- **Edit**: Modify content in your default text editor
- **Revise**: Request AI improvements with specific instructions

#### Step 4: Output Organization
All generated content is saved in timestamped folders within `data/output/`

## Style Customization

### Writing Instructions
Customize writing styles through instruction files:
- `data/samples/writing_instructions_thread.txt` - Twitter thread style
- `data/samples/writing_instructions_post.txt` - Post and summary style

### Sample Content
Influence generation style with example content:
- `data/samples/sample_threads/` - Example thread content
- `data/samples/sample_posts/` - Example post content

Each writer processes up to:
- **3 thread samples** for Twitter threads
- **2 post samples** for detailed posts and summaries

## Architecture

### Core Components
- **Document Loader**: Processes various document formats
- **Content Generators**: Specialized writers for each content type
- **CLI Interface**: Interactive command-line experience
- **Style Integration**: Direct sample processing by individual writers

### Key Architecture Improvements
- **Simplified Style System**: Removed centralized StyleProcessor
- **Direct Sample Processing**: Each writer manages its own samples
- **Individual Post Handling**: Detailed posts processed one at a time
- **Enhanced Feedback Loops**: Granular control over content refinement

## Folder Structure

```
ContentAgent/
├── data/
│   ├── input/                    # Source documents
│   │   └── additional_content/   # Supplementary content
│   ├── output/                   # Generated content (timestamped)
│   └── samples/                  # Style guides and examples
│       ├── sample_threads/       # Thread examples
│       ├── sample_posts/         # Post examples
│       ├── writing_instructions_thread.txt
│       └── writing_instructions_post.txt
├── src/                          # Source code
├── requirements.txt              # Dependencies
└── run_agent.py                  # Main entry point
```

## Project Status

### ✅ Completed Features
- **Stage 1**: Basic document processing and Twitter thread generation
- **Stage 2**: Content expansion with interactive workflows
- **Stage 3**: Supporting document integration
- **Stage 4**: Style learning and adaptation
- **Stage 5**: User feedback integration

### 🚧 In Development
- **Stage 6**: Advanced features and multi-platform integration

## Contributing

The ContentAgent is designed for extensibility. Key areas for contribution:
- Additional document format support
- New content generation types
- Enhanced style learning algorithms
- Multi-platform content optimization

## License

This project is available under the MIT License.
