# Complete Full Pipeline Explanation

## Overview

The full pipeline is an **automated end-to-end system** that fetches Reddit posts, processes them, extracts text from images, and outputs organized files ready for storage and use.

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     FULL PIPELINE FLOW                          │
└─────────────────────────────────────────────────────────────────┘

1. FETCH POSTS FROM REDDIT
   ↓
   - Fetch recent posts from subreddit (sorted by "new")
   - Process in batches (e.g., 25 posts per batch)
   - Always starts from the beginning (freshest posts)
   ↓
2. FILTER NEW POSTS
   ↓
   - Check against local files (fast lookup)
   - Check against Supabase database (per-post check)
   - Skip posts that already exist
   ↓
3. IDENTIFY CORRECT LINKS
   ↓
   - Extract links from author's comment
   - Use LLM to identify correct link
   - Store identified link
   ↓
4. DOWNLOAD IMAGES
   ↓
   - Extract image URLs from the correct link
   - Download all images to local storage
   - Store image metadata
   ↓
5. EXTRACT TEXT (OCR)
   ↓
   - Run OCR on downloaded images (EasyOCR or pytesseract)
   - Extract text from all images in order
   - Combine text from multiple images
   ↓
6. SAVE TO SUPABASE
   ↓
   - Save post_id, title, correct_link, post_date
   - Use hash index for fast lookups
   ↓
7. DELETE IMAGES
   ↓
   - Clean up downloaded images after OCR
   - Remove empty directories
   - Free disk space
   ↓
8. AGGREGATE RESULTS
   ↓
   - Save to pipeline_results/pipeline_results.json
   - Update after each post is processed
   ↓
9. CLEAN DATA
   ↓
   - Remove duplicate post IDs
   - Fix order of posts
   - Validate data structure
   ↓
10. FLATTEN DATA
   ↓
   - Simplify to essential fields only
   - Aggregate all OCR text per post
   - Create simplified structure
   ↓
11. SPLIT INTO INDIVIDUAL FILES
   ↓
   - Split each post into separate file
   - Filename: {post_id},{title},{correct_link}.json
   - Structure: metadata + content
   ↓
12. UPLOAD TO S3 BUCKET
   ↓
   - Upload all split files to S3
   - Path: s3://reddit-sextstories/posts/
   - Progress tracking
   ↓
    FINAL OUTPUT: Individual files in S3 bucket
```

## Detailed Step-by-Step Breakdown

### Step 1: Fetch Posts from Reddit

**What it does:**
- Connects to Reddit API
- Fetches posts from specified subreddit (e.g., "SextStories")
- Uses "new" sort to get freshest posts first
- Processes in batches (25 posts per batch by default)

**Output:** List of post objects from Reddit

---

### Step 2: Filter New Posts

**What it does:**
- Loads existing post IDs from:
  - Local files: `pipeline_results.json`, `posts.json`
  - Supabase database (per-post check)
- Compares each fetched post against existing ones
- Skips posts that already exist
- Only processes truly new posts

**Why:** Avoids duplicate work, saves time and resources

**Output:** Filtered list of new posts to process

---

### Step 3: Identify Correct Links

**What it does:**
- Analyzes author's comment in the post
- Extracts all URLs from the comment
- Uses LLM (OpenAI) to identify the correct link
- Stores the identified link for each post

**Output:** Correct link URL for each post

---

### Step 4: Download Images

**What it does:**
- Visits the correct link URL
- Scrapes HTML for image URLs
- Downloads all images found
- Stores images in: `downloaded_images/{post_id}/`

**Output:** Local image files ready for OCR

---

### Step 5: Extract Text (OCR)

**What it does:**
- Runs OCR on each downloaded image
- Uses EasyOCR (or pytesseract as fallback)
- Extracts text from all images
- Combines text in correct order
- Processes multiple images in parallel

**Output:** Complete OCR text extracted from images

---

### Step 6: Save to Supabase Database

**What it does:**
- Saves essential data to PostgreSQL database:
  - `post_id` (hashed for fast lookup)
  - `title`
  - `correct_link`
  - `post_date`
- Uses hash index for efficient queries
- Prevents duplicates

**Output:** Post saved in Supabase database

---

### Step 7: Delete Images (Cleanup)

**What it does:**
- Deletes all downloaded images after OCR is complete
- Removes empty post directories
- Frees up disk space

**Why:** Images are temporary, only text is needed

**Output:** Clean disk (images removed)

---

### Step 8: Aggregate Results

**What it does:**
- Saves complete processing results to:
  - `pipeline_results/pipeline_results.json`
- Updates file after each post is processed
- Maintains order and metadata

**Output:** Aggregated JSON file with all processed posts

---

### Step 9: Clean Data

**What it does:**
- Loads aggregated results
- Removes duplicate post IDs
- Fixes order of posts
- Validates data structure
- Saves cleaned version

**Output:** `pipeline_results/pipeline_results.cleaned.json`

---

### Step 10: Flatten Data

**What it does:**
- Simplifies data structure to essential fields:
  - `post_id`
  - `title`
  - `status`
  - `correct_link`
  - `ocr_text` (all text aggregated)
- Removes nested/complex structures
- Creates flat, simple format

**Output:** `pipeline_results/pipeline_results.cleaned.flat.json`

---

### Step 11: Split Into Individual Files

**What it does:**
- Takes flattened JSON
- Splits each post into separate file
- **Filename format:** `{post_id},{title},{correct_link}.json`
- **File structure:**
  ```json
  {
    "metadata": {
      "post_id": "...",
      "title": "...",
      "correct_link": "...",
      "status": "..."
    },
    "content": "Full OCR text..."
  }
  ```
- Creates directory: `pipeline_results/posts_{timestamp}/`

**Output:** Individual JSON files, one per post

---

### Step 12: Upload to S3 Bucket

**What it does:**
- Uploads all split files to S3
- Uses configured bucket: `reddit-sextstories`
- Uses prefix: `posts/`
- Uploads to: `s3://reddit-sextstories/posts/{filename}.json`
- Shows progress every 50 files
- Handles errors gracefully

**Output:** Files in S3 bucket ready for use

---

## Complete Example Flow

### Input
```
Subreddit: SextStories
Limit: 100 posts
```

### Processing
```
1. Fetch 100 recent posts from Reddit
2. Filter: 80 already exist, 20 are new
3. Process 20 new posts:
   - Identify links → 18 found, 2 failed
   - Download images → 150 images total
   - Extract OCR → 15,000 characters of text
   - Save to Supabase → 20 posts saved
   - Delete images → 150 files deleted
4. Clean data → Remove duplicates, fix order
5. Flatten data → Simplify structure
6. Split files → 20 individual JSON files
7. Upload to S3 → 20 files uploaded
```

### Final Output
```
S3 Location: s3://reddit-sextstories/posts/

Files:
- 1pdgyr2,Family_Traditions_Chapter_2,imgchest.com_p_abc123.json
- 2abc123,Another_Story_Part_1,imgchest.com_p_def456.json
- ... (18 more files)
```

## Key Features

### ✅ Incremental Processing
- Processes batches one at a time
- No need to load all posts into memory
- Efficient resource usage

### ✅ Duplicate Prevention
- Checks local files first (fast)
- Checks Supabase database (accurate)
- Skips already processed posts

### ✅ Automatic Cleanup
- Images deleted after OCR
- Disk space freed automatically
- Clean working directory

### ✅ Data Organization
- Cleaned and validated
- Flattened for easy access
- Split into individual files
- Ready for knowledge bases

### ✅ Cloud Storage
- Automatic S3 upload
- Organized with prefix
- Progress tracking
- Error handling

## Output Locations

### Local Files
1. `pipeline_results/pipeline_results.json` - Raw aggregated results
2. `pipeline_results/pipeline_results.cleaned.json` - Cleaned version
3. `pipeline_results/pipeline_results.cleaned.flat.json` - Flattened version
4. `pipeline_results/posts_{timestamp}/` - Individual split files

### Database
- Supabase PostgreSQL: `posts` table
  - `post_id` (hashed)
  - `title`
  - `correct_link`
  - `post_date`

### Cloud Storage
- S3 Bucket: `s3://reddit-sextstories/posts/`
  - Individual JSON files
  - Metadata in filename
  - Ready for processing

## Running the Pipeline

```bash
python run_full_pipeline.py --subreddit SextStories --max-posts 100
```

### What Happens Automatically
1. ✅ Fetches posts from Reddit
2. ✅ Filters new posts
3. ✅ Processes each new post
4. ✅ Saves to Supabase
5. ✅ Cleans up images
6. ✅ Cleans and flattens data
7. ✅ Splits into individual files
8. ✅ Uploads to S3 bucket

**Everything runs automatically - no manual steps needed!**

## Summary

The full pipeline is a **complete automated system** that:
- Fetches Reddit posts
- Processes only new ones
- Extracts text from images
- Organizes data efficiently
- Stores in database and cloud
- Outputs ready-to-use files

The final result: **Individual JSON files in S3 bucket** with all extracted content, ready for knowledge bases, search, or further processing!

