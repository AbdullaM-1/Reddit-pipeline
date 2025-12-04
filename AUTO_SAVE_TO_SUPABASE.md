# Automatic Save to Supabase - Implementation

## Overview

The pipeline now **automatically saves processed posts to Supabase database** after processing them. This ensures that every unique post that gets processed is immediately saved to your database.

## How It Works

### 1. Post Processing Flow

```
1. Fetch posts from Reddit
   ↓
2. Check if post exists (local files + Supabase)
   ↓
3. If new → Process post:
   ├─ Identify correct link
   ├─ Download images
   ├─ Run OCR
   └─ Save to local pipeline_results.json
   ↓
4. ✅ Automatically save to Supabase database
```

### 2. When Posts Are Saved

Posts are saved to Supabase in **all scenarios**:

- ✅ **Successfully processed** (has link + images + OCR)
- ✅ **No link found** (status: "no_link") - still recorded
- ✅ **No images found** (status: "no_images") - link is saved

### 3. What Gets Saved

For each processed post, the following is saved to Supabase:

| Field | Description | Source |
|-------|-------------|--------|
| `post_id` | Reddit post ID | From Reddit post data |
| `title` | Post title | From Reddit post data |
| `correct_link` | Identified link from author's comment | From processing result |
| `post_date` | Date of the post | Extracted from `created_utc` timestamp |

## Implementation Details

### Function: `save_post_to_supabase()`

Located in `run_full_pipeline.py` (line ~186)

**Features:**
- Automatically extracts post date from `created_utc` timestamp
- Handles missing dates gracefully (falls back to current time)
- Uses upsert (insert or update) to prevent duplicates
- Provides clear error messages if Supabase is unavailable

**Code location:**
```python
def save_post_to_supabase(
    post_id: str,
    title: str,
    correct_link: str | None,
    post_date: datetime | None,
    post_data: RedditPost | None = None
) -> bool
```

### Integration Points

1. **After successful processing** (line ~1158):
   - Post has link, images, and OCR results
   - Saves with all data

2. **When no link found** (line ~1139):
   - Still saves to record that post was processed
   - `correct_link` is `None`

3. **When no images found** (line ~1150):
   - Saves with the identified link
   - `correct_link` has value but no images

## Benefits

✅ **Automatic**: No manual upload needed  
✅ **Immediate**: Posts saved right after processing  
✅ **Complete**: All processed posts are recorded  
✅ **Safe**: Uses upsert to prevent duplicates  
✅ **Resilient**: Continues even if Supabase save fails

## Database Uniqueness

The database schema ensures no duplicates:

```sql
post_id VARCHAR(255) NOT NULL UNIQUE  -- Prevents duplicates
```

Even if we try to save the same post twice:
- First save: Inserts new record
- Second save: Updates existing record (upsert)

## Error Handling

If Supabase is unavailable:
- ✅ Pipeline continues processing
- ✅ Warning message is displayed
- ✅ Post is still saved to local `pipeline_results.json`
- ✅ Can be uploaded later using `upload_to_supabase.py`

## Example Output

When a post is successfully saved:

```
[SUPABASE] Saved post abc123 to database
```

If Supabase is unavailable:

```
Supabase client not available, skipping database save
```

## Next Steps

1. **Run the pipeline**:
   ```bash
   python run_full_pipeline.py --subreddit YourSubreddit --max-posts 100
   ```

2. **Check your Supabase database**:
   - All processed posts will be automatically saved
   - No manual upload needed!

3. **Monitor the output**:
   - Look for `[SUPABASE]` messages in the console
   - Each successful save will be confirmed

