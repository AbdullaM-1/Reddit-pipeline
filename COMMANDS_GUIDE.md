# Command Guide for Incremental Updates

## Default Command (New Sort - Recommended)

The script defaults to **"new" sort** which fetches the most recent posts:

```bash
python run_full_pipeline.py --subreddit SextStories --max-posts 100
```

This will:
- ✅ Fetch last 100 posts sorted by "new" (most recent first)
- ✅ Process them incrementally (batch by batch)
- ✅ Skip posts that already exist in database
- ✅ Save new posts to Supabase automatically

## Command Options for "New" Sort

### Basic Command (All Defaults)
```bash
python run_full_pipeline.py
```
- Subreddit: `SextStories` (default)
- Sort: `new` (default)
- Max posts: `100` (default)

### Specify Subreddit
```bash
python run_full_pipeline.py --subreddit YourSubredditName
```

### Specify Number of Recent Posts to Check
```bash
python run_full_pipeline.py --subreddit SextStories --max-posts 200
```

### Explicitly Set "New" Sort (same as default)
```bash
python run_full_pipeline.py --subreddit SextStories --sort new --max-posts 100
```

## Understanding the "After" Keyword (Pagination)

The `--resume-after` parameter allows you to continue fetching **after** a specific post. This is useful for:
- Resuming interrupted runs
- Fetching posts older than a specific point
- Continuing from where you left off

### How It Works

The script stores pagination state in `pagination_state.json`:
```json
{
  "subreddit": "SextStories",
  "sort": "new",
  "after": "t3_abc123xyz",
  "last_post_fullname": "t3_abc123xyz",
  "processed_posts": 50,
  "updated_at": "2024-01-15T10:30:00Z"
}
```

The `after` field is a Reddit cursor (fullname) that tells Reddit where to continue from.

### Resume from Specific Post

```bash
python run_full_pipeline.py --subreddit SextStories --resume-after t3_abc123xyz
```

This will:
- Start fetching posts **after** the post with ID `abc123xyz`
- Useful for continuing a previous run

### Resume from Stored State (Automatic)

The script automatically resumes from the last position if `pagination_state.json` exists:

```bash
python run_full_pipeline.py --subreddit SextStories
```

If the file exists with matching subreddit/sort, it continues from there.

### Start Fresh (Ignore Previous State)

To start fresh and fetch the newest posts (ignore saved state):

```bash
# Option 1: Delete the state file first
del pagination_state.json
python run_full_pipeline.py --subreddit SextStories

# Option 2: Use a different subreddit or sort (creates new state)
python run_full_pipeline.py --subreddit SextStories --sort new
```

## Common Use Cases

### 1. Daily Update (Fetch Latest Posts)

**Goal**: Check for new posts since last run

```bash
python run_full_pipeline.py --subreddit SextStories --max-posts 100 --sort new
```

**How it works**:
- Fetches last 100 posts from "new" sort
- Skips posts already in database
- Processes only new posts

### 2. Process More Posts

**Goal**: Check last 500 posts for any missed ones

```bash
python run_full_pipeline.py --subreddit SextStories --max-posts 500 --sort new
```

### 3. Resume Interrupted Run

**Goal**: Continue from where you left off

```bash
# Automatic resume (uses pagination_state.json)
python run_full_pipeline.py --subreddit SextStories

# Or manually specify post ID
python run_full_pipeline.py --subreddit SextStories --resume-after t3_xyz789
```

### 4. Start Fresh (Ignore Previous State)

**Goal**: Start from the absolute newest posts

```bash
# Delete state file first
del pagination_state.json

# Then run normally
python run_full_pipeline.py --subreddit SextStories --max-posts 100
```

## Other Sort Options

While "new" is recommended for incremental updates, you can use other sorts:

### Hot Posts
```bash
python run_full_pipeline.py --subreddit SextStories --sort hot --max-posts 100
```

### Top Posts
```bash
python run_full_pipeline.py --subreddit SextStories --sort top --max-posts 100
```

### Rising Posts
```bash
python run_full_pipeline.py --subreddit SextStories --sort rising --max-posts 100
```

**Note**: For incremental updates, **"new" sort is recommended** because:
- ✅ Posts are ordered by time (newest first)
- ✅ Easy to check for new posts
- ✅ Consistent ordering

## Complete Command with All Options

```bash
python run_full_pipeline.py \
    --subreddit SextStories \
    --sort new \
    --max-posts 100 \
    --workers 20 \
    --ocr-workers 45 \
    --resume-after t3_abc123
```

## Parameters Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--subreddit` | `SextStories` | Subreddit name to scrape |
| `--sort` | `new` | Sort order: `hot`, `new`, `top`, `rising`, `controversial` |
| `--max-posts` | `100` | Number of recent posts to fetch |
| `--workers` | `20` | Concurrent worker threads |
| `--ocr-workers` | `45` | Parallel OCR workers per post |
| `--resume-after` | `None` | Resume after specific post ID (fullname) |

## Incremental Update Strategy

For regular updates, use this approach:

1. **First Run**: Fetch recent posts
   ```bash
   python run_full_pipeline.py --subreddit SextStories --max-posts 100
   ```

2. **Daily Updates**: Check for new posts
   ```bash
   python run_full_pipeline.py --subreddit SextStories --max-posts 100
   ```
   - Script automatically skips existing posts
   - Only processes new ones

3. **Weekly Deep Check**: Check more posts
   ```bash
   python run_full_pipeline.py --subreddit SextStories --max-posts 500
   ```

## State File Management

### Location
`pagination_state.json` in the project root

### When It's Created
- Automatically created/updated after each run
- Stores the last cursor position

### When It's Used
- Automatically loaded on next run
- Used to continue from last position

### When to Delete It
- Start fresh (fetch newest posts)
- Change subreddit or sort permanently
- State file is corrupted

## Troubleshooting

### Want to Start Fresh?

```bash
# Delete state file
del pagination_state.json

# Run normally
python run_full_pipeline.py --subreddit SextStories
```

### Want to Continue from Specific Point?

```bash
# Use resume-after with post fullname
python run_full_pipeline.py --subreddit SextStories --resume-after t3_postid123
```

### State File Not Working?

```bash
# Check if file exists
dir pagination_state.json

# Delete and restart
del pagination_state.json
python run_full_pipeline.py --subreddit SextStories
```

