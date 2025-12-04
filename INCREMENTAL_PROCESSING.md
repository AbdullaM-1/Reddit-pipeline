# Incremental Batch Processing

## What Changed?

The pipeline now processes posts **incrementally batch-by-batch** instead of fetching all posts at once.

### Before (Batch Approach)
```
1. Fetch ALL 100 posts from Reddit (multiple API calls)
2. Collect all posts into memory
3. Filter all posts
4. Process all new posts
```

**Problems:**
- High memory usage (all posts in memory at once)
- Long wait time before any processing starts
- All-or-nothing approach

### After (Incremental Approach)
```
1. Fetch first batch of posts (e.g., 25 posts from one JSON response)
2. Filter that batch immediately
3. Process new posts from that batch
4. Fetch next batch
5. Filter next batch
6. Process new posts from next batch
7. Repeat until max_posts limit reached
```

**Benefits:**
- ✅ Lower memory usage (only one batch in memory at a time)
- ✅ Processing starts immediately
- ✅ Real-time progress updates
- ✅ More efficient for large datasets

## How It Works

### Processing Flow

```
┌─────────────────────────────────────────┐
│ Start Pipeline                          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Fetch Batch 1 (e.g., 25 posts)         │
│ from Reddit API                         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Filter Batch 1:                         │
│ - Check against local files             │
│ - Check against Supabase                │
│ - Identify new posts                    │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Process new posts from Batch 1:         │
│ - Identify correct link                 │
│ - Download images                       │
│ - Run OCR                               │
│ - Save to Supabase                      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Fetch Batch 2 (next 25 posts)          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Filter Batch 2                          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Process new posts from Batch 2          │
└──────────────┬──────────────────────────┘
               │
               ▼
         Continue until
         max_posts reached
```

## Example Output

```
Starting incremental processing from r/SextStories...
Will process posts as they are fetched (batch by batch)

============================================================
Batch 1: Fetched 25 posts
============================================================

Checking batch 1 against existing database...
Skipping post abc123 - already exists in Supabase
Skipping post def456 - already exists in Supabase
Batch 1 filtered: 5 new posts, 20 skipped

Processing 5 new posts from batch 1...
[Processing messages...]
Completed batch 1: 5 posts processed

============================================================
Batch 2: Fetched 25 posts
============================================================

Checking batch 2 against existing database...
Batch 2 filtered: 8 new posts, 17 skipped

Processing 8 new posts from batch 2...
[Processing messages...]
Completed batch 2: 8 posts processed

...

Total fetched: 100 posts from Reddit
Pipeline update complete. Processed 15 new posts, skipped 85 existing posts
```

## Configuration

### Batch Size

The batch size is determined by Reddit API limits:
- **Authenticated requests**: Up to 100 posts per batch
- **Anonymous requests**: Up to 25 posts per batch

The pipeline automatically uses the maximum available based on your authentication status.

### Max Posts Parameter

```bash
python run_full_pipeline.py --subreddit YourSubreddit --max-posts 100
```

The `--max-posts` parameter limits:
- Total number of posts **fetched** from Reddit
- Processing continues for all new posts within that limit

## Memory Efficiency

### Memory Usage Comparison

| Approach | Memory Usage | Processing Start |
|----------|--------------|------------------|
| **Old (batch)** | High (all posts) | After all fetched |
| **New (incremental)** | Low (one batch) | Immediately |

### Example Memory Footprint

For 100 posts:
- **Old approach**: ~50-100 MB (all posts in memory)
- **New approach**: ~5-10 MB (one batch at a time)

## Benefits

✅ **Immediate Processing**: Start processing as soon as first batch arrives  
✅ **Lower Memory**: Only one batch in memory at a time  
✅ **Real-time Progress**: See progress after each batch  
✅ **Better Error Recovery**: If one batch fails, others continue  
✅ **Scalable**: Works efficiently even with thousands of posts  

## Technical Details

### Batch Processing Logic

1. **Stream Generator**: Uses Python generators to yield batches lazily
2. **Immediate Filtering**: Each batch is filtered as soon as it arrives
3. **Concurrent Processing**: Uses ThreadPoolExecutor for parallel processing within each batch
4. **Incremental Updates**: Database and local files updated after each batch

### Code Structure

```python
for batch in stream_full_post_batches(...):
    # Filter batch
    new_posts = filter_batch(batch)
    
    # Process immediately
    process_batch_concurrently(new_posts)
    
    # Continue to next batch
```

## Migration Notes

No changes needed to your workflow! The incremental processing is automatic and transparent. Just run the pipeline as usual:

```bash
python run_full_pipeline.py --subreddit YourSubreddit --max-posts 100
```

The pipeline now processes posts more efficiently while maintaining the same functionality.

