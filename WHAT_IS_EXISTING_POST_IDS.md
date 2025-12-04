# What is `existing_post_ids`?

## Answer: It's LOCAL (in-memory), NOT a database!

`existing_post_ids` is a **Python set** that lives only in your computer's memory during the script execution. It's NOT saved to a database.

## What It Does

### 1. **Loaded from Local Files** (at start)
- Reads `pipeline_results.json` file
- Reads `posts.json` file
- Creates a set of post IDs from these files

### 2. **Updated During Runtime** (in-memory)
- When we check Supabase for a post, we add it to the set
- When we process a new post, we add it to the set after saving
- Only exists while the script is running

### 3. **Used for Fast Lookups**
- Quick check: "Have we seen this post ID before?"
- Avoids duplicate processing within the same run
- Not persistent - disappears when script ends

## Where Data Is Actually Saved

### Database (Supabase):
- Function: `save_post_to_supabase()`
- Saves: `post_id`, `title`, `correct_link`, `post_date`
- Location: Supabase PostgreSQL database
- Persistent: ✅ Yes, saved permanently

### Local Files:
- File: `pipeline_results/pipeline_results.json`
- Saves: Full processing results (link, images, OCR, etc.)
- Location: Your computer's hard drive
- Persistent: ✅ Yes, saved to disk

## Summary

| Item | Type | Location | Persistent? |
|------|------|----------|-------------|
| `existing_post_ids` | Python set | RAM (memory) | ❌ No - disappears when script ends |
| Supabase database | PostgreSQL | Cloud database | ✅ Yes - permanent |
| `pipeline_results.json` | JSON file | Local hard drive | ✅ Yes - permanent |

## Code Location

```python
# Line 1342: Creates the set from local files
existing_post_ids = load_all_existing_post_ids()  # Returns a Python set

# This is just a set in memory:
# existing_post_ids = {"post1", "post2", "post3"}  # Not a database!

# Actual database saving happens here (line 1185):
save_post_to_supabase(...)  # This saves to Supabase database
```

## Key Point

- `existing_post_ids` = Temporary tracking (local, in-memory)
- `save_post_to_supabase()` = Actual database save (Supabase, permanent)

The set is just for tracking during the run. The database save happens separately!

