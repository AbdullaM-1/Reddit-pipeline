-- Simple Supabase PostgreSQL Schema for Reddit Scraper
-- Single table with post_id, title, correct_link, and date

CREATE TABLE IF NOT EXISTS posts (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Reddit post ID (unique identifier from Reddit)
    post_id VARCHAR(255) NOT NULL UNIQUE,
    
    -- Hashed post_id for fast lookups
    post_id_hash VARCHAR(64) NOT NULL UNIQUE,
    
    -- Post title from Reddit
    title TEXT NOT NULL,
    
    -- Identified correct link from author's comment
    correct_link TEXT,
    
    -- Date of post (timestamp)
    post_date TIMESTAMPTZ NOT NULL,
    
    -- Created at timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Updated at timestamp
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index on hashed post_id for fast lookups
CREATE INDEX IF NOT EXISTS idx_posts_post_id_hash ON posts(post_id_hash);

-- Create index on post_id for direct lookups
CREATE INDEX IF NOT EXISTS idx_posts_post_id ON posts(post_id);

-- Create index on post_date for time-based queries
CREATE INDEX IF NOT EXISTS idx_posts_post_date ON posts(post_date DESC);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at on row updates
CREATE TRIGGER update_posts_updated_at 
    BEFORE UPDATE ON posts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to generate and store hash when post_id is inserted/updated
CREATE OR REPLACE FUNCTION generate_post_id_hash()
RETURNS TRIGGER AS $$
BEGIN
    -- Generate SHA256 hash of post_id
    NEW.post_id_hash = encode(digest(NEW.post_id, 'sha256'), 'hex');
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically hash post_id on insert/update
CREATE TRIGGER generate_posts_post_id_hash
    BEFORE INSERT OR UPDATE OF post_id ON posts
    FOR EACH ROW
    EXECUTE FUNCTION generate_post_id_hash();
