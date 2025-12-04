# Quick Start Commands

## Most Common Commands

### 1. Basic Update (Recommended for Daily Use)
```bash
python run_full_pipeline.py --subreddit SextStories --max-posts 100
```
- Fetches last 100 posts from "new" sort
- Processes only new posts (skips existing)
- Saves to Supabase automatically

### 2. Update More Posts
```bash
python run_full_pipeline.py --subreddit SextStories --max-posts 200
```

### 3. Start Fresh (Clear Previous State)
```bash
del pagination_state.json
python run_full_pipeline.py --subreddit SextStories --max-posts 100
```

### 4. Resume from Specific Post
```bash
python run_full_pipeline.py --subreddit SextStories --resume-after t3_postid123
```

## Default Values

If you run without parameters:
```bash
python run_full_pipeline.py
```

**Default settings:**
- Subreddit: `SextStories`
- Sort: `new` (most recent first)
- Max posts: `100`
- Workers: `20`
- OCR workers: `45`

## The "After" Keyword Explained

The `--resume-after` parameter lets you continue fetching **after** a specific post ID.

**Example:**
```bash
python run_full_pipeline.py --subreddit SextStories --resume-after t3_abc123xyz
```

This tells Reddit: "Give me posts that come after post ID `abc123xyz`"

**When to use it:**
- Resume interrupted run
- Continue from a known point
- Fetch older posts beyond a certain point

**Automatic resume:**
The script automatically saves your position in `pagination_state.json` and resumes from there on the next run.

## For Incremental Updates (Your Use Case)

**Daily update command:**
```bash
python run_full_pipeline.py --subreddit SextStories --max-posts 100 --sort new
```

This will:
1. Fetch last 100 posts sorted by "new"
2. Check each against database
3. Process only new posts
4. Skip existing ones
5. Save to Supabase

**To check more posts weekly:**
```bash
python run_full_pipeline.py --subreddit SextStories --max-posts 500
```

