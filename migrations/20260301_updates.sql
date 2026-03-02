-- Migration to add unseen-only feed, saving functionality, and share/reaction tracking

-- Create joke_views table to track seen jokes
CREATE TABLE IF NOT EXISTS joke_views (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joke_id UUID NOT NULL REFERENCES jokes(id) ON DELETE CASCADE,
    viewed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, joke_id)
);

-- Index for performance on feed generation
CREATE INDEX IF NOT EXISTS idx_joke_views_user ON joke_views(user_id);

-- Add share tracking to jokes
ALTER TABLE jokes ADD COLUMN IF NOT EXISTS shares_count INTEGER DEFAULT 0;

-- Add emoji reaction tracks to rezokes
ALTER TABLE rezokes ADD COLUMN IF NOT EXISTS funny_count INTEGER DEFAULT 0;
ALTER TABLE rezokes ADD COLUMN IF NOT EXISTS not_funny_count INTEGER DEFAULT 0;

-- Note: saved_jokes table should already exist
CREATE TABLE IF NOT EXISTS saved_jokes (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joke_id UUID NOT NULL REFERENCES jokes(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, joke_id)
);
