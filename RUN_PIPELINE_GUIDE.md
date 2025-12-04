# How to Run the Full Pipeline Script

## Basic Command

The simplest way to run the script with default settings:

```bash
python run_full_pipeline.py
```

**Default settings:**
- Subreddit: `SextStories`
- Sort: `new` (most recent posts)
- Max posts: `100` (fetches last 100 posts)
- Workers: `20` concurrent threads
- OCR workers: `45` parallel OCR threads

## Common Usage Examples

### 1. Run with default subreddit (SextStories)
```bash
python run_full_pipeline.py
```

### 2. Specify a different subreddit
```bash
python run_full_pipeline.py --subreddit YourSubredditName
```

### 3. Fetch more posts (e.g., last 200 posts)
```bash
python run_full_pipeline.py --subreddit YourSubredditName --max-posts 200
```

### 4. Fetch fewer posts (e.g., last 50 posts)
```bash
python run_full_pipeline.py --subreddit YourSubredditName --max-posts 50
```

### 5. Use different sort order
```bash
python run_full_pipeline.py --subreddit YourSubredditName --sort hot
```
Available sort options: `hot`, `new`, `top`, `rising`, `controversial`

### 6. Adjust worker threads (for slower/faster processing)
```bash
# Fewer workers (less CPU usage)
python run_full_pipeline.py --subreddit YourSubredditName --workers 10

# More workers (faster processing, more CPU)
python run_full_pipeline.py --subreddit YourSubredditName --workers 30
```

### 7. Adjust OCR workers (for image processing speed)
```bash
# Fewer OCR workers
python run_full_pipeline.py --subreddit YourSubredditName --ocr-workers 20

# More OCR workers
python run_full_pipeline.py --subreddit YourSubredditName --ocr-workers 60
```

### 8. Complete example with all options
```bash
python run_full_pipeline.py \
    --subreddit SextStories \
    --max-posts 150 \
    --workers 25 \
    --ocr-workers 50 \
    --sort new
```

## What the Script Does

1. ✅ Loads existing post IDs from:
   - Local `pipeline_results.json` file
   - Local `posts.json` file
   - Supabase database (checks individually per post)

2. ✅ Fetches recent posts from Reddit (sorted by "new" by default)

3. ✅ Filters out posts that already exist in the database

4. ✅ Processes only new posts:
   - Identifies correct link from author's comment
   - Downloads images from that link
   - Runs OCR on images
   - Saves results to `pipeline_results/pipeline_results.json`

## Full List of Options

| Option | Default | Description |
|--------|---------|-------------|
| `--subreddit` | `SextStories` | Name of the subreddit to scrape |
| `--sort` | `new` | Sort order: `hot`, `new`, `top`, `rising`, `controversial` |
| `--max-posts` | `100` | Number of recent posts to fetch and check |
| `--workers` | `20` | Number of concurrent worker threads |
| `--ocr-workers` | `45` | Number of parallel OCR worker threads per post |
| `--fetch-all` | `False` | Fetch all posts (not recommended for updates) |
| `--resume-after` | `None` | Resume after a specific post ID |

## Important Notes

⚠️ **For incremental updates** (recommended):
- Use `--sort new` (default) to get the most recent posts
- Use `--max-posts` to limit how many to check (default: 100)
- The script automatically skips posts that already exist

⚠️ **Do NOT use** `--fetch-all` for regular updates - it will fetch ALL posts which is slow and unnecessary!

## Example: Running from PowerShell (Windows)

```powershell
cd "C:\Users\AL FATAH LAPTOP\Desktop\Google ads api\google-ads-app\reddit-scraper"
python run_full_pipeline.py --subreddit SextStories --max-posts 100
```

## Troubleshooting

### Script not found
Make sure you're in the correct directory:
```bash
cd "C:\Users\AL FATAH LAPTOP\Desktop\Google ads api\google-ads-app\reddit-scraper"
```

### Python not found
Try:
```bash
python3 run_full_pipeline.py
# or
py run_full_pipeline.py
```

### Missing dependencies
Install requirements:
```bash
pip install -r requirements.txt
```

