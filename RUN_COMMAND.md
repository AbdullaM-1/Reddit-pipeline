# Command to Run the Full Pipeline

## Basic Command (Recommended)

```bash
python run_full_pipeline.py --subreddit SextStories --max-posts 100
```

This will:
- Fetch 100 recent posts from "SextStories" subreddit
- Process only new posts (skip duplicates)
- Save to Supabase database
- Clean and flatten data
- Split into individual files
- Upload to S3 bucket (if configured)

## Common Variations

### Different Number of Posts
```bash
# Fetch 50 posts
python run_full_pipeline.py --subreddit SextStories --max-posts 50

# Fetch 200 posts
python run_full_pipeline.py --subreddit SextStories --max-posts 200
```

### Different Subreddit
```bash
python run_full_pipeline.py --subreddit YourSubreddit --max-posts 100
```

### Default Settings (No Arguments)
```bash
python run_full_pipeline.py
```

Defaults:
- Subreddit: `SextStories`
- Max posts: `100`
- Sort: `new`

## Full Command with All Options

```bash
python run_full_pipeline.py \
  --subreddit SextStories \
  --max-posts 100 \
  --sort new \
  --workers 20 \
  --ocr-workers 45
```

## Parameters Explained

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--subreddit` | `SextStories` | Name of subreddit to fetch |
| `--max-posts` | `100` | Number of posts to fetch |
| `--sort` | `new` | Sort order (new/hot/top) |
| `--workers` | `20` | Concurrent processing threads |
| `--ocr-workers` | `45` | Parallel OCR threads per post |

## Example Output

After running, you'll see:
```
Starting pipeline update mode: fetching recent posts and processing only new ones
Found 50 existing posts in local files
Batch 1: Fetched 25 posts
[SKIP] Post abc123 - already exists
[NEW] Post xyz789 - will be processed
...
✓✓✓ PIPELINE COMPLETE ✓✓✓
Final output: Individual post files in directory:
pipeline_results/posts_20240115_143022/
Files uploaded to S3 bucket: reddit-sextstories
```

## Quick Start

**Just run this:**
```bash
python run_full_pipeline.py --subreddit SextStories --max-posts 100
```

Everything else happens automatically! 🚀

