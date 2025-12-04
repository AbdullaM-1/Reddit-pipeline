# Supabase Setup Guide

## Installation

1. Install the Supabase Python client:
```bash
pip install supabase
```

2. Add Supabase credentials to your `.env` file:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
```

## Database Setup

1. Open your Supabase project dashboard
2. Go to SQL Editor
3. Copy and paste the contents of `supabase_schema.sql`
4. Execute the SQL to create the table

## Schema

Single table `posts` with columns:
- `post_id` (VARCHAR) - Reddit post ID (unique)
- `post_id_hash` (VARCHAR) - SHA256 hash of post_id (auto-generated)
- `title` (TEXT) - Post title
- `correct_link` (TEXT) - Identified correct link
- `post_date` (TIMESTAMPTZ) - Date of post
- `created_at` (TIMESTAMPTZ) - When record was created
- `updated_at` (TIMESTAMPTZ) - When record was last updated

## Usage

```python
from supabase_client import get_supabase_client, post_exists, upsert_post, load_existing_post_ids
from datetime import datetime

client = get_supabase_client()

# Check if post exists
if post_exists("abc123", client):
    print("Post already exists")

# Insert or update post
upsert_post(
    post_id="abc123",
    title="My Post Title",
    correct_link="https://example.com/story",
    post_date=datetime(2024, 1, 15),
    client=client
)

# Load all existing post IDs
existing_ids = load_existing_post_ids(client)
```
