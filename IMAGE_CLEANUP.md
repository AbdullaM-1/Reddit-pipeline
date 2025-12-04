# Image Cleanup After Processing

## What It Does

The pipeline now **automatically deletes downloaded images** after processing them. This saves disk space since images are only needed temporarily for OCR processing.

## How It Works

### 1. **Download Phase**
- Images are downloaded to: `downloaded_images/{post_id}/`
- Example: `downloaded_images/1pdgyr2/image1.jpg`

### 2. **Processing Phase**
- OCR extracts text from images
- Results are saved to `pipeline_results.json`
- Data is saved to Supabase database

### 3. **Cleanup Phase** (After Processing)
- All downloaded images are deleted
- Empty post directory is removed
- Disk space is freed

## When Cleanup Happens

Images are deleted **after**:
- ✅ OCR processing is complete
- ✅ Results are saved to `pipeline_results.json`
- ✅ Data is saved to Supabase database

This ensures data is safe before cleanup.

## Code Location

**Cleanup Function:** `cleanup_images()` (line 1111)

**Called After:**
- Successful OCR processing (line 1239)
- Data saved to database

## Example Output

```
[DOWNLOADED] Post 1pdgyr2: Family Traditions (Chapter 2) - downloaded 5 images, starting OCR...
OCR summary: 5 images, 120 lines, 3500 chars
[CLEANUP] Deleted 5 images for post 1pdgyr2
[CLEANUP] Deleted empty directory: downloaded_images/1pdgyr2
[COMPLETE] Post 1pdgyr2: Family Traditions (Chapter 2) - processing complete
```

## Benefits

✅ **Saves Disk Space** - Images don't accumulate on disk  
✅ **Automatic** - No manual cleanup needed  
✅ **Safe** - Only deletes after data is saved  
✅ **Efficient** - Keeps disk usage minimal  

## What Gets Deleted

- ✅ All image files in the post directory
- ✅ Empty post directories (if all images deleted)

## What's Preserved

- ✅ OCR text results (in pipeline_results.json)
- ✅ Post data (in Supabase database)
- ✅ All processing results

## Summary

Images are downloaded → Processed → **Deleted automatically** → Only text/data is kept!

