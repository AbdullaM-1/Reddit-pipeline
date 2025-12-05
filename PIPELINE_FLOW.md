# Complete Pipeline Flow

## Overview

The complete pipeline processes Reddit posts and outputs individual files with metadata as filenames.

## Complete Flow

```
1. FETCH POSTS
   ↓
   Fetch posts from Reddit API
   ↓
2. PROCESS POSTS
   ↓
   - Identify correct links
   - Download images
   - Extract OCR text
   - Save to Supabase
   ↓
   pipeline_results/pipeline_results.json
   ↓
3. CLEAN DATA
   ↓
   - Remove duplicates
   - Fix order
   - Validate structure
   ↓
   pipeline_results/pipeline_results.cleaned.json
   ↓
4. FLATTEN DATA
   ↓
   - Simplify structure
   - Extract essential fields
   - Aggregate OCR text
   ↓
   pipeline_results/pipeline_results.cleaned.flat.json
   ↓
5. SPLIT INTO INDIVIDUAL FILES ← FINAL OUTPUT
   ↓
   - Split each post into separate file
   - Filename: {post_id},{title},{correct_link}.json
   - Structure: metadata + content
   ↓
   pipeline_results/posts_{timestamp}/
   ├── 1pdgyr2,Family_Traditions_Chapter_2,imgchest.com_p_abc123.json
   ├── 2abc123,Another_Story_Part_1,imgchest.com_p_def456.json
   └── ...
```

## Step Details

### Step 1: Fetch Posts
- Fetches posts from Reddit API
- Filters out posts that already exist in database
- Processes only new posts

### Step 2: Process Posts
- Identifies correct links from author comments
- Downloads images from identified links
- Extracts OCR text from images
- Saves data to Supabase database
- Aggregates results into `pipeline_results.json`

### Step 3: Clean Data
- Loads aggregated results
- Removes duplicate post IDs
- Fixes order of posts
- Saves cleaned version to `pipeline_results.cleaned.json`

### Step 4: Flatten Data
- Simplifies data structure to essential fields:
  - `post_id`
  - `title`
  - `status`
  - `correct_link`
  - `ocr_text` (aggregated from all images)
- Saves flattened version to `pipeline_results.cleaned.flat.json`

### Step 5: Split Into Individual Files (FINAL OUTPUT)
- **Takes**: `pipeline_results.cleaned.flat.json`
- **Creates**: Individual JSON files, one per post
- **Location**: `pipeline_results/posts_{timestamp}/`
- **Filename Format**: `{post_id},{title},{correct_link}.json`
- **File Structure**:
  ```json
  {
    "metadata": {
      "post_id": "1pdgyr2",
      "title": "Family Traditions (Chapter 2)",
      "status": "success",
      "correct_link": "https://imgchest.com/p/abc123"
    },
    "content": "Full OCR text extracted from images..."
  }
  ```

## Output Files

### Intermediate Files (Kept for Reference)
1. `pipeline_results/pipeline_results.json` - Raw aggregated results
2. `pipeline_results/pipeline_results.cleaned.json` - Cleaned version
3. `pipeline_results/pipeline_results.cleaned.flat.json` - Flattened version

### Final Output (Main Result)
- **Directory**: `pipeline_results/posts_{timestamp}/`
- **Files**: Individual JSON files, one per post
- **Naming**: `{post_id},{title},{correct_link}.json`
- **Structure**: Metadata object + content field

## Running the Pipeline

```bash
python run_full_pipeline.py --subreddit SextStories --limit 100
```

### What Happens
1. ✅ Fetches 100 recent posts
2. ✅ Processes new posts (skips existing)
3. ✅ Cleans and deduplicates
4. ✅ Flattens data structure
5. ✅ **Splits into individual files** ← Final output

### Final Output Location
```
pipeline_results/posts_20240115_143022/
├── 1pdgyr2,Family_Traditions_Chapter_2,imgchest.com_p_abc123.json
├── 2abc123,Another_Story_Part_1,imgchest.com_p_def456.json
└── ... (one file per post)
```

## Benefits

✅ **Complete Automation** - All steps run automatically  
✅ **Individual Files** - Easy to process/manage per post  
✅ **Metadata in Filename** - Quick identification  
✅ **Structured Content** - Ready for knowledge bases  
✅ **Clean Workflow** - Organized intermediate files  
✅ **Final Output Clear** - Individual files are the end result  

