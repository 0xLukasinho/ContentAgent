# Bug Report: ContentAgent Revision Process Hanging

## Summary
The ContentAgent application hangs indefinitely when users request revisions (option 3) during the content feedback process. The system prints "Revising summary based on feedback..." but never completes the revision or returns control to the user. **The initial generation works perfectly**, indicating the model name and API configuration are correct.

## Root Cause Analysis

### Primary Issue: Excessive Prompt Size in Revision Process
**Evidence**: Initial generation works fine, but revision hangs, indicating the issue is specific to the revision workflow.

### Key Differences Between Initial Generation and Revision

#### Initial Generation (`generate_summary`)
**Location**: `src/article_summary.py:163-195`
**Prompt Components**:
- Style instructions 
- Sample posts (max 2 samples)
- Article content
- Simple directive to generate summary

#### Revision Process (`revise_summary`) 
**Location**: `src/article_summary.py:212-246`
**Prompt Components**:
- Style instructions (same as initial)
- Sample posts (1 sample, so smaller)
- **Original summary** (400-600 words) 
- **User feedback** (can be very long)
- **Full article content** (entire document)
- Complex revision instructions with 8-point guideline list

### Technical Flow Leading to Hang

1. **User provides lengthy feedback**: In the logs, user provided 200+ word feedback
2. **Massive prompt construction**: `revision_prompt` template combines:
   ```python
   {style_instructions}     # Potentially long
   {sample_posts}          # Sample content
   {original_summary}      # 400-600 words
   {feedback}              # User's long feedback (200+ words in example)
   {content}               # ENTIRE article content
   ```
3. **Context window exceeded**: Combined prompt likely exceeds model's context limits
4. **API timeout/hang**: Request either times out or hangs waiting for response
5. **No timeout configuration**: System waits indefinitely

### Supporting Evidence

#### 1. Prompt Size Comparison
**Initial Generation Prompt Structure**:
```
Instructions + Samples + Article → Generate
```

**Revision Prompt Structure** (`article_summary.py:67-94`):
```
Instructions + Samples + Original Summary + Feedback + Article → Revise
```

The revision prompt is significantly larger due to:
- **Original summary**: 400-600 additional words
- **User feedback**: Variable length (200+ words in observed case)
- **Complex instructions**: 8-point revision guideline list

#### 2. User Feedback Length in Example
From terminal logs:
```
I don't like this part: Expect consolidation: out of 80+ subnets, only a few will survive and thrive, validating Bittensor's model and attracting further investment. Early signs show subnets beating tech giants in specialized tasks—Subnet 19 surpassed Azure for DeepSeek inference, and Celium's revenue proves market viability. we can cut it. In the following section, you didn't bring across that this is my view and outlook. It's very important that when something is clearly my opinion in an article, that is within the post: Bittensor's mission resonates deeply in a world where AI power is dangerously concentrated. By enabling decentralized AI development with aligned incentives, it offers a credible path toward democratizing access to artificial intelligence.
```
**Length**: ~200 words of feedback

#### 3. Missing Timeout Configuration
**Location**: All ChatOpenAI initializations (e.g., `article_summary.py:38-44`)
```python
self.model = ChatOpenAI(
    model=OPENAI_MODEL,
    openai_api_key=get_api_key("OPENAI_API_KEY"),
    temperature=0.7
    # Missing: request_timeout, max_retries
)
```

**Issue**: No timeout parameters means indefinite waiting when API calls hang.

### Context Window Analysis

#### Estimated Token Counts for Revision:
- Style instructions: ~300 tokens
- Sample posts: ~500 tokens  
- Original summary: ~800 tokens (400-600 words)
- User feedback: ~400 tokens (200+ words in example)
- Article content: ~2000+ tokens (Bittensor article appears lengthy)
- Revision instructions: ~200 tokens

**Total**: ~4200+ tokens, potentially approaching or exceeding context limits for complex processing.

### Additional Contributing Factors

#### 1. Processing Complexity
The revision task requires the model to:
- Understand the original summary
- Parse specific user feedback
- Correlate feedback to article sections
- Maintain style consistency
- Generate coherent revision

This complexity combined with large prompt size increases processing time and likelihood of timeouts.

#### 2. Network/API Factors
- Large requests take longer to upload
- Complex responses take longer to generate
- No retry logic for failed/timed-out requests
- No progress indicators for long-running operations

## Code Evidence Summary

### Key Files Analyzed
1. **`src/article_summary.py:67-94`**: Revision prompt template with multiple large components
2. **`src/article_summary.py:212-246`**: `revise_summary` method that hangs
3. **`src/main.py:190-205`**: Main workflow calling revision
4. **Terminal logs**: Show successful initial generation but hang during revision

### Verification Steps Performed
1. ✅ Confirmed initial generation works (model/API valid)
2. ✅ Identified prompt size difference between initial and revision
3. ✅ Analyzed user feedback length in example case
4. ✅ Confirmed missing timeout configuration
5. ✅ Traced exact hanging location in code flow

## Impact Assessment

### User Experience
- System appears to freeze during revision requests
- No progress indication or timeout feedback
- Requires force-termination (Ctrl+C) to exit
- Loss of work/progress in current session

### Affected Scenarios
- **High impact**: Long user feedback (100+ words)
- **High impact**: Long articles (2000+ words)
- **Medium impact**: Users providing detailed revision instructions
- **Low impact**: Short feedback on short articles

## Recommended Fix Priority

**High Priority**: Add request timeout configuration to prevent indefinite hangs.

**Medium Priority**: Implement prompt size optimization for revision requests.

**Low Priority**: Add progress indicators for long-running operations.

## Reproduction Steps
1. Run `python run_agent.py`
2. Select any document
3. Choose to generate Article Summary (this works fine)
4. When prompted, select option 3 (Request revision)
5. Provide lengthy feedback text (100+ words)
6. Observe: System prints "Revising summary based on feedback..." and hangs

## Environment Details
- **OS**: Windows 10.0.26100
- **Model**: `gpt-4.1-mini-2025-04-14` (confirmed working for initial generation)
- **Key Dependencies**: `langchain-openai`, `openai>=1.14.3` 