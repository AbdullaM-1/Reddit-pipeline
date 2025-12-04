# Pipeline Supabase Integration Explanation

## How Post ID Uniqueness Works

### Database Level (Automatic)
The Supabase database schema (`supabase_schema.sql`) ensures uniqueness at the database level:

```sql
post_id VARCHAR(255) NOT NULL UNIQUE,
post_id_hash VARCHAR(64) NOT NULL UNIQUE,
```

- **`post_id UNIQUE`**: PostgreSQL prevents duplicate `post_id` values
- **`post_id_hash UNIQUE`**: The hash index also ensures uniqueness and provides fast lookups

If you try to insert a duplicate `post_id`, PostgreSQL will reject it automatically.

### Application Level (Checking Before Processing)

The `run_full_pipeline.py` script checks for existing posts **before processing** them to avoid unnecessary work:

#### Step 1: Load Local File IDs (Fast)
```python
existing_post_ids = load_all_existing_post_ids()
```
- Loads post IDs from local files (`pipeline_results.json`, `posts.json`)
- This is fast because files are on disk
- **Does NOT load all IDs from Supabase** - that would be slow

#### Step 2: Check Each Post Individually
For each post fetched from Reddit:

1. **Check local files first** (already loaded in memory)
   ```python
   if post_id in existing_post_ids:
       skip this post
   ```

2. **Check Supabase individually** (only if not in local files)
   ```python
   if check_post_exists_in_supabase(post_id):
       skip this post
   ```
   - Uses `post_exists()` function which queries Supabase using the hash index
   - Fast O(1) lookup using `post_id_hash`
   - Only checks posts that aren't in local files

#### Why This Approach?

- **Efficient**: We don't load ALL post IDs from Supabase into memory
- **Fast**: Uses hash index for database lookups
- **Safe**: Database UNIQUE constraint prevents duplicates even if we miss a check
- **Scalable**: Works even with millions of posts in database

## Flow Diagram

```
1. Fetch recent posts from Reddit (e.g., last 100 posts)
   ↓
2. Load existing IDs from local files (fast)
   ↓
3. For each fetched post:
   ├─ Check if in local files → Skip if yes
   └─ Check Supabase individually → Skip if yes
   ↓
4. Process only new posts (not in local files OR Supabase)
   ↓
5. Save results to:
   ├─ Local pipeline_results.json
   └─ Supabase database (with UNIQUE constraint protection)
```

## Database Schema Uniqueness Features

1. **UNIQUE constraint on `post_id`**: Prevents duplicates at database level
2. **UNIQUE constraint on `post_id_hash`**: Ensures hash uniqueness + fast lookups
3. **Index on `post_id_hash`**: Makes existence checks very fast
4. **Index on `post_id`**: Allows direct lookups by post_id

## Summary

- ✅ **Database enforces uniqueness** automatically via UNIQUE constraints
- ✅ **Script checks before processing** to avoid unnecessary work
- ✅ **Efficient approach** - only checks posts we actually fetched, not all posts
- ✅ **Safe** - even if check fails, database will prevent duplicates

