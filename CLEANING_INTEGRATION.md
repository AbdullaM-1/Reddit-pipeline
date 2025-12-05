# Cleaning Scripts Integration

## Overview

The cleaning functionality from `clean_pipeline_data.py` has been integrated directly into `run_full_pipeline.py`. Now the pipeline automatically cleans and flattens the results after processing completes.

## What Gets Cleaned

### 1. **Data Cleaning**
- Removes duplicate post IDs
- Fixes order of posts
- Validates post data structure
- Creates cleaned version: `pipeline_results/pipeline_results.cleaned.json`

### 2. **Data Flattening**
- Simplifies data structure to essential fields only:
  - `post_id`
  - `title`
  - `status`
  - `correct_link`
  - `ocr_text` (aggregated from all images)
- Creates flattened version: `pipeline_results/pipeline_results.cleaned.flat.json`

## When Cleaning Runs

Cleaning runs **automatically** after all processing is complete:
1. Pipeline fetches and processes posts
2. Results are saved to `pipeline_results.json`
3. **Cleaning starts automatically**
4. Cleaned and flattened files are created

## Integrated Functions

The following functions from `clean_pipeline_data.py` are now in `run_full_pipeline.py`:

### Core Functions
- `normalize_path()` - Normalizes file paths for comparison
- `text_from_extraction()` - Extracts text from OCR results
- `aggregate_post_text()` - Combines all OCR text from images in order
- `rebuild_order()` - Removes duplicates from order list
- `build_clean_payload()` - Cleans and deduplicates pipeline results
- `build_flat_posts()` - Flattens data to simple structure
- `run_cleaning_steps()` - Orchestrates the cleaning process

## Output Files

After running the pipeline, you'll have:

1. **`pipeline_results/pipeline_results.json`**
   - Raw aggregated results from processing

2. **`pipeline_results/pipeline_results.cleaned.json`**
   - Cleaned version with duplicates removed
   - Fixed order
   - Same structure as original

3. **`pipeline_results/pipeline_results.cleaned.flat.json`**
   - Simplified flattened structure
   - Only essential fields
   - Perfect for uploads or further processing

## Example Output

```
Pipeline update complete. Processed 10 new posts, skipped 5 existing posts from SextStories.

Starting data cleaning and flattening...
Loading pipeline results from pipeline_results/pipeline_results.json...
Cleaning pipeline results (removing duplicates, fixing order)...
Cleaned payload written to: pipeline_results/pipeline_results.cleaned.json
Creating flattened dataset...
Flattened dataset written to: pipeline_results/pipeline_results.cleaned.flat.json (15 entries)

Cleaning Summary:
  Total posts: 15
  Status breakdown:
    success          10
    no_link          3
    no_images        2
Data cleaning complete!
```

## Benefits

✅ **Automatic** - No manual cleaning step needed  
✅ **Consistent** - Same cleaning logic every time  
✅ **Efficient** - Runs only after processing completes  
✅ **Safe** - Creates new files, doesn't overwrite originals  
✅ **Integrated** - Part of the pipeline workflow  

## Usage

Just run the pipeline as normal:

```bash
python run_full_pipeline.py --subreddit SextStories --limit 100
```

Cleaning happens automatically at the end!

## Manual Cleaning (Optional)

If you need to re-run cleaning on existing data, you can still use:

```bash
python clean_pipeline_data.py --input pipeline_results/pipeline_results.json
```

But it's no longer necessary since cleaning is integrated into the pipeline.

