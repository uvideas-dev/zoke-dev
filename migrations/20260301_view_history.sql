-- Migration to add unseen-only feed and saving functionality

-- Create joke_views table to track seen jokes
CREATE TABLE IF NOT EXISTS joke_views (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joke_id UUID NOT NULL REFERENCES jokes(id) ON DELETE CASCADE,
    viewed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, joke_id)
);

-- Index for performance on feed generation
CREATE INDEX IF NOT EXISTS idx_joke_views_user ON joke_views(user_id);

-- Note: saved_jokes table should already exist from previous steps, 
-- but here is the schema just in case:
-- CREATE TABLE IF NOT EXISTS saved_jokes (
--     user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
--     joke_id UUID NOT NULL REFERENCES jokes(id) ON DELETE CASCADE,
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
--     PRIMARY KEY (user_id, joke_id)
-- );
