# Upload to Supabase Script

This script uploads posts from the pipeline results JSON file to your Supabase database.

## Prerequisites

1. Make sure you have the Supabase schema set up (run `supabase_schema.sql`)
2. Install dependencies: `pip install supabase python-dotenv colorama`
3. Your `.env` file should have:
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   # OR
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
   ```

## Usage

```bash
python upload_to_supabase.py
```

The script will:
1. Load the JSON file from: `C:\Users\AL FATAH LAPTOP\Desktop\pipeline_results\pipeline_results_merged.cleaned.flat.with_ocr.json`
2. Extract all posts from the JSON
3. Upload each post to Supabase with:
   - `post_id` (with automatic hashing)
   - `title`
   - `correct_link`
   - `post_date` (extracted from various possible fields)

## What it does

- Automatically extracts post dates from various JSON field names
- Uses upsert (insert or update) so running it multiple times is safe
- Shows progress and summary statistics
- Handles different JSON structures (dictionary of posts, array of posts, etc.)

## Output

The script will show:
- ✓ Successfully uploaded posts
- ⚠ Failed uploads
- Summary statistics at the end

