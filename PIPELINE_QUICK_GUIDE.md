# Full Pipeline - Quick Guide

## What It Does (One Sentence)

The pipeline fetches Reddit posts, extracts text from images, processes them, and outputs individual files to S3 bucket.

## Complete Flow (12 Steps)

```
1. FETCH POSTS
   ↓ Fetch from Reddit API
   
2. FILTER NEW POSTS  
   ↓ Check against database, skip duplicates
   
3. IDENTIFY LINKS
   ↓ Find correct link from author comment
   
4. DOWNLOAD IMAGES
   ↓ Download all images from link
   
5. EXTRACT TEXT (OCR)
   ↓ Run OCR on images, extract text
   
6. SAVE TO DATABASE
   ↓ Save to Supabase PostgreSQL
   
7. DELETE IMAGES
   ↓ Clean up downloaded images
   
8. AGGREGATE RESULTS
   ↓ Save to pipeline_results.json
   
9. CLEAN DATA
   ↓ Remove duplicates, fix order
   
10. FLATTEN DATA
    ↓ Simplify structure
   
11. SPLIT FILES
    ↓ One file per post with metadata
   
12. UPLOAD TO S3
    ↓ Upload to s3://reddit-sextstories/posts/
```

## Input

- **Subreddit name** (e.g., "SextStories")
- **Number of posts** to fetch (e.g., 100)

## Output

**Final Result:** Individual JSON files in S3 bucket

- **Location:** `s3://reddit-sextstories/posts/`
- **Format:** `{post_id},{title},{correct_link}.json`
- **Content:** Metadata + OCR text from images

## What Each Step Does

### 1. Fetch Posts
- Gets recent posts from Reddit
- Processes in batches

### 2. Filter New Posts  
- Checks: "Have we seen this post before?"
- Skips duplicates
- Only processes new posts

### 3. Identify Links
- Finds links in author's comment
- Uses AI to pick the correct one

### 4. Download Images
- Gets all images from the link
- Saves them temporarily

### 5. Extract Text (OCR)
- Reads text from images
- Combines text from all images

### 6. Save to Database
- Saves post info to Supabase
- Prevents duplicates

### 7. Delete Images
- Removes downloaded images
- Frees disk space

### 8. Aggregate Results
- Collects all processed posts
- Saves to JSON file

### 9. Clean Data
- Removes duplicates
- Fixes order

### 10. Flatten Data
- Simplifies structure
- Essential fields only

### 11. Split Files
- One file per post
- Metadata in filename

### 12. Upload to S3
- Uploads all files to S3
- Ready for use

## Example Run

```bash
python run_full_pipeline.py --subreddit SextStories --max-posts 100
```

**What Happens:**
1. Fetches 100 posts from Reddit
2. Filters: 80 already exist → Skip
3. Processes: 20 new posts
   - Download images
   - Extract text
   - Save to database
4. Cleans and organizes data
5. Splits into 20 individual files
6. Uploads to S3

**Result:** 20 JSON files in S3 bucket

## Key Features

✅ **Automatic** - Everything runs automatically  
✅ **Smart** - Skips duplicates automatically  
✅ **Efficient** - Only processes new posts  
✅ **Clean** - Removes temporary files  
✅ **Organized** - Well-structured output  
✅ **Cloud-Ready** - Uploads to S3 automatically  

## Final Output Structure

Each file in S3:
```
Filename: 1pdgyr2,Family_Traditions_Chapter_2,imgchest.com_p_abc123.json

Content:
{
  "metadata": {
    "post_id": "1pdgyr2",
    "title": "Family Traditions (Chapter 2)",
    "correct_link": "https://imgchest.com/p/abc123",
    "status": "success"
  },
  "content": "Full OCR text extracted from images..."
}
```

## Summary

**Start:** Reddit posts  
**End:** Organized JSON files in S3 bucket  
**Process:** Fully automated, 12 steps  
**Result:** Ready for knowledge bases, search, or processing!

