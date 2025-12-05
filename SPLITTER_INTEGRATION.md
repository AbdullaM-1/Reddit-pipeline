# Post Splitter Integration

## Overview

The post splitter from `utils/split_posts_into_files.py` has been integrated into `run_full_pipeline.py`. It automatically splits each post into individual files with a metadata convention after cleaning and flattening.

## What It Does

After cleaning and flattening, the splitter:

1. **Takes the flattened JSON** (`pipeline_results.cleaned.flat.json`)
2. **Splits each post** into a separate file
3. **Uses metadata convention**: Each file contains:
   - `metadata` object with all post fields (except `ocr_text`)
   - `content` field with the OCR text
4. **File naming**: `{post_id},{title},{correct_link}.json`

## File Structure

Each individual post file has this structure:

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

## Output Location

Posts are saved to:
- **Directory**: `pipeline_results/posts_{timestamp}/`
- **Example**: `pipeline_results/posts_20240115_143022/`
- Each run creates a new timestamped directory

## When It Runs

The splitter runs automatically at the end of the pipeline:

1. ✅ Processing posts
2. ✅ Cleaning results
3. ✅ Flattening data
4. ✅ **Splitting into individual files** ← Automatic!

## Integration Points

### Functions Added

1. **`sanitize_filename_for_splitter()`** - Sanitizes filenames for filesystem safety
2. **`split_posts_into_individual_files()`** - Main splitting logic

### Called In

- **`run_cleaning_steps()`** - After flattening completes
- Runs automatically when cleaning is done

## Example Output

```
Flattened dataset written to: pipeline_results/pipeline_results.cleaned.flat.json (150 entries)

Cleaning Summary:
  Total posts: 150
  Status breakdown:
    success          120
    no_link          20
    no_images        10

Splitting posts into individual files...
Loading flattened data from pipeline_results/pipeline_results.cleaned.flat.json...
Total posts to split: 150
Output directory: pipeline_results/posts_20240115_143022

[50/150] Saved 50 posts...
[100/150] Saved 100 posts...
[150/150] Saved 150 posts...

Successfully saved 150 posts to individual files
Output directory: pipeline_results/posts_20240115_143022
Each post has 1 file: {post_id},{title},{correct_link}.json (contains content + metadata)
Post splitting complete!
```

## Benefits

✅ **Automatic** - Runs at the end of pipeline  
✅ **Metadata Convention** - Structured for knowledge bases  
✅ **Individual Files** - Easy to process/manage  
✅ **Safe Filenames** - Sanitized for filesystem  
✅ **No Overwrites** - Skips existing files  
✅ **Progress Tracking** - Shows progress every 50 files  

## Usage

Just run the pipeline normally - splitting happens automatically!

```bash
python run_full_pipeline.py --subreddit SextStories --limit 100
```

The splitter will run automatically after cleaning and flattening.

## Manual Splitting (Optional)

If you need to re-split existing flattened data:

```bash
python utils/split_posts_into_files.py --input pipeline_results/pipeline_results.cleaned.flat.json
```

But it's no longer necessary since splitting is integrated into the pipeline!

